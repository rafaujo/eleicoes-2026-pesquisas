from __future__ import annotations

import unittest

from scripts.sync_tse import build_monitor


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
