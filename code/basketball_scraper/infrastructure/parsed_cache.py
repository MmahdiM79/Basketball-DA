import hashlib
import json
import os
import tempfile
from dataclasses import asdict
from pathlib import Path

from basketball_scraper.domain.contracts import HtmlParser
from basketball_scraper.domain.models import Page, ParseContext, ParsedData


class CachedParser(HtmlParser):
    def __init__(self, parser: HtmlParser, cache_dir: Path, reuse_cache: bool):
        self._parser = parser
        self._directory = cache_dir / "parsed"
        self._reuse_cache = reuse_cache
        package = Path(__file__).resolve().parents[1]
        sources = sorted((package / "parsers").glob("*.py"))
        sources.extend((package / "domain" / "models.py", Path(__file__)))
        self._code_hash = hashlib.sha256(
            b"".join(path.read_bytes() for path in sources)
        ).hexdigest()

    def parse(self, page: Page, context: ParseContext) -> ParsedData:
        identity = {
            "parser": type(self._parser).__name__,
            "code": self._code_hash,
            "url": page.url,
            "fetched_at": page.fetched_at,
            "html": hashlib.sha256(page.html.encode("utf-8")).hexdigest(),
            "context": asdict(context),
        }
        key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
        path = self._directory / f"{key}.json"
        if self._reuse_cache and path.exists():
            try:
                result = json.loads(path.read_text(encoding="utf-8"))
                rows = result["rows"]
                players = result["player_urls"]
                teams = result["team_urls"]
                if not isinstance(rows, list) or not all(
                    isinstance(row, dict) for row in rows
                ):
                    raise ValueError("Invalid cached rows")
                for urls in (players, teams):
                    if not isinstance(urls, dict) or not all(
                        isinstance(name, str) and isinstance(url, str)
                        for name, url in urls.items()
                    ):
                        raise ValueError("Invalid cached links")
                return ParsedData(rows, players, teams)
            except ValueError, KeyError, TypeError:
                print(f"Ignoring invalid parsed cache: {path.name}")
        result = self._parser.parse(page, context)
        self._directory.mkdir(parents=True, exist_ok=True)
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=self._directory, delete=False
            ) as stream:
                temp_path = Path(stream.name)
                json.dump(asdict(result), stream)
            os.replace(temp_path, path)
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)
        return result
