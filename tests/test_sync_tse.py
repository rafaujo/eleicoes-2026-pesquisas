from __future__ import annotations

import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from scripts.sync_tse import (
    CONTRACTORS_ZIP_URL,
    DATASET_URL,
    POLLS_ZIP_URL,
    build_monitor,
    fetch,
    office_rows,
    resolve_resource_urls,
)


def poll(protocol: str) -> dict[str, str]:
    return {
        "NR_PROTOCOLO_REGISTRO": protocol,
        "DT_REGISTRO": "2026-08-16 10:00:00",
        "DT_INICIO_PESQUISA": "2026-08-15",
        "DT_FIM_PESQUISA": "2026-08-16",
        "DT_DIVULGACAO": "2026-08-17",
        "QT_ENTREVISTADO": "2000",
        "NM_EMPRESA": "INSTITUTO TESTE LTDA",
        "NM_EMPRESA_FANTASIA": "Instituto Teste",
    }


class BuildMonitorTests(unittest.TestCase):
    @patch("scripts.sync_tse.urllib.request.urlopen")
    def test_fetch_uses_browser_headers_required_by_tse(self, urlopen_mock) -> None:
        urlopen_mock.return_value.__enter__.return_value.read.return_value = b"ok"

        self.assertEqual(fetch(POLLS_ZIP_URL), b"ok")
        request = urlopen_mock.call_args.args[0]
        self.assertIn("Mozilla/5.0", request.get_header("User-agent"))
        self.assertEqual(request.get_header("Accept-language"), "pt-BR,pt;q=0.9,en;q=0.8")
        self.assertEqual(request.get_header("Referer"), DATASET_URL)

    @patch("scripts.sync_tse.fetch")
    def test_cdn_urls_are_used_when_ckan_blocks_the_runner(self, fetch_mock) -> None:
        fetch_mock.side_effect = HTTPError("https://dadosabertos.tse.jus.br", 403, "Forbidden", {}, None)

        self.assertEqual(resolve_resource_urls(), (POLLS_ZIP_URL, CONTRACTORS_ZIP_URL))

    def test_office_rows_filters_jurisdiction_and_office(self) -> None:
        sp_governor = poll("SP000012026") | {"SG_UE": "SP", "DS_CARGO": "Governador"}
        sp_senator = poll("SP000022026") | {"SG_UE": "SP", "DS_CARGO": "Senador"}
        mg_governor = poll("MG000012026") | {"SG_UE": "MG", "DS_CARGO": "Governador"}

        filtered = office_rows([sp_governor, sp_senator, mg_governor], "SP", "Governador")

        self.assertEqual(filtered, {"SP000012026": sp_governor})

    def test_bootstrap_marks_everything_seen_without_pending_items(self) -> None:
        rows = {"BR000012026": poll("BR000012026"), "BR000022026": poll("BR000022026")}
        monitor, new_protocols, changed = build_monitor(
            None, rows, {}, {"BR000012026"}, "2026-08-16 12:00:00", True
        )

        self.assertTrue(changed)
        self.assertEqual(new_protocols, [])
        self.assertEqual(monitor["seenProtocols"], ["BR000012026", "BR000022026"])
        self.assertEqual(monitor["pending"], {})

    def test_new_uncurated_protocol_enters_review_queue(self) -> None:
        existing = {
            "seenProtocols": ["BR000012026"],
            "pending": {},
            "sourceGeneratedAt": "2026-08-15 12:00:00",
        }
        rows = {"BR000012026": poll("BR000012026"), "BR000022026": poll("BR000022026")}
        monitor, new_protocols, changed = build_monitor(
            existing, rows, {}, {"BR000012026"}, "2026-08-16 12:00:00", False
        )

        self.assertTrue(changed)
        self.assertEqual(new_protocols, ["BR000022026"])
        self.assertIn("BR000022026", monitor["pending"])

    def test_curated_protocol_is_removed_from_pending_queue(self) -> None:
        existing = {
            "seenProtocols": ["BR000012026"],
            "pending": {"BR000012026": {"protocol": "BR000012026"}},
            "sourceGeneratedAt": "2026-08-15 12:00:00",
        }
        monitor, _, changed = build_monitor(
            existing,
            {"BR000012026": poll("BR000012026")},
            {},
            {"BR000012026"},
            "2026-08-16 12:00:00",
            False,
        )

        self.assertTrue(changed)
        self.assertEqual(monitor["pending"], {})


if __name__ == "__main__":
    unittest.main()
