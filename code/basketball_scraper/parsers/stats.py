from basketball_scraper.domain.contracts import HtmlParser
from basketball_scraper.domain.models import Page, ParseContext, ParsedData, ParseError

from .html import (
    body_rows,
    linked_entity,
    number,
    provenance,
    require_columns,
    required_table,
    text,
)

STAT_ALIASES = {
    "games": ("g", "games"),
    "games_started": ("gs", "games_started"),
    "minutes_per_game": ("mp_per_g", "mp_per_game"),
    "field_goals_per_game": ("fg_per_g", "fg_per_game"),
    "field_goal_attempts_per_game": ("fga_per_g", "fga_per_game"),
    "field_goal_pct": ("fg_pct",),
    "three_pointers_per_game": ("fg3_per_g", "fg3_per_game"),
    "three_point_attempts_per_game": ("fg3a_per_g", "fg3a_per_game"),
    "three_point_pct": ("fg3_pct",),
    "two_pointers_per_game": ("fg2_per_g", "fg2_per_game"),
    "two_point_attempts_per_game": ("fg2a_per_g", "fg2a_per_game"),
    "two_point_pct": ("fg2_pct",),
    "effective_field_goal_pct": ("efg_pct",),
    "free_throws_per_game": ("ft_per_g", "ft_per_game"),
    "free_throw_attempts_per_game": ("fta_per_g", "fta_per_game"),
    "free_throw_pct": ("ft_pct",),
    "offensive_rebounds_per_game": ("orb_per_g", "orb_per_game"),
    "defensive_rebounds_per_game": ("drb_per_g", "drb_per_game"),
    "rebounds_per_game": ("trb_per_g", "trb_per_game"),
    "assists_per_game": ("ast_per_g", "ast_per_game"),
    "steals_per_game": ("stl_per_g", "stl_per_game"),
    "blocks_per_game": ("blk_per_g", "blk_per_game"),
    "turnovers_per_game": ("tov_per_g", "tov_per_game"),
    "personal_fouls_per_game": ("pf_per_g", "pf_per_game"),
    "points_per_game": ("pts_per_g", "pts_per_game"),
}
ADVANCED_ALIASES = {
    "per": ("per",),
    "true_shooting_pct": ("ts_pct",),
    "usage_pct": ("usg_pct",),
    "ws": ("ws",),
    "ws_per_48": ("ws_per_48",),
    "bpm": ("bpm",),
    "vorp": ("vorp",),
}


def season_identity(row, page: Page, context: ParseContext):
    player = linked_entity(row, "player", page.url)
    if player is None:
        return None
    team = linked_entity(row, "team", page.url)
    label = text(row, "team_id", "team_name_abbr")
    if not label:
        raise ParseError(f"Missing team for {player[0]} in {page.url}")
    is_total = label == "TOT" or (label.endswith("TM") and label[:-2].isdigit())
    if not is_total and team is None:
        raise ParseError(f"Missing team link for {player[0]} in {page.url}")
    return (
        player,
        team,
        {
            "season": context.season,
            "player_id": player[0],
            "team_id": None if is_total else team[0],
            "team_label": label,
            "is_total": is_total,
        },
    )


class PerGameParser(HtmlParser):
    def parse(self, page: Page, context: ParseContext) -> ParsedData:
        table = required_table(page, "per_game_stats", "per_game")
        require_columns(
            page,
            table,
            (
                ("name_display", "player"),
                ("team_id", "team_name_abbr"),
                ("pos", "position"),
                ("age",),
                *STAT_ALIASES.values(),
            ),
        )
        result = ParsedData()
        for tr in body_rows(table):
            identity = season_identity(tr, page, context)
            if identity is None:
                continue
            player, team, row = identity
            result.player_urls[player[0]] = player[1]
            if team and not row["is_total"]:
                result.team_urls[team[0]] = team[1]
            row.update(
                {
                    "age": number(text(tr, "age"), integer=True),
                    "position": text(tr, "pos", "position"),
                    **provenance(page),
                }
            )
            row.update(
                {
                    name: number(
                        text(tr, *aliases), integer=name in ("games", "games_started")
                    )
                    for name, aliases in STAT_ALIASES.items()
                }
            )
            result.rows.append(row)
        if not result.rows:
            raise ParseError(f"No player statistics in {page.url}")
        return result


class AdvancedParser(HtmlParser):
    def parse(self, page: Page, context: ParseContext) -> ParsedData:
        table = required_table(page, "advanced", "advanced_stats")
        require_columns(
            page,
            table,
            (
                ("player", "name_display"),
                ("team_id", "team_name_abbr"),
                *ADVANCED_ALIASES.values(),
            ),
        )
        result = ParsedData()
        for tr in body_rows(table):
            identity = season_identity(tr, page, context)
            if identity is None:
                continue
            _, _, row = identity
            row.update(
                {
                    name: number(text(tr, *aliases))
                    for name, aliases in ADVANCED_ALIASES.items()
                }
            )
            row.update(
                {
                    "advanced_source_url": page.url,
                    "advanced_fetched_at": page.fetched_at,
                }
            )
            result.rows.append(row)
        if not result.rows:
            raise ParseError(f"No advanced statistics in {page.url}")
        return result
