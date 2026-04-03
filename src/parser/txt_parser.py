from __future__ import annotations

from pathlib import Path
import pandas as pd


def parse_txt_file(file_path: str | Path, scenario: str) -> pd.DataFrame:
    path = Path(file_path)
    rows: list[dict] = []

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            parts = line.split("\t")
            if len(parts) < 5:
                continue

            parameter, value, unit, timestamp, status_code = [part.strip() for part in parts[:5]]
            rows.append(
                {
                    "parameter": parameter,
                    "value": value,
                    "unit": unit,
                    "timestamp_raw": timestamp,
                    "status_code": status_code,
                    "source_file": path.name,
                    "scenario": scenario,
                }
            )

    return pd.DataFrame(rows)
