# Basketball-DA

Collect and analyze NBA data from Basketball Reference. The scraper exports five linked CSV datasets for the 2019-20 through 2025-26 seasons by default.

## Setup

The project uses Python 3.14, `uv`, and GNU Make 3.81 or later. Follow the [official uv installation guide](https://docs.astral.sh/uv/getting-started/installation/) for your operating system.

Clone the repository and enter its directory:

```bash
git clone https://github.com/MmahdiM79/Basketball-DA.git
cd Basketball-DA
```

Follow the [Makefile guide](docs/makefile/README.md) to set up the environment, collect data, run tests, and customize commands.

## Documentation

- [Makefile guide](docs/makefile/README.md): project commands, variables, and examples.
- [Scraper guide](docs/scraper/README.md): execution flow, class relationships, datasets, configuration, caching, and verification limits.
