from __future__ import annotations

from pathlib import Path
from typing import Any

from src.engine.threshold_engine import find_exceedances
from src.vision.image_predictor import analyze_image


CAMERA_MAP = {
    "TB_CAPH": {"normal": "data/camera/normal/normal_01.jpg", "polluted": "data/camera/polluted/polluted_01.jpg"},
    "HN_PHCH": {"normal": "data/camera/normal/normal_02.jpg", "polluted": "data/camera/polluted/polluted_02.jpg"},
    "TB_NMAM": {"normal": "data/camera/normal/normal_03.jpg", "polluted": "data/camera/polluted/polluted_03.jpg"},
    "HN_BKHN": {"normal": "data/camera/normal/normal_04.jpg", "polluted": "data/camera/polluted/polluted_04.jpg"},
}


def build_station_status(df, thresholds: dict[str, Any], scenario: str) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for station_code, station_df in df.groupby("station_code"):
        station_df = station_df.sort_values("observed_at")
        exceedances = find_exceedances(station_df, thresholds)
        image_rel = CAMERA_MAP.get(station_code, CAMERA_MAP["TB_CAPH"])["polluted" if scenario == "polluted" else "normal"]
        image_info = analyze_image(Path(image_rel))

        if exceedances:
            level = "danger"
            final_status = "Cảnh báo ô nhiễm"
        else:
            level = "normal"
            final_status = "Bình thường"

        result.append(
            {
                "station_code": station_code,
                "station_name": station_df.iloc[0]["station_name"],
                "domain": station_df.iloc[0]["domain"],
                "scenario": scenario,
                "observed_at": station_df["observed_at"].max().isoformat(),
                "is_alert": bool(exceedances),
                "alert_count": len(exceedances),
                "final_status": final_status,
                "level": level,
                "reasons": [item["reason"] for item in exceedances],
                "camera_image": image_rel,
                "ai_prediction": image_info["prediction_label"],
                "ai_confidence": image_info["confidence"],
                "dark_ratio": image_info["dark_ratio"],
                "ai_note": image_info["note"],
            }
        )
    return result
