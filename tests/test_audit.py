"""Step 9 audit helpers: counts, holdout guard, timing checks and load value flags."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from audit.full_history import (date_offset_minutes, dst_transitions, flatline_runs, hours_to_nearest_dst,
                                load_deviation_flags, missing_by_month, missing_by_year, pre_holdout,
                                require_pre_holdout, weather_range_flags)
from cleaning.hours import expected_hours

ROOT = Path(__file__).resolve().parents[1]


def hourly(start, periods):
    return pd.date_range(start, periods=periods, freq="h", tz="UTC")


def test_missing_by_year_counts_dst_years_and_allows_holdout_counts():
    full = expected_hours("2024-01-01", "2026-01-01")
    present = full.delete([10, 9000])  # one gap in 2024, one in 2025
    out = missing_by_year(full, present).set_index("year")
    assert out.loc[2024, "expected_hours"] == 8784 and out.loc[2025, "expected_hours"] == 8760
    assert out.loc[2024, "missing_hours"] == 1 and out.loc[2025, "missing_hours"] == 1


def test_missing_by_month_uses_local_months():
    full = expected_hours("2024-11-01", "2024-12-01")
    month = missing_by_month(full, full[1:])
    assert month.to_dict() == {"2024-11": 1}


def test_holdout_boundary_is_new_york_local_year():
    require_pre_holdout(pd.DatetimeIndex(["2025-01-01 04:00"], tz="UTC"))  # 2024-12-31 23:00 EST: allowed
    with pytest.raises(ValueError, match="holdout"):
        require_pre_holdout(pd.DatetimeIndex(["2025-01-01 05:00"], tz="UTC"))  # 2025-01-01 00:00 EST
    frame = pd.DataFrame({"interval_start_utc": hourly("2025-01-01 03:00", 4)})
    assert len(pre_holdout(frame)) == 2


def test_value_checks_refuse_2025_rows():
    t = hourly("2024-12-31 20:00", 24)
    load = pd.DataFrame({"interval_start_utc": t, "load_mw": np.linspace(5000, 6000, 24)})
    wx = pd.DataFrame({"interval_start_utc": t, "temperature_c": 1.0, "dewpoint_c": 0.0,
                       "relative_humidity_pct": 90.0, "wind_speed_m_s": 2.0, "precipitation_mm": 0.0})
    for call in (lambda: load_deviation_flags(load), lambda: flatline_runs(load.interval_start_utc, load.load_mw),
                 lambda: weather_range_flags(wx)):
        with pytest.raises(ValueError, match="holdout"):
            call()


def test_flatline_runs_need_consecutive_hours():
    t = hourly("2024-06-01", 10).delete(6)  # gap between index 5 and 6
    v = pd.Series([1, 2, 2, 2, 3, 4, 4, 4, 5])  # run of 3 at idx 1-3; second "run" spans the gap
    runs = flatline_runs(pd.Series(t), v, min_hours=3)
    assert len(runs) == 1 and runs.hours.iloc[0] == 3 and runs.value.iloc[0] == 2
    assert str(runs.start_utc.dt.tz) == "UTC"


def test_load_deviation_flags_catch_an_injected_spike():
    t = hourly("2024-05-01 04:00", 24 * 21)
    hour = t.tz_convert("America/New_York").hour
    rng = np.random.default_rng(0)
    load = np.asarray(5000 + 1000 * np.sin(2 * np.pi * hour / 24) + rng.normal(0, 20, len(t)))
    load[24 * 10 + 15] *= 1.8
    load[24 * 12 + 3] = 0.0
    out = load_deviation_flags(pd.DataFrame({"interval_start_utc": t, "load_mw": load}))
    assert out.flag_deviation.iloc[24 * 10 + 15]
    assert out.flag_nonpositive.sum() == 1 and out.flag_nonpositive.iloc[24 * 12 + 3]
    assert out.flag_deviation.sum() <= 3  # the spike, the zero, and at most one neighbor-driven flag


def test_weather_range_flags_count_bad_values():
    t = pd.Series(hourly("2024-07-01", 3))
    wx = pd.DataFrame({"interval_start_utc": t, "temperature_c": [20.0, 50.0, 10.0],
                       "dewpoint_c": [15.0, 10.0, 12.0], "relative_humidity_pct": [70.0, 30.0, 100.0],
                       "wind_speed_m_s": [3.0, np.nan, 2.0], "precipitation_mm": [0.0, 0.0, 0.2]})
    out = weather_range_flags(wx).set_index("check").flagged
    assert out["temperature_c outside [-30, 45]"] == 1
    assert out["dewpoint_c > temperature_c + 0.5"] == 1
    assert out.sum() == 2


def test_date_offset_and_dst_distance():
    date = pd.Series(["2022-03-12T21:51:00", "2022-06-01T10:51:00"])
    utc = pd.Series(pd.to_datetime(["2022-03-13T03:51:00Z", "2022-06-01T15:51:00Z"]))
    assert date_offset_minutes(date, utc).tolist() == [60.0, 0.0]
    tr = dst_transitions(2022, 2022)
    assert len(tr) == 2 and tr[0] == pd.Timestamp("2022-03-13 07:00", tz="UTC")
    assert hours_to_nearest_dst(utc, tr).round(2).tolist()[0] == 3.15


SILVER = ROOT / "data/silver/nyiso/load_hourly_2017_2025.parquet"


@pytest.mark.skipif(not SILVER.exists(), reason="needs Step 8 silver tables")
def test_real_load_pre_holdout_slice_is_2017_2024():
    load = pd.read_parquet(SILVER)
    pre = pre_holdout(load)
    years = pre.interval_start_utc.dt.tz_convert("America/New_York").dt.year
    assert len(pre) == 70_128 and years.min() == 2017 and years.max() == 2024
    require_pre_holdout(pre.interval_start_utc)
