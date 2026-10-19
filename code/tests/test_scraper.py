import csv
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock, patch

import requests
from basketball_scraper.application.collector import BASE_URL, BasketballCollector
from basketball_scraper.application.config import PROJECT_ROOT, Settings, load_settings
from basketball_scraper.application.validation import DatasetValidator
from basketball_scraper.domain.models import (
    FetchError,
    Page,
    ParseContext,
    ParseError,
    ScraperError,
    ValidationError,
)
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

PARSERS = {
    "per_game": PerGameParser(),
    "advanced": AdvancedParser(),
    "mvp": MvpVotesParser(),
    "champions": ChampionsParser(),
    "roster": RosterParser(),
    "profile": PlayerProfileParser(),
}
NAMES = [
    "g",
    "gs",
    "mp_per_g",
    "fg_per_g",
    "fga_per_g",
    "fg_pct",
    "fg3_per_g",
    "fg3a_per_g",
    "fg3_pct",
    "fg2_per_g",
    "fg2a_per_g",
    "fg2_pct",
    "efg_pct",
    "ft_per_g",
    "fta_per_g",
    "ft_pct",
    "orb_per_g",
    "drb_per_g",
    "trb_per_g",
    "ast_per_g",
    "stl_per_g",
    "blk_per_g",
    "tov_per_g",
    "pf_per_g",
    "pts_per_g",
]
VALUES = [
    "62",
    "60",
    "32.1",
    "8",
    "16",
    ".500",
    "2",
    "5",
    ".400",
    "6",
    "11",
    ".545",
    ".562",
    "4",
    "5",
    ".800",
    "1",
    "5",
    "6",
    "7",
    "1",
    "0.5",
    "2",
    "2",
    "22",
]


def html(content):
    return "<html><body>" + content + "</body></html>"


def cell(name, value):
    return f'<td data-stat="{name}">{value}</td>'


def player_link(player):
    return f'<a href="/players/{player[0]}/{player}.html">{player.title()}</a>'


def identity(player, team, season):
    label = (
        team if team == "TOT" else f'<a href="/teams/{team}/{season}.html">{team}</a>'
    )
    return cell("player", player_link(player)) + cell("team_id", label)


def table(name, rows):
    return (
        f'<table id="{name}"><tbody>'
        + "".join("<tr>" + row + "</tr>" for row in rows)
        + "</tbody></table>"
    )


def fixture_pages(seasons):
    pages = {}
    for season in seasons:
        identities = [
            ("alpha01", "TOT"),
            ("alpha01", "LAL"),
            ("alpha01", "BOS"),
            ("beta01", "BOS"),
        ]
        stats = [
            identity(p, t, season)
            + cell("pos", "PG")
            + cell("age", "25")
            + "".join(cell(k, v) for k, v in zip(NAMES, VALUES))
            for p, t in identities
        ]
        pages[f"{BASE_URL}/leagues/NBA_{season}_per_game.html"] = html(
            table("per_game_stats", stats)
        )
        advanced = [
            identity(p, t, season)
            + "".join(
                cell(k, v)
                for k, v in {
                    "per": "22.5",
                    "ts_pct": ".610",
                    "usg_pct": "25",
                    "ws": "8",
                    "ws_per_48": ".150",
                    "bpm": "4",
                    "vorp": "3",
                }.items()
            )
            for p, t in identities
        ]
        pages[f"{BASE_URL}/leagues/NBA_{season}_advanced.html"] = html(
            "<!--" + table("advanced", advanced) + "-->"
        )
        votes = [
            cell("player", player_link(p))
            + cell("rank", r)
            + cell("votes_first", first)
            + cell("points_won", points)
            + cell("points_max", "1000")
            + cell("award_share", share)
            for p, r, first, points, share in [
                ("alpha01", "1", "80", "800", ".800"),
                ("beta01", "2T", "0", "200", ".200"),
            ]
        ]
        pages[f"{BASE_URL}/awards/awards_{season}.html"] = html(table("mvp", votes))
        for team in ("BOS", "LAL"):
            roster = [
                cell("player", player_link("alpha01"))
                + cell("pos", "PG")
                + cell("years_experience", "2")
                + cell("height", "6-6")
                + cell("weight", "200")
            ]
            if team == "BOS":
                roster += [
                    cell("player", player_link("beta01"))
                    + cell("pos", "PG")
                    + cell("years_experience", "R")
                    + cell("height", "")
                    + cell("weight", "")
                ]
            pages[f"{BASE_URL}/teams/{team}/{season}.html"] = html(
                table("roster", roster)
            )
    champion_rows = [
        cell(
            "season", f'<a href="/leagues/NBA_{season}.html">{season - 1}-{season}</a>'
        )
        + cell("lg_id", "NBA")
        + cell("champion", f'<a href="/teams/BOS/{season}.html">Boston Celtics</a>')
        for season in seasons
    ]
    pages[f"{BASE_URL}/leagues/"] = html(table("stats", champion_rows))
    for p in ("alpha01", "beta01"):
        pages[f"{BASE_URL}/players/{p[0]}/{p}.html"] = html(
            f'<div id="meta"><h1>{p.title()}</h1><span id="necro-birth" data-birth="2000-01-02"></span><span itemprop="height">6-6</span><span itemprop="weight">200lb</span><span itemprop="birthPlace">in Test City, <a href="/friv/birthplaces.fcgi?country=US">United States</a></span></div>'
        )
    return pages


def response(status=200, content="<html>ok</html>", headers=None):
    result = requests.Response()
    result.status_code = status
    result._content = content.encode()
    result.headers.update({"Content-Type": "text/html", **(headers or {})})
    return result


class Checks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        printer = patch("builtins.print")
        printer.start()
        self.addCleanup(printer.stop)

    def source(self, pages):
        source = HttpSource(0.001, 1, 3)
        source._session.get = Mock(
            side_effect=lambda url, **kwargs: response(content=pages[url])
        )
        return source

    def test_config_precedence_and_errors(self):
        path = self.root / "scraper.json"
        path.write_text(
            json.dumps(
                {
                    "start_season": 2022,
                    "end_season": 2024,
                    "delay": 7.0,
                    "reuse_cache": False,
                    "output_dir": "custom/out",
                    "datasets": ["mvp_votes"],
                }
            )
        )
        configured = load_settings(["--config", str(path)])
        self.assertEqual(
            (configured.start_season, configured.end_season, configured.delay),
            (2022, 2024, 7.0),
        )
        self.assertEqual(configured.output_dir, PROJECT_ROOT / "custom/out")
        overridden = load_settings(
            [
                "--config",
                str(path),
                "--delay",
                "9",
                "--reuse-cache",
                "--datasets",
                "champions",
            ]
        )
        self.assertEqual(
            (overridden.delay, overridden.reuse_cache, overridden.datasets),
            (9, True, ("champions",)),
        )
        for bad in (
            {"unknown": 1},
            {"delay": "bad"},
            {"timeout": 0},
            {"delay": float("nan")},
            {"datasets": []},
            {"reuse_cache": "yes"},
            {"start_season": True},
            {"max_attempts": 0},
            {"output_dir": "data/raw"},
            [],
        ):
            path.write_text(json.dumps(bad))
            with self.assertRaises(ScraperError, msg=str(bad)):
                load_settings(["--config", str(path)])
        path.write_text("{broken json")
        with self.assertRaises(ScraperError):
            load_settings(["--config", str(path)])
        with self.assertRaises(ScraperError):
            load_settings(["--start-season", "2026", "--end-season", "2024"])
        with self.assertRaises(ScraperError):
            load_settings(["--config", str(self.root / "absent")])

    def test_full_collection_and_cache_replay(self):
        pages = fixture_pages(range(2020, 2027))
        settings = replace(
            Settings(), output_dir=self.root / "processed", cache_dir=self.root / "raw"
        )
        parsers = {
            name: CachedParser(parser, settings.cache_dir, True)
            for name, parser in PARSERS.items()
        }
        with (
            self.source(pages) as source,
            patch("basketball_scraper.infrastructure.http.time.sleep"),
        ):
            counts = BasketballCollector(
                source, parsers, CsvDatasetWriter(), DatasetValidator()
            ).run(settings)
            self.assertEqual(
                counts,
                {
                    "players": 2,
                    "player_seasons": 28,
                    "mvp_votes": 14,
                    "champions": 7,
                    "team_rosters": 21,
                },
            )
            self.assertEqual(source._session.get.call_count, len(pages) + 6)
        with self.source({}) as source:
            again = BasketballCollector(
                source, parsers, CsvDatasetWriter(), DatasetValidator()
            ).run(settings)
            self.assertEqual(again, counts)
            source._session.get.assert_not_called()

        def rows(name):
            with (settings.output_dir / f"{name}.csv").open(encoding="utf-8-sig") as f:
                return list(csv.DictReader(f))

        self.assertEqual(rows("players")[0]["height_cm"], "198.12")
        self.assertEqual(rows("players")[0]["nationality"], "")
        self.assertEqual(rows("players")[0]["birth_country"], "US")
        self.assertEqual(rows("player_seasons")[0]["is_total"], "True")
        self.assertEqual(rows("player_seasons")[0]["team_id"], "")
        self.assertEqual(rows("player_seasons")[0]["per"], "22.5")
        self.assertEqual(rows("player_seasons")[0]["points_per_game"], "22.0")
        rookies = [r for r in rows("team_rosters") if r["player_id"] == "beta01"]
        self.assertTrue(
            all(r["experience_years"] == "0" and r["height_cm"] == "" for r in rookies)
        )
        self.assertEqual(rows("mvp_votes")[1]["rank"], "2")
        for file in settings.output_dir.glob("*.csv"):
            self.assertTrue(file.read_bytes().startswith(b"\xef\xbb\xbf"))

    def test_profile_without_itemprop_and_state_birthplace_link(self):
        page = Page(
            f"{BASE_URL}/players/a/arizatr01.html",
            "2026-10-19",
            html(
                '<div id="meta"><h1>Trevor Ariza</h1>'
                "<p><span>6-8</span>, <span>215lb</span> (203cm, 97kg)</p>"
                '<p><strong>Born:</strong><span id="necro-birth" data-birth="1985-06-30"></span>'
                '<span>in Miami, <a href="/friv/birthplaces.fcgi?country=US&amp;state=FL">Florida</a></span></p></div>'
            ),
        )
        row = PlayerProfileParser().parse(page, ParseContext()).rows[0]
        self.assertEqual(row["birth_date"], "1985-06-30")
        self.assertEqual(row["height_cm"], 203.2)
        self.assertEqual(row["weight_kg"], 97.52)
        self.assertEqual(row["birth_country"], "US")
        self.assertIsNone(row["nationality"])

    def test_modern_column_aliases_and_missing_table(self):
        url = f"{BASE_URL}/leagues/NBA_2024_per_game.html"
        content = (
            fixture_pages([2024])[url]
            .replace('data-stat="player"', 'data-stat="name_display"')
            .replace('data-stat="team_id"', 'data-stat="team_name_abbr"')
            .replace('_per_g"', '_per_game"')
            .replace('data-stat="g"', 'data-stat="games"')
            .replace('data-stat="gs"', 'data-stat="games_started"')
        )
        parsed = PerGameParser().parse(
            Page(url, "2026-10-18", content), ParseContext(2024)
        )
        self.assertEqual(parsed.rows[0]["games"], 62)
        with self.assertRaises(ParseError):
            PerGameParser().parse(
                Page(url, "2026-10-18", "<html></html>"), ParseContext(2024)
            )
        broken = content.replace('data-stat="pts_per_game"', 'data-stat="new_points"')
        with self.assertRaises(ParseError):
            PerGameParser().parse(Page(url, "2026-10-18", broken), ParseContext(2024))

    def test_block_and_failure_preserve_existing_exports(self):
        pages = fixture_pages([2024])
        settings = replace(
            Settings(),
            start_season=2024,
            end_season=2024,
            output_dir=self.root / "processed",
        )
        with (
            self.source(pages) as source,
            patch("basketball_scraper.infrastructure.http.time.sleep"),
        ):
            BasketballCollector(
                source, PARSERS, CsvDatasetWriter(), DatasetValidator()
            ).run(settings)
        before = {p.name: p.read_bytes() for p in settings.output_dir.iterdir()}
        with self.source({}) as source:
            source._session.get = Mock(return_value=response(403))
            with self.assertRaises(FetchError):
                BasketballCollector(
                    source, PARSERS, CsvDatasetWriter(), DatasetValidator()
                ).run(settings)
            self.assertEqual(source._session.get.call_count, 1)
        self.assertEqual(
            before, {p.name: p.read_bytes() for p in settings.output_dir.iterdir()}
        )
        with self.assertRaises(ValueError):
            CsvDatasetWriter().write({"players": [{"unknown": 1}]}, settings.output_dir)
        self.assertEqual(
            before, {p.name: p.read_bytes() for p in settings.output_dir.iterdir()}
        )

    def test_retry_after_and_timeout(self):
        url = f"{BASE_URL}/leagues/"
        with (
            self.source({}) as source,
            patch("basketball_scraper.infrastructure.http.time.sleep") as sleep,
        ):
            source._session.get = Mock(
                side_effect=[response(429, headers={"Retry-After": "12"}), response()]
            )
            source.get(url)
            self.assertIn(unittest.mock.call(12.0), sleep.call_args_list)
        with (
            self.source({}) as source,
            patch("basketball_scraper.infrastructure.http.time.sleep"),
        ):
            source._session.get = Mock(side_effect=requests.Timeout("timeout"))
            with self.assertRaises(FetchError):
                source.get(url)
            self.assertEqual(source._session.get.call_count, 3)

    def test_validation_duplicate_and_foreign_keys(self):
        validator = DatasetValidator()
        row = {
            "season": 2024,
            "team_id": "BOS",
            "source_url": "https://example.test",
            "fetched_at": "2026-10-18",
        }
        with self.assertRaises(ValidationError):
            validator.validate({"champions": [row, row]}, range(2024, 2025))
        with self.assertRaises(ValidationError):
            validator.validate({"champions": [row]}, range(2023, 2025))
        with self.assertRaises(ValidationError):
            validator.validate(
                {
                    "players": [
                        {"player_id": "alpha", "source_url": "x", "fetched_at": "x"}
                    ],
                    "team_rosters": [
                        {
                            "player_id": "missing",
                            "season": 2024,
                            "team_id": "BOS",
                            "source_url": "x",
                            "fetched_at": "x",
                        }
                    ],
                },
                range(2024, 2025),
            )

    def test_selected_dataset_only_fetches_required_sources(self):
        settings = replace(
            Settings(),
            start_season=2024,
            end_season=2024,
            datasets=("mvp_votes",),
            output_dir=self.root / "processed",
        )
        url = f"{BASE_URL}/awards/awards_2024.html"
        pages = {url: fixture_pages([2024])[url]}
        with self.source(pages) as source:
            counts = BasketballCollector(
                source, PARSERS, CsvDatasetWriter(), DatasetValidator()
            ).run(settings)
            self.assertEqual(counts, {"mvp_votes": 2})
            self.assertEqual(source._session.get.call_count, 1)
        self.assertFalse((settings.output_dir / "players.csv").exists())

    def test_failed_publish_restores_previous_directory(self):
        output = self.root / "processed"
        output.mkdir()
        (output / "previous.csv").write_bytes(b"previous export")
        import os

        real_replace = os.replace

        def replace_path(source, destination):
            if (
                Path(source) != output
                and Path(destination) == output
                and "backup" not in Path(source).name
            ):
                raise OSError("simulated publish failure")
            return real_replace(source, destination)

        with (
            patch(
                "basketball_scraper.infrastructure.csv_writer.os.replace",
                side_effect=replace_path,
            ),
            self.assertRaises(OSError),
        ):
            CsvDatasetWriter().write({"players": []}, output)
        self.assertEqual((output / "previous.csv").read_bytes(), b"previous export")

    def test_challenge_page_is_not_cached(self):
        with self.source({}) as source:
            source._session.get = Mock(
                return_value=response(
                    content="<html><title>Just a moment...</title></html>"
                )
            )
            with self.assertRaises(FetchError):
                source.get(f"{BASE_URL}/leagues/")
        self.assertEqual(list((self.root / "raw").glob("*.json")), [])

    def test_parsed_cache_reuse_and_invalidation(self):
        parser = MvpVotesParser()
        cache = CachedParser(parser, self.root / "raw", True)
        url = f"{BASE_URL}/awards/awards_2024.html"
        source = Mock()
        source.get.return_value = Page(
            url, "2026-10-18T00:00:00+00:00", fixture_pages([2024])[url]
        )
        with patch.object(parser, "parse", wraps=parser.parse) as parse:
            first = cache.parse_url(source, url, ParseContext(2024))
            first.rows[0]["rank"] = 999
            second = cache.parse_url(source, url, ParseContext(2024))
            self.assertEqual(second.rows[0]["rank"], 1)
            self.assertEqual(parse.call_count, 1)
            self.assertEqual(source.get.call_count, 1)
            cache.parse_url(source, url, ParseContext(2025))
            cache._code_hash = "changed-parser-code"
            cache.parse_url(source, url, ParseContext(2024))
            self.assertEqual(parse.call_count, 3)
            self.assertEqual(source.get.call_count, 3)
            self.assertEqual(len(list((self.root / "raw" / "parsed").glob("*.json"))), 2)

    def test_disabled_and_corrupted_parsed_cache(self):
        parser = MvpVotesParser()
        url = f"{BASE_URL}/awards/awards_2024.html"
        source = Mock()
        source.get.return_value = Page(
            url, "2026-10-18T00:00:00+00:00", fixture_pages([2024])[url]
        )
        cache = CachedParser(parser, self.root / "raw", False)
        with patch.object(parser, "parse", wraps=parser.parse) as parse:
            cache.parse_url(source, url, ParseContext(2024))
            cache.parse_url(source, url, ParseContext(2024))
            self.assertEqual(parse.call_count, 2)
            stored = next((self.root / "raw" / "parsed").glob("*.json"))
            stored.write_text("{broken")
            cache._reuse_cache = True
            cache.parse_url(source, url, ParseContext(2024))
            self.assertEqual(parse.call_count, 3)
            self.assertEqual(source.get.call_count, 3)

    def test_full_collection_skips_previously_parsed_pages(self):
        pages = fixture_pages(range(2020, 2027))
        settings = replace(
            Settings(), output_dir=self.root / "processed", cache_dir=self.root / "raw"
        )
        parsers = {
            name: CachedParser(parser, settings.cache_dir, True)
            for name, parser in PARSERS.items()
        }
        with (
            self.source(pages) as source,
            patch("basketball_scraper.infrastructure.http.time.sleep"),
        ):
            expected = BasketballCollector(
                source, parsers, CsvDatasetWriter(), DatasetValidator()
            ).run(settings)
        self.assertEqual(list(settings.cache_dir.glob("*.json")), [])
        from contextlib import ExitStack

        with ExitStack() as patches, self.source({}) as source:
            for parser in PARSERS.values():
                patches.enter_context(
                    patch.object(
                        parser,
                        "parse",
                        side_effect=AssertionError(
                            "Already parsed page was parsed again"
                        ),
                    )
                )
            actual = BasketballCollector(
                source, parsers, CsvDatasetWriter(), DatasetValidator()
            ).run(settings)
            self.assertEqual(actual, expected)
            source._session.get.assert_not_called()

    def test_restart_reuses_successes_from_failed_collection(self):
        pages = fixture_pages([2024, 2025])
        settings = replace(
            Settings(),
            start_season=2024,
            end_season=2025,
            datasets=("mvp_votes",),
            output_dir=self.root / "processed",
            cache_dir=self.root / "raw",
        )
        parser = MvpVotesParser()
        parsers = {"mvp": CachedParser(parser, settings.cache_dir, True)}
        with patch.object(parser, "parse", wraps=parser.parse) as parse:
            with (
                self.source(pages) as source,
                patch("basketball_scraper.infrastructure.http.time.sleep"),
            ):
                source._session.get = Mock(
                    side_effect=[
                        response(content=pages[f"{BASE_URL}/awards/awards_2024.html"]),
                        response(403),
                    ]
                )
                with self.assertRaises(FetchError):
                    BasketballCollector(
                        source, parsers, CsvDatasetWriter(), DatasetValidator()
                    ).run(settings)
                self.assertEqual(parse.call_count, 1)
                self.assertFalse(settings.output_dir.exists())
            with self.source(pages) as source:
                counts = BasketballCollector(
                    source, parsers, CsvDatasetWriter(), DatasetValidator()
                ).run(settings)
                self.assertEqual(counts, {"mvp_votes": 4})
                self.assertEqual(parse.call_count, 2)
                self.assertEqual(source._session.get.call_count, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
