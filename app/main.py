from __future__ import annotations

from pathlib import Path
import base64
import math
import sys
from typing import Any

BASE_ROOT = Path(__file__).resolve().parents[1]
if str(BASE_ROOT) not in sys.path:
    sys.path.append(str(BASE_ROOT))

import pandas as pd
import plotly.express as px
import streamlit as st

from src.data.loader import load_history, load_measurements, load_status
from src.data.thresholds import load_thresholds
from src.utils.metrics import rmse, nrmse_percent

st.set_page_config(page_title="EnviSoft Alert Demo", layout="wide")

ASSET_AUDIO = BASE_ROOT / "assets" / "alert.wav"


def autoplay_audio(path: Path) -> None:
    if not path.exists():
        return
    audio_bytes = path.read_bytes()
    b64 = base64.b64encode(audio_bytes).decode()
    st.markdown(
        f"""
        <audio autoplay>
            <source src="data:audio/wav;base64,{b64}" type="audio/wav">
        </audio>
        """,
        unsafe_allow_html=True,
    )


def is_missing(value: Any) -> bool:
    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except Exception:
        return False


def safe_cell(value: Any):
    if isinstance(value, list):
        return " | ".join(str(x) for x in value if not is_missing(x))
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, (dict, tuple, set)):
        return str(value)
    if is_missing(value):
        return ""
    return value


def make_arrow_safe(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=df.columns if df is not None else [])

    safe_df = df.copy()
    for col in safe_df.columns:
        safe_df[col] = safe_df[col].apply(safe_cell)
        if pd.api.types.is_object_dtype(safe_df[col]):
            safe_df[col] = safe_df[col].astype(str)
    return safe_df


def format_metric_value(value, digits: int = 2) -> str:
    if value is None:
        return "-"
    try:
        if pd.isna(value):
            return "-"
    except Exception:
        pass

    if isinstance(value, (int, float)):
        if isinstance(value, float):
            if math.isfinite(value):
                return f"{value:.{digits}f}"
            return "-"
        return str(value)

    return str(value)


def normalize_text(value: Any) -> str:
    if is_missing(value):
        return ""
    return str(value).strip()


def get_station_meta(status_df: pd.DataFrame, station_code: str) -> dict:
    matched = status_df[status_df["station_code"].astype(str) == str(station_code)]
    if matched.empty:
        return {
            "station_code": station_code,
            "station_name": station_code,
            "domain": "",
            "camera_image": "",
            "ai_prediction": "Chưa có dữ liệu AI ảnh",
            "ai_confidence": "-",
            "dark_ratio": None,
            "ai_note": "",
        }

    row = matched.iloc[0]
    return {
        "station_code": normalize_text(row.get("station_code")),
        "station_name": normalize_text(row.get("station_name")) or normalize_text(row.get("station_code")),
        "domain": normalize_text(row.get("domain")),
        "camera_image": normalize_text(row.get("camera_image")),
        "ai_prediction": normalize_text(row.get("ai_prediction")) or "Chưa có dữ liệu AI ảnh",
        "ai_confidence": row.get("ai_confidence", "-"),
        "dark_ratio": row.get("dark_ratio"),
        "ai_note": normalize_text(row.get("ai_note")),
    }


def evaluate_parameter(domain: str, parameter_std: str, value: float, thresholds: dict) -> str | None:
    domain_thresholds = thresholds.get(domain, {})
    p = normalize_text(parameter_std).lower()

    if p == "ph":
        ph_min = domain_thresholds.get("ph_min")
        ph_max = domain_thresholds.get("ph_max")
        if ph_min is not None and value < ph_min:
            return f"pH thấp ({value:.2f} < {ph_min})"
        if ph_max is not None and value > ph_max:
            return f"pH cao ({value:.2f} > {ph_max})"
        return None

    if p == "do":
        do_min = domain_thresholds.get("do_min")
        if do_min is not None and value < do_min:
            return f"DO thấp ({value:.2f} < {do_min})"
        return None

    threshold_value = domain_thresholds.get(p)
    if threshold_value is None:
        return None

    if value > threshold_value:
        return f"{p.upper()} vượt ngưỡng ({value:.2f} > {threshold_value})"

    return None


def get_threshold_display(domain: str, parameter_std: str, thresholds: dict) -> str:
    domain_thresholds = thresholds.get(domain, {})
    p = normalize_text(parameter_std).lower()

    if p == "ph":
        return f"{domain_thresholds.get('ph_min', '-')} - {domain_thresholds.get('ph_max', '-')}"
    if p == "do":
        return f">= {domain_thresholds.get('do_min', '-')}"
    return str(domain_thresholds.get(p, "-"))


def ensure_prediction_columns(df: pd.DataFrame, scenario: str) -> pd.DataFrame:
    """
    Nếu dữ liệu thật chưa có observed_value / predicted_value,
    tạo cột demo để RMSE và NRMSE vẫn hiển thị được.
    """
    working_df = df.copy()

    if "observed_value" not in working_df.columns:
        working_df["observed_value"] = pd.to_numeric(working_df.get("value"), errors="coerce")
    else:
        working_df["observed_value"] = pd.to_numeric(working_df["observed_value"], errors="coerce")

    if "predicted_value" not in working_df.columns:
        # tạo dự đoán demo dựa trên value
        if scenario == "normal":
            working_df["predicted_value"] = working_df["observed_value"] * 0.96
        else:
            working_df["predicted_value"] = working_df["observed_value"] * 0.90
    else:
        working_df["predicted_value"] = pd.to_numeric(working_df["predicted_value"], errors="coerce")

    return working_df


def compute_station_result(
    station_df: pd.DataFrame,
    station_meta: dict,
    thresholds: dict,
) -> dict:
    domain = normalize_text(station_meta.get("domain"))
    reasons: list[str] = []

    working_df = station_df.copy()
    if "value" in working_df.columns:
        working_df["value"] = pd.to_numeric(working_df["value"], errors="coerce")

    for _, row in working_df.iterrows():
        value = row.get("value")
        if pd.isna(value):
            continue

        parameter_std = normalize_text(row.get("parameter_std"))
        reason = evaluate_parameter(domain, parameter_std, float(value), thresholds)
        if reason:
            reasons.append(reason)

    is_alert = len(reasons) > 0
    final_status = "Cảnh báo ô nhiễm" if is_alert else "Bình thường"

    observed_series = pd.to_numeric(working_df.get("observed_value"), errors="coerce")
    predicted_series = pd.to_numeric(working_df.get("predicted_value"), errors="coerce")

    metric_df = pd.DataFrame({
        "observed": observed_series,
        "predicted": predicted_series,
    }).dropna()

    if metric_df.empty:
        rmse_value = float("nan")
        nrmse_value = float("nan")
    else:
        rmse_value = rmse(metric_df["observed"], metric_df["predicted"])
        nrmse_value = nrmse_percent(metric_df["observed"], metric_df["predicted"])

    return {
        "station_code": station_meta.get("station_code", ""),
        "station_name": station_meta.get("station_name", ""),
        "domain": domain,
        "is_alert": is_alert,
        "alert_count": len(reasons),
        "reasons": reasons,
        "final_status": final_status,
        "camera_image": station_meta.get("camera_image", ""),
        "ai_prediction": station_meta.get("ai_prediction", ""),
        "ai_confidence": station_meta.get("ai_confidence", "-"),
        "dark_ratio": station_meta.get("dark_ratio"),
        "ai_note": station_meta.get("ai_note", ""),
        "rmse": rmse_value,
        "nrmse_percent": nrmse_value,
    }


def render_popup_overlay(station_result: dict) -> None:
    reasons = station_result.get("reasons", [])
    short_reason = reasons[0] if reasons else "Có chỉ số vượt ngưỡng"
    more_count = max(0, len(reasons) - 1)
    more_text = f" và {more_count} chỉ số khác" if more_count > 0 else ""

    station_code = station_result.get("station_code", "")
    view_href = f"?action=view&station={station_code}"
    close_href = "?action=close"

    popup_html = f"""
    <style>
      .env-popup-backdrop {{
        position: fixed;
        inset: 0;
        background: rgba(0, 0, 0, 0.45);
        z-index: 99998;
      }}
      .env-popup-modal {{
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        width: min(540px, calc(100vw - 32px));
        background: #ffffff;
        border-radius: 20px;
        border: 2px solid #ef4444;
        box-shadow: 0 24px 80px rgba(0,0,0,0.35);
        z-index: 99999;
        overflow: hidden;
        font-family: Arial, sans-serif;
      }}
      .env-popup-header {{
        background: linear-gradient(90deg, #b91c1c, #ef4444);
        color: white;
        padding: 18px 22px;
        font-size: 24px;
        font-weight: 700;
      }}
      .env-popup-body {{
        padding: 20px 22px 22px 22px;
      }}
      .env-popup-line {{
        margin-bottom: 12px;
        font-size: 16px;
        color: #111827;
        line-height: 1.45;
      }}
      .env-popup-note {{
        margin-top: 10px;
        padding: 12px 14px;
        background: #fff7ed;
        border-radius: 12px;
        color: #9a3412;
        font-size: 14px;
      }}
      .env-popup-actions {{
        display: flex;
        gap: 12px;
        margin-top: 18px;
        flex-wrap: wrap;
      }}
      .env-popup-btn {{
        text-decoration: none !important;
        padding: 12px 18px;
        border-radius: 12px;
        font-size: 15px;
        font-weight: 700;
        display: inline-block;
      }}
      .env-popup-btn-view {{
        background: #2563eb;
        color: white !important;
      }}
      .env-popup-btn-close {{
        background: #e5e7eb;
        color: #111827 !important;
      }}
    </style>

    <div class="env-popup-backdrop"></div>
    <div class="env-popup-modal">
      <div class="env-popup-header">⚠️ CẢNH BÁO Ô NHIỄM</div>
      <div class="env-popup-body">
        <div class="env-popup-line"><b>Trạm:</b> {station_result.get("station_name", "-")}</div>
        <div class="env-popup-line"><b>Kết luận:</b> {station_result.get("final_status", "-")}</div>
        <div class="env-popup-line"><b>Chi tiết:</b> {short_reason}{more_text}</div>
        <div class="env-popup-note">
          Hệ thống đã phát hiện chỉ số vượt ngưỡng demo. Vui lòng kiểm tra ngay.
        </div>
        <div class="env-popup-actions">
          <a class="env-popup-btn env-popup-btn-view" href="{view_href}">
            Xem chi tiết
          </a>
          <a class="env-popup-btn env-popup-btn-close" href="{close_href}">
            Tắt popup
          </a>
        </div>
      </div>
    </div>
    """
    st.markdown(popup_html, unsafe_allow_html=True)


# ===== xử lý action từ popup =====
query_action = st.query_params.get("action", "")
query_station = st.query_params.get("station", "")

if "scenario" not in st.session_state:
    st.session_state["scenario"] = "normal"
if "selected_station" not in st.session_state:
    st.session_state["selected_station"] = ""
if "hide_popup_for_key" not in st.session_state:
    st.session_state["hide_popup_for_key"] = None

if query_action == "close":
    st.session_state["hide_popup_for_key"] = "manual_close"
    st.query_params.clear()
    st.rerun()

if query_action == "view" and query_station:
    st.session_state["scenario"] = "polluted"
    st.session_state["selected_station"] = str(query_station)
    st.session_state["hide_popup_for_key"] = f"viewed_{query_station}"
    st.query_params.clear()
    st.rerun()


st.title("Demo cảnh báo ô nhiễm đa trạm")
st.caption(
    "Khi chỉ số vượt ngưỡng demo, hệ thống phát cảnh báo màn hình + âm thanh, "
    "đồng thời hiển thị camera, AI dự đoán từ ảnh."
)

scenario = st.sidebar.radio(
    "Chọn kịch bản",
    ["normal", "polluted"],
    format_func=lambda x: "Bình thường" if x == "normal" else "Cảnh báo",
    key="scenario",
)

status_df = load_status(scenario)
measurements_df = load_measurements(scenario)
measurements_df = ensure_prediction_columns(measurements_df, scenario)

history_df = load_history()
thresholds = load_thresholds()

if history_df is not None and not history_df.empty:
    history_df = ensure_prediction_columns(history_df, scenario)

if measurements_df.empty:
    st.error("Không có dữ liệu chỉ số để hiển thị.")
    st.stop()

if "station_code" not in measurements_df.columns:
    st.error("Thiếu cột station_code trong dữ liệu measurements.")
    st.stop()

station_options = sorted(measurements_df["station_code"].astype(str).unique().tolist())
default_station = station_options[0] if station_options else ""

if not st.session_state["selected_station"] or st.session_state["selected_station"] not in station_options:
    st.session_state["selected_station"] = default_station

selected_station = st.sidebar.selectbox(
    "Chọn trạm",
    station_options,
    index=station_options.index(st.session_state["selected_station"]),
)
st.session_state["selected_station"] = selected_station

selected_station_df = measurements_df[measurements_df["station_code"].astype(str) == str(selected_station)].copy()
station_meta = get_station_meta(status_df, selected_station)
selected_result = compute_station_result(selected_station_df, station_meta, thresholds)

first_alert_result = None
for station_code in station_options:
    tmp_station_df = measurements_df[measurements_df["station_code"].astype(str) == str(station_code)].copy()
    tmp_meta = get_station_meta(status_df, station_code)
    tmp_result = compute_station_result(tmp_station_df, tmp_meta, thresholds)
    if tmp_result["is_alert"]:
        first_alert_result = tmp_result
        break

show_popup = False
if first_alert_result:
    if scenario == "polluted":
        if st.session_state["hide_popup_for_key"] not in {"manual_close", f"viewed_{first_alert_result['station_code']}"}:
            show_popup = True

if show_popup and first_alert_result:
    autoplay_audio(ASSET_AUDIO)
    render_popup_overlay(first_alert_result)

if selected_result["is_alert"]:
    st.error(f"CẢNH BÁO Ô NHIỄM tại {selected_result['station_name']}")
else:
    st.success(f"{selected_result['station_name']} đang ở trạng thái bình thường")

summary_cols = st.columns(4)
summary_cols[0].metric("Trạm", selected_result["station_code"])
summary_cols[1].metric("Loại dữ liệu", selected_result["domain"])
summary_cols[2].metric("Kết luận", selected_result["final_status"])
summary_cols[3].metric("Số chỉ số vượt ngưỡng", str(selected_result["alert_count"]))

col1, col2 = st.columns([1.2, 1])

with col1:
    st.subheader("Chỉ số quan trắc hiện tại")

    latest_table = selected_station_df[
        ["parameter", "parameter_std", "value", "unit_std", "status_code", "observed_value", "predicted_value"]
    ].copy()

    latest_table["value"] = pd.to_numeric(latest_table["value"], errors="coerce")
    latest_table["observed_value"] = pd.to_numeric(latest_table["observed_value"], errors="coerce")
    latest_table["predicted_value"] = pd.to_numeric(latest_table["predicted_value"], errors="coerce")

    display_rows = []
    for _, row in latest_table.iterrows():
        parameter_std = normalize_text(row.get("parameter_std"))
        value = row.get("value")
        reason = None
        if not pd.isna(value):
            reason = evaluate_parameter(selected_result["domain"], parameter_std, float(value), thresholds)

        threshold_text = get_threshold_display(selected_result["domain"], parameter_std, thresholds)

        display_rows.append(
            {
                "Chỉ số": normalize_text(row.get("parameter")),
                "Giá trị đo": row.get("observed_value"),
                "Giá trị dự đoán": row.get("predicted_value"),
                "Giá trị hiện tại": row.get("value"),
                "Đơn vị": normalize_text(row.get("unit_std")),
                "Ngưỡng demo": threshold_text,
                "Kết quả": "Vượt ngưỡng" if reason else "Bình thường",
                "Mã trạng thái": normalize_text(row.get("status_code")),
            }
        )

    display_df = pd.DataFrame(display_rows)

    if not display_df.empty:
        st.dataframe(make_arrow_safe(display_df), use_container_width=True, hide_index=True)
    else:
        st.info("Không có dữ liệu bảng chỉ số.")

    st.subheader("Các chỉ số vượt ngưỡng")
    if selected_result["reasons"]:
        for reason in selected_result["reasons"]:
            st.markdown(f"• {reason}")
    else:
        st.write("Không có chỉ số nào vượt ngưỡng.")

with col2:
    st.subheader("Hình ảnh camera")
    camera_image = normalize_text(selected_result.get("camera_image"))
    image_path = BASE_ROOT / camera_image if camera_image else None

    if image_path and image_path.exists():
        st.image(
            str(image_path),
            caption=f"{selected_result['station_name']} - {selected_result['final_status']}",
            use_container_width=True,
        )
    else:
        st.warning("Không tìm thấy ảnh camera cho trạm này.")

    st.subheader("AI dự đoán từ ảnh")
    st.write(f"**Kết quả:** {selected_result.get('ai_prediction', '-')}")
    st.write(f"**Độ tin cậy demo:** {selected_result.get('ai_confidence', '-')}")
    st.write(f"**Dark ratio:** {format_metric_value(selected_result.get('dark_ratio'))}")
    st.caption(str(selected_result.get("ai_note", "")))

st.subheader("Biểu đồ so sánh đo thực tế và dự đoán")
if not display_df.empty:
    chart_df = display_df.copy()
    chart_df["Giá trị đo"] = pd.to_numeric(chart_df["Giá trị đo"], errors="coerce")
    chart_df["Giá trị dự đoán"] = pd.to_numeric(chart_df["Giá trị dự đoán"], errors="coerce")

    melted_df = chart_df.melt(
        id_vars=["Chỉ số"],
        value_vars=["Giá trị đo", "Giá trị dự đoán"],
        var_name="Loại giá trị",
        value_name="Giá trị",
    ).dropna(subset=["Giá trị"])

    if not melted_df.empty:
        fig_compare = px.bar(
            melted_df,
            x="Chỉ số",
            y="Giá trị",
            color="Loại giá trị",
            barmode="group",
        )
        st.plotly_chart(fig_compare, use_container_width=True)
    else:
        st.info("Không có dữ liệu hợp lệ để vẽ biểu đồ so sánh.")

st.subheader("Biểu đồ nhanh các chỉ số hiện tại")
if not display_df.empty:
    chart_df2 = display_df.copy()
    chart_df2["Giá trị hiện tại"] = pd.to_numeric(chart_df2["Giá trị hiện tại"], errors="coerce")
    chart_df2 = chart_df2.dropna(subset=["Giá trị hiện tại"])

    if not chart_df2.empty:
        fig = px.bar(
            chart_df2,
            x="Chỉ số",
            y="Giá trị hiện tại",
            color="Kết quả",
            hover_data=["Đơn vị", "Ngưỡng demo", "Mã trạng thái"],
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Không có dữ liệu số hợp lệ để vẽ biểu đồ.")
else:
    st.info("Không có dữ liệu biểu đồ.")

st.subheader("Lịch sử cảnh báo")
if history_df.empty:
    st.info("Chưa có lịch sử cảnh báo.")
else:
    filtered_history = history_df[history_df["station_code"].astype(str) == str(selected_station)].copy()

    if "observed_at" in filtered_history.columns:
        filtered_history["observed_at"] = pd.to_datetime(
            filtered_history["observed_at"], errors="coerce"
        )

    if "reasons" in filtered_history.columns:
        filtered_history["reasons"] = filtered_history["reasons"].apply(safe_cell)

    history_metric_df = filtered_history.copy()
    history_metric_df["observed_value"] = pd.to_numeric(history_metric_df.get("observed_value"), errors="coerce")
    history_metric_df["predicted_value"] = pd.to_numeric(history_metric_df.get("predicted_value"), errors="coerce")

    valid_metric_history = history_metric_df[["observed_value", "predicted_value"]].dropna()

    if not valid_metric_history.empty:
        history_rmse = rmse(valid_metric_history["observed_value"], valid_metric_history["predicted_value"])
        history_nrmse = nrmse_percent(valid_metric_history["observed_value"], valid_metric_history["predicted_value"])

        h1, h2 = st.columns(2)
        h1.metric("RMSE lịch sử", format_metric_value(history_rmse, 3))
        h2.metric("NRMSE lịch sử", f"{format_metric_value(history_nrmse, 2)}%")

    st.dataframe(make_arrow_safe(filtered_history), use_container_width=True, hide_index=True)

st.subheader("Tổng quan 4 trạm trong kịch bản hiện tại")

overview_rows = []
for station_code in station_options:
    station_df = measurements_df[measurements_df["station_code"].astype(str) == str(station_code)].copy()
    meta = get_station_meta(status_df, str(station_code))
    result = compute_station_result(station_df, meta, thresholds)

    overview_rows.append(
        {
            "Mã trạm": result["station_code"],
            "Tên trạm": result["station_name"],
            "Loại dữ liệu": result["domain"],
            "Kết luận": result["final_status"],
            "Số chỉ số vượt": result["alert_count"],
            "AI ảnh": result["ai_prediction"],
        }
    )

overview_df = pd.DataFrame(overview_rows)
st.dataframe(make_arrow_safe(overview_df), use_container_width=True, hide_index=True)