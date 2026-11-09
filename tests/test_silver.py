"""Step 8 tests: DST handling, duplicate hours, METAR parsing and raw-to-silver spot checks.

Synthetic tests always run (including GitHub Actions). Spot checks against your real raw
files run only on a machine where Step 7 and scripts/build_silver.py have been run.
"""
import io
import json
import zipfile
from pathlib import Path

import pandas as pd
import pytest

from cleaning.hours import expected_hours, missing_hours
from cleaning.lcd_weather import metar_utc
from cleaning.nyiso_forecast import SOURCE_COLUMNS as P7_COLUMNS, decode_isolf, select_day_ahead
from cleaning.nyiso_load import SOURCE_COLUMNS as LOAD_COLUMNS, decode_integrated_load
from cleaning.openmeteo import flatten_previous_runs

ROOT = Path(__file__).resolve().parents[1]

# (spring-forward day, fall-back day) for two years
DST_DAYS = {2018: ("2018-03-11", "2018-11-04"), 2024: ("2024-03-10", "2024-11-03")}


@pytest.mark.parametrize("year", sorted(DST_DAYS))
def test_expected_hours_on_dst_days(year):
    spring, fall = DST_DAYS[year]
    nxt = lambda d: (pd.Timestamp(d) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    assert len(expected_hours(spring, nxt(spring))) == 23
    assert len(expected_hours(fall, nxt(fall))) == 25
    assert len(expected_hours(f"{year}-01-01", f"{year + 1}-01-01")) == (8784 if year % 4 == 0 else 8760)


def test_full_study_period_hour_count():
    assert len(expected_hours("2017-01-01", "2026-01-01")) == 78888


def test_missing_hours_are_listed_with_local_label():
    grid = expected_hours("2024-11-03", "2024-11-04")
    gaps = missing_hours(grid, grid.delete(2))  # drop the second 01:00 (EST)
    assert len(gaps) == 1 and gaps.local_time.iloc[0] == "2024-11-03 01:00 EST"


@pytest.mark.parametrize("year", sorted(DST_DAYS))
def test_load_fall_back_keeps_both_hours(year):
    _, fall = DST_DAYS[year]
    stamp = pd.Timestamp(fall).strftime("%m/%d/%Y") + " 01:00:00"
    raw = pd.DataFrame([[stamp, "EDT", "N.Y.C.", 61761, 4000.0], [stamp, "EST", "N.Y.C.", 61761, 3900.0]],
                       columns=LOAD_COLUMNS)
    out = decode_integrated_load(raw)
    assert out.interval_start_utc.diff().iloc[1] == pd.Timedelta(hours=1)


def p7_frame(stamps):
    rows = [[s] + [1000 + i] * (len(P7_COLUMNS) - 1) for i, s in enumerate(stamps)]
    return pd.DataFrame(rows, columns=P7_COLUMNS)


def local_stamps(day, hours):
    return [pd.Timestamp(day).strftime("%m/%d/%Y") + f" {h:02d}:00" for h in hours]


@pytest.mark.parametrize("year", sorted(DST_DAYS))
def test_p7_fall_back_repeated_hour_is_edt_then_est(year):
    _, fall = DST_DAYS[year]
    out = decode_isolf(p7_frame(local_stamps(fall, [0, 1, 1, 2, 3])), issue_date=fall)
    assert len(out) == 5
    assert out.interval_start_utc.diff().dropna().eq(pd.Timedelta(hours=1)).all()
    assert out.interval_start_utc.iloc[1].hour == 5 and out.interval_start_utc.iloc[2].hour == 6


@pytest.mark.parametrize("year", sorted(DST_DAYS))
def test_p7_spring_forward_is_contiguous(year):
    spring, _ = DST_DAYS[year]
    out = decode_isolf(p7_frame(local_stamps(spring, [0, 1, 3, 4])), issue_date=spring)
    assert out.interval_start_utc.diff().dropna().eq(pd.Timedelta(hours=1)).all()


def test_p7_rejects_duplicate_hour_outside_dst():
    with pytest.raises(ValueError):
        decode_isolf(p7_frame(local_stamps("2024-07-15", [0, 1, 1, 2])), issue_date="2024-07-15")


def test_p7_day_ahead_selection_keeps_only_next_day():
    a = decode_isolf(p7_frame(local_stamps("2024-07-15", range(24)) + local_stamps("2024-07-16", range(24))), "2024-07-15")
    b = decode_isolf(p7_frame(local_stamps("2024-07-16", range(24)) + local_stamps("2024-07-17", range(24))), "2024-07-16")
    out = select_day_ahead(pd.concat([a, b]))
    assert sorted(out.target_local_date.unique()) == ["2024-07-16", "2024-07-17"]
    assert out.loc[out.target_local_date.eq("2024-07-16"), "issue_date_local"].eq("2024-07-15").all()


def test_metar_token_glued_to_prefix_is_read():
    # NOAA sometimes writes 'MET055METAR' with no space; the pilot parser missed these.
    got = metar_utc("2025-02-21T21:09:00", "MET055METAR KNYC 220209Z 31010G20KT 10SM CLR", "KNYC")
    assert got == pd.Timestamp("2025-02-22T02:09Z")
    assert pd.isna(metar_utc("2025-02-21T21:09:00", "XMETAR KNYC 220209Z", "KNYC"))


def test_openmeteo_flatten_keeps_nulls_and_converts_wind():
    hourly = {"time": ["2024-01-01T00:00", "2024-01-01T01:00"]}
    for v in ["temperature_2m", "dew_point_2m", "relative_humidity_2m", "wind_speed_10m", "precipitation"]:
        hourly[v + "_previous_day2"] = [None, 36.0]
    out = flatten_previous_runs({"utc_offset_seconds": 0, "hourly": hourly})
    assert out.fc_temperature_c.isna().iloc[0] and out.fc_wind_speed_m_s.iloc[1] == pytest.approx(10.0)
    with pytest.raises(ValueError):
        flatten_previous_runs({"error": True, "reason": "limit"})


# ---------------- spot checks against real raw files (skipped in GitHub Actions)
SILVER = ROOT / "data/silver"
needs_data = pytest.mark.skipif(not (SILVER / "nyiso/load_hourly_2017_2025.parquet").exists(),
                                reason="run Step 7 and scripts/build_silver.py first")


@needs_data
def test_spot_check_load_against_raw_csv():
    silver = pd.read_parquet(SILVER / "nyiso/load_hourly_2017_2025.parquet")
    with zipfile.ZipFile(ROOT / "data/bronze/nyiso/integrated_load/20180701palIntegrated_csv.zip") as z:
        raw = pd.read_csv(io.BytesIO(z.read("20180702palIntegrated.csv")))
    row = raw[(raw.Name == "N.Y.C.") & (raw["Time Stamp"] == "07/02/2018 17:00:00")].iloc[0]
    hour = pd.Timestamp("2018-07-02 21:00", tz="UTC")  # 17:00 EDT
    assert silver.set_index("interval_start_utc").loc[hour, "load_mw"] == pytest.approx(row["Integrated Load"])
    assert len(silver) == 78888 and not silver.interval_start_utc.duplicated().any()


@needs_data
def test_spot_check_p7_against_raw_csv():
    silver = pd.read_parquet(SILVER / "nyiso/p7_day_ahead_2017_2025.parquet").set_index("interval_start_utc")
    with zipfile.ZipFile(ROOT / "data/bronze/nyiso/isolf/20190101isolf_csv.zip") as z:
        raw = pd.read_csv(io.BytesIO(z.read("20190114isolf.csv")))
    value = raw.loc[raw["Time Stamp"] == "01/15/2019 08:00", "N.Y.C."].iloc[0]
    hour = pd.Timestamp("2019-01-15 13:00", tz="UTC")  # 08:00 EST, issued 2019-01-14
    assert silver.loc[hour, "forecast_mw"] == value and silver.loc[hour, "issue_date_local"] == "2019-01-14"


@needs_data
def test_spot_check_weather_against_raw_csv():
    silver = pd.read_parquet(SILVER / "noaa/weather_hourly_2017_2025.parquet")
    row = silver[silver.source_station.eq("USW00094728") & silver.core_tuple_valid].iloc[5000]
    raw = pd.read_csv(ROOT / "data/bronze/noaa/lcdv2" / row.source_file, dtype=str, keep_default_na=False)
    source = raw.iloc[int(row.source_row_number) - 2]
    assert float(source.HourlyDryBulbTemperature) == pytest.approx(row.temperature_c)
    assert source.REPORT_TYPE == "FM-15"
    assert row.observation_time_utc >= row.interval_start_utc
    assert row.observation_time_utc < row.interval_end_utc
    assert len(silver) == 78888


@needs_data
def test_dst_days_have_expected_rows_in_silver_load():
    silver = pd.read_parquet(SILVER / "nyiso/load_hourly_2017_2025.parquet")
    local_day = silver.interval_start_utc.dt.tz_convert("America/New_York").dt.strftime("%Y-%m-%d")
    counts = local_day.value_counts()
    for spring, fall in DST_DAYS.values():
        assert counts[spring] == 23 and counts[fall] == 25
