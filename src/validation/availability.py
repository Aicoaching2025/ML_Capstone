"""Forecast timing and availability checks from research contract v0.1.

These checks require explicit availability timestamps. They do not infer source
publication delays or prove historical vintage availability.
"""
from numbers import Integral

import pandas as pd


def _utc(values: pd.Series, name: str) -> pd.Series:
    """Reject naive or missing timestamps before normalizing to UTC."""
    converted = []
    for value in values:
        stamp = pd.Timestamp(value)
        if pd.isna(stamp) or stamp.tzinfo is None:
            raise ValueError(f"{name} must contain explicit timezone-aware timestamps")
        converted.append(stamp.tz_convert("UTC"))
    return pd.Series(converted, index=values.index, dtype="datetime64[ns, UTC]")


def forecast_targets(origins: pd.Series, horizon_hours: int) -> pd.DataFrame:
    """Build one hourly target per origin; horizon is measured to target end."""
    if isinstance(horizon_hours, bool) or not isinstance(horizon_hours, Integral) or horizon_hours not in (1, 24):
        raise ValueError("horizon_hours must be 1 or 24")
    origin = _utc(origins, "origin_utc")
    if not origin.eq(origin.dt.floor("h")).all():
        raise ValueError("Forecast origins must lie on exact UTC hour boundaries")
    if origin.duplicated().any():
        raise ValueError("Duplicate forecast origin")
    end = origin + pd.Timedelta(hours=int(horizon_hours))
    return pd.DataFrame({
        "origin_utc": origin,
        "horizon_hours": horizon_hours,
        "target_start_utc": end - pd.Timedelta(hours=1),
        "target_end_utc": end,
    })


def validate_availability(frame: pd.DataFrame, *, kind: str) -> pd.DataFrame:
    """Validate one input record per row against its forecast origin.

    All kinds require origin_utc and available_at_utc. Load requires
    interval_end_utc; observations require event_time_utc; weather forecasts
    require initialization_time_utc and valid_time_utc. Future forecast valid
    times are allowed, but future initialization or availability is rejected.
    This checks timing only, not run selection or target/weather alignment.
    """
    fields = {
        "load": ["interval_end_utc"],
        "observation": ["event_time_utc"],
        "forecast": ["initialization_time_utc", "valid_time_utc"],
    }
    if kind not in fields:
        raise ValueError("kind must be load, observation, or forecast")
    required = ["origin_utc", "available_at_utc", *fields[kind]]
    missing = set(required) - set(frame.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    result = frame.copy()
    for name in required:
        result[name] = _utc(result[name], name)
    if result.available_at_utc.gt(result.origin_utc).any():
        raise ValueError("Input was unavailable at forecast origin")
    event = result[fields[kind][0]]
    if event.gt(result.available_at_utc).any():
        raise ValueError("Availability precedes event or initialization time")
    if kind == "forecast" and result.valid_time_utc.lt(event).any():
        raise ValueError("Forecast valid time precedes initialization")
    return result
