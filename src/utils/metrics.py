from __future__ import annotations

import math
from typing import Iterable

import numpy as np


def _to_float_array(values: Iterable[float]) -> np.ndarray:
    arr = np.array(list(values), dtype=float)
    return arr


def rmse(y_true: Iterable[float], y_pred: Iterable[float]) -> float:
    y_true = _to_float_array(y_true)
    y_pred = _to_float_array(y_pred)

    if len(y_true) == 0 or len(y_pred) == 0 or len(y_true) != len(y_pred):
        return float("nan")

    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def nrmse(y_true: Iterable[float], y_pred: Iterable[float]) -> float:
    y_true = _to_float_array(y_true)
    y_pred = _to_float_array(y_pred)

    if len(y_true) == 0 or len(y_pred) == 0 or len(y_true) != len(y_pred):
        return float("nan")

    obs_range = float(np.max(y_true) - np.min(y_true))
    if math.isclose(obs_range, 0.0):
        return float("nan")

    return float(rmse(y_true, y_pred) / obs_range)


def nrmse_percent(y_true: Iterable[float], y_pred: Iterable[float]) -> float:
    value = nrmse(y_true, y_pred)
    if np.isnan(value):
        return float("nan")
    return float(value * 100.0)
