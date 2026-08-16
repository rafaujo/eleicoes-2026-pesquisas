#!/usr/bin/env python3
"""Valida a base curada e sua consistência com o recorte oficial do TSE."""

from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
POLLS_FILE = ROOT / "data" / "polls.json"
METADATA_FILE = ROOT / "data" / "tse-metadata.json"
MONITOR_FILE = ROOT / "data" / "tse-monitor.json"
PROTOCOL_PATTERN = re.compile(r"^[A-Z]{2}\d{9}$")
REQUIRED_POLL_FIELDS = {
    "id",
    "pollster",
    "publication",
    "protocol",
    "start",
    "end",
    "field",
    "sample",
    "margin",
    "confidence",
    "method",
    "resultSource",
    "resultSourceLabel",
    "lula",
    "flavio",
    "caiado",
    "zema",
    "renan",
    "undecided",
}
RESULT_FIELDS = {"lula", "flavio", "caiado", "zema", "renan", "undecided"}
RUNOFF_FIELDS = {"lula", "flavio", "undecided"}
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


def duplicate_values(values: list[object]) -> list[object]:
    return sorted({value for value in values if values.count(value) > 1})


def valid_percentage(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and 0 <= value <= 100


def validate_poll(poll: object, position: int, errors: list[str]) -> None:
    label = f"Pesquisa #{position}"
    if not isinstance(poll, dict):
        errors.append(f"{label} não é um objeto")
        return

    missing = sorted(REQUIRED_POLL_FIELDS - set(poll))
    if missing:
        errors.append(f"{label} sem campos: {', '.join(missing)}")
        return

    label = f"Pesquisa {poll['protocol']}"
    if not isinstance(poll["id"], int) or poll["id"] <= 0:
        errors.append(f"{label} tem ID inválido")
    if not PROTOCOL_PATTERN.fullmatch(str(poll["protocol"])):
        errors.append(f"{label} tem protocolo inválido")
    if not str(poll["resultSource"]).startswith("https://"):
        errors.append(f"{label} precisa de fonte HTTPS")
    if not isinstance(poll["sample"], int) or poll["sample"] <= 0:
        errors.append(f"{label} tem amostra inválida")
    for field in ("start", "end"):
        try:
            date.fromisoformat(str(poll[field]))
        except ValueError:
            errors.append(f"{label} tem data inválida em {field}")
    if str(poll["start"]) > str(poll["end"]):
        errors.append(f"{label} termina antes do início do campo")
    for field in RESULT_FIELDS | {"margin", "confidence"}:
        if not valid_percentage(poll[field]):
            errors.append(f"{label} tem percentual inválido em {field}")

    runoff = poll.get("runoff")
    if runoff is not None:
        if not isinstance(runoff, dict):
            errors.append(f"{label} tem segundo turno inválido")
        else:
            missing_runoff = sorted(RUNOFF_FIELDS - set(runoff))
            if missing_runoff:
                errors.append(f"{label} sem campos de segundo turno: {', '.join(missing_runoff)}")
            for field in RUNOFF_FIELDS & set(runoff):
                if not valid_percentage(runoff[field]):
                    errors.append(f"{label} tem percentual inválido no segundo turno em {field}")


def main() -> int:
    errors: list[str] = []
    poll_data = json.loads(POLLS_FILE.read_text(encoding="utf-8"))
    if poll_data.get("schemaVersion") != 1:
        errors.append("Versão desconhecida de data/polls.json")
    election = poll_data.get("election", {})
    if election != {"year": 2026, "country": "BR", "office": "president", "jurisdiction": "BR"}:
        errors.append("Identificação eleitoral inválida em data/polls.json")
    polls = poll_data.get("polls")
    if not isinstance(polls, list) or not polls:
        errors.append("data/polls.json deve conter uma lista não vazia de pesquisas")
        polls = []

    for position, poll in enumerate(polls, start=1):
        validate_poll(poll, position, errors)

    ids = [poll.get("id") for poll in polls if isinstance(poll, dict)]
    protocols = [poll.get("protocol") for poll in polls if isinstance(poll, dict)]
    duplicate_protocols = duplicate_values(protocols)
    duplicate_ids = duplicate_values(ids)
    if duplicate_protocols:
        errors.append(f"Protocolos duplicados: {', '.join(map(str, duplicate_protocols))}")
    if duplicate_ids:
        errors.append(f"IDs duplicados: {', '.join(map(str, duplicate_ids))}")

    metadata = json.loads(METADATA_FILE.read_text(encoding="utf-8"))
    records = metadata.get("records", {})
    protocol_set = set(protocols)
    missing_records = sorted(protocol_set - set(records))
    extra_records = sorted(set(records) - protocol_set)
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
    overlap = sorted(protocol_set & set(pending))
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
        f"Dados válidos: {len(polls)} pesquisas curadas, "
        f"{len(seen)} protocolos monitorados e {len(pending)} pendentes"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
