import unittest

from scripts.ingest_results import (
    index_links,
    normalize,
    parse_detail,
    protocol_key,
    merge_scenarios,
    scenario_for,
)


class IngestResultsTests(unittest.TestCase):
    def test_index_only_returns_recent_first_round_fiches(self) -> None:
        markup = """
        <a href="/pesquisas/nexus_2026-08-23_T1_BR090282026_1/">ficha</a>
        <a href="/pesquisas/nexus_2026-08-23_T2_BR090282026_2/">ficha</a>
        <a href="/pesquisas/old_2026-08-01_T1_BR000002026_3/">ficha</a>
        <script>[[0,&quot;indexa_2026-08-23_T1_BR063662026_4&quot;]]</script>
        <script>[[0,&quot;pres-sp-quaest_2026-08-23_T1_BR000012026_5&quot;]]</script>
        """
        links = index_links(markup, __import__("datetime").date(2026, 8, 20))
        self.assertEqual(len(links), 2)
        self.assertTrue(all("_T1_" in link for link in links))
        self.assertFalse(any("pres-sp" in link for link in links))

    def test_detail_parser_reads_results_metadata_and_related_links(self) -> None:
        markup = """
        <p class="olho">Presidente — nacional · 1º turno · campo encerrado em 23 de ago. de 2026</p>
        <h1>Nexus</h1>
        <section><ol class="placar"><li class="linha"><span class="nome">Lula<span class="sigla">PT</span></span><span class="valor num">41,0%</span></li><li class="linha"><span class="nome">Flávio Bolsonaro<span class="sigla">PL</span></span><span class="valor num">37,0%</span></li></ol></section>
        <div class="agregados"><span class="ag-val num">9,0%</span></div>
        <a class="tb-link" href="/pesquisas/nexus_2026-08-23_T2_BR090282026_2/">segundo turno</a>
        <div class="par"><dt>Registro no TSE</dt><dd>BR-09028/2026</dd></div>
        <div class="par"><dt>Entrevistas</dt><dd>2.006</dd></div>
        <div class="par"><dt>Margem de erro</dt><dd>±2,0 p.p.</dd></div>
        <div class="par"><dt>Coleta</dt><dd>telefone</dd></div>
        <p class="fonte"><a href="https://example.com/pesquisa">Ver a fonte deste número</a></p>
        """
        detail = parse_detail("https://depoisdas17.com.br/pesquisas/nexus_2026-08-23_T1_BR090282026_1/", markup)
        self.assertEqual(detail["protocol"], "BR090282026")
        self.assertEqual(detail["sample"], 2006)
        self.assertEqual(detail["results"], {"Lula": 41, "Flávio Bolsonaro": 37})
        self.assertEqual(detail["undecided"], 9)
        self.assertEqual(len(detail["related"]), 1)

    def test_presidential_scenario_with_marcal_is_classified_separately(self) -> None:
        detail = {
            "round": 1,
            "results": {
                "Lula": 38, "Flávio Bolsonaro": 35, "Ronaldo Caiado": 4,
                "Romeu Zema": 2, "Renan Santos": 4, "Pablo Marçal": 3,
            },
        }
        catalog = {
            "first-main": {"id": "first-main", "round": 1, "candidates": ["lula", "flavio", "caiado", "zema", "renan"]},
            "first-with-marcal": {"id": "first-with-marcal", "round": 1, "candidates": ["lula", "flavio", "marcal", "caiado", "renan", "zema"]},
        }
        scenario_id, results = scenario_for(detail, "president-br", catalog)
        self.assertEqual(scenario_id, "first-with-marcal")
        self.assertEqual(results["marcal"], 3)

    def test_presidential_scenario_keeps_cury_in_the_most_complete_variant(self) -> None:
        detail = {
            "round": 1,
            "results": {
                "Lula": 38, "Flávio Bolsonaro": 33, "Augusto Cury": 8,
                "Ronaldo Caiado": 4, "Romeu Zema": 2, "Renan Santos": 3,
            },
        }
        catalog = {
            "first-main": {"id": "first-main", "round": 1, "candidates": ["lula", "flavio", "caiado", "zema", "renan"]},
            "first-with-cury": {"id": "first-with-cury", "round": 1, "candidates": ["lula", "flavio", "cury", "caiado", "zema", "renan"]},
        }

        scenario_id, results = scenario_for(detail, "president-br", catalog)

        self.assertEqual(scenario_id, "first-with-cury")
        self.assertEqual(results["cury"], 8)

    def test_existing_poll_is_enriched_and_truncated_variant_is_removed(self) -> None:
        existing = {
            "scenarios": {
                "first-main": {"results": {"lula": 38, "flavio": 33}},
                "runoff-lula-flavio": {"results": {"lula": 46, "flavio": 44}},
            },
        }
        catalog = {
            "first-main": {"id": "first-main", "round": 1, "comparisonGroup": "first-round", "candidates": ["lula", "flavio"]},
            "first-with-cury": {"id": "first-with-cury", "round": 1, "comparisonGroup": "first-round", "candidates": ["lula", "flavio", "cury"]},
            "runoff-lula-flavio": {"id": "runoff-lula-flavio", "round": 2, "candidates": ["lula", "flavio"]},
        }
        incoming = {
            "first-with-cury": {"results": {"lula": 38, "flavio": 33, "cury": 8}},
        }

        changed = merge_scenarios(existing, incoming, catalog)

        self.assertTrue(changed)
        self.assertNotIn("first-main", existing["scenarios"])
        self.assertEqual(existing["scenarios"]["first-with-cury"]["results"]["cury"], 8)
        self.assertIn("runoff-lula-flavio", existing["scenarios"])

    def test_normalization_and_protocol_are_accent_and_punctuation_safe(self) -> None:
        self.assertEqual(normalize("Tarcísio — São Paulo"), "tarcisio sao paulo")
        self.assertEqual(protocol_key("BR-09028/2026"), "BR090282026")


if __name__ == "__main__":
    unittest.main()
