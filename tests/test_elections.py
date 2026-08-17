from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ElectionCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = json.loads((ROOT / "data" / "elections.json").read_text(encoding="utf-8"))
        cls.sp = json.loads((ROOT / "data" / "polls-sp-governor.json").read_text(encoding="utf-8"))
        cls.mg = json.loads((ROOT / "data" / "polls-mg-governor.json").read_text(encoding="utf-8"))

    def test_catalog_exposes_brazil_sao_paulo_and_minas_gerais(self) -> None:
        elections = {item["id"]: item for item in self.catalog["elections"]}

        self.assertEqual(self.catalog["defaultElection"], "president-br")
        self.assertEqual(elections["president-br"]["dataFile"], "data/polls.json")
        self.assertEqual(elections["governor-sp"]["dataFile"], "data/polls-sp-governor.json")
        self.assertEqual(elections["governor-sp"]["metadataFile"], "data/tse-metadata-sp.json")
        self.assertEqual(elections["governor-sp"]["monitorFile"], "data/tse-monitor-sp.json")
        self.assertEqual(elections["governor-mg"]["dataFile"], "data/polls-mg-governor.json")
        self.assertEqual(elections["governor-mg"]["tse"]["jurisdiction"], "MG")
        self.assertEqual({item["group"] for item in elections.values()}, {"Brasil", "Estados"})

    def test_sao_paulo_keeps_comparable_scenarios_separate(self) -> None:
        polls = self.sp["polls"]

        self.assertEqual(sum("first-main" in poll["scenarios"] for poll in polls), 3)
        self.assertEqual(sum("runoff-tarcisio-haddad" in poll["scenarios"] for poll in polls), 6)

    def test_latest_sao_paulo_results_match_sources(self) -> None:
        parana = next(poll for poll in self.sp["polls"] if poll["protocol"] == "SP046242026")
        quaest = next(poll for poll in self.sp["polls"] if poll["protocol"] == "SP048462026")

        self.assertEqual(parana["scenarios"]["first-main"]["results"]["tarcisio"], 48.5)
        self.assertEqual(parana["scenarios"]["runoff-tarcisio-haddad"]["results"]["haddad"], 38.3)
        self.assertEqual(quaest["scenarios"]["first-main"]["results"]["haddad"], 26)

    def test_sao_paulo_official_files_cover_curated_protocols(self) -> None:
        metadata = json.loads((ROOT / "data" / "tse-metadata-sp.json").read_text(encoding="utf-8"))
        monitor = json.loads((ROOT / "data" / "tse-monitor-sp.json").read_text(encoding="utf-8"))
        curated = {poll["protocol"] for poll in self.sp["polls"]}

        self.assertEqual(set(metadata["records"]), curated)
        self.assertTrue(curated.issubset(set(monitor["seenProtocols"])))
        self.assertEqual(monitor["pending"], {})

    def test_minas_gerais_keeps_current_first_round_and_runoffs_separate(self) -> None:
        polls = self.mg["polls"]
        quaest = next(poll for poll in polls if poll["protocol"] == "MG034902026")

        self.assertEqual(sum("first-main" in poll["scenarios"] for poll in polls), 1)
        self.assertEqual(sum("runoff-cleitinho-kalil" in poll["scenarios"] for poll in polls), 2)
        self.assertEqual(quaest["scenarios"]["first-main"]["results"]["cleitinho"], 35)
        self.assertEqual(quaest["scenarios"]["runoff-cleitinho-patrus"]["results"]["patrus"], 31)

    def test_minas_gerais_official_files_cover_curated_protocols(self) -> None:
        metadata = json.loads((ROOT / "data" / "tse-metadata-mg.json").read_text(encoding="utf-8"))
        monitor = json.loads((ROOT / "data" / "tse-monitor-mg.json").read_text(encoding="utf-8"))
        curated = {poll["protocol"] for poll in self.mg["polls"]}

        self.assertEqual(set(metadata["records"]), curated)
        self.assertTrue(curated.issubset(set(monitor["seenProtocols"])))
        self.assertEqual(monitor["pending"], {})


if __name__ == "__main__":
    unittest.main()
