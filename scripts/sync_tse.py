#!/usr/bin/env python3
"""Sincroniza recortes oficiais do TSE e monitora registros por eleição."""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
import time
import urllib.error
import urllib.request
import zipfile
from collections import defaultdict
from datetime import datetime
from pathlib import Path


PACKAGE_API = "https://dadosabertos.tse.jus.br/api/3/action/package_show?id=pesquisas-eleitorais-2026"
DATASET_URL = "https://dadosabertos.tse.jus.br/dataset/pesquisas-eleitorais-2026"
PESQELE_URL = "https://pesqele-divulgacao.tse.jus.br/app/pesquisa/listar.xhtml"
POLLS_ZIP_URL = "https://cdn.tse.jus.br/estatistica/sead/odsele/pesquisa_eleitoral/pesquisa_eleitoral_2026.zip"
CONTRACTORS_ZIP_URL = "https://cdn.tse.jus.br/estatistica/sead/odsele/pesquisa_eleitoral/pesquisa_contratante_2026.zip"
PRESIDENTIAL_MIRROR_URL = (
    "https://huggingface.co/datasets/AFOS-Analytics1/brazil-2026-electoral-divergence/"
    "resolve/main/polls/tse-registry.csv"
)
ROOT = Path(__file__).resolve().parents[1]
ELECTIONS_FILE = ROOT / "data" / "elections.json"
POLLS_FILE = ROOT / "data" / "polls.json"
METADATA_OUTPUT = ROOT / "data" / "tse-metadata.json"
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
    "Referer": DATASET_URL,
    "Origin": "https://dadosabertos.tse.jus.br",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--bootstrap-monitor",
        action="store_true",
        help="reinicializa todos os monitores com o catálogo atual, sem criar pendências",
    )
    parser.add_argument(
        "--bootstrap-sp-monitor",
        action="store_true",
        help="inicializa somente o monitor de São Paulo (compatibilidade)",
    )
    parser.add_argument(
        "--bootstrap-target",
        action="append",
        default=[],
        metavar="CHAVE",
        help="inicializa somente o monitor identificado pela chave tse.key do catálogo",
    )
    parser.add_argument("--summary", type=Path, help="grava o resumo presidencial (compatibilidade)")
    parser.add_argument("--summary-president", type=Path, help="grava o resumo presidencial")
    parser.add_argument("--summary-sp", type=Path, help="grava o resumo de São Paulo")
    parser.add_argument("--summary-dir", type=Path, help="grava um resumo por eleição neste diretório")
    parser.add_argument("--issue-manifest", type=Path, help="grava o manifesto das filas editoriais")
    parser.add_argument("--github-output", type=Path, help="acrescenta resultados ao GITHUB_OUTPUT")
    return parser.parse_args()


def fetch(url: str, attempts: int = 3) -> bytes:
    request = urllib.request.Request(url, headers=BROWSER_HEADERS)
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return response.read()
        except urllib.error.HTTPError as error:
            if error.code not in {429, 500, 502, 503, 504} or attempt == attempts:
                raise
        except urllib.error.URLError:
            if attempt == attempts:
                raise
        time.sleep(2 ** (attempt - 1))
    raise RuntimeError(f"Não foi possível baixar {url}")


def find_resource(resources: list[dict], filename: str) -> str:
    for resource in resources:
        if resource.get("url", "").endswith(filename):
            return resource["url"]
    raise RuntimeError(f"Recurso {filename} não encontrado no catálogo do TSE")


def resolve_resource_urls() -> tuple[str, str]:
    try:
        package = json.loads(fetch(PACKAGE_API).decode("utf-8"))["result"]
        resources = package["resources"]
        return (
            find_resource(resources, "pesquisa_eleitoral_2026.zip"),
            find_resource(resources, "pesquisa_contratante_2026.zip"),
        )
    except (OSError, ValueError, KeyError, RuntimeError) as error:
        print(
            f"Aviso: catálogo CKAN indisponível ({error}); usando URLs canônicas do CDN do TSE.",
            file=sys.stderr,
        )
        return POLLS_ZIP_URL, CONTRACTORS_ZIP_URL


def national_rows(zip_bytes: bytes, filename: str) -> list[dict[str, str]]:
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        member = next((name for name in archive.namelist() if name.endswith(filename)), None)
        if not member:
            raise RuntimeError(f"Arquivo {filename} não encontrado no ZIP")
        with archive.open(member) as raw:
            text = io.TextIOWrapper(raw, encoding="latin-1", newline="")
            return list(csv.DictReader(text, delimiter=";"))


def presidential_mirror_rows(csv_bytes: bytes) -> list[dict[str, str]]:
    """Converte o espelho presidencial diário para o esquema do CSV oficial."""
    generated = datetime.now().astimezone()
    aliases = {
        "NR_PROTOCOLO_REGISTRO": "register_tse",
        "DT_REGISTRO": "registration_date",
        "ST_PESQUISA_PROPRIA": "own_poll",
        "NR_CNPJ_EMPRESA": "cnpj",
        "NM_EMPRESA": "institute",
        "NM_EMPRESA_FANTASIA": "institute_trade_name",
        "DS_CARGO": "office",
        "DT_INICIO_PESQUISA": "field_start",
        "DT_FIM_PESQUISA": "field_end",
        "DT_DIVULGACAO": "publication_date",
        "QT_ENTREVISTADO": "sample_size",
        "CD_CONRE": "conre",
        "NM_ESTATISTICO_RESP": "statistician",
        "VR_PESQUISA": "cost_brl",
        "DS_METODOLOGIA_PESQUISA": "methodology",
        "DS_PLANO_AMOSTRAL": "sampling_plan",
    }
    source = csv.DictReader(io.StringIO(csv_bytes.decode("utf-8-sig")))
    rows: list[dict[str, str]] = []
    for item in source:
        # O espelho inclui registros presidenciais com amostra restrita a uma UF.
        # Eles não são comparáveis ao retrato nacional exibido pelo site.
        if item.get("scope", "").strip().lower() == "state":
            continue
        row = {target: item.get(source_name, "") for target, source_name in aliases.items()}
        row.update({
            "SG_UE": "BR",
            "NM_UE": "BRASIL",
            "DT_GERACAO": generated.date().isoformat(),
            "HH_GERACAO": generated.strftime("%H:%M:%S"),
        })
        if row["NR_PROTOCOLO_REGISTRO"]:
            rows.append(row)
    if not rows:
        raise RuntimeError("O espelho presidencial não retornou registros")
    return rows


def iso_date(value: str) -> str:
    if not value or value == "#NULO#":
        return ""
    return datetime.strptime(value[:10], "%Y-%m-%d").date().isoformat()


def clean(value: str) -> str:
    return "" if not value or value == "#NULO#" else " ".join(value.split())


def money(value: str) -> float:
    if not value or value == "#NULO#":
        return 0.0
    return float(value.replace(".", "").replace(",", "."))


def source_generated_at(rows: list[dict[str, str]]) -> str:
    if not rows:
        return ""
    return f"{rows[0]['DT_GERACAO']} {rows[0]['HH_GERACAO']}"


def curated_protocols(path: Path = POLLS_FILE) -> set[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    protocols = {poll["protocol"] for poll in payload.get("polls", [])}
    if not protocols:
        raise RuntimeError(f"Nenhum protocolo curado foi encontrado em {path.relative_to(ROOT)}")
    return protocols


def configured_exclusions(tse: dict) -> set[str]:
    """Retorna protocolos revisados que não pertencem à série configurada."""
    exclusions = tse.get("excludedProtocols", [])
    if not isinstance(exclusions, list):
        raise RuntimeError("excludedProtocols deve ser uma lista")

    protocols: set[str] = set()
    for item in exclusions:
        if not isinstance(item, dict) or not item.get("protocol"):
            raise RuntimeError("Cada exclusão deve informar protocol, reason e source")
        if not item.get("reason") or not item.get("source"):
            raise RuntimeError(f"Exclusão incompleta para {item['protocol']}")
        protocol = str(item["protocol"])
        if protocol in protocols:
            raise RuntimeError(f"Protocolo excluído em duplicidade: {protocol}")
        protocols.add(protocol)
    return protocols


def presidential_rows(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return office_rows(rows, "BR", "Presidente")


def office_rows(
    rows: list[dict[str, str]],
    jurisdiction: str,
    office: str,
) -> dict[str, dict[str, str]]:
    return {
        row["NR_PROTOCOLO_REGISTRO"]: row
        for row in rows
        if row.get("SG_UE") == jurisdiction and office in row.get("DS_CARGO", "")
    }


def contractor_index(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    indexed: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        indexed[row["NR_PROTOCOLO_REGISTRO"]].append(row)
    return indexed


def contractor_payload(rows: list[dict[str, str]]) -> list[dict]:
    return [
        {
            "name": clean(row["NM_CONTRATANTE"]),
            "amount": money(row["VR_PAGO_CONTRATANTE"]),
            "payer": row["ST_CONTRATANTE_PAGANTE"] == "S",
            "resourceOrigin": clean(row["DS_ORIGEM_RECURSO"]),
        }
        for row in rows
    ]


def metadata_record(row: dict[str, str], contractors: list[dict[str, str]]) -> dict:
    return {
        "protocol": row["NR_PROTOCOLO_REGISTRO"],
        "registeredAt": row["DT_REGISTRO"],
        "fieldStart": iso_date(row["DT_INICIO_PESQUISA"]),
        "fieldEnd": iso_date(row["DT_FIM_PESQUISA"]),
        "disclosureDate": iso_date(row["DT_DIVULGACAO"]),
        "sample": int(row["QT_ENTREVISTADO"]),
        "company": clean(row["NM_EMPRESA"]),
        "tradeName": clean(row["NM_EMPRESA_FANTASIA"]),
        "statistician": clean(row["NM_ESTATISTICO_RESP"]),
        "conre": clean(row["CD_CONRE"]),
        "researchCost": money(row["VR_PESQUISA"]),
        "methodology": clean(row["DS_METODOLOGIA_PESQUISA"]),
        "samplingPlan": clean(row["DS_PLANO_AMOSTRAL"]),
        "contractors": contractor_payload(contractors),
    }


def monitor_record(row: dict[str, str], contractors: list[dict[str, str]]) -> dict:
    return {
        "protocol": row["NR_PROTOCOLO_REGISTRO"],
        "registeredAt": row["DT_REGISTRO"],
        "fieldStart": iso_date(row["DT_INICIO_PESQUISA"]),
        "fieldEnd": iso_date(row["DT_FIM_PESQUISA"]),
        "disclosureDate": iso_date(row["DT_DIVULGACAO"]),
        "sample": int(row["QT_ENTREVISTADO"]),
        "company": clean(row["NM_EMPRESA"]),
        "tradeName": clean(row["NM_EMPRESA_FANTASIA"]),
        "contractors": [clean(item["NM_CONTRATANTE"]) for item in contractors],
    }


def read_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def update_metadata(
    poll_rows: dict[str, dict[str, str]],
    contractors: dict[str, list[dict[str, str]]],
    protocols: set[str],
    generated_at: str,
    resource_urls: dict[str, str],
    output_path: Path = METADATA_OUTPUT,
    preserve_contractors: bool = False,
    allow_partial: bool = False,
) -> bool:
    missing = sorted(protocols - poll_rows.keys())
    if missing and not allow_partial:
        raise RuntimeError(f"Protocolos ausentes no arquivo oficial: {', '.join(missing)}")

    current = read_json(output_path)
    if missing and allow_partial and current:
        return False
    current_records = current.get("records", {}) if current else {}
    records: dict[str, dict] = {}
    for protocol in sorted(protocols):
        if protocol not in poll_rows:
            if protocol in current_records:
                records[protocol] = current_records[protocol]
            continue
        contractor_rows = contractors.get(protocol, [])
        record = metadata_record(poll_rows[protocol], contractor_rows)
        if preserve_contractors and not contractor_rows:
            record["contractors"] = current_records.get(protocol, {}).get("contractors", [])
        records[protocol] = record
    core = {
        "source": DATASET_URL,
        "pesqEle": PESQELE_URL,
        "resourceUrls": resource_urls,
        "records": records,
    }
    if current and all(current.get(key) == value for key, value in core.items()):
        return False

    payload = {
        "generatedAt": current.get("generatedAt", generated_at) if missing and current else generated_at,
        "syncedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        **core,
    }
    write_json(output_path, payload)
    return True


def build_monitor(
    existing: dict | None,
    poll_rows: dict[str, dict[str, str]],
    contractors: dict[str, list[dict[str, str]]],
    protocols: set[str],
    generated_at: str,
    bootstrap: bool,
    review_since: str = "",
) -> tuple[dict, list[str], bool]:
    if review_since:
        try:
            datetime.strptime(review_since, "%Y-%m-%d")
        except ValueError as error:
            raise RuntimeError(f"reviewSince inválido: {review_since}") from error
    reviewable_protocols = {
        protocol
        for protocol, row in poll_rows.items()
        if review_since and iso_date(row.get("DT_DIVULGACAO", "")) >= review_since
    }
    current_protocols = set(poll_rows)
    if bootstrap:
        seen = current_protocols
        pending: dict[str, dict] = {}
        new_protocols: list[str] = []
    else:
        if existing is None:
            raise RuntimeError("Monitor ainda não inicializado; execute uma vez com --bootstrap-monitor")
        previous_seen = set(existing.get("seenProtocols", []))
        seen = previous_seen | current_protocols
        new_protocols = sorted(current_protocols - previous_seen)
        pending = dict(existing.get("pending", {}))
        for protocol in sorted(set(new_protocols) | reviewable_protocols):
            if protocol not in protocols:
                pending[protocol] = monitor_record(poll_rows[protocol], contractors.get(protocol, []))

        for protocol in list(pending):
            if protocol in protocols:
                pending.pop(protocol)
            elif protocol in poll_rows:
                pending[protocol] = monitor_record(poll_rows[protocol], contractors.get(protocol, []))

    queue_changed = (
        existing is None
        or sorted(existing.get("seenProtocols", [])) != sorted(seen)
        or existing.get("pending", {}) != dict(sorted(pending.items()))
    )
    payload = {
        "schemaVersion": 1,
        "source": DATASET_URL,
        "sourceGeneratedAt": generated_at,
        "seenProtocols": sorted(seen),
        "pending": dict(sorted(pending.items())),
    }
    return payload, new_protocols, queue_changed


def markdown_escape(value: object) -> str:
    return str(value or "—").replace("|", "\\|").replace("\n", " ")


def write_summary(
    path: Path,
    monitor: dict,
    heading: str = "Pesquisas presidenciais aguardando revisão",
    database: str = "data/polls.json",
) -> None:
    pending = list(monitor.get("pending", {}).values())
    lines = [
        f"## {heading}",
        "",
        f"O monitor encontrou registros novos no PesqEle/TSE. Antes de publicar percentuais, confira o cenário e vincule uma fonte de resultados verificável em `{database}`.",
        "",
    ]
    if not pending:
        lines.append("Não há protocolos pendentes.")
    else:
        lines.extend([
            "| Protocolo | Instituto | Campo | Divulgação | Amostra | Contratante(s) |",
            "| --- | --- | --- | --- | ---: | --- |",
        ])
        for item in sorted(pending, key=lambda row: (row.get("disclosureDate", ""), row["protocol"]), reverse=True):
            company = item.get("tradeName") or item.get("company")
            field = f"{item.get('fieldStart') or '—'} a {item.get('fieldEnd') or '—'}"
            contractors = ", ".join(item.get("contractors", [])) or "—"
            lines.append(
                f"| {markdown_escape(item['protocol'])} | {markdown_escape(company)} | "
                f"{markdown_escape(field)} | {markdown_escape(item.get('disclosureDate'))} | "
                f"{markdown_escape(item.get('sample'))} | {markdown_escape(contractors)} |"
            )
    lines.extend(["", f"Fonte: [Dados Abertos do TSE]({DATASET_URL}).", ""])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_github_output(path: Path, values: dict[str, object]) -> None:
    with path.open("a", encoding="utf-8") as output:
        for key, value in values.items():
            output.write(f"{key}={str(value).lower() if isinstance(value, bool) else value}\n")


def main() -> int:
    args = parse_args()
    polls_url, contractors_url = resolve_resource_urls()

    mirror_mode = False
    try:
        all_polls = national_rows(fetch(polls_url), "pesquisa_eleitoral_2026_BRASIL.csv")
        all_contractors = national_rows(fetch(contractors_url), "pesquisa_contratante_2026_BRASIL.csv")
    except urllib.error.HTTPError as error:
        if error.code != 403:
            raise
        print(
            "Aviso: downloads do TSE bloqueados para o runner; usando o espelho presidencial diário.",
            file=sys.stderr,
        )
        all_polls = presidential_mirror_rows(fetch(PRESIDENTIAL_MIRROR_URL))
        all_contractors = []
        mirror_mode = True
    contractors = contractor_index(all_contractors)
    generated_at = source_generated_at(all_polls)
    resource_urls = {
        "polls": PRESIDENTIAL_MIRROR_URL if mirror_mode else polls_url,
        "contractors": "" if mirror_mode else contractors_url,
    }
    catalog = json.loads(ELECTIONS_FILE.read_text(encoding="utf-8"))
    elections = catalog.get("elections", [])
    if not elections:
        raise RuntimeError("Nenhuma eleição encontrada em data/elections.json")

    results: list[dict] = []
    outputs: dict[str, object] = {"source_generated_at": generated_at}
    bootstrap_targets = set(args.bootstrap_target)
    if args.bootstrap_sp_monitor:
        bootstrap_targets.add("sp")

    for election in elections:
        tse = election.get("tse")
        if not isinstance(tse, dict):
            raise RuntimeError(f"Configuração TSE ausente para {election.get('id', 'eleição sem ID')}")

        key = str(tse["key"])
        poll_path = ROOT / election["dataFile"]
        metadata_path = ROOT / election["metadataFile"]
        monitor_path = ROOT / election["monitorFile"]
        protocols = curated_protocols(poll_path)
        resolved_protocols = protocols | configured_exclusions(tse)
        if mirror_mode and key != "president":
            monitor = read_json(monitor_path)
            if monitor is None:
                raise RuntimeError(f"Monitor estadual ausente para {key}")
            summary_path = args.summary_dir / f"{key}.md" if args.summary_dir else None
            if key == "sp":
                summary_path = args.summary_sp or summary_path
            if summary_path:
                write_summary(summary_path, monitor, str(tse["issueHeading"]), str(election["dataFile"]))
            result = {
                "key": key,
                "label": election["context"],
                "issueTitle": tse["issueTitle"],
                "summaryFile": str(summary_path.resolve()) if summary_path else "",
                "metadataChanged": False,
                "monitorChanged": False,
                "queueChanged": False,
                "newCount": 0,
                "pendingCount": len(monitor["pending"]),
                "curatedCount": len(protocols),
                "monitoredCount": len(monitor["seenProtocols"]),
            }
            results.append(result)
            outputs.update({
                f"{key}_metadata_changed": False,
                f"{key}_monitor_changed": False,
                f"{key}_queue_changed": False,
                f"{key}_new_count": 0,
                f"{key}_pending_count": len(monitor["pending"]),
            })
            continue
        poll_rows = office_rows(all_polls, str(tse["jurisdiction"]), str(tse["office"]))
        metadata_changed = update_metadata(
            poll_rows,
            contractors,
            protocols,
            generated_at,
            resource_urls,
            metadata_path,
            preserve_contractors=mirror_mode,
            allow_partial=mirror_mode,
        )
        previous_monitor = read_json(monitor_path)
        monitor, new_protocols, queue_changed = build_monitor(
            previous_monitor,
            poll_rows,
            contractors,
            resolved_protocols,
            generated_at,
            args.bootstrap_monitor or key in bootstrap_targets,
            str(tse.get("reviewSince", "")),
        )
        monitor_changed = previous_monitor != monitor
        if monitor_changed:
            write_json(monitor_path, monitor)

        summary_path = args.summary_dir / f"{key}.md" if args.summary_dir else None
        if key == "president":
            summary_path = args.summary_president or args.summary or summary_path
        elif key == "sp":
            summary_path = args.summary_sp or summary_path
        if summary_path:
            write_summary(
                summary_path,
                monitor,
                str(tse["issueHeading"]),
                str(election["dataFile"]),
            )

        result = {
            "key": key,
            "label": election["context"],
            "issueTitle": tse["issueTitle"],
            "summaryFile": str(summary_path.resolve()) if summary_path else "",
            "metadataChanged": metadata_changed,
            "monitorChanged": monitor_changed,
            "queueChanged": queue_changed,
            "newCount": len(new_protocols),
            "pendingCount": len(monitor["pending"]),
            "curatedCount": len(protocols),
            "monitoredCount": len(poll_rows),
        }
        results.append(result)
        outputs.update({
            f"{key}_metadata_changed": metadata_changed,
            f"{key}_monitor_changed": monitor_changed,
            f"{key}_queue_changed": queue_changed,
            f"{key}_new_count": len(new_protocols),
            f"{key}_pending_count": len(monitor["pending"]),
        })

    outputs.update({
        "metadata_changed": any(item["metadataChanged"] for item in results),
        "monitor_changed": any(item["monitorChanged"] for item in results),
        "queue_changed": any(item.get("queueChanged", False) for item in results),
        "new_count": sum(item["newCount"] for item in results),
        "pending_count": sum(item["pendingCount"] for item in results),
    })
    if args.issue_manifest:
        write_json(args.issue_manifest, {"elections": results})
    if args.github_output:
        write_github_output(args.github_output, outputs)

    print("; ".join(
        f"{item['label']}: {item['curatedCount']} curados, {item['monitoredCount']} monitorados, "
        f"{item['newCount']} novos, {item['pendingCount']} pendentes"
        for item in results
    ))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"Erro: {error}", file=sys.stderr)
        raise SystemExit(1)
