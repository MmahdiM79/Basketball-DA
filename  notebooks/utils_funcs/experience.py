import pandas as pd


def attach_experience(data: pd.DataFrame, experience: pd.DataFrame) -> pd.DataFrame:
    by_season = experience[
        ["player_id", "season", "experience_years"]
    ].drop_duplicates()
    return data.merge(
        by_season,
        on=["player_id", "season"],
        how="left",
        validate="many_to_one",
    )
