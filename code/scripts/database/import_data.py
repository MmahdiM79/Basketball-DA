from pathlib import Path

import pandas as pd
from database_models import (
    Champions,
    Experience,
    Mvp_Votes,
    Player_of_season,
    Players,
    Position,
    Season,
    Team,
    engine,
)

ROOT = Path(__file__).resolve().parents[3]
DATA_FOLDER = ROOT / "data" / "database"


class DataImporter:
    def __init__(self, engine, folder=DATA_FOLDER):
        self.engine = engine
        self.folder = Path(folder)

    def import_table(self, file_name, model):
        df = pd.read_csv(self.folder / file_name, encoding="utf-8-sig")
        df.to_sql(model.__tablename__, self.engine, if_exists="append", index=False)
        print(f"{model.__tablename__}: {len(df)} rows imported")

    def import_all(self):
        # Parent tables first, then the tables that reference them.
        tables = [
            ("seasons.csv", Season),
            ("positions.csv", Position),
            ("team.csv", Team),
            ("players.csv", Players),
            ("champions.csv", Champions),
            ("mvp_votes.csv", Mvp_Votes),
            ("experience.csv", Experience),
            ("player_season.csv", Player_of_season),
        ]
        for file_name, model in tables:
            self.import_table(file_name, model)


if __name__ == "__main__":
    DataImporter(engine).import_all()
