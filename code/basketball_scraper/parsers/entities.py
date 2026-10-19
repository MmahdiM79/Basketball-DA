import re
from datetime import date
from urllib.parse import parse_qs, urlparse

from basketball_scraper.domain.contracts import HtmlParser
from basketball_scraper.domain.models import Page, ParseContext, ParsedData, ParseError

from .html import (
    body_rows,
    document,
    height_cm,
    linked_entity,
    number,
    provenance,
    require_columns,
    required_table,
    text,
    weight_kg,
)


class MvpVotesParser(HtmlParser):
    def parse(self, page: Page, context: ParseContext) -> ParsedData:
        table = required_table(page, "mvp")
        aliases = {
            "rank": ("rank",),
            "first_place_votes": ("votes_first",),
            "points_won": ("points_won",),
            "points_max": ("points_max",),
            "vote_share": ("award_share",),
        }
        require_columns(page, table, (("player", "name_display"), *aliases.values()))
        result = ParsedData()
        for tr in body_rows(table):
            player = linked_entity(tr, "player", page.url)
            if not player:
                continue
            row = {"season": context.season, "player_id": player[0], **provenance(page)}
            for name, names in aliases.items():
                value = text(tr, *names)
                if name == "rank" and value:
                    value = value.removesuffix("T")
                row[name] = number(value, integer=name in ("rank", "first_place_votes"))
            result.rows.append(row)
            result.player_urls[player[0]] = player[1]
        if not result.rows:
            raise ParseError(f"No MVP votes in {page.url}")
        return result


class ChampionsParser(HtmlParser):
    def parse(self, page: Page, context: ParseContext) -> ParsedData:
        table = required_table(page, "stats", "league_index")
        require_columns(page, table, (("season",), ("champion",), ("lg_id",)))
        result = ParsedData()
        for tr in body_rows(table):
            if text(tr, "lg_id") != "NBA":
                continue
            season = tr.find(["th", "td"], attrs={"data-stat": "season"})
            link = season.find("a", href=True) if season else None
            match = re.search(r"/NBA_(\d{4})\.html", link["href"]) if link else None
            if not match or int(match[1]) != context.season:
                continue
            champion = tr.find("td", attrs={"data-stat": "champion"})
            team = linked_entity(champion, "team", page.url) if champion else None
            if team is None:
                raise ParseError(
                    f"No NBA champion listed for {context.season} in {page.url}"
                )
            result.rows.append(
                {
                    "season": context.season,
                    "team_id": team[0],
                    "team_name": team[2],
                    **provenance(page),
                }
            )
            result.team_urls[team[0]] = team[1]
        if len(result.rows) != 1:
            raise ParseError(
                f"Expected one NBA champion for {context.season} in {page.url}"
            )
        return result


class RosterParser(HtmlParser):
    def parse(self, page: Page, context: ParseContext) -> ParsedData:
        table = required_table(page, "roster")
        require_columns(
            page, table, (("player", "name_display"), ("pos",), ("years_experience",))
        )
        result = ParsedData()
        for tr in body_rows(table):
            player = linked_entity(tr, "player", page.url)
            if not player:
                continue
            experience = text(tr, "years_experience")
            row = {
                "season": context.season,
                "team_id": context.team_id,
                "player_id": player[0],
                "position": text(tr, "pos"),
                "age": None,
                "experience_years": 0
                if experience == "R"
                else number(experience, integer=True),
                "height_cm": height_cm(text(tr, "height")),
                "weight_kg": weight_kg(text(tr, "weight")),
                **provenance(page),
            }
            result.rows.append(row)
            result.player_urls[player[0]] = player[1]
        if not result.rows:
            raise ParseError(f"No roster entries in {page.url}")
        return result


class PlayerProfileParser(HtmlParser):
    def parse(self, page: Page, context: ParseContext) -> ParsedData:
        soup = document(page)
        info = soup.find(id="meta")
        match = re.fullmatch(r"/players/[a-z]/([^/]+)\.html", urlparse(page.url).path)
        if info is None or match is None:
            raise ParseError(f"Missing player profile in {page.url}")
        heading = info.find("h1")
        if heading is None or not heading.get_text(strip=True):
            raise ParseError(f"Missing player name in {page.url}")
        birth = info.find(id="necro-birth")
        birthday = birth.get("data-birth") if birth else None
        if birthday:
            try:
                birthday = date.fromisoformat(birthday).isoformat()
            except ValueError as exc:
                raise ParseError(
                    f"Invalid birth date in {page.url}: {birthday}"
                ) from exc

        def item_value(name):
            item = info.find(attrs={"itemprop": name})
            return item.get_text(" ", strip=True) if item else None

        height = item_value("height")
        weight = item_value("weight")
        if not height or not weight:
            for paragraph in info.find_all("p"):
                measurements = re.search(
                    r"(\d+[-′']\s*\d+)[″\"]?\s*,?\s*(\d+(?:\.\d+)?\s*lbs?)\b",
                    paragraph.get_text(" ", strip=True),
                )
                if measurements:
                    height = height or measurements[1]
                    weight = weight or measurements[2]
                    break
        country = info.find(attrs={"itemprop": "birthPlace"})
        if country is None and birth is not None:
            country = birth.find_parent("p")
        country_link = (
            country.find("a", href=re.compile(r"country=")) if country else None
        )
        country_code = (
            parse_qs(urlparse(country_link["href"]).query).get("country", [None])[0]
            if country_link
            else None
        )
        row = {
            "player_id": match[1],
            "name": heading.get_text(" ", strip=True),
            "birth_date": birthday,
            "height_cm": height_cm(height),
            "weight_kg": weight_kg(weight),
            "birth_country": country_code.upper() if country_code else None,
            "nationality": item_value("nationality"),
            "measurement_scope": "profile_snapshot",
            **provenance(page),
        }
        return ParsedData(rows=[row])
