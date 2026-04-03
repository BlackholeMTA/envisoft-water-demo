from __future__ import annotations

from pathlib import Path
import cv2
import numpy as np


def analyze_image(image_path: str | Path) -> dict:
    path = Path(image_path)
    image = cv2.imread(str(path))
    if image is None:
        return {
            "prediction_label": "Không đọc được ảnh",
            "confidence": 0.0,
            "dark_ratio": 0.0,
            "note": "Thiếu dữ liệu camera",
        }

    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    lower = np.array([0, 0, 0])
    upper = np.array([180, 255, 80])
    mask = cv2.inRange(hsv, lower, upper)
    dark_ratio = float(mask.mean() / 255.0)
    polluted = dark_ratio > 0.18
    confidence = min(0.99, max(0.55, dark_ratio * 2.5))

    return {
        "prediction_label": "Có dấu hiệu ô nhiễm" if polluted else "Chưa phát hiện rõ ô nhiễm",
        "confidence": round(confidence, 2),
        "dark_ratio": round(dark_ratio, 3),
        "note": "AI demo dựa trên tỷ lệ vùng tối/đục trong ảnh.",
    }
