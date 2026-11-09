"""Flatten Open-Meteo Previous Runs JSON into an hourly UTC table.

Values are kept exactly as returned; null stays missing (no imputation).
Instantaneous variables are valid at valid_time_utc. Open-Meteo precipitation is the
sum over the preceding hour, so it describes the interval ending at valid_time_utc.
"""
import pandas as pd

RENAME = {
    "temperature_2m_previous_day2": "fc_temperature_c",
    "dew_point_2m_previous_day2": "fc_dewpoint_c",
    "relative_humidity_2m_previous_day2": "fc_relative_humidity_pct",
    "wind_speed_10m_previous_day2": "fc_wind_speed_km_h",
    "precipitation_previous_day2": "fc_precipitation_mm_prev_hour",
}


def flatten_previous_runs(data: dict) -> pd.DataFrame:
    if "error" in data or "hourly" not in data:
        raise ValueError(f"Not a valid Open-Meteo response: {data.get('reason')}")
    if data.get("utc_offset_seconds", 0) != 0:
        raise ValueError("Expected timezone=GMT (UTC) response")
    hourly = data["hourly"]
    missing = set(RENAME) - set(hourly)
    if missing:
        raise ValueError(f"Missing variables: {sorted(missing)}")
    frame = pd.DataFrame({"valid_time_utc": pd.to_datetime(hourly["time"], format="%Y-%m-%dT%H:%M").tz_localize("UTC")})
    for source, name in RENAME.items():
        frame[name] = pd.to_numeric(pd.Series(hourly[source]), errors="raise").astype(float)
    if frame.valid_time_utc.duplicated().any():
        raise ValueError("Duplicate valid time")
    frame["fc_wind_speed_m_s"] = frame.fc_wind_speed_km_h / 3.6
    frame["forecast_lead"] = "previous_day2 (predicted 48 h before valid time)"
    return frame
