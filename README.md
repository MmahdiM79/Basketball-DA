# Basketball-DA

For a concise explanation of the scraper workflow, entities, relationships, configuration, and commands, see the [scraper documentation](docs/scraper/README.md).

## Setup

This project uses Python 3.14 and `uv` to manage its virtual environment and dependencies.

### Install uv

Follow the [official uv installation guide](https://docs.astral.sh/uv/getting-started/installation/) for instructions for your operating system.

### Set up the environment

Clone the repository and enter the project directory:

```bash
git clone https://github.com/MmahdiM79/Basketball-DA.git
cd Basketball-DA
```

Run this command for the initial setup and after each `git pull`:

```bash
uv sync --locked
```

This downloads Python 3.14 if needed, creates the `.venv` virtual environment, and installs the dependency versions recorded in `uv.lock`.

Use `uv run python` followed by a script path to run a Python file in this environment. To check the environment's Python version:

```bash
uv run python --version
```

### Add dependencies

Dependencies are declared in `pyproject.toml`. To add a package, replace `PACKAGE_NAME` with its name:

```bash
uv add PACKAGE_NAME
```

This updates `pyproject.toml` and `uv.lock` and installs the package. Commit both files so everyone can install the same dependency versions with `uv sync --locked`. The `.venv` directory is ignored by Git.

## Collect NBA data

Run the scraper from the repository root:

```bash
uv run python code/main.py --config config/scraper.json
```

The default range covers the 2019-20 through 2025-26 seasons. A season is identified by its ending year: `2024` means 2023-24. The range is inclusive. Regular-season player statistics are collected; playoff statistics and statistical analysis are outside this collector's scope.

Start with a single season:

```bash
uv run python code/main.py --start-season 2024 --end-season 2024
```

### Configuration

Edit `config/scraper.json` or override individual settings on the command line:

```bash
uv run python code/main.py --config config/scraper.json --start-season 2020 --end-season 2026 --output-dir data/processed --delay 4
```

Command-line values take precedence over the configuration file, which takes precedence over built-in defaults. Without `--config`, the collector reads `config/scraper.json` if it exists. An explicitly requested configuration file must exist. All relative paths, including configuration paths, are resolved from the repository root.

| JSON key | Command-line option | Default |
| --- | --- | --- |
| `start_season` | `--start-season` | `2020` |
| `end_season` | `--end-season` | `2026` |
| `datasets` | `--datasets` | All five datasets |
| `output_dir` | `--output-dir` | `data/processed` |
| `cache_dir` | `--cache-dir` | `data/raw` |
| `delay` | `--delay` | `4.0` seconds between request starts |
| `timeout` | `--timeout` | `30.0` seconds |
| `max_attempts` | `--max-attempts` | `3`, including the initial request |
| `reuse_cache` | `--reuse-cache` / `--no-reuse-cache` | `true` |

Delays and timeouts must be finite positive numbers. Season ending years currently range from 1947 to 2026; NBA coverage for early historical seasons may be incomplete. The default seven-season range is the project target.

To export only MVP voting and champions:

```bash
uv run python code/main.py --datasets mvp_votes champions
```

To download and parse pages again instead of reusing the local caches:

```bash
uv run python code/main.py --no-reuse-cache
```

All options are listed by `uv run python code/main.py --help`.

### Output files

| File in `data/processed/` | Contents and row identity |
| --- | --- |
| `players.csv` | Player profile, birth date, height, weight, birth country, and explicitly stated nationality; one row per `player_id` |
| `player_seasons.csv` | Age, position, games, per-game statistics, shooting percentages, PER, TS%, USG%, WS, WS/48, BPM, and VORP; one row per season, player, team, and aggregate flag |
| `mvp_votes.csv` | Every player listed in MVP voting, including rank, first-place votes, points, maximum points, and vote share; one row per season and player |
| `champions.csv` | NBA champion team; one row per season |
| `team_rosters.csv` | Published team-season roster, experience, height, weight, and season age when available from player statistics; one row per season, team, and player |

Files use UTF-8 with a BOM for Excel compatibility. Missing values remain empty. Heights are in centimeters and weights in kilograms. `R` in a roster's experience column becomes `0` years. Shooting percentages and MVP vote shares are fractions, while `usage_pct` follows the source's percentage-point convention.

Player and team IDs come from source links. Use `player_id`, `team_id`, and `season` to join the files. Traded players retain both their team rows and a separate aggregate row: `is_total=True`, an empty `team_id`, and the source's `TOT` or `2TM`-style label. Select the aggregate row when present, otherwise the single-team row, for player-season rankings; do not sum aggregate and team rows together.

Profile measurements are marked `measurement_scope=profile_snapshot`; they are not historical measurements. Roster measurements are taken from the published team-season page. Season age is copied from per-game statistics, not calculated from today's date. Roster players without a matching statistics row have an empty age; join to `player_seasons.csv` and filter by games played when selecting active players. Birth country is not treated as nationality.

Each record includes `source_url` and `fetched_at` in UTC. Player statistics also retain the advanced-statistics source and timestamp. Roster rows retain the source and timestamp used for their age. `last_run.json` records row counts and season coverage for the most recent successful export.

### Cache and failure handling

Successful HTML responses are cached as JSON files in `data/raw/`, preserving their original URL and fetch timestamp. Cached pages have no automatic expiry. Reruns reuse them unless `--no-reuse-cache` is supplied. Generated files in the default cache and CSV directories are ignored by Git.

Successful parsing results are saved separately in `data/raw/parsed/`. Restarting a failed or interrupted collection reuses those results, so previously parsed pages are not parsed again. A changed HTML page, fetch timestamp, season/team context, or parser implementation invalidates the corresponding result. `--no-reuse-cache` bypasses both the HTML cache and the parsed-results cache. CSVs are still validated and exported again from the combined results after collection succeeds.

Requests run sequentially. Temporary network errors and HTTP 429/500/502/503/504 responses receive bounded retries with increasing delays; `Retry-After` is respected. HTTP 403 stops collection immediately. Missing tables, changed required columns, duplicates, unresolved player references, and incomplete season coverage fail validation.

Selected datasets are published only after the whole collection and validation succeeds. A failed run preserves previous exports. Unselected CSV files remain unchanged, so keep their season ranges consistent or use separate output directories. Run only one collector per output directory at a time.

The live single-season verification received HTTP 403 from Basketball Reference. Live extraction and a complete real dataset have **not** been verified. The automated checks use controlled HTML fixtures; they do not prove that the site's current HTML matches the parsers. There is no access-block bypass or alternate data source.

## Code structure

All Python code lives in `code/`. `main.py` connects the components in `basketball_scraper`: `domain` defines data structures and contracts, `application` handles configuration and collection, `parsers` extracts HTML records, and `infrastructure` manages HTTP, caching, and CSV publication. The collector receives its dependencies through its constructor.

## Verification

Run the standard-library test suite without additional test dependencies:

```bash
uv run --directory code python -m unittest discover -s tests -v
```

The checks cover JSON configuration precedence and errors, legacy and modern column aliases, commented tables, traded players, rookies, missing values, seven-season fixture collection, CSV relationships, HTML and parsed-result cache replay, invalidation, resuming a failed collection, retries, blocked access, selected datasets, and restoration after a failed export.
