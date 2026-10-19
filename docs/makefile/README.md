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
| `make test` | Run the existing test suite |

| Make variable | Default | Meaning |
| --- | --- | --- |
| `UV` | `uv` | Executable path used by all targets that invoke `uv` |
| `CONFIG` | `config/scraper.json` | Configuration path for `scrape` and `scrape-refresh` |
| `ARGS` | Empty | Additional scraper CLI arguments for `scrape` and `scrape-refresh` |

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
