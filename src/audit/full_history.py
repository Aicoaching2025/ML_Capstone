"""Step 9 full-history data audit helpers.

Holdout rule (contract v0.2): 2025 rows may be COUNTED (rows, missing hours, fallback hours,
timestamp disagreements, quarantined rows) but never summarized by value. Every function that
looks at load or weather VALUES calls require_pre_holdout() first and refuses 2025 data.
"""
import numpy as np
import pandas as pd

NYC = "America/New_York"
HOLDOUT_YEAR = 2025


def local_year(times) -> pd.Series:
    """Calendar year in New York local time (the study's split calendar)."""
    return pd.Series(pd.DatetimeIndex(times).tz_convert(NYC).year, index=getattr(times, "index", None))


def pre_holdout(frame: pd.DataFrame, column: str = "interval_start_utc",
                holdout_year: int = HOLDOUT_YEAR) -> pd.DataFrame:
    """Rows whose local year is before the holdout year."""
    return frame[local_year(frame[column]).lt(holdout_year).to_numpy()]


def require_pre_holdout(times, holdout_year: int = HOLDOUT_YEAR) -> None:
    """Raise if any timestamp falls in the holdout year (value checks are pre-holdout only)."""
    years = pd.DatetimeIndex(times).tz_convert(NYC).year
    if len(years) and years.max() >= holdout_year:
        raise ValueError(f"Value-based audit refused: input contains {holdout_year}+ (holdout) rows.")


def missing_by_year(expected: pd.DatetimeIndex, present) -> pd.DataFrame:
    """Expected, present and missing hours per local year. Counts only, so 2025 is allowed."""
    expected = pd.DatetimeIndex(expected)
    have = expected.isin(pd.DatetimeIndex(pd.Series(present).dropna().unique()))
    frame = pd.DataFrame({"year": expected.tz_convert(NYC).year, "present": have})
    out = frame.groupby("year").present.agg(expected_hours="size", present_hours="sum")
    out["missing_hours"] = out.expected_hours - out.present_hours
    return out.astype(int).reset_index()


def missing_by_month(expected: pd.DatetimeIndex, present) -> pd.Series:
    """Missing hours per local month (index 'YYYY-MM'), for the missingness heatmap."""
    expected = pd.DatetimeIndex(expected)
    have = expected.isin(pd.DatetimeIndex(pd.Series(present).dropna().unique()))
    month = expected.tz_convert(NYC).strftime("%Y-%m")
    return pd.Series(~have, index=month).groupby(level=0).sum().astype(int)


def date_offset_minutes(date_text: pd.Series, metar_utc: pd.Series) -> pd.Series:
    """Minutes between the recovered METAR UTC time and the LCD DATE read as fixed EST (DATE + 5 h).

    0 means DATE agrees with a fixed UTC-5 clock. NaN means the METAR time was not recovered.
    """
    naive = pd.to_datetime(date_text.to_numpy()).tz_localize("UTC") + pd.Timedelta(hours=5)
    utc = pd.DatetimeIndex(pd.to_datetime(metar_utc.to_numpy(), utc=True))
    return pd.Series((utc - naive).total_seconds() / 60, index=date_text.index)


def flatline_runs(times: pd.Series, values: pd.Series, min_hours: int = 3) -> pd.DataFrame:
    """Runs of identical consecutive hourly values lasting at least min_hours (pre-holdout only)."""
    require_pre_holdout(times)
    t = pd.DatetimeIndex(times).to_numpy()
    v = values.to_numpy()
    contiguous = np.r_[False, np.diff(t) == np.timedelta64(1, "h")]
    same = np.r_[False, v[1:] == v[:-1]] & contiguous
    run_id = np.cumsum(~same)
    frame = pd.DataFrame({"run": run_id, "start": t, "value": v})
    runs = frame.groupby("run").agg(start_utc=("start", "first"), last_utc=("start", "last"),
                                    hours=("start", "size"), value=("value", "first"))
    runs = runs[runs.hours.ge(min_hours)].reset_index(drop=True)
    for col in ("start_utc", "last_utc"):
        runs[col] = pd.to_datetime(runs[col], utc=True)
    return runs


def load_deviation_flags(load: pd.DataFrame, z: float = 6.0) -> pd.DataFrame:
    """Flag hours that depart sharply from the same hour on nearby days (pre-holdout only).

    Reference = median load at the same clock hour 1, 2 and 3 days before and after.
    Score = robust z of the relative deviation (median/MAD). Flags are for review, not removal.
    """
    require_pre_holdout(load.interval_start_utc)
    s = load.set_index("interval_start_utc").load_mw.sort_index()
    ref = pd.concat([s.shift(k, freq="h").reindex(s.index) for k in (-72, -48, -24, 24, 48, 72)],
                    axis=1).median(axis=1)
    rel = (s - ref) / ref
    scale = 1.4826 * np.nanmedian(np.abs(rel - np.nanmedian(rel)))
    score = (rel - np.nanmedian(rel)) / scale
    step = s.diff()
    step = step.where(s.index.to_series().diff().eq(pd.Timedelta(hours=1)))
    out = pd.DataFrame({"interval_start_utc": s.index, "load_mw": s.to_numpy(),
                        "reference_mw": ref.to_numpy(), "relative_deviation": rel.to_numpy(),
                        "robust_z": score.to_numpy(), "hour_to_hour_change_mw": step.to_numpy()})
    out["flag_deviation"] = out.robust_z.abs().gt(z)
    out["flag_nonpositive"] = out.load_mw.le(0) | ~np.isfinite(out.load_mw)
    return out


WEATHER_RANGES = {  # Plausible NYC hourly ranges; outside = flagged for review, not removed
    "temperature_c": (-30.0, 45.0),
    "dewpoint_c": (-40.0, 35.0),
    "relative_humidity_pct": (1.0, 100.0),
    "wind_speed_m_s": (0.0, 40.0),
    "precipitation_mm": (0.0, 100.0),
}


def weather_range_flags(weather: pd.DataFrame) -> pd.DataFrame:
    """Count values outside plausible ranges, plus dew point above temperature (pre-holdout only)."""
    require_pre_holdout(weather.interval_start_utc)
    rows = []
    for col, (lo, hi) in WEATHER_RANGES.items():
        x = weather[col]
        rows.append({"check": f"{col} outside [{lo:g}, {hi:g}]",
                     "rows_checked": int(x.notna().sum()), "flagged": int((x.lt(lo) | x.gt(hi)).sum())})
    bad = weather.dewpoint_c.gt(weather.temperature_c + 0.5)
    rows.append({"check": "dewpoint_c > temperature_c + 0.5",
                 "rows_checked": int((weather.dewpoint_c.notna() & weather.temperature_c.notna()).sum()),
                 "flagged": int(bad.sum())})
    return pd.DataFrame(rows)


def dst_transitions(first_year: int, last_year: int) -> pd.DatetimeIndex:
    """UTC instants when New York switches between EST and EDT."""
    idx = pd.date_range(f"{first_year}-01-01", f"{last_year + 1}-01-01", freq="h", tz="UTC")
    offsets = idx.tz_convert(NYC).map(lambda t: t.utcoffset())
    change = np.r_[False, np.array(offsets[1:]) != np.array(offsets[:-1])]
    return idx[change]


def hours_to_nearest_dst(times, transitions: pd.DatetimeIndex) -> pd.Series:
    """Absolute hours from each timestamp to the nearest DST transition."""
    t = pd.DatetimeIndex(pd.to_datetime(times, utc=True)).asi8[:, None]
    gap = np.abs(t - transitions.asi8[None, :]).min(axis=1) / 3.6e12
    return pd.Series(gap, index=getattr(times, "index", None))
