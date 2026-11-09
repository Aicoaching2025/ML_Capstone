"""Expected hourly UTC grids for New York local-time periods (DST-aware)."""
import pandas as pd

NYC = "America/New_York"


def expected_hours(first_local_day: str, end_local_day_exclusive: str) -> pd.DatetimeIndex:
    """Hour-start UTC timestamps covering NYC local midnight to local midnight (end exclusive).

    A spring-forward local day has 23 hours and a fall-back local day has 25.
    """
    start = pd.Timestamp(first_local_day, tz=NYC).tz_convert("UTC")
    end = pd.Timestamp(end_local_day_exclusive, tz=NYC).tz_convert("UTC")
    return pd.date_range(start, end, freq="h", inclusive="left", name="interval_start_utc")


def missing_hours(expected: pd.DatetimeIndex, present) -> pd.DataFrame:
    """List every expected hour that is absent, with its NYC local label."""
    gap = expected.difference(pd.DatetimeIndex(present))
    return pd.DataFrame({"interval_start_utc": gap,
                         "local_time": gap.tz_convert(NYC).strftime("%Y-%m-%d %H:%M %Z")})
