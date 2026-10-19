import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests
from test_scraper import fixture_pages, response

from basketball_scraper.application.collector import BASE_URL
from basketball_scraper.application.config import load_settings
from basketball_scraper.application.smoke import SmokeCheck
from basketball_scraper.application.validation import DatasetValidator
from basketball_scraper.domain.contracts import PageSource
from basketball_scraper.domain.models import Page, ParseError, ValidationError
from smoke import main


class SmokeTests(unittest.TestCase):
    def setUp(self):
        self.pages = fixture_pages([2024])
        self.source = Mock(spec=PageSource)
        self.source.get.side_effect = lambda url: Page(
            url, "2026-10-19T00:00:00+00:00", self.pages[url]
        )
        self.settings = load_settings(["--config", "config/smoke.json"])
        printer = patch("builtins.print")
        printer.start()
        self.addCleanup(printer.stop)

    def run_smoke(self):
        return SmokeCheck(self.source, DatasetValidator()).run(self.settings)

    def test_six_pages_and_deterministic_champion_player(self):
        counts = self.run_smoke()
        self.assertEqual(
            counts,
            {
                "per_game": 4,
                "advanced": 4,
                "mvp_votes": 2,
                "champions": 1,
                "team_rosters": 2,
                "players": 1,
            },
        )
        urls = [call.args[0] for call in self.source.get.call_args_list]
        self.assertEqual(len(urls), 6)
        self.assertEqual(len(set(urls)), 6)
        self.assertEqual(urls[-2], f"{BASE_URL}/teams/BOS/2024.html")
        self.assertEqual(urls[-1], f"{BASE_URL}/players/a/alpha01.html")

    def test_multiple_seasons_or_partial_datasets_fail_before_fetch(self):
        for options in (
            ["--end-season", "2025"],
            ["--datasets", "mvp_votes"],
        ):
            with self.subTest(options=options):
                self.settings = load_settings(
                    ["--config", "config/smoke.json", *options]
                )
                with self.assertRaises(ValidationError):
                    self.run_smoke()
        self.source.get.assert_not_called()

    def test_changed_table_stops_collection(self):
        self.pages[f"{BASE_URL}/leagues/NBA_2024_advanced.html"] = "<html></html>"
        with self.assertRaises(ParseError):
            self.run_smoke()
        self.assertEqual(self.source.get.call_count, 2)

    def test_stat_identity_mismatch_fails(self):
        url = f"{BASE_URL}/leagues/NBA_2024_advanced.html"
        self.pages[url] = self.pages[url].replace("beta01", "gamma01")
        with self.assertRaisesRegex(ValidationError, "do not match"):
            self.run_smoke()
        self.assertEqual(self.source.get.call_count, 2)

    def test_missing_profile_measurements_fail(self):
        url = f"{BASE_URL}/players/a/alpha01.html"
        self.pages[url] = self.pages[url].replace(
            'itemprop="height"', 'itemprop="other"'
        )
        with self.assertRaisesRegex(ValidationError, "height_cm"):
            self.run_smoke()

    def test_cli_preserves_existing_outputs_and_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output, cache = root / "output", root / "cache"
            output.mkdir()
            cache.mkdir()
            (output / "players.csv").write_text("existing CSV")
            (cache / "entry.json").write_text("existing cache")
            before = {
                p.relative_to(root): p.read_bytes()
                for p in root.rglob("*")
                if p.is_file()
            }
            with (
                patch(
                    "requests.Session.get",
                    side_effect=lambda url, **kwargs: response(content=self.pages[url]),
                ) as get,
                patch("basketball_scraper.infrastructure.http.time.sleep"),
            ):
                result = main(["--output-dir", str(output), "--cache-dir", str(cache)])
            self.assertEqual(result, 0)
            self.assertEqual(get.call_count, 6)
            after = {
                p.relative_to(root): p.read_bytes()
                for p in root.rglob("*")
                if p.is_file()
            }
            self.assertEqual(before, after)

    def test_cli_reports_block_and_network_failures(self):
        with (
            patch("requests.Session.get", return_value=response(403)) as get,
            patch("sys.stderr"),
        ):
            self.assertEqual(main([]), 1)
            self.assertEqual(get.call_count, 1)
        with (
            patch(
                "requests.Session.get", side_effect=requests.Timeout("timeout")
            ) as get,
            patch("basketball_scraper.infrastructure.http.time.sleep"),
            patch("sys.stderr"),
        ):
            self.assertEqual(main([]), 1)
            self.assertEqual(get.call_count, 3)


if __name__ == "__main__":
    unittest.main()
