from basketball_scraper.domain.contracts import HtmlParser, PageSource
from basketball_scraper.domain.models import (
    SCHEMAS,
    ParseContext,
    ParsedData,
    ValidationError,
)
from basketball_scraper.parsers.entities import (
    ChampionsParser,
    MvpVotesParser,
    PlayerProfileParser,
    RosterParser,
)
from basketball_scraper.parsers.stats import AdvancedParser, PerGameParser

from .collector import BASE_URL
from .config import Settings
from .validation import DatasetValidator, season_key, unique_index


class SmokeCheck:
    def __init__(self, source: PageSource, validator: DatasetValidator):
        self._source = source
        self._validator = validator

    def _read(
        self, name: str, parser: HtmlParser, url: str, context: ParseContext
    ) -> ParsedData:
        result = parser.parse(self._source.get(url), context)
        print(f"Parsed {name}: {len(result.rows)} rows")
        return result

    def run(self, settings: Settings) -> dict[str, int]:
        if settings.start_season != settings.end_season:
            raise ValidationError("Smoke checks require exactly one season")
        if set(settings.datasets) != set(SCHEMAS):
            raise ValidationError("Smoke checks require all five datasets")
        season = settings.start_season
        context = ParseContext(season)
        seasons = range(season, season + 1)
        stats = self._read(
            "per-game statistics",
            PerGameParser(),
            f"{BASE_URL}/leagues/NBA_{season}_per_game.html",
            context,
        )
        advanced = self._read(
            "advanced statistics",
            AdvancedParser(),
            f"{BASE_URL}/leagues/NBA_{season}_advanced.html",
            context,
        )
        base_index = unique_index(stats.rows, season_key, "per-game statistics")
        advanced_index = unique_index(advanced.rows, season_key, "advanced statistics")
        if base_index.keys() != advanced_index.keys():
            raise ValidationError("Per-game and advanced player/team rows do not match")
        for key, row in base_index.items():
            row.update(advanced_index[key])
        self._validator.validate({"player_seasons": stats.rows}, seasons)
        votes = self._read(
            "MVP votes",
            MvpVotesParser(),
            f"{BASE_URL}/awards/awards_{season}.html",
            context,
        )
        self._validator.validate({"mvp_votes": votes.rows}, seasons)
        champions = self._read(
            "champions", ChampionsParser(), f"{BASE_URL}/leagues/", context
        )
        self._validator.validate({"champions": champions.rows}, seasons)
        team_id = champions.rows[0]["team_id"]
        roster = self._read(
            "champion roster",
            RosterParser(),
            f"{BASE_URL}/teams/{team_id}/{season}.html",
            ParseContext(season, team_id),
        )
        self._validator.validate(
            {"team_rosters": roster.rows, "champions": champions.rows}, seasons
        )
        roster_ids = {row["player_id"] for row in roster.rows}
        team_players = {
            row["player_id"] for row in stats.rows if row["team_id"] == team_id
        }
        if not team_players or not team_players <= roster_ids:
            raise ValidationError("Champion season players missing from the roster")
        player_id = min(roster_ids)
        if player_id not in roster.player_urls:
            raise ValidationError("Missing profile link for the selected roster player")
        profile = self._read(
            "player profile",
            PlayerProfileParser(),
            roster.player_urls[player_id],
            ParseContext(),
        )
        self._validator.validate({"players": profile.rows}, seasons)
        if len(profile.rows) != 1 or profile.rows[0]["player_id"] != player_id:
            raise ValidationError("Profile does not match the selected roster player")
        for field in ("name", "birth_date", "height_cm", "weight_kg"):
            if not profile.rows[0].get(field):
                raise ValidationError(f"Missing profile field: {field}")
        counts = {
            "per_game": len(stats.rows),
            "advanced": len(advanced.rows),
            "mvp_votes": len(votes.rows),
            "champions": len(champions.rows),
            "team_rosters": len(roster.rows),
            "players": len(profile.rows),
        }
        print(f"Smoke check passed for season {season}: {counts}")
        return counts
