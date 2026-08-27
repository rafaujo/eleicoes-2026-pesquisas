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

        presidential_exclusions = elections["president-br"]["tse"]["excludedProtocols"]
        self.assertEqual(
            {item["protocol"] for item in presidential_exclusions},
            {
                "BR078502026",
                "BR062782026",
                "BR054232026",
                "BR067832026",
                "BR087572026",
            },
        )
        self.assertTrue(all(item["reason"] and item["source"] for item in presidential_exclusions))

    def test_sao_paulo_keeps_comparable_scenarios_separate(self) -> None:
        polls = self.sp["polls"]

        self.assertEqual(sum("first-main" in poll["scenarios"] for poll in polls), 3)
        self.assertEqual(sum("first-short" in poll["scenarios"] for poll in polls), 1)
        self.assertEqual(sum("first-pre-campaign" in poll["scenarios"] for poll in polls), 3)
        self.assertEqual(sum("runoff-tarcisio-haddad" in poll["scenarios"] for poll in polls), 11)

    def test_latest_sao_paulo_results_match_sources(self) -> None:
        parana = next(poll for poll in self.sp["polls"] if poll["protocol"] == "SP046242026")
        quaest = next(poll for poll in self.sp["polls"] if poll["protocol"] == "SP048462026")

        self.assertEqual(parana["scenarios"]["first-pre-campaign"]["results"]["tarcisio"], 48.5)
        self.assertEqual(parana["scenarios"]["runoff-tarcisio-haddad"]["results"]["haddad"], 38.3)
        self.assertEqual(quaest["scenarios"]["first-pre-campaign"]["results"]["haddad"], 26)

        datafolha = next(poll for poll in self.sp["polls"] if poll["protocol"] == "SP018062026")
        latest_parana = next(poll for poll in self.sp["polls"] if poll["protocol"] == "SP089132026")
        self.assertEqual(datafolha["scenarios"]["first-main"]["results"]["tarcisio"], 45)
        self.assertEqual(datafolha["scenarios"]["first-main"]["results"]["edjane"], 3)
        self.assertEqual(datafolha["scenarios"]["runoff-tarcisio-haddad"]["results"]["haddad"], 35)
        self.assertEqual(latest_parana["scenarios"]["runoff-tarcisio-haddad"]["results"]["tarcisio"], 53)

        latest_quaest = next(poll for poll in self.sp["polls"] if poll["protocol"] == "SP069462026")
        latest_gerp = next(poll for poll in self.sp["polls"] if poll["protocol"] == "SP014772026")
        latest_realtime = next(poll for poll in self.sp["polls"] if poll["protocol"] == "SP013472026")
        self.assertEqual(latest_quaest["scenarios"]["first-main"]["results"]["tarcisio"], 40)
        self.assertEqual(latest_gerp["scenarios"]["first-main"]["results"]["haddad"], 32)
        self.assertEqual(latest_realtime["scenarios"]["first-short"]["results"]["tarcisio"], 52)

    def test_sao_paulo_official_files_cover_curated_protocols(self) -> None:
        metadata = json.loads((ROOT / "data" / "tse-metadata-sp.json").read_text(encoding="utf-8"))
        monitor = json.loads((ROOT / "data" / "tse-monitor-sp.json").read_text(encoding="utf-8"))
        curated = {poll["protocol"] for poll in self.sp["polls"]}

        metadata_date = str(metadata["generatedAt"])[:10]
        awaiting_sync = {
            poll["protocol"] for poll in self.sp["polls"]
            if poll.get("published", "") > metadata_date
        }
        self.assertTrue(set(metadata["records"]).issubset(curated))
        self.assertTrue((curated - awaiting_sync).issubset(set(metadata["records"])))
        self.assertTrue((curated - awaiting_sync).issubset(set(monitor["seenProtocols"])))
        self.assertTrue(curated.isdisjoint(set(monitor["pending"])))
        self.assertTrue(set(monitor["pending"]).issubset(set(monitor["seenProtocols"])))

    def test_minas_gerais_keeps_current_first_round_and_runoffs_separate(self) -> None:
        polls = self.mg["polls"]
        quaest = next(poll for poll in polls if poll["protocol"] == "MG034902026")

        self.assertEqual(sum("first-main" in poll["scenarios"] for poll in polls), 2)
        self.assertEqual(sum("first-short" in poll["scenarios"] for poll in polls), 1)
        self.assertEqual(sum("first-pre-campaign" in poll["scenarios"] for poll in polls), 1)
        self.assertEqual(sum("runoff-cleitinho-kalil" in poll["scenarios"] for poll in polls), 4)
        self.assertEqual(quaest["scenarios"]["first-pre-campaign"]["results"]["cleitinho"], 35)
        self.assertEqual(quaest["scenarios"]["runoff-cleitinho-patrus"]["results"]["patrus"], 31)

        datafolha = next(poll for poll in polls if poll["protocol"] == "MG004462026")
        self.assertEqual(datafolha["scenarios"]["first-main"]["results"]["cleitinho"], 32)
        self.assertEqual(datafolha["scenarios"]["first-main"]["results"]["indira"], 1)

        latest_quaest = next(poll for poll in polls if poll["protocol"] == "MG040602026")
        latest_realtime = next(poll for poll in polls if poll["protocol"] == "MG079722026")
        self.assertEqual(latest_quaest["scenarios"]["first-main"]["results"]["cleitinho"], 29)
        self.assertEqual(latest_realtime["scenarios"]["first-short"]["results"]["cleitinho"], 33)

    def test_minas_gerais_official_files_cover_curated_protocols(self) -> None:
        metadata = json.loads((ROOT / "data" / "tse-metadata-mg.json").read_text(encoding="utf-8"))
        monitor = json.loads((ROOT / "data" / "tse-monitor-mg.json").read_text(encoding="utf-8"))
        curated = {poll["protocol"] for poll in self.mg["polls"]}

        metadata_date = str(metadata["generatedAt"])[:10]
        awaiting_sync = {
            poll["protocol"] for poll in self.mg["polls"]
            if poll.get("published", "") > metadata_date
        }
        self.assertTrue(set(metadata["records"]).issubset(curated))
        self.assertTrue((curated - awaiting_sync).issubset(set(metadata["records"])))
        self.assertTrue((curated - awaiting_sync).issubset(set(monitor["seenProtocols"])))
        self.assertTrue(curated.isdisjoint(set(monitor["pending"])))
        self.assertTrue(set(monitor["pending"]).issubset(set(monitor["seenProtocols"])))


if __name__ == "__main__":
    unittest.main()
