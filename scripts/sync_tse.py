#!/usr/bin/env python3
"""Baixa e recorta os metadados oficiais do PesqEle/TSE usados no Pulso 26."""

from __future__ import annotations

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
PROTOCOLS = {
    "BR010842026",
    "BR011662026",
    "BR014892026",
    "BR028742026",
    "BR044882026",
    "BR045792026",
    "BR065912026",
    "BR065962026",
    "BR067732026",
    "BR068682026",
    "BR069352026",
    "BR078452026",
    "BR080452026",
    "BR081092026",
    "BR084282026",
    "BR086022026",
}
OUTPUT = Path(__file__).resolve().parents[1] / "data" / "tse-metadata.json"


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "Pulso26/1.0 (+dados eleitorais abertos)"})
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
    return "" if value == "#NULO#" else " ".join(value.split())


def money(value: str) -> float:
    return float(value.replace(".", "").replace(",", "."))


def main() -> int:
    package = json.loads(fetch(PACKAGE_API).decode("utf-8"))["result"]
    resources = package["resources"]
    polls_url = find_resource(resources, "pesquisa_eleitoral_2026.zip")
    contractors_url = find_resource(resources, "pesquisa_contratante_2026.zip")

    polls = national_rows(fetch(polls_url), "pesquisa_eleitoral_2026_BRASIL.csv")
    contractors = national_rows(fetch(contractors_url), "pesquisa_contratante_2026_BRASIL.csv")
    poll_rows = {row["NR_PROTOCOLO_REGISTRO"]: row for row in polls if row["NR_PROTOCOLO_REGISTRO"] in PROTOCOLS}
    contractor_rows: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in contractors:
        if row["NR_PROTOCOLO_REGISTRO"] in PROTOCOLS:
            contractor_rows[row["NR_PROTOCOLO_REGISTRO"]].append(row)

    missing = sorted(PROTOCOLS - poll_rows.keys())
    if missing:
        raise RuntimeError(f"Protocolos ausentes no arquivo oficial: {', '.join(missing)}")

    records: dict[str, dict] = {}
    for protocol in sorted(PROTOCOLS):
        row = poll_rows[protocol]
        records[protocol] = {
            "protocol": protocol,
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
            "contractors": [
                {
                    "name": clean(contractor["NM_CONTRATANTE"]),
                    "amount": money(contractor["VR_PAGO_CONTRATANTE"]),
                    "payer": contractor["ST_CONTRATANTE_PAGANTE"] == "S",
                    "resourceOrigin": clean(contractor["DS_ORIGEM_RECURSO"]),
                }
                for contractor in contractor_rows[protocol]
            ],
        }

    first = next(iter(poll_rows.values()))
    payload = {
        "generatedAt": f"{first['DT_GERACAO']} {first['HH_GERACAO']}",
        "syncedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "source": DATASET_URL,
        "pesqEle": PESQELE_URL,
        "resourceUrls": {"polls": polls_url, "contractors": contractors_url},
        "records": records,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(records)} registros gravados em {OUTPUT}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"Erro: {error}", file=sys.stderr)
        raise SystemExit(1)
