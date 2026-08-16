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
    "scenarios",
}
REQUIRED_CANDIDATE_FIELDS = {"name", "shortName", "color"}
REQUIRED_SCENARIO_FIELDS = {"id", "round", "label", "candidates"}
HEX_COLOR_PATTERN = re.compile(r"^#[0-9a-fA-F]{6}$")
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


def validate_poll(
    poll: object,
    position: int,
    errors: list[str],
    scenario_catalog: dict[str, dict] | None = None,
) -> None:
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
    for field in ("margin", "confidence"):
        if not valid_percentage(poll[field]):
            errors.append(f"{label} tem percentual inválido em {field}")

    poll_scenarios = poll.get("scenarios")
    if not isinstance(poll_scenarios, dict) or not poll_scenarios:
        errors.append(f"{label} não possui cenários")
        return
    if "first-main" not in poll_scenarios:
        errors.append(f"{label} não possui o cenário principal")

    catalog = scenario_catalog or {}
    unknown = sorted(set(poll_scenarios) - set(catalog)) if catalog else []
    if unknown:
        errors.append(f"{label} possui cenários desconhecidos: {', '.join(unknown)}")
    for scenario_id, scenario_result in poll_scenarios.items():
        scenario_label = f"{label}, cenário {scenario_id}"
        if not isinstance(scenario_result, dict):
            errors.append(f"{scenario_label} é inválido")
            continue
        results = scenario_result.get("results")
        if not isinstance(results, dict):
            errors.append(f"{scenario_label} não possui resultados")
            continue
        expected_candidates = catalog.get(scenario_id, {}).get("candidates")
        expected = set(expected_candidates) if isinstance(expected_candidates, list) else set(results)
        missing_results = sorted(expected - set(results))
        extra_results = sorted(set(results) - expected)
        if missing_results:
            errors.append(f"{scenario_label} não possui: {', '.join(missing_results)}")
        if extra_results:
            errors.append(f"{scenario_label} possui candidatos extras: {', '.join(extra_results)}")
        for candidate, value in results.items():
            if not valid_percentage(value):
                errors.append(f"{scenario_label} tem percentual inválido para {candidate}")
        if not valid_percentage(scenario_result.get("undecided")):
            errors.append(f"{scenario_label} tem brancos/nulos/indecisos inválido")
        scenario_source = scenario_result.get("resultSource")
        scenario_source_label = scenario_result.get("resultSourceLabel")
        if bool(scenario_source) != bool(scenario_source_label):
            errors.append(f"{scenario_label} deve informar URL e rótulo da fonte juntos")
        if scenario_source and not str(scenario_source).startswith("https://"):
            errors.append(f"{scenario_label} precisa de fonte HTTPS")


def validate_catalog(poll_data: dict, errors: list[str]) -> dict[str, dict]:
    candidates = poll_data.get("candidates")
    if not isinstance(candidates, dict) or not candidates:
        errors.append("data/polls.json deve possuir um cadastro de candidatos")
        candidates = {}
    for key, candidate in candidates.items():
        label = f"Candidato {key}"
        if not isinstance(candidate, dict):
            errors.append(f"{label} é inválido")
            continue
        missing = sorted(REQUIRED_CANDIDATE_FIELDS - set(candidate))
        if missing:
            errors.append(f"{label} sem campos: {', '.join(missing)}")
        if not HEX_COLOR_PATTERN.fullmatch(str(candidate.get("color", ""))):
            errors.append(f"{label} tem cor inválida")

    scenarios = poll_data.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        errors.append("data/polls.json deve possuir um catálogo de cenários")
        return {}
    catalog: dict[str, dict] = {}
    for position, scenario in enumerate(scenarios, start=1):
        label = f"Cenário #{position}"
        if not isinstance(scenario, dict):
            errors.append(f"{label} é inválido")
            continue
        missing = sorted(REQUIRED_SCENARIO_FIELDS - set(scenario))
        if missing:
            errors.append(f"{label} sem campos: {', '.join(missing)}")
            continue
        scenario_id = str(scenario["id"])
        if scenario_id in catalog:
            errors.append(f"ID de cenário duplicado: {scenario_id}")
        if scenario["round"] not in (1, 2):
            errors.append(f"{label} tem turno inválido")
        scenario_candidates = scenario["candidates"]
        if not isinstance(scenario_candidates, list) or len(scenario_candidates) < 2:
            errors.append(f"{label} precisa ter ao menos dois candidatos")
        else:
            if len(scenario_candidates) != len(set(scenario_candidates)):
                errors.append(f"{label} possui candidatos duplicados")
            unknown_candidates = sorted(set(scenario_candidates) - set(candidates))
            if unknown_candidates:
                errors.append(f"{label} possui candidatos desconhecidos: {', '.join(unknown_candidates)}")
        catalog[scenario_id] = scenario
    if "first-main" not in catalog or catalog["first-main"].get("round") != 1:
        errors.append("O catálogo precisa definir first-main como cenário de primeiro turno")
    return catalog


def main() -> int:
    errors: list[str] = []
    poll_data = json.loads(POLLS_FILE.read_text(encoding="utf-8"))
    if poll_data.get("schemaVersion") != 2:
        errors.append("Versão desconhecida de data/polls.json")
    election = poll_data.get("election", {})
    if election != {"year": 2026, "country": "BR", "office": "president", "jurisdiction": "BR"}:
        errors.append("Identificação eleitoral inválida em data/polls.json")
    scenario_catalog = validate_catalog(poll_data, errors)
    polls = poll_data.get("polls")
    if not isinstance(polls, list) or not polls:
        errors.append("data/polls.json deve conter uma lista não vazia de pesquisas")
        polls = []

    for position, poll in enumerate(polls, start=1):
        validate_poll(poll, position, errors, scenario_catalog)

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
