from __future__ import annotations

import unittest

from scripts.sync_agenda import matches_election, parse_agenda


FIXTURE = """
<table><tbody>
  <tr class="dia"><th colspan="7"><span>sábado</span><span>29 de ago. de 2026</span></th></tr>
  <tr><th>Vox Brasil</th><td><span>Presidente</span><span>Nacional</span></td><td>2.100</td><td>25/08–27/08</td><td>Responsável</td><td>R$ 50.000</td><td>BR-05519/2026</td></tr>
  <tr><th>Quaest</th><td><span>Presidente</span><span>Pará</span></td><td>804</td><td>25/08–28/08</td><td>Responsável</td><td>R$ 92.259</td><td>BR-05309/2026</td></tr>
</tbody></table>
"""


class AgendaSyncTests(unittest.TestCase):
    def test_parser_keeps_disclosure_date_and_technical_fields(self) -> None:
        rows = parse_agenda(FIXTURE)

        self.assertEqual(rows[0]["protocol"], "BR055192026")
        self.assertEqual(rows[0]["disclosureDate"], "2026-08-29")
        self.assertEqual(rows[0]["fieldStart"], "2026-08-25")
        self.assertEqual(rows[0]["fieldEnd"], "2026-08-27")
        self.assertEqual(rows[0]["sample"], 2100)

    def test_only_national_presidential_scope_matches_brazil(self) -> None:
        election = {"context": "Brasil", "tse": {"office": "Presidente", "jurisdiction": "BR"}}

        self.assertTrue(matches_election("Presidente Nacional", election))
        self.assertFalse(matches_election("Presidente Pará", election))
        self.assertFalse(matches_election("Presidente alcance não declarado", election))

    def test_governor_scope_requires_the_exact_state(self) -> None:
        election = {"context": "São Paulo", "tse": {"office": "Governador", "jurisdiction": "SP"}}

        self.assertTrue(matches_election("Governador e Senado São Paulo", election))
        self.assertFalse(matches_election("Governador e Senado Minas Gerais", election))


if __name__ == "__main__":
    unittest.main()
