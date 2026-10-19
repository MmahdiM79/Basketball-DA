import sys

import requests

from basketball_scraper.application.config import load_settings
from basketball_scraper.application.smoke import SmokeCheck
from basketball_scraper.application.validation import DatasetValidator
from basketball_scraper.domain.models import ScraperError
from basketball_scraper.infrastructure.http import HttpSource


def main(argv: list[str] | None = None) -> int:
    try:
        settings = load_settings(
            ["--config", "config/smoke.json", *(sys.argv[1:] if argv is None else argv)]
        )
        with HttpSource(
            settings.delay, settings.timeout, settings.max_attempts
        ) as source:
            SmokeCheck(source, DatasetValidator()).run(settings)
    except (ScraperError, OSError, requests.RequestException) as exc:
        print(f"{exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Smoke check interrupted", file=sys.stderr)
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
