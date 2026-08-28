#!/usr/bin/env python3
"""Atualiza próximas divulgações a partir de uma agenda pública estruturada.

O PesqEle continua sendo a referência dos protocolos. Esta etapa existe para
cobrir atrasos do espelho diário consumido pelo workflow e só aceita recortes
cujo cargo e território correspondam exatamente às eleições cadastradas.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import unicodedata
import urllib.request
from datetime import date, timedelta
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ELECTIONS_FILE = ROOT / "data" / "elections.json"
AGENDA_URL = "https://depoisdas17.com.br/agenda/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; Pulso26Bot/1.0; +https://github.com/rafaujo/eleicoes-2026-pesquisas)",
    "Accept-Language": "pt-BR,pt;q=0.9",
}
MONTHS = {
    "jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
    "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12,
}


def normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", html.unescape(value or ""))
    plain = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(re.sub(r"[^a-z0-9]+", " ", plain.lower()).split())


def protocol_key(value: str) -> str:
    return "".join(char for char in value.upper() if char.isalnum())


def parse_disclosure_date(value: str) -> str | None:
    match = re.search(r"(\d{1,2})\s+de\s+([a-zç.]+)\s+de\s+(20\d{2})", normalize(value))
    if not match:
        return None
    month = MONTHS.get(match.group(2)[:3])
    if not month:
        return None
    return date(int(match.group(3)), month, int(match.group(1))).isoformat()


def parse_field(value: str, year: int) -> tuple[str, str] | None:
    numbers = [int(item) for item in re.findall(r"\d+", value)]
    if len(numbers) != 4:
        return None
    start_day, start_month, end_day, end_month = numbers
    start_year = year - 1 if start_month > end_month else year
    try:
        return date(start_year, start_month, start_day).isoformat(), date(year, end_month, end_day).isoformat()
    except ValueError:
        return None


class AgendaParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.current_date: str | None = None
        self.rows: list[dict] = []
        self.in_row = False
        self.in_cell = False
        self.cells: list[str] = []
        self.chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            self.in_row = True
            self.cells = []
        elif self.in_row and tag in {"th", "td"}:
            self.in_cell = True
            self.chunks = []

    def handle_data(self, data: str) -> None:
        if self.in_cell and data.strip():
            self.chunks.append(data.strip())

    def handle_endtag(self, tag: str) -> None:
        if self.in_row and self.in_cell and tag in {"th", "td"}:
            self.cells.append(" ".join(self.chunks))
            self.in_cell = False
            self.chunks = []
        elif tag == "tr" and self.in_row:
            self._finish_row()
            self.in_row = False

    def _finish_row(self) -> None:
        disclosure = parse_disclosure_date(" ".join(self.cells))
        if disclosure:
            self.current_date = disclosure
            return
        if not self.current_date or len(self.cells) < 7:
            return
        protocol = protocol_key(self.cells[6])
        field = parse_field(self.cells[3], date.fromisoformat(self.current_date).year)
        if not re.fullmatch(r"[A-Z]{2}\d{9}", protocol) or not field:
            return
        sample_digits = re.sub(r"\D", "", self.cells[2])
        self.rows.append({
            "protocol": protocol,
            "disclosureDate": self.current_date,
            "institute": self.cells[0],
            "scope": self.cells[1],
            "sample": int(sample_digits) if sample_digits else 0,
            "fieldStart": field[0],
            "fieldEnd": field[1],
        })


def parse_agenda(markup: str) -> list[dict]:
    parser = AgendaParser()
    parser.feed(markup)
    return parser.rows


def fetch(url: str = AGENDA_URL) -> str:
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=35) as response:
        payload = response.read()
    try:
        return payload.decode("utf-8")
    except UnicodeDecodeError:
        return payload.decode("cp1252", "replace")


def matches_election(scope: str, election: dict) -> bool:
    normalized = normalize(scope)
    tse = election["tse"]
    office = normalize(str(tse["office"]))
    jurisdiction = normalize(str(tse["jurisdiction"]))
    if office == "presidente":
        return normalized == "presidente nacional"
    if office == "governador":
        territory = normalize(str(election["context"]))
        return normalized.startswith("governador") and normalized.endswith(territory) and jurisdiction != "br"
    return False


def curated_protocols(election: dict) -> set[str]:
    database = json.loads((ROOT / election["dataFile"]).read_text(encoding="utf-8"))
    return {poll["protocol"] for poll in database["polls"]}


def update_agenda(rows: list[dict], today: date, days: int) -> tuple[int, int]:
    catalog = json.loads(ELECTIONS_FILE.read_text(encoding="utf-8"))
    changed = 0
    total = 0
    end = today + timedelta(days=days)
    for election in catalog["elections"]:
        monitor_path = ROOT / election["monitorFile"]
        monitor = json.loads(monitor_path.read_text(encoding="utf-8"))
        curated = curated_protocols(election)
        upcoming = {}
        for row in rows:
            disclosure = date.fromisoformat(row["disclosureDate"])
            if not today <= disclosure <= end or row["protocol"] in curated or not matches_election(row["scope"], election):
                continue
            upcoming[row["protocol"]] = {
                "protocol": row["protocol"],
                "fieldStart": row["fieldStart"],
                "fieldEnd": row["fieldEnd"],
                "disclosureDate": row["disclosureDate"],
                "sample": row["sample"],
                "company": row["institute"],
                "tradeName": row["institute"],
                "contractors": [],
                "source": AGENDA_URL,
            }
        upcoming = dict(sorted(upcoming.items()))
        total += len(upcoming)
        if monitor.get("upcoming", {}) != upcoming or monitor.get("agendaSource") != AGENDA_URL:
            monitor["agendaSource"] = AGENDA_URL
            monitor["upcoming"] = upcoming
            monitor_path.write_text(json.dumps(monitor, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            changed += 1
    return changed, total


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=10)
    parser.add_argument("--today", type=date.fromisoformat, default=date.today())
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        rows = parse_agenda(fetch())
    except OSError as error:
        print(f"Aviso: agenda pública indisponível: {error}")
        return 0
    changed, total = update_agenda(rows, args.today, args.days)
    print(f"Agenda pública: {total} próxima(s) pesquisa(s), {changed} monitor(es) atualizado(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
