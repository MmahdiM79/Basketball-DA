import math
import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Comment

from basketball_scraper.domain.models import Page, ParseError


def document(page: Page) -> BeautifulSoup:
    soup = BeautifulSoup(page.html, "html.parser")
    for comment in soup.find_all(string=lambda item: isinstance(item, Comment)):
        if "<table" in comment:
            comment.replace_with(BeautifulSoup(str(comment), "html.parser"))
    return soup


def required_table(page: Page, *ids: str):
    soup = document(page)
    for table_id in ids:
        table = soup.find("table", id=table_id)
        if table is not None:
            return table
    raise ParseError(
        f"Missing table {ids} in {page.url}; the page structure may have changed"
    )


def cell(row, *names: str):
    for name in names:
        found = row.find(["td", "th"], attrs={"data-stat": name})
        if found is not None:
            return found
    return None


def text(row, *names: str) -> str | None:
    found = cell(row, *names)
    value = found.get_text(" ", strip=True) if found is not None else ""
    return value or None


def number(value: str | None, integer: bool = False):
    if value is None or value.strip() in ("", "-", "—", "N/A"):
        return None
    try:
        numeric = float(value.replace(",", "").replace("%", "").strip())
        if integer:
            if not numeric.is_integer():
                raise ValueError("not an integer")
            return int(numeric)
        if not math.isfinite(numeric):
            raise ValueError("not finite")
        return numeric
    except ValueError as exc:
        raise ParseError(f"Invalid numeric value: {value!r}") from exc


def linked_entity(row, kind: str, base_url: str):
    pattern = (
        r"/players/[a-z]/([^/]+)\.html"
        if kind == "player"
        else r"/teams/([A-Z0-9]+)/(?:(\d{4})\.html)?"
    )
    for link in row.find_all("a", href=True):
        url = urljoin(base_url, link["href"])
        if urlparse(url).netloc != "www.basketball-reference.com":
            continue
        match = re.fullmatch(pattern, urlparse(url).path)
        if match:
            return match.group(1), url, link.get_text(" ", strip=True)
    return None


def body_rows(table):
    body = table.find("tbody") or table
    return [
        row
        for row in body.find_all("tr", recursive=False)
        if "thead" not in row.get("class", []) and row.find("td") is not None
    ]


def require_columns(page: Page, table, columns: tuple[tuple[str, ...], ...]) -> None:
    available = {item.get("data-stat") for item in table.find_all(["td", "th"])}
    for aliases in columns:
        if not available.intersection(aliases):
            raise ParseError(f"Missing column {aliases} in {page.url}")


def provenance(page: Page):
    return {"source_url": page.url, "fetched_at": page.fetched_at}


def height_cm(value: str | None):
    if not value:
        return None
    match = re.fullmatch(r"(\d+)[-′']\s*(\d+)[″\"]?", value.strip())
    if match:
        return round((int(match[1]) * 12 + int(match[2])) * 2.54, 2)
    metric = re.fullmatch(r"([\d.]+)\s*cm", value.strip())
    if metric:
        return number(metric[1])
    raise ParseError(f"Unrecognized height: {value!r}")


def weight_kg(value: str | None):
    if not value:
        return None
    match = re.fullmatch(r"([\d.]+)\s*(lb|lbs|kg)?", value.strip())
    if not match:
        raise ParseError(f"Unrecognized weight: {value!r}")
    weight = number(match[1])
    return round(weight if match[2] == "kg" else weight * 0.45359237, 2)
