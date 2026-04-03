from __future__ import annotations

from pathlib import Path
import json
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data" / "processed"


def load_measurements(scenario: str) -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / f"measurements_{scenario}.csv", parse_dates=["observed_at"])


def load_status(scenario: str) -> pd.DataFrame:
    with (DATA_DIR / f"status_{scenario}.json").open("r", encoding="utf-8") as f:
        data = json.load(f)
    return pd.DataFrame(data)


def load_history() -> pd.DataFrame:
    path = DATA_DIR / "alert_history.csv"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, parse_dates=["observed_at"])
