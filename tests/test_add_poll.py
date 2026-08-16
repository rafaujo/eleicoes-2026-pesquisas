from __future__ import annotations

import unittest

from scripts.add_poll import upsert_poll


SCENARIOS = [
    {"id": "first-main", "round": 1, "label": "Cenário principal", "candidates": ["lula", "flavio", "caiado", "zema", "renan"]},
    {"id": "runoff-lula-flavio", "round": 2, "label": "Lula × Flávio", "candidates": ["lula", "flavio"]},
]


def database(polls: list[dict]) -> dict:
    return {"scenarios": SCENARIOS, "polls": polls}


def poll(protocol: str = "BR000012026") -> dict:
    return {
        "pollster": "Instituto Teste",
        "publication": "Divulgação própria",
        "protocol": protocol,
        "start": "2026-08-01",
        "end": "2026-08-03",
        "field": "1–3 ago",
        "sample": 2000,
        "margin": 2.2,
        "confidence": 95,
        "method": "Entrevistas",
        "resultSource": "https://example.com/resultado",
        "resultSourceLabel": "Fonte — resultado",
        "scenarios": {
            "first-main": {
                "results": {"lula": 40, "flavio": 35, "caiado": 5, "zema": 3, "renan": 4},
                "undecided": 10,
            },
            "runoff-lula-flavio": {
                "results": {"lula": 46, "flavio": 43},
                "undecided": 11,
            },
        },
    }


class UpsertPollTests(unittest.TestCase):
    def test_assigns_next_id(self) -> None:
        target = database([{"id": 4, "protocol": "BR999992026", "end": "2026-07-01"}])

        updated = upsert_poll(target, poll())

        self.assertEqual(updated["polls"][0]["id"], 5)

    def test_rejects_duplicate_protocol(self) -> None:
        existing = {"id": 2, **poll()}

        with self.assertRaisesRegex(ValueError, "já existe"):
            upsert_poll(database([existing]), poll())

    def test_replace_preserves_id(self) -> None:
        existing = {"id": 7, **poll()}
        replacement = poll()
        replacement["scenarios"]["first-main"]["results"]["lula"] = 42

        updated = upsert_poll(database([existing]), replacement, replace=True)

        self.assertEqual(updated["polls"][0]["id"], 7)
        self.assertEqual(updated["polls"][0]["scenarios"]["first-main"]["results"]["lula"], 42)


if __name__ == "__main__":
    unittest.main()
