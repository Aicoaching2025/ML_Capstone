"""Decoder for NYISO ISO Load Forecast (P-7, isolf) daily files.

Each daily file is named YYYYMMDDisolf.csv (the issue date) and holds about six local days
of hourly forecasts. Timestamps are NYC local clock times without a timezone label:
the repeated fall-back hour appears twice (first EDT, then EST) and the skipped spring
hour is absent. The selection rule keeps the file issued on the local day before each
target local day (a day-ahead forecast); the exact issue time is not published here.
"""
import pandas as pd

NYC = "America/New_York"
ZONES = ["Capitl", "Centrl", "Dunwod", "Genese", "Hud Vl", "Longil", "Mhk Vl", "Millwd",
         "N.Y.C.", "North", "West", "NYISO"]
SOURCE_COLUMNS = ["Time Stamp", *ZONES]


def decode_isolf(raw: pd.DataFrame, issue_date: str, zone: str = "N.Y.C.") -> pd.DataFrame:
    if list(raw.columns) != SOURCE_COLUMNS:
        raise ValueError(f"Unexpected P-7 schema: {list(raw.columns)}")
    if raw.empty or raw[["Time Stamp", zone]].isna().any().any():
        raise ValueError("Empty source or missing source fields")
    naive = pd.to_datetime(raw["Time Stamp"], format="%m/%d/%Y %H:%M", errors="raise")
    if not naive.is_monotonic_increasing:
        raise ValueError("Timestamps out of order")
    repeats = naive.duplicated(keep="first")
    counts = naive.value_counts()
    if (counts > 2).any():
        raise ValueError("Duplicate local hour (more than two occurrences)")
    first_of_pair = naive.isin(counts[counts == 2].index) & ~repeats
    # First occurrence of a repeated local hour is daylight time (EDT), the second standard time.
    ambiguous = (first_of_pair | ~naive.isin(counts[counts == 2].index)).to_numpy()
    try:
        local = naive.dt.tz_localize(NYC, ambiguous=ambiguous, nonexistent="raise")
    except Exception as e:  # repeated hour that is not a real DST repeat, or a skipped hour present
        raise ValueError(f"Duplicate or nonexistent local hour: {e}") from e
    utc = local.dt.tz_convert("UTC")
    if utc.duplicated().any():
        raise ValueError("Duplicate UTC hour")
    if not utc.diff().dropna().eq(pd.Timedelta(hours=1)).all():
        raise ValueError("Forecast hours are not contiguous in UTC")
    forecast = pd.to_numeric(raw[zone], errors="raise").astype(float)
    return pd.DataFrame({
        "interval_start_utc": utc.to_numpy(),
        "interval_end_utc": (utc + pd.Timedelta(hours=1)).to_numpy(),
        "target_local_date": local.dt.strftime("%Y-%m-%d").to_numpy(),
        "issue_date_local": pd.Timestamp(issue_date).strftime("%Y-%m-%d"),
        "source_timestamp": raw["Time Stamp"].to_numpy(),
        "forecast_mw": forecast.to_numpy(),
    })


def select_day_ahead(decoded: pd.DataFrame) -> pd.DataFrame:
    """Keep rows whose target local day is exactly one day after the issue day."""
    issue = pd.to_datetime(decoded.issue_date_local)
    target = pd.to_datetime(decoded.target_local_date)
    keep = decoded[(target - issue).dt.days.eq(1)]
    if keep.duplicated("interval_start_utc").any():
        raise ValueError("More than one day-ahead forecast for a target hour")
    return keep.sort_values("interval_start_utc").reset_index(drop=True)
