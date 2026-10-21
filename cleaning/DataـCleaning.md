# Data Cleaning

## Summary
A basic cleaning script that reads the SQLite database (`DB/basketbal_da.db`) and writes one cleaned CSV file per table.

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
- `team_id` in the `exprience` table does not match `team_id` in `player_season`, so it should not be used. Join `exprience` on `player_id` and `season_id` instead.
- Table names `exprience` and `positons` keep their original spelling from the database.

## How to run
From the project root:

    uv run --with pandas python cleaning/cleaning_data.py

## Output
One file per table, saved next to the script in `cleaning/`, named `<table>_clean.csv`.