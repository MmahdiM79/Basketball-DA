import csv
import json
import os
import shutil
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path

from basketball_scraper.domain.contracts import DatasetWriter
from basketball_scraper.domain.models import SCHEMAS, Row


class CsvDatasetWriter(DatasetWriter):
    def write(self, datasets: dict[str, list[Row]], output_dir: Path) -> None:
        output_dir.parent.mkdir(parents=True, exist_ok=True)
        staging = Path(
            tempfile.mkdtemp(prefix=f".{output_dir.name}-", dir=output_dir.parent)
        )
        backup = output_dir.with_name(f".{output_dir.name}-backup-{uuid.uuid4().hex}")
        try:
            if output_dir.exists():
                shutil.copytree(output_dir, staging, dirs_exist_ok=True)
            for name, rows in datasets.items():
                with (staging / f"{name}.csv").open(
                    "w", newline="", encoding="utf-8-sig"
                ) as stream:
                    writer = csv.DictWriter(stream, fieldnames=SCHEMAS[name])
                    writer.writeheader()
                    writer.writerows(rows)
            summary = {
                "completed_at": datetime.now(UTC).isoformat(),
                "datasets": {
                    name: {
                        "rows": len(rows),
                        "seasons": sorted(
                            {row["season"] for row in rows if "season" in row}
                        ),
                    }
                    for name, rows in datasets.items()
                },
            }
            (staging / "last_run.json").write_text(
                json.dumps(summary, indent=2), encoding="utf-8"
            )
            if output_dir.exists():
                os.replace(output_dir, backup)
            try:
                os.replace(staging, output_dir)
            except BaseException:
                if backup.exists():
                    os.replace(backup, output_dir)
                raise
        finally:
            if staging.exists():
                shutil.rmtree(staging)
        if backup.exists():
            shutil.rmtree(backup)
