from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ScenarioDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.database = json.loads((ROOT / "data" / "polls.json").read_text(encoding="utf-8"))

    def test_catalog_has_dynamic_runoff_scenarios(self) -> None:
        scenarios = {item["id"]: item for item in self.database["scenarios"]}

        self.assertEqual(scenarios["runoff-lula-flavio"]["candidates"], ["lula", "flavio"])
        self.assertEqual(scenarios["runoff-lula-caiado"]["candidates"], ["lula", "caiado"])
        self.assertEqual(scenarios["runoff-lula-zema"]["candidates"], ["lula", "zema"])
        self.assertEqual(scenarios["runoff-lula-renan"]["candidates"], ["lula", "renan"])

    def test_ten_polls_have_extended_runoff_results(self) -> None:
        polls = self.database["polls"]

        self.assertEqual(sum("runoff-lula-caiado" in poll["scenarios"] for poll in polls), 10)
        self.assertEqual(sum("runoff-lula-zema" in poll["scenarios"] for poll in polls), 10)
        self.assertEqual(sum("runoff-lula-renan" in poll["scenarios"] for poll in polls), 1)

    def test_latest_datafolha_values_match_published_scenarios(self) -> None:
        datafolha = next(poll for poll in self.database["polls"] if poll["protocol"] == "BR044962026")

        self.assertEqual(datafolha["published"], "2026-08-21")
        self.assertEqual(
            datafolha["scenarios"]["first-main"]["results"],
            {"lula": 39, "flavio": 33, "caiado": 5, "zema": 3, "renan": 4},
        )
        self.assertEqual(datafolha["scenarios"]["runoff-lula-flavio"]["results"], {"lula": 47, "flavio": 43})
        self.assertEqual(datafolha["scenarios"]["runoff-lula-caiado"]["results"], {"lula": 47, "caiado": 40})
        self.assertEqual(datafolha["scenarios"]["runoff-lula-zema"]["results"], {"lula": 48, "zema": 38})
        self.assertEqual(datafolha["scenarios"]["runoff-lula-renan"]["results"], {"lula": 47, "renan": 37})

    def test_latest_nexus_values_match_published_scenarios(self) -> None:
        nexus = next(poll for poll in self.database["polls"] if poll["protocol"] == "BR033172026")

        self.assertEqual(nexus["published"], "2026-08-17")
        self.assertEqual(nexus["scenarios"]["first-main"]["results"]["lula"], 41)
        self.assertEqual(nexus["scenarios"]["runoff-lula-flavio"]["results"], {"lula": 47, "flavio": 44})
        self.assertEqual(nexus["scenarios"]["runoff-lula-caiado"]["results"], {"lula": 45, "caiado": 42})
        self.assertEqual(nexus["scenarios"]["runoff-lula-zema"]["results"], {"lula": 46, "zema": 41})

    def test_atlas_values_match_published_scenarios(self) -> None:
        atlas = next(poll for poll in self.database["polls"] if poll["protocol"] == "BR086022026")

        self.assertEqual(
            atlas["scenarios"]["runoff-lula-caiado"],
            {
                "results": {"lula": 48.2, "caiado": 38.9},
                "undecided": 12.9,
                "resultSource": "https://noticias.uol.com.br/politica/ultimas-noticias/2026/07/29/pesquisa-atlasbloomberg-lula-tem-492-e-flavio-429-no-2-turno.ghtm",
                "resultSourceLabel": "UOL — cenários de segundo turno Atlas/Bloomberg",
            },
        )


if __name__ == "__main__":
    unittest.main()

