#!/usr/bin/env python3
"""Adiciona ou atualiza uma pesquisa curada em data/polls.json."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from scripts.validate_data import validate_poll
except ModuleNotFoundError:  # Execução direta: python scripts/add_poll.py
    from validate_data import validate_poll


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE = ROOT / "data" / "polls.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="ficha JSON da pesquisa")
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--replace", action="store_true", help="substitui o protocolo se ele já existir")
    return parser.parse_args()


def upsert_poll(database: dict, poll: dict, replace: bool = False) -> dict:
    polls = database["polls"]
    existing = next((item for item in polls if item["protocol"] == poll.get("protocol")), None)
    if existing and not replace:
        raise ValueError(f"O protocolo {poll['protocol']} já existe; use --replace para atualizá-lo")

    candidate = dict(poll)
    if existing:
        candidate["id"] = existing["id"]
        polls = [item for item in polls if item["protocol"] != candidate["protocol"]]
    elif "id" not in candidate:
        candidate["id"] = max((item["id"] for item in polls), default=0) + 1

    errors: list[str] = []
    validate_poll(candidate, candidate["id"], errors)
    if errors:
        raise ValueError("Ficha inválida:\n- " + "\n- ".join(errors))

    polls.append(candidate)
    database["polls"] = sorted(polls, key=lambda item: (item["end"], item["id"]), reverse=True)
    return database


def main() -> int:
    args = parse_args()
    database = json.loads(args.database.read_text(encoding="utf-8"))
    poll = json.loads(args.input.read_text(encoding="utf-8"))
    updated = upsert_poll(database, poll, args.replace)
    args.database.write_text(json.dumps(updated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Pesquisa {poll['protocol']} gravada em {args.database}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
