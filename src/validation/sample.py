"""Validation for the synthetic setup fixture, not production source rules."""
import numpy as np
import pandas as pd


def validate_sample(frame: pd.DataFrame) -> pd.DataFrame:
    required = {"interval_start_utc", "interval_end_utc", "zone", "load_mw", "temperature_c"}
    if not required.issubset(frame.columns):
        raise ValueError("Missing required sample columns")
    result = frame.copy()
    if result.empty or result[list(required)].isna().any().any():
        raise ValueError("Sample is empty or contains missing values")
    for field in ["interval_start_utc", "interval_end_utc"]:
        if not result[field].astype(str).str.endswith("Z").all():
            raise ValueError("Fixture timestamps must explicitly use UTC Z suffix")
        result[field] = pd.to_datetime(result[field], utc=True, errors="raise")
    if result.duplicated(["zone", "interval_start_utc"]).any():
        raise ValueError("Duplicate interval")
    if not result["zone"].eq("J").all():
        raise ValueError("Unexpected zone")
    if not (result.interval_end_utc - result.interval_start_utc).dt.total_seconds().eq(3600).all():
        raise ValueError("Intervals must span one hour")
    result = result.sort_values("interval_start_utc").reset_index(drop=True)
    if not result.interval_start_utc.diff().iloc[1:].dt.total_seconds().eq(3600).all():
        raise ValueError("Sample hours must be contiguous")
    for field in ["load_mw", "temperature_c"]:
        result[field] = pd.to_numeric(result[field], errors="raise")
        if not np.isfinite(result[field]).all():
            raise ValueError("Nonfinite numeric value")
    if not result.load_mw.gt(0).all():
        raise ValueError("Synthetic load must be positive")
    return result
