# Makefile guide

Run commands from the repository root with GNU Make 3.81 or later and `uv` installed. See the [setup guide](../../README.md#setup) for Python and `uv` installation. The [Makefile](../../Makefile) provides shortcuts for the existing project commands.

Every Make target is phony, so a file with the same name does not prevent execution. Running `make` without a target only displays help.

| Command | Purpose |
| --- | --- |
| `make` or `make help` | Display commands and variables |
| `make setup` | Create the environment and install locked dependencies |
| `make scrape` | Collect data using the selected configuration and existing caches |
| `make scrape-refresh` | Fetch and parse again without reusing caches |
| `make scrape-help` | Show all scraper options |
| `make test` | Run the offline test suite |
| `make lint` | Check Python code with the locked Ruff version |
| `make format-check` | Check Ruff formatting without editing files |
| `make format` | Apply Ruff formatting locally |
| `make smoke` | Fetch and check six live pages without writing CSVs or cache |
| `make import-db` | Build the SQLite database and load the CSV files from `data/database/` |

| Make variable | Default | Meaning |
| --- | --- | --- |
| `UV` | `uv` | Executable path used by all targets that invoke `uv` |
| `CONFIG` | `config/scraper.json`; `config/smoke.json` for `smoke` | Configuration path for `scrape`, `scrape-refresh`, and `smoke` |
| `ARGS` | Empty | Additional CLI arguments for `scrape`, `scrape-refresh`, and `smoke` |

Use the existing CLI options through `ARGS`; Make does not define separate season or dataset settings:

```bash
make setup
make scrape ARGS="--start-season 2024 --end-season 2024"
make scrape ARGS="--datasets mvp_votes champions --delay 5"
make scrape CONFIG=config/custom.json
make scrape-refresh ARGS="--start-season 2024 --end-season 2024"
make test
```

Quote paths containing spaces. For paths inside `ARGS`, preserve their quotes for the shell:

```bash
make scrape CONFIG="config/custom file.json"
make scrape ARGS='--output-dir "data/custom output"'
make setup UV="/path/to/uv"
```

`CONFIG` supplies `--config`; use it to select the configuration file. Values in `ARGS` override settings from that file through the existing CLI. `scrape-refresh` appends `--no-reuse-cache` after `ARGS`, so even an earlier `--reuse-cache` cannot disable refresh. A failing command causes Make to fail. These targets use the locked dependencies and do not change scraper behavior or the lockfile.

See the [scraper documentation](../scraper/README.md#configuration-and-commands) for the underlying CLI options and configuration behavior.

## Code checks and live smoke check

```bash
make lint
make format-check
make format
make test
make smoke
make smoke ARGS="--start-season 2023 --end-season 2023 --delay 5"
make smoke CONFIG="config/custom smoke.json"
```

`make format` edits Python files; `make lint` and `make format-check` only report issues. `make smoke` requires one season and all five datasets, fetches fresh pages regardless of cache settings, and does not write CSVs or cache. See the [CI guide](../ci/README.md) for page selection, validation, triggers, and failure behavior.

## Database import

```bash
make import-db
```

`make import-db` creates `DB/basketbal_da.db` and fills it from the CSV files in `data/database/`. Like `make clean-data`, it installs pandas and SQLAlchemy for this run only with `uv run --with`, so the project dependencies and the lockfile stay unchanged. The import appends rows: delete the existing database file first, or it fails with `UNIQUE constraint failed`. See the [database guide](../database/README.md) for the tables and relationships.