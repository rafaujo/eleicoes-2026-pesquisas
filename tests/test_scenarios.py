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
        self.assertEqual(scenarios["runoff-lula-marcal"]["candidates"], ["lula", "marcal"])
        self.assertEqual(scenarios["runoff-lula-cury"]["candidates"], ["lula", "cury"])
        self.assertEqual(
            scenarios["first-with-marcal"]["candidates"],
            ["lula", "flavio", "marcal", "caiado", "renan", "zema"],
        )
        self.assertEqual(
            scenarios["first-with-cury-marcal"]["candidates"],
            ["lula", "flavio", "cury", "marcal", "caiado", "renan", "zema"],
        )

    def test_first_round_variants_share_a_comparison_group(self) -> None:
        first_round = [item for item in self.database["scenarios"] if item["round"] == 1]

        self.assertEqual({item["comparisonGroup"] for item in first_round}, {"first-round"})
        self.assertEqual(
            {item["comparisonLabel"] for item in first_round},
            {"Primeiro turno — listas integradas"},
        )

    def test_extended_runoff_results_keep_growing(self) -> None:
        polls = self.database["polls"]

        self.assertGreaterEqual(sum("runoff-lula-caiado" in poll["scenarios"] for poll in polls), 13)
        self.assertGreaterEqual(sum("runoff-lula-zema" in poll["scenarios"] for poll in polls), 13)
        self.assertGreaterEqual(sum("runoff-lula-renan" in poll["scenarios"] for poll in polls), 4)
        self.assertGreaterEqual(sum("runoff-lula-marcal" in poll["scenarios"] for poll in polls), 1)

    def test_verita_values_match_published_scenarios(self) -> None:
        verita = next(poll for poll in self.database["polls"] if poll["protocol"] == "BR040062026")

        self.assertEqual(verita["published"], "2026-08-21")
        self.assertEqual(
            verita["scenarios"]["first-with-marcal"]["results"],
            {"lula": 39.3, "flavio": 39.1, "marcal": 5.2, "caiado": 3.3, "renan": 3.8, "zema": 1.3},
        )
        self.assertEqual(verita["scenarios"]["runoff-lula-flavio"]["results"], {"lula": 42, "flavio": 47.3})
        self.assertEqual(verita["scenarios"]["runoff-lula-marcal"]["results"], {"lula": 42.7, "marcal": 43.6})
        self.assertEqual(verita["scenarios"]["runoff-lula-caiado"]["results"], {"lula": 40.4, "caiado": 23.7})
        self.assertEqual(verita["scenarios"]["runoff-lula-zema"]["results"], {"lula": 41.2, "zema": 25})
        self.assertEqual(verita["scenarios"]["runoff-lula-renan"]["results"], {"lula": 40.5, "renan": 16.2})

    def test_latest_datafolha_values_match_published_scenarios(self) -> None:
        datafolha = next(poll for poll in self.database["polls"] if poll["protocol"] == "BR044962026")

        self.assertEqual(datafolha["published"], "2026-08-21")
        self.assertEqual(
            datafolha["scenarios"]["first-with-cury"]["results"],
            {"lula": 39, "flavio": 33, "cury": 2, "caiado": 5, "zema": 3, "renan": 4},
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

    def test_latest_atlas_and_augusto_cury_are_present(self) -> None:
        atlas = next(poll for poll in self.database["polls"] if poll["protocol"] == "BR079722026")

        self.assertEqual(atlas["pollster"], "AtlasIntel")
        self.assertEqual(atlas["published"], "2026-08-31")
        self.assertEqual(atlas["scenarios"]["first-with-cury-marcal"]["results"]["cury"], 7.8)
        self.assertEqual(atlas["scenarios"]["runoff-lula-flavio"]["results"], {"lula": 47.1, "flavio": 42.6})

    def test_recent_published_national_polls_are_covered(self) -> None:
        protocols = {poll["protocol"] for poll in self.database["polls"]}

        self.assertTrue({
            "BR055192026",  # Vox Brasil
            "BR079722026",  # AtlasIntel/Bloomberg
            "BR027932026",  # Futura/Apex
            "BR075612026",  # PoderData/Aya
        }.issubset(protocols))


if __name__ == "__main__":
    unittest.main()
