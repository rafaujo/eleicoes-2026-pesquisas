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

    def test_eight_polls_have_new_runoff_results(self) -> None:
        polls = self.database["polls"]

        self.assertEqual(sum("runoff-lula-caiado" in poll["scenarios"] for poll in polls), 8)
        self.assertEqual(sum("runoff-lula-zema" in poll["scenarios"] for poll in polls), 8)

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
