# CI checks

Three independent workflows—[lint](../../.github/workflows/lint.yml), [tests](../../.github/workflows/tests.yml), and [live smoke](../../.github/workflows/smoke.yml)—run on pull requests targeting `master`, on each new commit pushed to those pull requests, on pushes to `master`, and through GitHub's **Run workflow** button. It does not create pull requests automatically.

| Job | What it checks | Local command |
| --- | --- | --- |
| Lint and formatting | Ruff rules `E4`, `E7`, `E9`, `F`, and `I`, plus standard Ruff formatting | `make lint` and `make format-check` |
| Unit tests | The offline unittest suite, including simulated HTTP failures and smoke checks | `make test` |
| Live scraper smoke check | Fresh responses and extraction with all six production parsers | `make smoke` |

Jobs run on Ubuntu with a ten-minute timeout and read-only repository permissions. Within each workflow, a new run cancels an older run for the same pull request or branch; the other workflows continue independently. Test and smoke jobs use Python 3.14 and install the locked dependencies with the official `setup-uv` action. The lint job uses the official `ruff-action`, reading the Ruff version from `uv.lock`. CI reports failures without formatting, committing, or pushing code.

## Limited live scraping

The smoke check uses [smoke.json](../../config/smoke.json). Its defaults are season ending in **2024**, four seconds between requests, a thirty-second request timeout, and up to three attempts per URL.

It requests exactly six distinct URLs on success:

1. The season's per-game statistics.
2. The season's advanced statistics.
3. The season's MVP voting results.
4. The league index containing NBA champions.
5. The champion team's roster for that season.
6. The profile of that roster's first player, sorted by player ID.

Each page's required table is parsed in full; the check does not follow other team or player links. It validates statistics identities and values, MVP votes, champion/roster consistency, and the selected profile's identity, name, birth date, height, and weight. It prints parsed row counts and a final success message.

HTML stays in memory. The check neither reads nor writes the scraper cache and does not export CSVs. Cache/output path options inherited from the shared configuration loader do not control smoke output. These checks cover representative live extraction; the unit tests cover the complete collection flow and CSV writing.

## Running locally

Use `make setup` first. See the [Makefile guide](../makefile/README.md) for all commands and variables.

```bash
make lint
make format-check
make test
make smoke
make smoke ARGS="--start-season 2023 --end-season 2023 --delay 5"
make smoke CONFIG="config/custom smoke.json"
```

Smoke settings follow the existing precedence: `ARGS` overrides `CONFIG`, which overrides built-in defaults. Exactly one season and all five datasets are required. `CONFIG` defaults to `config/smoke.json` for `make smoke`. Even if cache reuse is enabled in a custom configuration, smoke always fetches fresh pages.

To fix formatting locally, run `make format`, review the changes, then rerun the checks.

## Failures

A changed/missing table, invalid record, missing profile measurement, exhausted retry, or HTTP `403` fails the live job. A failure stops further page requests; retries may increase the total request attempts beyond six. HTTP `403` stops immediately without bypass attempts. A green lint or test job does not establish live site access; inspect the live job separately.

No job suppresses failures with `continue-on-error`. Requiring these checks before merging must be configured separately in repository branch protection; this change does not alter those settings.
