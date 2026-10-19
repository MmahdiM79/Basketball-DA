from urllib.parse import urljoin

from basketball_scraper.domain.contracts import DatasetWriter, HtmlParser, PageSource
from basketball_scraper.domain.models import (
    ParseContext,
    ParsedData,
    Row,
    ValidationError,
)

from .config import Settings
from .validation import DatasetValidator, season_key, unique_index

BASE_URL = "https://www.basketball-reference.com"


class BasketballCollector:
    def __init__(
        self,
        source: PageSource,
        parsers: dict[str, HtmlParser],
        writer: DatasetWriter,
        validator: DatasetValidator,
    ):
        self._source = source
        self._parsers = parsers
        self._writer = writer
        self._validator = validator

    def _parse(self, name: str, url: str, context: ParseContext) -> ParsedData:
        return self._parsers[name].parse_url(self._source, url, context)

    def run(self, settings: Settings) -> dict[str, int]:
        selected = set(settings.datasets)
        datasets: dict[str, list[Row]] = {name: [] for name in settings.datasets}
        player_urls = {}
        needs_stats = bool(selected & {"players", "player_seasons", "team_rosters"})
        seasons = range(settings.start_season, settings.end_season + 1)
        for season in seasons:
            print(f"Collecting NBA season {season - 1}-{season}")
            context = ParseContext(season=season)
            stats = ParsedData()
            if needs_stats:
                stats = self._parse(
                    "per_game",
                    f"{BASE_URL}/leagues/NBA_{season}_per_game.html",
                    context,
                )
                player_urls.update(stats.player_urls)
            if "player_seasons" in selected:
                advanced = self._parse(
                    "advanced",
                    f"{BASE_URL}/leagues/NBA_{season}_advanced.html",
                    context,
                )
                indexed = unique_index(advanced.rows, season_key, "advanced statistics")
                base_index = unique_index(stats.rows, season_key, "per-game statistics")
                if indexed.keys() != base_index.keys():
                    raise ValidationError(
                        f"Per-game and advanced player/team rows do not match for {season}"
                    )
                for key, row in base_index.items():
                    row.update(indexed[key])
                datasets["player_seasons"].extend(stats.rows)
            if "mvp_votes" in selected:
                votes = self._parse(
                    "mvp", f"{BASE_URL}/awards/awards_{season}.html", context
                )
                datasets["mvp_votes"].extend(votes.rows)
                player_urls.update(votes.player_urls)
            if "champions" in selected:
                champions = self._parse("champions", f"{BASE_URL}/leagues/", context)
                datasets["champions"].extend(champions.rows)
            if "team_rosters" in selected:
                teams = set(stats.team_urls)
                if not teams:
                    raise ValidationError(f"No teams found for {season}")
                age_by_team = {
                    (row["team_id"], row["player_id"]): row
                    for row in stats.rows
                    if not row["is_total"]
                }
                for team_id in sorted(teams):
                    roster = self._parse(
                        "roster",
                        f"{BASE_URL}/teams/{team_id}/{season}.html",
                        ParseContext(season, team_id),
                    )
                    for row in roster.rows:
                        stat = age_by_team.get((team_id, row["player_id"]))
                        if stat:
                            row.update(
                                {
                                    "age": stat["age"],
                                    "age_source_url": stat["source_url"],
                                    "age_fetched_at": stat["fetched_at"],
                                }
                            )
                    datasets["team_rosters"].extend(roster.rows)
                    player_urls.update(roster.player_urls)
        if "players" in selected:
            total = len(player_urls)
            for index, (player_id, url) in enumerate(
                sorted(player_urls.items()), start=1
            ):
                print(f"Collecting player {index}/{total}: {player_id}")
                profile = self._parse("profile", urljoin(BASE_URL, url), ParseContext())
                datasets["players"].extend(profile.rows)
        self._validator.validate(datasets, seasons)
        self._writer.write(datasets, settings.output_dir)
        counts = {name: len(rows) for name, rows in datasets.items()}
        print(f"Collection completed: {counts}")
        return counts
