import time
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse

import requests

from basketball_scraper.domain.contracts import PageSource
from basketball_scraper.domain.models import FetchError, Page


class HttpSource(PageSource):
    def __init__(
        self,
        delay: float,
        timeout: float,
        max_attempts: int,
    ):
        self._delay = delay
        self._timeout = timeout
        self._max_attempts = max_attempts
        self._session = requests.Session()
        self._session.headers["User-Agent"] = (
            "Basketball-DA/0.1 (educational NBA data collection)"
        )
        self._last_request = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._session.close()

    def get(self, url: str) -> Page:
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.netloc != "www.basketball-reference.com":
            raise FetchError(f"Unsupported source URL: {url}")
        for attempt in range(1, self._max_attempts + 1):
            if self._last_request is not None:
                time.sleep(
                    max(0, self._delay - (time.monotonic() - self._last_request))
                )
            self._last_request = time.monotonic()
            print(f"Fetching {url} (attempt {attempt}/{self._max_attempts})")
            try:
                response = self._session.get(
                    url, timeout=self._timeout, allow_redirects=False
                )
            except (requests.Timeout, requests.ConnectionError) as exc:
                if attempt == self._max_attempts:
                    raise FetchError(f"Request failed for {url}: {exc}") from exc
                time.sleep(2**attempt)
                continue
            if response.status_code == 403:
                raise FetchError(
                    f"HTTP 403 for {url}. Access is blocked; collection stopped."
                )
            if response.status_code == 429 or response.status_code in (
                500,
                502,
                503,
                504,
            ):
                if attempt == self._max_attempts:
                    raise FetchError(
                        f"HTTP {response.status_code} for {url}; attempts exhausted"
                    )
                pause = max(
                    2**attempt, self._retry_after(response.headers.get("Retry-After"))
                )
                print(f"HTTP {response.status_code}; retrying in {pause:.1f} seconds")
                time.sleep(pause)
                continue
            if response.status_code != 200:
                raise FetchError(f"Unexpected HTTP {response.status_code} for {url}")
            html = response.text
            if (
                "<html" not in html.lower()
                or "text/html" not in response.headers.get("Content-Type", "").lower()
            ):
                raise FetchError(f"Expected an HTML page from {url}")
            if any(
                marker in html.lower()
                for marker in (
                    "<title>just a moment",
                    "<title>access denied",
                    "<title>attention required",
                )
            ):
                raise FetchError(f"Received a challenge page from {url}")
            page = Page(url, datetime.now(UTC).isoformat(), html)
            return page
        raise FetchError(f"Could not fetch {url}")

    @staticmethod
    def _retry_after(value: str | None) -> float:
        if not value:
            return 0
        try:
            seconds = float(value)
            return max(0, seconds) if seconds < float("inf") else 0
        except ValueError:
            try:
                date = parsedate_to_datetime(value)
                if date.tzinfo is None:
                    date = date.replace(tzinfo=UTC)
                return max(0, (date - datetime.now(UTC)).total_seconds())
            except ValueError, TypeError, OverflowError:
                return 0
