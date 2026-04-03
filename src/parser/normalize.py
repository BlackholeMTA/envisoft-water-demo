from __future__ import annotations

from pathlib import Path
import pandas as pd

PARAMETER_MAP = {
    "Temp": "temperature",
    "TempIn": "temperature_indoor",
    "Nhiệtđộ": "temperature",
    "Amoni": "ammonia",
    "COD": "cod",
    "pH": "ph",
    "TSS": "tss",
    "Flow": "flow",
    "Flowin": "flow_in",
    "Flow_Out": "flow_out",
    "DO": "do",
    "TURB": "turbidity",
    "COND": "conductivity",
    "NO3-N": "nitrate",
    "PM2.5": "pm25",
    "PM10": "pm10",
    "PM": "pm",
    "NO2": "no2",
    "NO": "no",
    "NOx": "nox",
    "SO2": "so2",
    "CO": "co",
    "O3": "o3",
    "NH3": "nh3",
    "Humidity": "humidity",
    "Pressure": "pressure",
    "Ápsuất": "pressure",
    "WindSpeed": "wind_speed",
    "WindDir": "wind_direction",
    "Radiation": "radiation",
    "Hg": "hg",
}

UNIT_MAP = {
    "mg/l": "mg/L",
    "mg/L": "mg/L",
    "ug/m3": "µg/m3",
    "oC": "°C",
    "uS/cm": "µS/cm",
    "w/m2": "W/m²",
    "m3/h": "m3/h",
    "mg/Nm3": "mg/Nm3",
    "": "-",
}

STATION_NAME_MAP = {
    "TB_CAPH": "Trạm TB_CAPH",
    "HN_PHCH": "Trạm HN_PHCH",
    "TB_NMAM": "Trạm TB_NMAM",
    "HN_BKHN": "Trạm HN_BKHN",
}


def infer_station_code(source_file: str) -> str:
    stem = Path(source_file).stem
    parts = stem.split("_")
    return "_".join(parts[:2]) if len(parts) >= 2 else stem


def infer_domain(source_file: str) -> str:
    name = source_file.upper()
    if "NUOSXL" in name:
        return "wastewater"
    if "NUOPCH" in name:
        return "water"
    if "KHIAMO" in name:
        return "stack_emission"
    if "KHIKXQ" in name:
        return "ambient_air"
    return "unknown"


def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    result["parameter_std"] = result["parameter"].map(PARAMETER_MAP).fillna(result["parameter"].str.lower())
    result["unit_std"] = result["unit"].map(UNIT_MAP).fillna(result["unit"])
    result["value"] = pd.to_numeric(result["value"], errors="coerce")
    result["station_code"] = result["source_file"].apply(infer_station_code)
    result["station_name"] = result["station_code"].map(STATION_NAME_MAP).fillna(result["station_code"])
    result["domain"] = result["source_file"].apply(infer_domain)
    result["observed_at"] = pd.to_datetime(result["timestamp_raw"], format="%Y%m%d%H%M%S", errors="coerce")
    return result
