# Database

## Summary
The SQLite database `DB/basketbal_da.db` is built from the project CSV files. The tables are defined as SQLAlchemy models in `code/scripts/database/database_models.py`, and `code/scripts/database/import_data.py` fills them.

## Files
- `code/scripts/database/database_models.py`: table definitions. Running or importing it creates the database file and the tables.
- `code/scripts/database/import_data.py`: the `DataImporter` class, which reads the CSV files and fills the tables.
- `data/database/`: the eight input CSV files. This lowercase path is the canonical directory; the older `data/DataBase/` export directory has been consolidated here.
- ` notebooks/DataBase.ipynb`: reads the scraper exports from `data/processed/` and regenerates all eight files in `data/database/`. Paths are resolved from the project or notebook directory.

## Tables

| Table | CSV file | Content |
| --- | --- | --- |
| `seasons` | `seasons.csv` | Seasons (2020-2026) |
| `positions` | `positions.csv` | Player positions |
| `team` | `team.csv` | Teams |
| `players` | `players.csv` | Player bio data: birth date, height, weight, country |
| `player_season` | `player_season.csv` | Per-game and advanced statistics for each player, season, and team |
| `champions` | `champions.csv` | Champion team of each season |
| `mvp_votes` | `mvp_votes.csv` | MVP voting results per season |
| `experience` | `experience.csv` | Experience years for each player, team, and season |

## Relationships
- `player_season` references `seasons`, `players`, `team`, and `positions`.
- `mvp_votes` references `seasons` and `players`.
- `experience` references `seasons`, `players`, and `team`.
- `champions` references `seasons` and `team`; each season has one champion row, so both relationships are one-to-one.
- Columns marked NOT NULL in the project diagram are declared with `nullable=False`: the four foreign keys of `player_season`, the two foreign keys of `mvp_votes`, the three foreign keys of `experience`, and `seasons.season`.

## What the import does
- Loads the generated CSV values as they are. The import does not clean or convert anything; `make clean-data` prepares the analysis exports afterward.
- Loads parent tables first (`seasons`, `positions`, `team`, `players`), then the child tables, because of the foreign keys.
- Stores empty cells as NULL. Percentage columns such as `three_point_pct` are empty when a player had no attempts.

## How to run
From the project root:

```bash
make import-db
```

This runs `uv run --locked python code/scripts/database/import_data.py` using the pandas and SQLAlchemy versions recorded in `uv.lock`. Without `make`, run the same command directly.

The import appends rows. Delete `DB/basketbal_da.db` before running it again, otherwise it fails with `UNIQUE constraint failed`.

## Known notes
- Table names are the same as in the earlier version of the database, because the [data cleaning](../data_cleaning/README.md) script and the notebooks read tables by name. They differ from the names in the project diagram (`season`, `position`, `Team`, `Players`, `player_of_season`).
- The database file is generated from the CSV files in `data/database/`, so rebuild it from them instead of editing it by hand.