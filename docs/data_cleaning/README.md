# Data Cleaning

## Summary
A basic cleaning script (`code/scripts/cleaning/cleaning_data.py`) that reads the SQLite database (`DB/basketbal_da.db`) and writes one cleaned CSV file per table.

## What it does
For every table:
- Trims leading and trailing whitespace in text columns
- Converts empty strings to missing values
- Removes fully duplicated rows

Only for `Players`:
- Converts `birth_date` from `M/D/YYYY` to `YYYY-MM-DD`
- Rounds `height_cm` and `weight_kg` to one decimal place

## What we checked before cleaning
- `Players` has no missing values, and heights and weights are in a realistic range
- No duplicate player names
- Foreign keys in `player_season` are valid (no orphan players or teams)
- Key columns in `player_season` have no missing values
- Missing percentage columns (e.g. `three_point_pct`) only occur when a player had zero attempts, so they are left empty on purpose

## Known notes
- `player_season` has "total" rows (`is_total = 1`, teams `2TM`, `3TM`, `4TM`) for players who played for several teams in one season. These rows are kept; filter on `is_total` when needed.
- `experience.team_id` and `player_season.team_id` now reference the same `team` IDs. Join team-specific experience on `player_id`, `season_id`, and `team_id`; players who changed teams can have several rows per season.
- The current database uses the table names `experience` and `positions`. Previously exported files named `exprience_clean.csv` and `positons_clean.csv` retain their old names until regenerated.
- `champions` stores one champion team per season, with foreign keys to `seasons` and `team`. The hypothesis notebook reads the database directly using a read-only connection.

## How to run
From the project root:

```bash
make clean-data
```

This runs `uv run --with pandas python code/scripts/cleaning/cleaning_data.py`. The `--with pandas` option installs pandas for this run only, so the project dependencies stay unchanged.

## Output
One file per table, saved in `data/cleaned/`, named `<table>_clean.csv`.