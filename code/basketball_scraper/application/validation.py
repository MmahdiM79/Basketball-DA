from collections import Counter

from basketball_scraper.domain.models import SCHEMAS, Row, ValidationError


def season_key(row: Row):
    return row["season"], row["player_id"], row["team_id"], row["is_total"]


def unique_index(rows: list[Row], key, label: str) -> dict:
    result = {}
    for row in rows:
        identity = key(row)
        if identity in result:
            raise ValidationError(f"Duplicate {label}: {identity}")
        result[identity] = row
    return result


class DatasetValidator:
    def validate(self, datasets: dict[str, list[Row]], seasons: range) -> None:
        keys = {
            "players": lambda row: row["player_id"],
            "player_seasons": season_key,
            "mvp_votes": lambda row: (row["season"], row["player_id"]),
            "champions": lambda row: row["season"],
            "team_rosters": lambda row: (
                row["season"],
                row["team_id"],
                row["player_id"],
            ),
        }
        for name, rows in datasets.items():
            if not rows:
                raise ValidationError(f"Dataset is empty: {name}")
            unique_index(rows, keys[name], name)
            for row in rows:
                unexpected = set(row) - set(SCHEMAS[name])
                if unexpected:
                    raise ValidationError(f"Unexpected fields in {name}: {unexpected}")
                for required in (
                    "source_url",
                    "fetched_at",
                    "player_id" if name != "champions" else "team_id",
                ):
                    if not row.get(required):
                        raise ValidationError(f"Missing {required} in {name}: {row}")
                for numeric in ("height_cm", "weight_kg", "age"):
                    if row.get(numeric) is not None and row[numeric] <= 0:
                        raise ValidationError(f"Invalid {numeric} in {name}: {row}")
                if (
                    row.get("experience_years") is not None
                    and row["experience_years"] < 0
                ):
                    raise ValidationError(f"Negative experience in {name}: {row}")
            if name != "players" and {row["season"] for row in rows} != set(seasons):
                raise ValidationError(f"Incomplete season coverage in {name}")
        stats = datasets.get("player_seasons", [])
        for row in stats:
            if row.get("games") is None or row["games"] < 0 or row.get("age") is None:
                raise ValidationError(f"Missing or invalid season games/age: {row}")
            if row["is_total"] != (row["team_id"] is None):
                raise ValidationError(f"Invalid total/team identity: {row}")
        totals = Counter(
            (row["season"], row["player_id"]) for row in stats if row["is_total"]
        )
        if any(count > 1 for count in totals.values()):
            raise ValidationError("Multiple aggregate rows for the same player-season")
        team_counts = Counter(
            (row["season"], row["player_id"]) for row in stats if not row["is_total"]
        )
        if any(
            count > 1 and identity not in totals
            for identity, count in team_counts.items()
        ):
            raise ValidationError(
                "A multi-team player-season is missing its aggregate row"
            )
        for row in datasets.get("mvp_votes", []):
            if row.get("rank") is None or row["rank"] < 1:
                raise ValidationError(f"Invalid MVP rank: {row}")
            if row.get("vote_share") is None or not 0 <= row["vote_share"] <= 1:
                raise ValidationError(f"Invalid MVP vote share: {row}")
            if (
                row.get("points_won") is None
                or row.get("points_max") is None
                or not 0 <= row["points_won"] <= row["points_max"]
            ):
                raise ValidationError(f"Invalid MVP vote points: {row}")
        if "players" in datasets:
            player_ids = {row["player_id"] for row in datasets["players"]}
            for name in ("player_seasons", "mvp_votes", "team_rosters"):
                missing = {
                    row["player_id"] for row in datasets.get(name, [])
                } - player_ids
                if missing:
                    raise ValidationError(
                        f"Unresolved players in {name}: {sorted(missing)}"
                    )
        if "team_rosters" in datasets:
            memberships = {
                (row["season"], row["team_id"], row["player_id"])
                for row in datasets["team_rosters"]
            }
            missing = {
                (row["season"], row["team_id"], row["player_id"])
                for row in stats
                if not row["is_total"]
            } - memberships
            if missing:
                raise ValidationError(
                    f"Season players missing from team rosters: {sorted(missing)}"
                )
            teams = {
                (row["season"], row["team_id"]) for row in datasets["team_rosters"]
            }
            for champion in datasets.get("champions", []):
                if (champion["season"], champion["team_id"]) not in teams:
                    raise ValidationError(f"Champion roster missing: {champion}")
