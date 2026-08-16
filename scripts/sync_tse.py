#!/usr/bin/env python3
"""Sincroniza o recorte oficial do TSE e monitora novos registros presidenciais."""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
import urllib.request
import zipfile
from collections import defaultdict
from datetime import datetime
from pathlib import Path


PACKAGE_API = "https://dadosabertos.tse.jus.br/api/3/action/package_show?id=pesquisas-eleitorais-2026"
DATASET_URL = "https://dadosabertos.tse.jus.br/dataset/pesquisas-eleitorais-2026"
PESQELE_URL = "https://pesqele-divulgacao.tse.jus.br/app/pesquisa/listar.xhtml"
ROOT = Path(__file__).resolve().parents[1]
POLLS_FILE = ROOT / "data" / "polls.json"
METADATA_OUTPUT = ROOT / "data" / "tse-metadata.json"
MONITOR_OUTPUT = ROOT / "data" / "tse-monitor.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--bootstrap-monitor",
        action="store_true",
        help="registra o catálogo atual como linha de base, sem criar pendências",
    )
    parser.add_argument("--summary", type=Path, help="grava um resumo Markdown das pendências")
    parser.add_argument("--github-output", type=Path, help="acrescenta resultados ao GITHUB_OUTPUT")
    return parser.parse_args()


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "Pulso26/2.0 (+dados eleitorais abertos)"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def find_resource(resources: list[dict], filename: str) -> str:
    for resource in resources:
        if resource.get("url", "").endswith(filename):
            return resource["url"]
    raise RuntimeError(f"Recurso {filename} não encontrado no catálogo do TSE")


def national_rows(zip_bytes: bytes, filename: str) -> list[dict[str, str]]:
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        member = next((name for name in archive.namelist() if name.endswith(filename)), None)
        if not member:
            raise RuntimeError(f"Arquivo {filename} não encontrado no ZIP")
        with archive.open(member) as raw:
            text = io.TextIOWrapper(raw, encoding="latin-1", newline="")
            return list(csv.DictReader(text, delimiter=";"))


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


def curated_protocols() -> set[str]:
    payload = json.loads(POLLS_FILE.read_text(encoding="utf-8"))
    protocols = {poll["protocol"] for poll in payload.get("polls", [])}
    if not protocols:
        raise RuntimeError("Nenhum protocolo curado foi encontrado em data/polls.json")
    return protocols


def presidential_rows(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {
        row["NR_PROTOCOLO_REGISTRO"]: row
        for row in rows
        if row.get("SG_UE") == "BR" and "Presidente" in row.get("DS_CARGO", "")
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
) -> bool:
    missing = sorted(protocols - poll_rows.keys())
    if missing:
        raise RuntimeError(f"Protocolos ausentes no arquivo oficial: {', '.join(missing)}")

    records = {
        protocol: metadata_record(poll_rows[protocol], contractors.get(protocol, []))
        for protocol in sorted(protocols)
    }
    core = {
        "source": DATASET_URL,
        "pesqEle": PESQELE_URL,
        "resourceUrls": resource_urls,
        "records": records,
    }
    current = read_json(METADATA_OUTPUT)
    if current and all(current.get(key) == value for key, value in core.items()):
        return False

    payload = {
        "generatedAt": generated_at,
        "syncedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        **core,
    }
    write_json(METADATA_OUTPUT, payload)
    return True


def build_monitor(
    existing: dict | None,
    poll_rows: dict[str, dict[str, str]],
    contractors: dict[str, list[dict[str, str]]],
    protocols: set[str],
    generated_at: str,
    bootstrap: bool,
) -> tuple[dict, list[str], bool]:
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
        for protocol in new_protocols:
            if protocol not in protocols:
                pending[protocol] = monitor_record(poll_rows[protocol], contractors.get(protocol, []))

        for protocol in list(pending):
            if protocol in protocols:
                pending.pop(protocol)
            elif protocol in poll_rows:
                pending[protocol] = monitor_record(poll_rows[protocol], contractors.get(protocol, []))

    core_changed = (
        existing is None
        or sorted(existing.get("seenProtocols", [])) != sorted(seen)
        or existing.get("pending", {}) != dict(sorted(pending.items()))
    )
    payload = {
        "schemaVersion": 1,
        "source": DATASET_URL,
        "sourceGeneratedAt": generated_at if core_changed else existing.get("sourceGeneratedAt", generated_at),
        "seenProtocols": sorted(seen),
        "pending": dict(sorted(pending.items())),
    }
    return payload, new_protocols, core_changed


def markdown_escape(value: object) -> str:
    return str(value or "—").replace("|", "\\|").replace("\n", " ")


def write_summary(path: Path, monitor: dict) -> None:
    pending = list(monitor.get("pending", {}).values())
    lines = [
        "## Pesquisas presidenciais aguardando revisão",
        "",
        "O monitor encontrou registros nacionais novos no PesqEle/TSE. Antes de publicar percentuais, confira o cenário e vincule uma fonte de resultados verificável em `data/polls.json`.",
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
    package = json.loads(fetch(PACKAGE_API).decode("utf-8"))["result"]
    resources = package["resources"]
    polls_url = find_resource(resources, "pesquisa_eleitoral_2026.zip")
    contractors_url = find_resource(resources, "pesquisa_contratante_2026.zip")

    all_polls = national_rows(fetch(polls_url), "pesquisa_eleitoral_2026_BRASIL.csv")
    all_contractors = national_rows(fetch(contractors_url), "pesquisa_contratante_2026_BRASIL.csv")
    polls = presidential_rows(all_polls)
    contractors = contractor_index(all_contractors)
    protocols = curated_protocols()
    generated_at = source_generated_at(all_polls)

    metadata_changed = update_metadata(
        polls,
        contractors,
        protocols,
        generated_at,
        {"polls": polls_url, "contractors": contractors_url},
    )
    existing_monitor = read_json(MONITOR_OUTPUT)
    monitor, new_protocols, monitor_changed = build_monitor(
        existing_monitor,
        polls,
        contractors,
        protocols,
        generated_at,
        args.bootstrap_monitor,
    )
    if monitor_changed:
        write_json(MONITOR_OUTPUT, monitor)

    if args.summary:
        write_summary(args.summary, monitor)
    if args.github_output:
        write_github_output(args.github_output, {
            "metadata_changed": metadata_changed,
            "monitor_changed": monitor_changed,
            "new_count": len(new_protocols),
            "pending_count": len(monitor["pending"]),
            "source_generated_at": generated_at,
        })

    print(
        f"{len(protocols)} registros curados; {len(polls)} registros presidenciais monitorados; "
        f"{len(new_protocols)} novos; {len(monitor['pending'])} pendentes"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"Erro: {error}", file=sys.stderr)
        raise SystemExit(1)
