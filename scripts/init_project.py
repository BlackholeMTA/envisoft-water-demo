from __future__ import annotations

from pathlib import Path
import json
import sqlite3
import sys
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from src.parser.txt_parser import parse_txt_file
from src.parser.normalize import normalize_dataframe
from src.engine.alert_engine import build_station_status

SCENARIO_DIR = BASE_DIR / "data" / "scenarios"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
DB_PATH = BASE_DIR / "db" / "demo.db"

THRESHOLDS = {
    "wastewater": {"ph_min": 6.0, "ph_max": 9.0, "cod": 15.0, "tss": 20.0, "ammonia": 2.0, "flow_out": 9.5},
    "water": {"ph_min": 6.5, "ph_max": 8.5, "turbidity": 1.0, "nitrate": 80.0, "conductivity": 300.0, "tss": 5.0},
    "stack_emission": {"nh3": 1.2, "pm": 5.0, "flow": 70000.0},
    "ambient_air": {"pm25": 25.0, "pm10": 45.0, "co": 2500.0, "no2": 30.0, "o3": 60.0},
}


def parse_scenario(scenario: str) -> pd.DataFrame:
    dfs = []
    for file_path in sorted((SCENARIO_DIR / scenario).glob("*.txt")):
        df = parse_txt_file(file_path, scenario)
        df = normalize_dataframe(df)
        dfs.append(df)
    if not dfs:
        return pd.DataFrame()
    final_df = pd.concat(dfs, ignore_index=True)
    return final_df


def write_sqlite(normal_df: pd.DataFrame, polluted_df: pd.DataFrame) -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        normal_df.to_sql("measurements_normal", conn, if_exists="replace", index=False)
        polluted_df.to_sql("measurements_polluted", conn, if_exists="replace", index=False)


def build_alert_history(normal_status: list[dict], polluted_status: list[dict]) -> pd.DataFrame:
    records = []
    for item in normal_status + polluted_status:
        if not item["is_alert"]:
            continue
        records.append(
            {
                "observed_at": item["observed_at"],
                "scenario": item["scenario"],
                "station_code": item["station_code"],
                "station_name": item["station_name"],
                "domain": item["domain"],
                "final_status": item["final_status"],
                "reasons": " | ".join(item["reasons"]),
                "camera_image": item["camera_image"],
                "ai_prediction": item["ai_prediction"],
            }
        )
    return pd.DataFrame(records)


def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    normal_df = parse_scenario("normal")
    polluted_df = parse_scenario("polluted")

    normal_df.to_csv(PROCESSED_DIR / "measurements_normal.csv", index=False, encoding="utf-8-sig")
    polluted_df.to_csv(PROCESSED_DIR / "measurements_polluted.csv", index=False, encoding="utf-8-sig")

    with (PROCESSED_DIR / "thresholds.json").open("w", encoding="utf-8") as f:
        json.dump(THRESHOLDS, f, ensure_ascii=False, indent=2)

    normal_status = build_station_status(normal_df, THRESHOLDS, "normal")
    polluted_status = build_station_status(polluted_df, THRESHOLDS, "polluted")

    (PROCESSED_DIR / "status_normal.json").write_text(json.dumps(normal_status, ensure_ascii=False, indent=2), encoding="utf-8")
    (PROCESSED_DIR / "status_polluted.json").write_text(json.dumps(polluted_status, ensure_ascii=False, indent=2), encoding="utf-8")

    history_df = build_alert_history(normal_status, polluted_status)
    history_df.to_csv(PROCESSED_DIR / "alert_history.csv", index=False, encoding="utf-8-sig")

    write_sqlite(normal_df, polluted_df)
    print("Đã khởi tạo dữ liệu demo thành công.")


if __name__ == "__main__":
    main()
