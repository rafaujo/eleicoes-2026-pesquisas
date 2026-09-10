#!/usr/bin/env python3
"""Incorpora automaticamente resultados verificáveis de um acervo estruturado.

O importador usa o Depois das 17 como índice, mas só publica um cenário quando
o protocolo, a amostra e cada par candidato/percentual também aparecem na fonte
jornalística ligada pela ficha. Casos incompletos ou divergentes permanecem na
fila editorial produzida por ``discover_results.py``.
"""

from __future__ import annotations

import argparse
import html
import io
import json
import re
import sys
import unicodedata
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import date, timedelta
from html.parser import HTMLParser
from pathlib import Path

try:
    from pypdf import PdfReader
except ImportError:  # A mensagem amigável é emitida apenas se uma fonte PDF aparecer.
    PdfReader = None


ROOT = Path(__file__).resolve().parents[1]
ELECTIONS_FILE = ROOT / "data" / "elections.json"
DISCOVERY_FILE = ROOT / "data" / "result-discovery.json"
INDEX_URL = "https://depoisdas17.com.br/pesquisas/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; Pulso26Bot/1.0; +https://github.com/rafaujo/eleicoes-2026-pesquisas)",
    "Accept-Language": "pt-BR,pt;q=0.9",
}
MONTHS = {
    "janeiro": 1, "fevereiro": 2, "marco": 3, "abril": 4,
    "maio": 5, "junho": 6, "julho": 7, "agosto": 8,
    "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12,
}
PREFIXES = {
    "president-br": "",
    "governor-sp": "gov-sp-",
    "governor-mg": "gov-mg-",
}
CANDIDATE_ALIASES = {
    "president-br": {
        "lula": ("lula", "luiz inacio lula da silva"),
        "flavio": ("flavio bolsonaro",),
        "caiado": ("ronaldo caiado", "caiado"),
        "zema": ("romeu zema", "zema"),
        "renan": ("renan santos",),
        "marcal": ("pablo marcal", "marcal"),
        "cury": ("augusto cury", "cury"),
    },
    "governor-sp": {
        "tarcisio": ("tarcisio de freitas", "tarcisio"),
        "haddad": ("fernando haddad", "haddad"),
        "vera": ("vera lucia",),
        "machado": ("carlos machado",),
        "edjane": ("policial edjane", "edjane"),
        "vivian": ("vivian mendes",),
        "izadora": ("izadora dias",),
    },
    "governor-mg": {
        "cleitinho": ("cleitinho azevedo", "cleitinho"),
        "kalil": ("alexandre kalil", "kalil"),
        "patrus": ("patrus ananias", "patrus"),
        "mateus": ("mateus simoes",),
        "gabriel": ("gabriel azevedo", "gabriel"),
        "roscoe": ("flavio roscoe", "roscoe"),
        "tulio": ("professor tulio lopes", "tulio lopes"),
        "duda": ("rafael duda",),
        "ben": ("ben mendes",),
        "indira": ("indira xavier",),
        "henrique": ("henrique areas",),
    },
}


@dataclass
class Node:
    tag: str
    attrs: dict[str, str] = field(default_factory=dict)
    children: list["Node"] = field(default_factory=list)
    chunks: list[str] = field(default_factory=list)

    def text(self) -> str:
        parts: list[str] = []
        stack = [self]
        while stack:
            current = stack.pop()
            parts.extend(current.chunks)
            stack.extend(reversed(current.children))
        return " ".join(" ".join(parts).split())


class TreeParser(HTMLParser):
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = Node("document")
        self.stack = [self.root]

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        node = Node(tag, {key: value or "" for key, value in attrs})
        self.stack[-1].children.append(node)
        if tag not in self.VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID:
            self.stack.pop()

    def handle_endtag(self, tag: str) -> None:
        for position in range(len(self.stack) - 1, 0, -1):
            if self.stack[position].tag == tag:
                del self.stack[position:]
                return

    def handle_data(self, data: str) -> None:
        value = " ".join(data.split())
        if value:
            self.stack[-1].chunks.append(value)


def walk(node: Node):
    stack = [node]
    while stack:
        current = stack.pop()
        yield current
        stack.extend(reversed(current.children))


def has_class(node: Node, class_name: str) -> bool:
    return class_name in node.attrs.get("class", "").split()


def first(node: Node, *, tag: str | None = None, class_name: str | None = None) -> Node | None:
    for current in walk(node):
        if tag and current.tag != tag:
            continue
        if class_name and not has_class(current, class_name):
            continue
        return current
    return None


def descendants(node: Node, *, tag: str | None = None, class_name: str | None = None) -> list[Node]:
    found = []
    for current in walk(node):
        if current is node:
            continue
        if tag and current.tag != tag:
            continue
        if class_name and not has_class(current, class_name):
            continue
        found.append(current)
    return found


def normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", html.unescape(value or ""))
    plain = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(re.sub(r"[^a-z0-9%]+", " ", plain.lower()).split())


def protocol_key(value: str) -> str:
    return "".join(char for char in value.upper() if char.isalnum())


def direct_article_url(article: dict[str, str]) -> str:
    """Converte links descobertos em URLs diretas quando o portal é previsível.

    O Google Notícias não expõe a URL original no RSS. A CNN, porém, usa no
    endereço o título normalizado da matéria; reconstruí-lo nos dá uma fonte
    jornalística verificável sem depender do redirecionamento do Google.
    """
    if normalize(article.get("source", "")) != "cnn brasil":
        return ""
    title = re.sub(r"\s+-\s+CNN Brasil\s*$", "", article.get("title", ""), flags=re.I)
    title = re.sub(r"(?<=\d)[,.](?=\d)", "", title).replace("º", "o").replace("ª", "a")
    decomposed = unicodedata.normalize("NFKD", title)
    plain = "".join(char for char in decomposed if not unicodedata.combining(char))
    slug = re.sub(r"[^a-z0-9]+", "-", plain.lower()).strip("-")
    return f"https://www.cnnbrasil.com.br/eleicoes/{slug}/" if slug else ""


def percentage(value: str) -> float:
    number = float(re.search(r"\d+(?:[.,]\d+)?", value).group(0).replace(",", "."))
    return int(number) if number.is_integer() else number


def fetch(url: str) -> str:
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=35) as response:
        # Alguns servidores declaram ISO-8859-1 apesar de entregarem UTF-8.
        # As páginas monitoradas usam UTF-8; tentar esse codec primeiro evita
        # corromper nomes e, por consequência, a conciliação de candidatos.
        payload = response.read()
        content_type = response.headers.get_content_type()
        if content_type == "application/pdf" or payload.startswith(b"%PDF-"):
            if PdfReader is None:
                raise OSError("fonte em PDF exige a dependência pypdf")
            try:
                reader = PdfReader(io.BytesIO(payload))
                # O modo layout mantém cada candidato perto do respectivo
                # percentual em tabelas e gráficos horizontais.
                return "\n".join(
                    page.extract_text(extraction_mode="layout") or ""
                    for page in reader.pages
                )
            except Exception as error:
                raise OSError(f"não foi possível extrair o PDF: {error}") from error
        try:
            return payload.decode("utf-8")
        except UnicodeDecodeError:
            return payload.decode("cp1252", "replace")


def fetch_cached(cache: dict[str, str | OSError], url: str) -> str:
    """Busca cada URL uma única vez, inclusive quando a resposta falha."""
    if url not in cache:
        try:
            cache[url] = fetch(url)
        except OSError as error:
            cache[url] = error
    cached = cache[url]
    if isinstance(cached, OSError):
        raise cached
    return cached


def parse_tree(markup: str) -> Node:
    parser = TreeParser()
    parser.feed(markup)
    return parser.root


def index_links(markup: str, since: date) -> list[str]:
    # O componente pagina apenas 60 linhas no HTML visível, mas o Astro envia
    # todos os identificadores no estado serializado. Ler os slugs desse estado
    # evita que pesquisas da segunda página em diante desapareçam da automação.
    decoded = html.unescape(markup)
    slugs = set(re.findall(r"([a-z0-9-]+_2026-\d{2}-\d{2}_T1_[A-Z0-9]+_\d+)", decoded, re.I))
    links: set[str] = set()
    for slug in slugs:
        date_match = re.search(r"_(2026-\d{2}-\d{2})_T1_", slug)
        if not date_match or date.fromisoformat(date_match.group(1)) < since:
            continue
        if slug.startswith("gov-") and not slug.startswith(("gov-sp-", "gov-mg-")):
            continue
        if slug.startswith(("sen-", "pres-")):
            continue
        links.add(urllib.parse.urljoin(INDEX_URL, f"{slug}/"))
    return sorted(links)


def result_list(node: Node) -> dict[str, float]:
    values: dict[str, float] = {}
    for item in descendants(node, tag="li", class_name="linha"):
        name = first(item, tag="span", class_name="nome")
        value = first(item, tag="span", class_name="valor")
        if name and value:
            values[name.text().removesuffix(first(name, tag="span", class_name="sigla").text() if first(name, tag="span", class_name="sigla") else "").strip()] = percentage(value.text())
    return values


def parse_detail(url: str, markup: str) -> dict:
    root = parse_tree(markup)
    eye = first(root, tag="p", class_name="olho")
    title = first(root, tag="h1")
    placar = first(root, tag="ol", class_name="placar")
    source_block = first(root, tag="p", class_name="fonte")
    if not all((eye, title, placar, source_block)):
        raise ValueError(f"ficha incompleta: {url}")

    tech: dict[str, str] = {}
    for pair in descendants(root, tag="div", class_name="par"):
        term, value = first(pair, tag="dt"), first(pair, tag="dd")
        if term and value:
            tech[normalize(term.text())] = value.text()

    residual = 0.0
    aggregate = first(root, tag="div", class_name="agregados")
    if aggregate:
        residual = sum(percentage(item.text()) for item in descendants(aggregate, class_name="ag-val"))

    source_anchor = first(source_block, tag="a")
    scenario_label = first(root, tag="p", class_name="cenario")
    related = [
        urllib.parse.urljoin(url, anchor.attrs["href"])
        for anchor in descendants(root, tag="a", class_name="tb-link")
        if "_T2_" in anchor.attrs.get("href", "")
    ]
    scope = normalize(eye.text())
    round_match = re.search(r"(1|2)o? turno", scope)
    return {
        "url": url,
        "scope": scope,
        "pollster": title.text(),
        "protocol": protocol_key(tech.get("registro no tse", "")),
        "sample": int(re.sub(r"\D", "", tech.get("entrevistas", "0"))),
        "margin": percentage(tech.get("margem de erro", "0")),
        "method": tech.get("coleta", "não informado").capitalize(),
        "round": int(round_match.group(1)) if round_match else 0,
        "spontaneous": bool(scenario_label and "espontanea" in normalize(scenario_label.text())),
        "end": re.search(r"2026-\d{2}-\d{2}", url).group(0),
        "results": result_list(placar),
        "undecided": residual,
        "source": source_anchor.attrs.get("href", ""),
        "related": related,
    }


def election_for(detail: dict) -> str | None:
    scope = detail["scope"]
    if scope.startswith("presidente nacional"):
        return "president-br"
    if scope.startswith("governador sao paulo"):
        return "governor-sp"
    if scope.startswith("governador minas gerais"):
        return "governor-mg"
    return None


def candidate_id(election_id: str, name: str) -> str | None:
    normalized = normalize(name)
    for identifier, aliases in CANDIDATE_ALIASES[election_id].items():
        if normalized in aliases:
            return identifier
    return None


def scenario_for(detail: dict, election_id: str, catalog: dict[str, dict]) -> tuple[str, dict[str, float]] | None:
    mapped = {
        identifier: value
        for name, value in detail["results"].items()
        if (identifier := candidate_id(election_id, name))
    }
    if detail["round"] == 1:
        candidates = set(mapped)
        choices = [item for item in catalog.values() if item["round"] == 1]
        # Listas de candidatos mudam frequentemente. Reaproveitar apenas uma
        # correspondência exata impede que a ausência de um único nome descarte
        # ou atribua silenciosamente a pesquisa a outro cenário.
        for item in choices:
            expected = set(item["candidates"])
            if expected == candidates:
                return item["id"], {key: mapped[key] for key in item["candidates"]}
        if len(candidates) >= 2:
            scenario_id = "first-auto-" + "-".join(sorted(candidates))
            return scenario_id, mapped
        return None

    pair = set(mapped)
    for item in catalog.values():
        expected = set(item["candidates"])
        if item["round"] == 2 and expected == pair:
            return item["id"], {key: mapped[key] for key in item["candidates"]}
    return None


def source_text(markup: str) -> str:
    root = parse_tree(markup)
    for node in list(walk(root)):
        if node.tag in {"script", "style", "nav", "footer"}:
            node.children.clear()
            node.chunks.clear()
    return normalize(root.text())


def percentage_pattern(value: float) -> str:
    rendered = f"{float(value):g}"
    if "." not in rendered:
        return re.escape(rendered)
    whole, decimal = rendered.split(".", 1)
    # ``source_text`` normaliza vírgulas e pontos para espaços. Aceitar também
    # a pontuação original torna a função segura para futuros extratores.
    return rf"{re.escape(whole)}(?:\s+|[,.]){re.escape(decimal)}"


def source_confirms_metadata(detail: dict, text: str) -> bool:
    if detail["protocol"] not in protocol_key(text):
        return False
    if str(detail["sample"]) not in text.replace(" ", "").replace(".", ""):
        return False
    return True


def source_confirms_candidate(election_id: str, identifier: str, value: float, text: str) -> bool:
    aliases = CANDIDATE_ALIASES[election_id][identifier]
    rendered = percentage_pattern(value)
    return any(
        re.search(rf"{re.escape(alias)}.{{0,100}}{rendered}\s*%", text)
        or re.search(rf"{rendered}\s*%.{{0,100}}{re.escape(alias)}", text)
        for alias in aliases
    )


def source_confirms(detail: dict, election_id: str, results: dict[str, float], markup: str) -> bool:
    text = source_text(markup)
    if not source_confirms_metadata(detail, text):
        return False
    for identifier, value in results.items():
        if not source_confirms_candidate(election_id, identifier, value, text):
            return False
    return True


def load_discovered_articles() -> list[dict[str, str]]:
    if not DISCOVERY_FILE.is_file():
        return []
    return json.loads(DISCOVERY_FILE.read_text(encoding="utf-8")).get("pending", [])


def confirming_discovered_source(
    detail: dict,
    election_id: str,
    results: dict[str, float],
    articles: list[dict[str, str]],
    cache: dict[str, str | OSError],
) -> tuple[str, str] | None:
    """Localiza uma matéria descoberta que confirme integralmente a ficha.

    A conciliação exige mesma eleição, mesmo instituto, publicação até sete
    dias depois do campo e confirmação do protocolo, amostra e de todos os
    percentuais. Assim uma notícia semelhante não pode ser ligada por engano.
    """
    end = date.fromisoformat(detail["end"])
    pollster = normalize(detail["pollster"])
    for article in articles:
        if article.get("election") != election_id:
            continue
        article_pollster = normalize(article.get("pollster", ""))
        if not article_pollster or not (
            article_pollster in pollster or pollster in article_pollster
        ):
            continue
        try:
            published = date.fromisoformat(article.get("published", ""))
        except ValueError:
            continue
        if not end <= published <= end + timedelta(days=7):
            continue
        url = direct_article_url(article)
        if not url:
            continue
        try:
            markup = fetch_cached(cache, url)
        except OSError:
            continue
        if source_confirms(detail, election_id, results, markup):
            return url, markup
    return None


def source_confirmed_scenario(
    detail: dict,
    election_id: str,
    catalog: dict[str, dict],
    markup: str,
) -> tuple[str, dict[str, float]] | None:
    """Escolhe a lista mais completa cujos números constam na fonte.

    Algumas fichas trazem uma lista maior com um único número divergente da
    publicação. Nesses casos é preferível incorporar o subconjunto integralmente
    confirmado a perder toda a pesquisa.
    """
    mapped = {
        identifier: value
        for name, value in detail["results"].items()
        if (identifier := candidate_id(election_id, name))
    }
    text = source_text(markup)
    if not source_confirms_metadata(detail, text):
        return None
    confirmed = {
        identifier
        for identifier, value in mapped.items()
        if source_confirms_candidate(election_id, identifier, value, text)
    }
    choices = [item for item in catalog.values() if item["round"] == detail["round"]]
    choices.sort(key=lambda item: (-len(item["candidates"]), item["id"]))
    for item in choices:
        expected = set(item["candidates"])
        if expected.issubset(confirmed):
            return item["id"], {key: mapped[key] for key in item["candidates"]}
    return None


def field_start(source: str, end: str) -> str:
    normalized = normalize(source)
    cross_month = re.search(
        r"(?:entre os dias|dos dias|entre|de)\s+(\d{1,2})(?:o)?\s+de\s+([a-z]+)"
        r"\s+(?:e|a)\s+\d{1,2}(?:o)?\s+de\s+[a-z]+(?:\s+de\s+(20\d{2}))?",
        normalized,
    )
    if cross_month and cross_month.group(2) in MONTHS:
        year = int(cross_month.group(3)) if cross_month.group(3) else date.fromisoformat(end).year
        return date(year, MONTHS[cross_month.group(2)], int(cross_month.group(1))).isoformat()
    patterns = (
        r"(?:entre os dias|dos dias|entre|de)\s+(\d{1,2})(?:o)?\s+(?:e|a)\s+\d{1,2}(?:o)?\s+de\s+([a-z]+)(?:\s+de\s+(20\d{2}))?",
        r"(?:entre os dias|dos dias|entre|de)\s+(\d{1,2})(?:o)?\s+(?:e|a)\s+\d{1,2}(?:o)?\s+([a-z]+)(?:\s+(20\d{2}))?",
    )
    for pattern in patterns:
        match = re.search(pattern, normalized)
        if match and match.group(2) in MONTHS:
            year = int(match.group(3)) if match.group(3) else date.fromisoformat(end).year
            return date(year, MONTHS[match.group(2)], int(match.group(1))).isoformat()
    return end


def published_date(markup: str, end: str) -> str:
    candidates = re.findall(
        r"(?:datePublished|article:published_time).{0,120}?(2026-\d{2}-\d{2})",
        markup,
        re.I | re.S,
    )
    end_date = date.fromisoformat(end)
    valid = [date.fromisoformat(item) for item in candidates if end_date <= date.fromisoformat(item) <= end_date + timedelta(days=7)]
    return min(valid).isoformat() if valid else (end_date + timedelta(days=1)).isoformat()


def format_field(start: str, end: str) -> str:
    months = ("jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez")
    a, b = date.fromisoformat(start), date.fromisoformat(end)
    if a.month != b.month:
        return f"{a.day} {months[a.month - 1]}–{b.day} {months[b.month - 1]}"
    return f"{a.day}–{b.day} {months[b.month - 1]}"


def ensure_scenario(database: dict, catalog: dict[str, dict], scenario_id: str, results: dict[str, float]) -> None:
    if scenario_id in catalog:
        return
    scenario = {
        "id": scenario_id,
        "round": 1,
        "label": f"Lista com {len(results)} nomes",
        "comparisonGroup": "first-round",
        "comparisonLabel": "Primeiro turno — listas integradas",
        "candidates": list(results),
    }
    database["scenarios"].append(scenario)
    catalog[scenario_id] = scenario


def load_catalogs() -> tuple[list[dict], dict[str, dict]]:
    elections = json.loads(ELECTIONS_FILE.read_text(encoding="utf-8"))["elections"]
    databases = {}
    for election in elections:
        path = ROOT / election["dataFile"]
        databases[election["id"]] = json.loads(path.read_text(encoding="utf-8"))
    return elections, databases


def load_official_records(elections: list[dict]) -> dict[str, dict[str, dict]]:
    records: dict[str, dict[str, dict]] = {}
    for election in elections:
        election_records: dict[str, dict] = {}
        for key, bucket in (("metadataFile", "records"), ("monitorFile", "pending")):
            path = ROOT / election.get(key, "")
            if not path.is_file():
                continue
            payload = json.loads(path.read_text(encoding="utf-8"))
            election_records.update(payload.get(bucket, {}))
        records[election["id"]] = election_records
    return records


def merge_scenarios(existing: dict, incoming: dict[str, dict], catalog: dict[str, dict]) -> bool:
    """Complementa uma pesquisa já conhecida sem manter sua versão truncada."""
    before = json.dumps(existing["scenarios"], ensure_ascii=False, sort_keys=True)
    incoming_ids = set(incoming)
    for old_id in list(existing["scenarios"]):
        if old_id in incoming_ids or old_id not in catalog:
            continue
        old = catalog[old_id]
        old_candidates = set(old["candidates"])
        for new_id in incoming_ids:
            new = catalog[new_id]
            new_candidates = set(new["candidates"])
            same_group = (
                old.get("comparisonGroup", old_id)
                == new.get("comparisonGroup", new_id)
            )
            # Substituição conservadora: a nova ficha difere por exatamente
            # um nome. Listas alternativas (por exemplo, com/sem Marçal)
            # continuam coexistindo quando ambas foram efetivamente testadas.
            if same_group and old_candidates < new_candidates and len(new_candidates - old_candidates) == 1:
                del existing["scenarios"][old_id]
                break
    existing["scenarios"].update(incoming)
    after = json.dumps(existing["scenarios"], ensure_ascii=False, sort_keys=True)
    return before != after


def ingest(lookback_days: int = 10) -> tuple[int, list[str]]:
    elections, databases = load_catalogs()
    official_records = load_official_records(elections)
    election_by_id = {item["id"]: item for item in elections}
    grouped: dict[tuple[str, str], list[dict]] = {}
    warnings: list[str] = []
    since = date.today() - timedelta(days=lookback_days)
    document_cache: dict[str, str | OSError] = {}
    discovered_articles = load_discovered_articles()

    for url in index_links(fetch_cached(document_cache, INDEX_URL), since):
        slug = url.rstrip("/").rsplit("/", 1)[-1]
        if slug.startswith(("gov-", "sen-")) and not slug.startswith(("gov-sp-", "gov-mg-")):
            continue
        try:
            primary = parse_detail(url, fetch_cached(document_cache, url))
            election_id = election_for(primary)
            if not election_id:
                continue
            if not re.fullmatch(r"[A-Z]{2}\d{9}", primary["protocol"]):
                if primary["source"]:
                    source_markup = fetch_cached(document_cache, primary["source"])
                    protocol_match = re.search(r"\b(BR|SP|MG)[-\s]?(\d{5})[/\s-]?(2026)\b", source_markup, re.I)
                    if protocol_match:
                        primary["protocol"] = protocol_key("".join(protocol_match.groups()))
            if not re.fullmatch(r"[A-Z]{2}\d{9}", primary["protocol"]):
                warnings.append(f"{url}: protocolo não localizado")
                continue
            details = [primary]
            details.extend(
                parse_detail(related, fetch_cached(document_cache, related))
                for related in primary["related"]
            )
            grouped.setdefault((election_id, primary["protocol"]), []).extend(details)
        except (OSError, ValueError, AttributeError) as error:
            warnings.append(f"{url}: {error}")

    changed = 0
    for (election_id, protocol), details in grouped.items():
        database = databases[election_id]
        catalog = {item["id"]: item for item in database["scenarios"]}
        scenarios: dict[str, dict] = {}
        scenario_quality: dict[str, int] = {}
        source_labels: dict[str, str] = {}
        source_markup_for_dates = ""
        for detail in details:
            if detail.get("spontaneous"):
                continue
            mapped = scenario_for(detail, election_id, catalog)
            if not mapped or not detail["source"]:
                continue
            scenario_id, results = mapped
            try:
                markup = fetch_cached(document_cache, detail["source"])
            except OSError as error:
                warnings.append(f"{detail['source']}: {error}")
                markup = ""
            verified_source = detail["source"]
            exact_confirmation = bool(markup) and source_confirms(
                detail, election_id, results, markup
            )
            if not exact_confirmation:
                discovered = confirming_discovered_source(
                    detail,
                    election_id,
                    results,
                    discovered_articles,
                    document_cache,
                )
                if discovered:
                    verified_source, markup = discovered
                    exact_confirmation = True
            if not exact_confirmation:
                confirmed = source_confirmed_scenario(detail, election_id, catalog, markup)
                if not confirmed:
                    warnings.append(f"{protocol}/{scenario_id}: fonte não confirmou todos os valores")
                    continue
                scenario_id, results = confirmed
            elif detail["round"] == 1:
                ensure_scenario(database, catalog, scenario_id, results)
            quality = 1 if exact_confirmation else 0
            if scenario_quality.get(scenario_id, -1) > quality:
                continue
            source_markup_for_dates = source_markup_for_dates or markup
            source_labels[verified_source] = urllib.parse.urlparse(verified_source).netloc.removeprefix("www.")
            scenarios[scenario_id] = {
                "results": results,
                "undecided": detail["undecided"],
                "resultSource": verified_source,
                "resultSourceLabel": f"{source_labels[verified_source]} — resultado publicado",
            }
            scenario_quality[scenario_id] = quality
        if not scenarios:
            continue

        primary = details[0]
        existing = next((item for item in database["polls"] if item["protocol"] == protocol), None)
        if existing:
            updated = merge_scenarios(existing, scenarios, catalog)
            official = official_records.get(election_id, {}).get(protocol, {})
            detected_start = official.get("fieldStart") or field_start(
                source_text(source_markup_for_dates), primary["end"]
            )
            if detected_start < existing.get("start", primary["end"]):
                existing["start"] = detected_start
                existing["field"] = format_field(detected_start, existing["end"])
                updated = True
            if updated:
                changed += 1
            continue

        official = official_records.get(election_id, {}).get(protocol, {})
        start = official.get("fieldStart") or field_start(
            source_text(source_markup_for_dates), primary["end"]
        )
        source = next(iter(source_labels))
        poll = {
            "id": max((item["id"] for item in database["polls"]), default=0) + 1,
            "pollster": primary["pollster"],
            "publication": source_labels[source],
            "protocol": protocol,
            "published": official.get("disclosureDate") or published_date(
                source_markup_for_dates, primary["end"]
            ),
            "start": start,
            "end": primary["end"],
            "field": format_field(start, primary["end"]),
            "sample": primary["sample"],
            "margin": primary["margin"],
            "confidence": 95,
            "method": primary["method"],
            "resultSource": source,
            "resultSourceLabel": f"{source_labels[source]} — resultado publicado",
            "scenarios": scenarios,
        }
        database["polls"].append(poll)
        database["polls"].sort(key=lambda item: item["end"], reverse=True)
        changed += 1

    for election_id, database in databases.items():
        path = ROOT / election_by_id[election_id]["dataFile"]
        path.write_text(json.dumps(database, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return changed, list(dict.fromkeys(warnings))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lookback-days", type=int, default=10)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        added, warnings = ingest(args.lookback_days)
    except OSError as error:
        print(f"Aviso: índice estruturado indisponível: {error}", file=sys.stderr)
        return 0
    print(f"Ingestão automática: {added} pesquisa(s) incorporada(s).")
    for warning in warnings:
        print(f"Aviso: {warning}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
