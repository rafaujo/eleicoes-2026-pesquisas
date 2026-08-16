#!/usr/bin/env python3
"""Valida a consistência entre os dados curados e o recorte oficial do TSE."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_FILE = ROOT / "app.js"
METADATA_FILE = ROOT / "data" / "tse-metadata.json"
MONITOR_FILE = ROOT / "data" / "tse-monitor.json"
PROTOCOL_PATTERN = re.compile(r'protocol:\s*"([A-Z]{2}\d{9})"')
ID_PATTERN = re.compile(r"\bid:\s*(\d+),\s*pollster:")
RESULT_SOURCE_PATTERN = re.compile(r'resultSource:\s*"(https://[^"]+)"')
REQUIRED_METADATA_FIELDS = {
    "protocol",
    "registeredAt",
    "fieldStart",
    "fieldEnd",
    "disclosureDate",
    "sample",
    "company",
    "methodology",
    "contractors",
}


def duplicate_values(values: list[str]) -> list[str]:
    return sorted({value for value in values if values.count(value) > 1})


def main() -> int:
    errors: list[str] = []
    app = APP_FILE.read_text(encoding="utf-8")
    protocols = PROTOCOL_PATTERN.findall(app)
    ids = ID_PATTERN.findall(app)
    sources = RESULT_SOURCE_PATTERN.findall(app)

    duplicate_protocols = duplicate_values(protocols)
    duplicate_ids = duplicate_values(ids)
    if duplicate_protocols:
        errors.append(f"Protocolos duplicados em app.js: {', '.join(duplicate_protocols)}")
    if duplicate_ids:
        errors.append(f"IDs duplicados em app.js: {', '.join(duplicate_ids)}")
    if len(sources) != len(protocols):
        errors.append(f"Há {len(protocols)} pesquisas, mas {len(sources)} fontes HTTPS")

    metadata = json.loads(METADATA_FILE.read_text(encoding="utf-8"))
    records = metadata.get("records", {})
    missing_records = sorted(set(protocols) - set(records))
    extra_records = sorted(set(records) - set(protocols))
    if missing_records:
        errors.append(f"Protocolos sem metadados do TSE: {', '.join(missing_records)}")
    if extra_records:
        errors.append(f"Metadados sem pesquisa curada: {', '.join(extra_records)}")
    for protocol, record in records.items():
        missing_fields = sorted(REQUIRED_METADATA_FIELDS - set(record))
        if missing_fields:
            errors.append(f"{protocol} sem campos: {', '.join(missing_fields)}")
        if record.get("protocol") != protocol:
            errors.append(f"Chave e protocolo divergem em {protocol}")
        if not isinstance(record.get("sample"), int) or record.get("sample", 0) <= 0:
            errors.append(f"Amostra inválida em {protocol}")

    monitor = json.loads(MONITOR_FILE.read_text(encoding="utf-8"))
    seen = monitor.get("seenProtocols", [])
    pending = monitor.get("pending", {})
    if monitor.get("schemaVersion") != 1:
        errors.append("Versão desconhecida de data/tse-monitor.json")
    if seen != sorted(set(seen)):
        errors.append("seenProtocols deve estar ordenado e sem duplicatas")
    overlap = sorted(set(protocols) & set(pending))
    if overlap:
        errors.append(f"Protocolos curados ainda estão pendentes: {', '.join(overlap)}")
    if not set(pending).issubset(set(seen)):
        errors.append("Há protocolos pendentes ausentes de seenProtocols")

    if errors:
        print("Falha na validação:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(
        f"Dados válidos: {len(protocols)} pesquisas curadas, "
        f"{len(seen)} protocolos monitorados e {len(pending)} pendentes"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
