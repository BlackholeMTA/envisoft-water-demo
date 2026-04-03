from __future__ import annotations


def load_thresholds() -> dict:
    """
    Ngưỡng demo được chọn sao cho:
    - 4 file 'normal' không bị cảnh báo
    - 4 file 'polluted' chỉ cần tăng cao hơn các ngưỡng này là sẽ cảnh báo

    Bạn có thể sửa tiếp các ngưỡng này để khớp với bộ dữ liệu demo của mình.
    """

    return {
        "wastewater": {
            "ph_min": 6.0,
            "ph_max": 9.0,
            "cod": 20.0,
            "tss": 30.0,
            "ammonia": 3.0,
        },
        "water": {
            "ph_min": 6.5,
            "ph_max": 9.0,
            "tss": 10.0,
            "turbidity": 2.0,
            "conductivity": 500.0,
            "nitrate": 300.0,
            "do_min": 4.0,
        },
        "stack_emission": {
            "nh3": 2.0,
            "pm": 10.0,
        },
        "ambient_air": {
            "no2": 40.0,
            "so2": 20.0,
            "co": 4000.0,
            "o3": 80.0,
            "pm25": 35.0,
            "pm10": 60.0,
            "hg": 0.05,
        },
    }
