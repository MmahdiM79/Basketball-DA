import sys

import requests
from basketball_scraper.application.collector import BasketballCollector
from basketball_scraper.application.config import load_settings
from basketball_scraper.application.validation import DatasetValidator
from basketball_scraper.domain.models import ScraperError
from basketball_scraper.infrastructure.csv_writer import CsvDatasetWriter
from basketball_scraper.infrastructure.http import HttpSource
from basketball_scraper.infrastructure.parsed_cache import CachedParser
from basketball_scraper.parsers.entities import (
    ChampionsParser,
    MvpVotesParser,
    PlayerProfileParser,
    RosterParser,
)
from basketball_scraper.parsers.stats import AdvancedParser, PerGameParser


def main(argv: list[str] | None = None) -> int:
    try:
        settings = load_settings(argv)
        parsers = {
            "per_game": PerGameParser(),
            "advanced": AdvancedParser(),
            "mvp": MvpVotesParser(),
            "champions": ChampionsParser(),
            "roster": RosterParser(),
            "profile": PlayerProfileParser(),
        }
        parsers = {
            name: CachedParser(parser, settings.cache_dir, settings.reuse_cache)
            for name, parser in parsers.items()
        }
        with HttpSource(
            settings.delay,
            settings.timeout,
            settings.max_attempts,
        ) as source:
            collector = BasketballCollector(
                source, parsers, CsvDatasetWriter(), DatasetValidator()
            )
            collector.run(settings)
    except (ScraperError, OSError, requests.RequestException) as exc:
        print(f"{exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print(
            "Collection interrupted; existing CSV exports were preserved",
            file=sys.stderr,
        )
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
