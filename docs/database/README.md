# Database

## Summary
The SQLite database `DB/basketbal_da.db` is built from the project CSV files. The tables are defined as SQLAlchemy models in `code/scripts/database/database_models.py`, and `code/scripts/database/import_data.py` fills them. The schema follows the project diagram.

## Files
- `code/scripts/database/database_models.py`: table definitions. Running or importing it creates the database file and the tables.
- `code/scripts/database/import_data.py`: the `DataImporter` class, which reads the CSV files and fills the tables.
- `data/database/`: the eight input CSV files.

## Tables

| Table | CSV file | Content |
| --- | --- | --- |
| `season` | `seasons.csv` | Seasons (2020-2026) |
| `position` | `positions.csv` | Player positions |
| `Team` | `team.csv` | Teams |
| `Players` | `players.csv` | Player bio data: birth date, height, weight, country |
| `player_of_season` | `player_season.csv` | Per-game and advanced statistics for each player, season, and team |
| `champions` | `champions.csv` | Champion team of each season |
| `mvp_votes` | `mvp_votes.csv` | MVP voting results per season |
| `experience` | `experience.csv` | Experience years for each player, team, and season |

## Relationships
- `player_of_season` references `season`, `Players`, `Team`, and `position`.
- `mvp_votes` references `season` and `Players`.
- `experience` references `season`, `Players`, and `Team`.
- `champions` references `season` and `Team`; each season has one champion row, so both relationships are one-to-one.
- Columns marked NOT NULL in the project diagram are declared with `nullable=False`: the four foreign keys of `player_of_season`, the two foreign keys of `mvp_votes`, the three foreign keys of `experience`, and `season.season`.

## What the import does
- Loads the CSV values as they are. The files are already cleaned, so the import does not clean or convert anything.
- Loads parent tables first (`season`, `position`, `Team`, `Players`), then the child tables, because of the foreign keys.
- Stores empty cells as NULL. Percentage columns such as `three_point_pct` are empty when a player had no attempts.

## How to run
From the project root:

```bash
make import-db
```

This runs `uv run --with pandas --with sqlalchemy python code/scripts/database/import_data.py`. The `--with` options install the packages for this run only, so the project dependencies stay unchanged. Without `make`, run `python code/scripts/database/import_data.py` directly.

The import appends rows. Delete `DB/basketbal_da.db` before running it again, otherwise it fails with `UNIQUE constraint failed`.

## Known notes
- Table names follow the project diagram. Code that reads the database by table name, such as the [data cleaning](../data_cleaning/README.md) script and the notebooks, must use these names.
- The database file is generated from the CSV files in `data/database/`, so rebuild it from them instead of editing it by hand.