from dataclasses import dataclass, field

type Scalar = str | int | float | bool | None
type Row = dict[str, Scalar]


class ScraperError(Exception):
    pass


class FetchError(ScraperError):
    pass


class ParseError(ScraperError):
    pass


class ValidationError(ScraperError):
    pass


@dataclass(frozen=True)
class Page:
    url: str
    fetched_at: str
    html: str


@dataclass(frozen=True)
class ParseContext:
    season: int | None = None
    team_id: str | None = None


@dataclass
class ParsedData:
    rows: list[Row] = field(default_factory=list)
    player_urls: dict[str, str] = field(default_factory=dict)
    team_urls: dict[str, str] = field(default_factory=dict)


STAT_FIELDS = (
    "games",
    "games_started",
    "minutes_per_game",
    "field_goals_per_game",
    "field_goal_attempts_per_game",
    "field_goal_pct",
    "three_pointers_per_game",
    "three_point_attempts_per_game",
    "three_point_pct",
    "two_pointers_per_game",
    "two_point_attempts_per_game",
    "two_point_pct",
    "effective_field_goal_pct",
    "free_throws_per_game",
    "free_throw_attempts_per_game",
    "free_throw_pct",
    "offensive_rebounds_per_game",
    "defensive_rebounds_per_game",
    "rebounds_per_game",
    "assists_per_game",
    "steals_per_game",
    "blocks_per_game",
    "turnovers_per_game",
    "personal_fouls_per_game",
    "points_per_game",
)
ADVANCED_FIELDS = (
    "per",
    "true_shooting_pct",
    "usage_pct",
    "ws",
    "ws_per_48",
    "bpm",
    "vorp",
)
PROVENANCE = ("source_url", "fetched_at")
SCHEMAS = {
    "players": (
        "player_id",
        "name",
        "birth_date",
        "height_cm",
        "weight_kg",
        "birth_country",
        "nationality",
        "measurement_scope",
        *PROVENANCE,
    ),
    "player_seasons": (
        "season",
        "player_id",
        "team_id",
        "team_label",
        "is_total",
        "age",
        "position",
        *STAT_FIELDS,
        *ADVANCED_FIELDS,
        *PROVENANCE,
        "advanced_source_url",
        "advanced_fetched_at",
    ),
    "mvp_votes": (
        "season",
        "player_id",
        "rank",
        "first_place_votes",
        "points_won",
        "points_max",
        "vote_share",
        *PROVENANCE,
    ),
    "champions": ("season", "team_id", "team_name", *PROVENANCE),
    "team_rosters": (
        "season",
        "team_id",
        "player_id",
        "position",
        "age",
        "experience_years",
        "height_cm",
        "weight_kg",
        *PROVENANCE,
        "age_source_url",
        "age_fetched_at",
    ),
}
