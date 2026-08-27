from __future__ import annotations

import unittest

from scripts.discover_results import (
    ELECTION_RULES,
    already_curated,
    deduplicate_disclosures,
    matches_election,
    parse_feed,
)


VERITA_FEED = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <item>
      <title>Verit\xc3\xa1: Lula perde para Fl\xc3\xa1vio no 2\xc2\xba turno; com Mar\xc3\xa7al no pleito, h\xc3\xa1 empate</title>
      <link>https://news.google.com/rss/articles/verita</link>
      <pubDate>Fri, 21 Aug 2026 13:47:00 GMT</pubDate>
      <source>CNN Brasil</source>
    </item>
  </channel>
</rss>"""


class ResultDiscoveryTests(unittest.TestCase):
    def test_each_election_uses_redundant_news_queries(self) -> None:
        self.assertTrue(all(len(rule["queries"]) >= 2 for rule in ELECTION_RULES.values()))

    def test_verita_disclosure_is_detected_for_presidential_queue(self) -> None:
        articles = parse_feed(VERITA_FEED, "president-br")

        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0]["pollster"], "Veritá")
        self.assertEqual(articles[0]["published"], "2026-08-21")

    def test_editorial_roundup_is_not_treated_as_new_poll(self) -> None:
        self.assertFalse(
            matches_election(
                "O que dizem as pesquisas para presidente na primeira semana de campanha",
                "president-br",
            )
        )

    def test_vague_result_without_identifiable_pollster_is_rejected(self) -> None:
        self.assertFalse(
            matches_election(
                "Pesquisa: Tarcísio pode vencer no primeiro turno em SP",
                "governor-sp",
                "VEJA",
            )
        )

    def test_singular_parana_pesquisa_title_is_recognized(self) -> None:
        self.assertTrue(
            matches_election(
                "Paraná Pesquisa: Tarcísio chega a 50% e abre vantagem sobre Haddad em SP",
                "governor-sp",
                "InfoMoney",
            )
        )

    def test_regional_presidential_result_is_not_treated_as_national(self) -> None:
        self.assertFalse(
            matches_election(
                "Atlas: Lula lidera cenários de 1º e 2º turnos no Pará",
                "president-br",
            )
        )

    def test_state_abbreviations_are_not_treated_as_national(self) -> None:
        for state in ("ES", "MT", "RS", "SC"):
            with self.subTest(state=state):
                self.assertFalse(
                    matches_election(
                        f"Quaest em {state}: Lula tem 39% e Flávio Bolsonaro 35%",
                        "president-br",
                    )
                )

    def test_full_state_names_are_not_treated_as_national(self) -> None:
        for state in ("Tocantins", "Alagoas"):
            with self.subTest(state=state):
                self.assertFalse(
                    matches_election(
                        f"Quaest em {state}: Lula tem 39% e Flávio Bolsonaro 35%",
                        "president-br",
                    )
                )

    def test_social_post_is_not_used_as_editorial_source(self) -> None:
        self.assertFalse(
            matches_election(
                "Lula tem 47% e Flávio Bolsonaro 43%, de acordo com pesquisa",
                "president-br",
                "instagram.com",
            )
        )

    def test_multiple_articles_for_same_poll_create_one_queue_item(self) -> None:
        first = parse_feed(VERITA_FEED, "president-br")[0]
        second = {
            **first,
            "key": "alternative",
            "source": "Folha de S.Paulo",
            "published": "2026-08-22",
        }

        queue = deduplicate_disclosures([first, second])

        self.assertEqual(len(queue), 1)
        self.assertEqual(queue[0]["source"], "Folha de S.Paulo")

    def test_disclosure_leaves_queue_after_same_poll_is_curated(self) -> None:
        article = parse_feed(VERITA_FEED, "president-br")[0]
        polls = [{"pollster": "Veritá", "published": "2026-08-21"}]

        self.assertTrue(already_curated(article, polls))


if __name__ == "__main__":
    unittest.main()
