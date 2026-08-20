from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

from scripts.sync_tse import (
    CONTRACTORS_ZIP_URL,
    DATASET_URL,
    POLLS_ZIP_URL,
    build_monitor,
    configured_exclusions,
    fetch,
    office_rows,
    presidential_mirror_rows,
    resolve_resource_urls,
    update_metadata,
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
        "NM_ESTATISTICO_RESP": "Estatístico Teste",
        "CD_CONRE": "1234",
        "VR_PESQUISA": "100000,00",
        "DS_METODOLOGIA_PESQUISA": "Entrevistas por telefone",
        "DS_PLANO_AMOSTRAL": "Amostra nacional",
    }


class BuildMonitorTests(unittest.TestCase):
    def test_presidential_mirror_is_mapped_to_the_official_schema(self) -> None:
        content = (
            "register_tse,registration_date,institute,institute_trade_name,office,"
            "field_start,field_end,publication_date,sample_size,conre,statistician,scope\n"
            "BR-01234/2026,2026-08-20,Instituto Teste,Teste,Presidente,"
            "2026-08-18,2026-08-20,2026-08-21,2000,1234,Estatístico,national\n"
            "BR-05678/2026,2026-08-20,Instituto Estadual,Estadual,Presidente,"
            "2026-08-18,2026-08-20,2026-08-21,1200,1234,Estatístico,state\n"
        ).encode("utf-8")

        rows = presidential_mirror_rows(content)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["NR_PROTOCOLO_REGISTRO"], "BR-01234/2026")
        self.assertEqual(row["SG_UE"], "BR")
        self.assertEqual(row["DS_CARGO"], "Presidente")
        self.assertEqual(row["QT_ENTREVISTADO"], "2000")

    def test_exclusions_require_an_auditable_reason_and_source(self) -> None:
        tse = {
            "excludedProtocols": [
                {
                    "protocol": "BR000012026",
                    "reason": "Amostra estadual",
                    "source": "https://example.com/fonte",
                }
            ]
        }

        self.assertEqual(configured_exclusions(tse), {"BR000012026"})
        with self.assertRaisesRegex(RuntimeError, "Exclusão incompleta"):
            configured_exclusions({"excludedProtocols": [{"protocol": "BR000022026"}]})

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

    def test_seen_protocol_is_recovered_when_disclosed_after_cutoff(self) -> None:
        existing = {
            "seenProtocols": ["BR000012026"],
            "pending": {},
            "sourceGeneratedAt": "2026-08-16 12:00:00",
        }
        rows = {"BR000012026": poll("BR000012026")}

        monitor, new_protocols, changed = build_monitor(
            existing,
            rows,
            {},
            set(),
            "2026-08-20 12:00:00",
            False,
            "2026-08-16",
        )

        self.assertTrue(changed)
        self.assertEqual(new_protocols, [])
        self.assertIn("BR000012026", monitor["pending"])

    def test_seen_protocol_before_cutoff_is_not_reopened(self) -> None:
        existing = {
            "seenProtocols": ["BR000012026"],
            "pending": {},
            "sourceGeneratedAt": "2026-08-16 12:00:00",
        }
        old_poll = poll("BR000012026") | {"DT_DIVULGACAO": "2026-08-15"}

        monitor, _, changed = build_monitor(
            existing,
            {"BR000012026": old_poll},
            {},
            set(),
            "2026-08-20 12:00:00",
            False,
            "2026-08-16",
        )

        self.assertFalse(changed)
        self.assertEqual(monitor["pending"], {})
        self.assertEqual(monitor["sourceGeneratedAt"], "2026-08-20 12:00:00")

    def test_partial_mirror_keeps_authoritative_snapshot_untouched(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "metadata.json"
            original = {
                "generatedAt": "16/08/2026 05:46:46",
                "source": "fonte-antiga",
                "pesqEle": "pesqele",
                "resourceUrls": {},
                "records": {
                    "BR000012026": {
                        "protocol": "BR000012026",
                        "registeredAt": "2026-08-15 12:34:56",
                        "researchCost": 164888.89,
                        "contractors": [{"name": "Contratante preservado"}],
                    }
                },
            }
            output.write_text(json.dumps(original), encoding="utf-8")

            changed = update_metadata(
                {"BR000012026": poll("BR000012026")},
                {},
                {"BR000012026", "BR000022026"},
                "2026-08-20 12:00:00",
                {"polls": "espelho", "contractors": ""},
                output,
                preserve_contractors=True,
                allow_partial=True,
            )
            payload = json.loads(output.read_text(encoding="utf-8"))

        self.assertFalse(changed)
        self.assertEqual(payload, original)


if __name__ == "__main__":
    unittest.main()
