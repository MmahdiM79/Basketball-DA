import argparse
import json
import math
from dataclasses import dataclass, fields
from pathlib import Path

from basketball_scraper.domain.models import SCHEMAS, ScraperError

PROJECT_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class Settings:
    start_season: int = 2020
    end_season: int = 2026
    datasets: tuple[str, ...] = tuple(SCHEMAS)
    output_dir: Path = Path("data/processed")
    cache_dir: Path = Path("data/raw")
    delay: float = 4.0
    timeout: float = 30.0
    max_attempts: int = 3
    reuse_cache: bool = True


def load_settings(argv: list[str] | None = None) -> Settings:
    parser = argparse.ArgumentParser(
        description="Collect NBA data from Basketball Reference."
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="JSON configuration path, relative to the project root",
    )
    parser.add_argument(
        "--start-season", type=int, help="First season ending year (default: 2020)"
    )
    parser.add_argument(
        "--end-season", type=int, help="Last season ending year (default: 2026)"
    )
    parser.add_argument(
        "--datasets",
        nargs="+",
        choices=SCHEMAS,
        help="Datasets to export (default: all)",
    )
    parser.add_argument("--output-dir", type=Path, help="CSV output directory")
    parser.add_argument("--cache-dir", type=Path, help="HTML cache directory")
    parser.add_argument(
        "--delay", type=float, help="Minimum seconds between requests (default: 4)"
    )
    parser.add_argument(
        "--timeout", type=float, help="Request timeout in seconds (default: 30)"
    )
    parser.add_argument(
        "--max-attempts",
        type=int,
        help="Maximum attempts per URL, including the first (default: 3)",
    )
    parser.add_argument(
        "--reuse-cache",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Reuse successful cached pages (default: enabled)",
    )
    args = vars(parser.parse_args(argv))
    explicit_config = args.pop("config")
    config_path = explicit_config or Path("config/scraper.json")
    if not config_path.is_absolute():
        config_path = PROJECT_ROOT / config_path
    values = {}
    if config_path.exists():
        try:
            with config_path.open(encoding="utf-8") as stream:
                values = json.load(stream)
        except (OSError, json.JSONDecodeError) as exc:
            raise ScraperError(
                f"Cannot read configuration {config_path}: {exc}"
            ) from exc
    elif explicit_config is not None:
        raise ScraperError(f"Configuration file does not exist: {config_path}")
    if not isinstance(values, dict):
        raise ScraperError("Configuration must be a JSON object")
    unknown = set(values) - {item.name for item in fields(Settings)}
    if unknown:
        raise ScraperError(f"Unknown configuration keys: {', '.join(sorted(unknown))}")
    values.update({key: value for key, value in args.items() if value is not None})
    merged = {
        item.name: getattr(Settings(), item.name) for item in fields(Settings)
    } | values
    for key in ("start_season", "end_season", "max_attempts"):
        if type(merged[key]) is not int:
            raise ScraperError(f"{key} must be an integer")
    if not 1947 <= merged["start_season"] <= merged["end_season"] <= 2026:
        raise ScraperError(
            "Season ending years must satisfy 1947 <= start_season <= end_season <= 2026"
        )
    if merged["max_attempts"] < 1:
        raise ScraperError("max_attempts must be at least 1")
    for key in ("delay", "timeout"):
        value = merged[key]
        if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
            raise ScraperError(f"{key} must be a finite positive number")
    if type(merged["reuse_cache"]) is not bool:
        raise ScraperError("reuse_cache must be true or false")
    selected = merged["datasets"]
    if not isinstance(selected, (tuple, list)) or not selected:
        raise ScraperError("datasets must be a non-empty list")
    if any(not isinstance(name, str) or name not in SCHEMAS for name in selected):
        raise ScraperError(f"datasets must contain only: {', '.join(SCHEMAS)}")
    merged["datasets"] = tuple(dict.fromkeys(selected))
    for key in ("output_dir", "cache_dir"):
        value = merged[key]
        if not isinstance(value, (str, Path)) or not str(value).strip():
            raise ScraperError(f"{key} must be a non-empty path")
        path = Path(value).expanduser()
        merged[key] = (
            (PROJECT_ROOT / path).resolve()
            if not path.is_absolute()
            else path.resolve()
        )
        if merged[key].exists() and not merged[key].is_dir():
            raise ScraperError(f"{key} must refer to a directory")
    output, cache = merged["output_dir"], merged["cache_dir"]
    if output == PROJECT_ROOT or PROJECT_ROOT.is_relative_to(output):
        raise ScraperError("output_dir cannot be the project root or its parent")
    if output == cache or output.is_relative_to(cache) or cache.is_relative_to(output):
        raise ScraperError("output_dir and cache_dir must not overlap")
    return Settings(**merged)
