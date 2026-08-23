#!/usr/bin/env python3
"""Descobre divulgações recentes de pesquisas em feeds públicos de notícias."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ELECTIONS_FILE = ROOT / "data" / "elections.json"
STATE_FILE = ROOT / "data" / "result-discovery.json"
NEWS_ENDPOINT = "https://news.google.com/rss/search"
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9",
}
POLLSTER_ALIASES = {
    "atlasintel": "AtlasIntel",
    "atlas": "AtlasIntel",
    "cnt mda": "CNT/MDA",
    "datafolha": "Datafolha",
    "futura": "Futura",
    "gerp": "GERP",
    "ideia": "Ideia",
    "ipsos ipec": "Ipsos-Ipec",
    "nexus": "Nexus",
    "palver": "Palver",
    "parana pesquisa": "Paraná Pesquisas",
    "parana pesquisas": "Paraná Pesquisas",
    "poderdata": "PoderData",
    "quaest": "Quaest",
    "real time big data": "Real Time Big Data",
    "verita": "Veritá",
    "vox brasil": "Vox Brasil",
}
ELECTION_RULES = {
    "president-br": {
        "queries": (
            'pesquisa eleitoral presidente 2026 Lula "Flávio Bolsonaro"',
            'pesquisa 2026 Lula Flávio Caiado Zema Renan',
        ),
        "terms": ("presidente", "presidencial", "lula", "flavio bolsonaro", "marcal"),
    },
    "governor-sp": {
        "queries": (
            'pesquisa eleitoral governador "São Paulo" 2026',
            'pesquisa Tarcísio Haddad 2026',
        ),
        "terms": ("governo de sp", "governador de sao paulo", "tarcisio", "haddad"),
    },
    "governor-mg": {
        "queries": (
            'pesquisa eleitoral governador "Minas Gerais" 2026',
            'pesquisa Cleitinho Kalil Patrus 2026',
        ),
        "terms": ("governo de mg", "governador de minas", "cleitinho", "kalil"),
    },
}
RESULT_TERMS = (
    "lidera",
    "empata",
    "empate",
    "perde",
    "vence",
    "tem ",
    "marca ",
    "aponta",
)
EDITORIAL_ONLY_TERMS = (
    "agregador",
    "aprovacao",
    "aprovado",
    "avaliam a gestao",
    "comparativo",
    "desaprovacao",
    "desaprovado",
    "o que dizem as pesquisas",
    "popularidade",
    "voto feminino",
)
SOCIAL_SOURCES = ("facebook.com", "instagram.com", "tiktok.com", "youtube.com")
PRESIDENT_REGIONAL_TERMS = (
    "governo de ",
    "governador",
    "no acre",
    "no amapa",
    "no amazonas",
    "na bahia",
    "no ceara",
    "no distrito federal",
    "no df",
    "em df",
    "no espirito santo",
    "em goias",
    "no maranhao",
    "no mato grosso",
    "em minas gerais",
    "em mg",
    "no para",
    "no pa",
    "na paraiba",
    "no parana",
    "no pr",
    "em pernambuco",
    "em pe",
    "no piaui",
    "no rio de janeiro",
    "no rio grande do norte",
    "no rio grande do sul",
    "em rondonia",
    "em roraima",
    "em santa catarina",
    "em sao paulo",
    "em sp",
    "em sergipe",
    "no tocantins",
    "estado em que",
)
SOURCE_PRIORITY = {
    "Folha de S.Paulo": 0,
    "G1": 1,
    "CNN Brasil": 2,
    "Valor Econômico": 3,
    "Estadão": 4,
    "Poder360": 5,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, default=STATE_FILE)
    parser.add_argument("--summary", type=Path)
    parser.add_argument("--github-output", type=Path)
    parser.add_argument("--lookback-days", type=int, default=4)
    return parser.parse_args()


def normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value or "")
    plain = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(re.sub(r"[^a-z0-9%]+", " ", plain.lower()).split())


def detect_pollster(title: str, source: str = "") -> str:
    haystack = normalize(f"{title} {source}")
    for alias, canonical in sorted(POLLSTER_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
        if alias in haystack:
            return canonical
    return ""


def matches_election(title: str, election_id: str, source: str = "") -> bool:
    normalized = normalize(title)
    rule = ELECTION_RULES.get(election_id)
    if not rule:
        return False

    if normalize(source) in {normalize(item) for item in SOCIAL_SOURCES}:
        return False

    # Exigir um instituto identificável evita que análises, agregadores e
    # republicações vagas entrem na fila como se fossem um levantamento novo.
    # Os aliases são explícitos e ampliáveis conforme novos institutos surgem.
    if not detect_pollster(title, source):
        return False
    if any(term in normalized for term in EDITORIAL_ONLY_TERMS):
        return False
    if election_id == "president-br" and any(
        term in normalized for term in PRESIDENT_REGIONAL_TERMS
    ):
        return False
    if not any(term in normalized for term in rule["terms"]):
        return False
    has_result = bool(re.search(r"\d+(?:[,.]\d+)?\s*%", title)) or any(
        term in normalized for term in RESULT_TERMS
    )
    return has_result


def article_key(article: dict[str, str]) -> str:
    identity = f"{normalize(article['title'])}|{article.get('published', '')}|{article.get('source', '')}"
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20]


def parse_feed(xml_bytes: bytes, election_id: str) -> list[dict[str, str]]:
    root = ET.fromstring(xml_bytes)
    articles: list[dict[str, str]] = []
    for item in root.findall("./channel/item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        source_node = item.find("source")
        source = (source_node.text or "").strip() if source_node is not None else ""
        published_raw = (item.findtext("pubDate") or "").strip()
        if not title or not link or not matches_election(title, election_id, source):
            continue
        try:
            published = parsedate_to_datetime(published_raw).astimezone(timezone.utc).date().isoformat()
        except (TypeError, ValueError):
            published = ""
        article = {
            "election": election_id,
            "title": title,
            "url": link,
            "source": source,
            "published": published,
            "pollster": detect_pollster(title, source),
        }
        article["key"] = article_key(article)
        articles.append(article)
    return articles


def news_url(query: str, lookback_days: int) -> str:
    params = urllib.parse.urlencode({
        "q": f"{query} when:{lookback_days}d",
        "hl": "pt-BR",
        "gl": "BR",
        "ceid": "BR:pt-419",
    })
    return f"{NEWS_ENDPOINT}?{params}"


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers=BROWSER_HEADERS)
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def load_databases(elections: list[dict]) -> dict[str, list[dict]]:
    databases: dict[str, list[dict]] = {}
    for election in elections:
        path = ROOT / str(election["dataFile"])
        data = json.loads(path.read_text(encoding="utf-8"))
        databases[str(election["id"])] = data.get("polls", [])
    return databases


def already_curated(article: dict[str, str], polls: list[dict]) -> bool:
    pollster = normalize(article.get("pollster", ""))
    if not pollster:
        return False
    try:
        article_date = date.fromisoformat(article["published"])
    except (KeyError, ValueError):
        article_date = None
    for poll in polls:
        if pollster not in normalize(str(poll.get("pollster", ""))):
            continue
        if article_date is None:
            return True
        try:
            poll_date = date.fromisoformat(str(poll.get("published", "")))
        except ValueError:
            continue
        if abs((article_date - poll_date).days) <= 2:
            return True
    return False


def deduplicate_disclosures(articles: list[dict[str, str]]) -> list[dict[str, str]]:
    """Mantém uma fonte representativa por instituto, eleição e divulgação."""
    selected: list[dict[str, str]] = []
    ordered = sorted(
        articles,
        key=lambda item: (SOURCE_PRIORITY.get(item.get("source", ""), 99), item["key"]),
    )
    for article in ordered:
        pollster = normalize(article.get("pollster", ""))
        published = article.get("published", "")
        duplicate = False
        if pollster and published:
            article_date = date.fromisoformat(published)
            for current in selected:
                if current["election"] != article["election"]:
                    continue
                if normalize(current.get("pollster", "")) != pollster:
                    continue
                current_date = date.fromisoformat(current["published"])
                if abs((article_date - current_date).days) <= 1:
                    duplicate = True
                    break
        else:
            duplicate = any(current["key"] == article["key"] for current in selected)
        if not duplicate:
            selected.append(article)
    return selected


def write_summary(path: Path, pending: list[dict[str, str]]) -> None:
    lines = [
        "## Divulgações encontradas automaticamente",
        "",
        "Esta fila cruza buscas públicas recentes com as pesquisas já curadas. "
        "Os links são candidatos editoriais e precisam de conferência antes de entrarem na média.",
        "",
    ]
    if not pending:
        lines.append("Nenhuma divulgação nova aguarda revisão.")
    else:
        for article in pending:
            label = article.get("pollster") or article.get("source") or "Fonte não identificada"
            published = article.get("published") or "data não identificada"
            lines.extend([
                f"- **{label} · {article['election']} · {published}**",
                f"  - [{article['title']}]({article['url']})",
            ])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_github_output(path: Path, values: dict[str, object]) -> None:
    with path.open("a", encoding="utf-8") as output:
        for key, value in values.items():
            output.write(f"{key}={str(value).lower() if isinstance(value, bool) else value}\n")


def main() -> int:
    args = parse_args()
    catalog = json.loads(ELECTIONS_FILE.read_text(encoding="utf-8"))
    elections = catalog.get("elections", [])
    databases = load_databases(elections)
    state = {"schemaVersion": 1, "seenKeys": [], "pending": []}
    if args.state.is_file():
        state = json.loads(args.state.read_text(encoding="utf-8"))
    before_pending = list(state.get("pending", []))
    seen = set(state.get("seenKeys", []))
    pending_by_key = {item["key"]: item for item in before_pending}

    failures: list[str] = []
    for election in elections:
        election_id = str(election["id"])
        rule = ELECTION_RULES.get(election_id)
        if not rule:
            continue
        articles: list[dict[str, str]] = []
        for query in rule["queries"]:
            try:
                articles.extend(
                    parse_feed(fetch(news_url(str(query), args.lookback_days)), election_id)
                )
            except (OSError, ET.ParseError, ValueError) as error:
                failures.append(f"{election_id} ({query}): {error}")
        for article in articles:
            key = article["key"]
            seen.add(key)
            if not already_curated(article, databases.get(election_id, [])):
                pending_by_key[key] = article

    reclassified: list[dict[str, str]] = []
    for stored in pending_by_key.values():
        article = dict(stored)
        article["pollster"] = detect_pollster(
            article.get("title", ""), article.get("source", "")
        )
        if not matches_election(
            article.get("title", ""),
            article.get("election", ""),
            article.get("source", ""),
        ):
            continue
        if already_curated(article, databases.get(article["election"], [])):
            continue
        reclassified.append(article)
    pending = deduplicate_disclosures(reclassified)
    pending.sort(key=lambda item: (item.get("published", ""), item["key"]), reverse=True)
    new_state = {"schemaVersion": 1, "seenKeys": sorted(seen), "pending": pending}
    changed = new_state != state
    queue_changed = pending != before_pending
    if changed:
        args.state.parent.mkdir(parents=True, exist_ok=True)
        args.state.write_text(json.dumps(new_state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.summary:
        write_summary(args.summary, pending)
    if args.github_output:
        write_github_output(args.github_output, {
            "changed": changed,
            "queue_changed": queue_changed,
            "pending_count": len(pending),
        })
    print(f"Descoberta pública: {len(pending)} divulgação(ões) pendente(s).")
    for failure in failures:
        print(f"Aviso: busca indisponível em {failure}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
