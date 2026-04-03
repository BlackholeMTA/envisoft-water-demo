from __future__ import annotations

from typing import Any


def _compare(parameter_std: str, value: float, domain_thresholds: dict[str, Any]) -> tuple[bool, str | None]:
    if parameter_std == "ph":
        low = domain_thresholds.get("ph_min")
        high = domain_thresholds.get("ph_max")
        if low is not None and value < low:
            return True, f"pH thấp ({value} < {low})"
        if high is not None and value > high:
            return True, f"pH cao ({value} > {high})"
        return False, None

    threshold = domain_thresholds.get(parameter_std)
    if threshold is None:
        return False, None
    if value > threshold:
        return True, f"{parameter_std} vượt ngưỡng ({value} > {threshold})"
    return False, None


def find_exceedances(df, thresholds: dict) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        domain_thresholds = thresholds.get(row["domain"], {})
        exceeded, reason = _compare(row["parameter_std"], float(row["value"]), domain_thresholds)
        if exceeded and reason:
            record = row.to_dict()
            record["reason"] = reason
            record["threshold_value"] = domain_thresholds.get(row["parameter_std"], None)
            records.append(record)
    return records
