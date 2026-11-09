"""Step 10 tests: leakage is impossible by construction, plus checks on the real feature tables."""
import json
from pathlib import Path

import pandas as pd
import pytest
import yaml

from features.build import availability_frames, build_features
from features.calendar import calendar_features
from features.sets import feature_columns, operational_h24_inputs
from validation.availability import validate_availability

ROOT = Path(__file__).resolve().parents[1]
STUDY = yaml.safe_load((ROOT / "configs/study.yaml").read_text())
H = pd.Timedelta(hours=1)


def encoded_load(start="2017-12-01", end="2018-02-01"):
    """Synthetic load whose value is the interval END time in epoch hours, so any feature reveals its source."""
    ends = pd.date_range(pd.Timestamp(start, tz="UTC") + H, pd.Timestamp(end, tz="UTC"), freq="h")
    return pd.DataFrame({"interval_end_utc": ends, "load_mw": (ends - pd.Timestamp(0, tz="UTC")) / H})


def weather_grid(start="2017-12-01", end="2018-02-01", minute=51):
    starts = pd.date_range(pd.Timestamp(start, tz="UTC"), pd.Timestamp(end, tz="UTC"), freq="h", inclusive="left")
    return pd.DataFrame({"interval_start_utc": starts, "core_tuple_valid": True,
                         "observation_time_utc": starts + pd.Timedelta(minutes=minute), "source_station": "USW00094728",
                         "temperature_c": 10.0, "dewpoint_c": 5.0, "relative_humidity_pct": 70.0, "wind_speed_m_s": 3.0})


TARGETS = pd.date_range("2018-01-10", "2018-01-20", freq="h", tz="UTC", inclusive="left")


@pytest.mark.parametrize("horizon", [1, 24])
def test_no_load_feature_uses_interval_ending_at_or_after_origin(horizon):
    feats, _ = build_features(encoded_load(), weather_grid(), STUDY, horizon, TARGETS)
    origin = (feats.origin_utc - pd.Timestamp(0, tz="UTC")) / H
    delay = STUDY["load_publication_delay_hours"]
    load_cols = [c for c in feats.columns if c.startswith(("load_", "naive_"))]
    assert load_cols
    for c in load_cols:
        assert (feats[c] <= origin - delay).all(), c  # every source interval ends by O - delay
    assert (feats.y_load_mw == origin + horizon).all()  # the target itself is the interval ending O + h


def test_origin_relative_lags_match_config():
    for h in (1, 24):
        feats, _ = build_features(encoded_load(), weather_grid(), STUDY, h, TARGETS)
        origin = (feats.origin_utc - pd.Timestamp(0, tz="UTC")) / H
        for k in STUDY["load_lags_origin_relative"][f"h{h}"]:
            assert (feats[f"load_L{k}"] == origin - k).all()
        shift = STUDY["baselines"]["daily_naive_shift_hours"][f"h{h}"]
        assert (feats.naive_daily == origin + h - shift).all()


def test_lag_newer_than_publication_delay_is_rejected():
    study = {**STUDY, "load_lags_origin_relative": {"h1": [0, 2], "h24": [24]}}
    with pytest.raises(ValueError, match="publication delay"):
        build_features(encoded_load(), weather_grid(), study, 1, TARGETS)


def test_h1_weather_respects_15_minute_release_delay():
    feats, _ = build_features(encoded_load(), weather_grid(minute=51), STUDY, 1, TARGETS)
    # Obs at O-0:09 is published at O+0:06 (too late), so the O-1:09 obs is used.
    assert (feats.wx_obs_age_minutes == 69).all()
    zero = {**STUDY, "weather_release_delay_minutes": 0}
    feats0, _ = build_features(encoded_load(), weather_grid(minute=51), zero, 1, TARGETS)
    assert (feats0.wx_obs_age_minutes == 9).all()


def test_stale_weather_is_not_carried_forward():
    wx = weather_grid()
    gap = wx.interval_start_utc.between(pd.Timestamp("2018-01-12", tz="UTC"), pd.Timestamp("2018-01-12 12:00", tz="UTC"))
    feats, _ = build_features(encoded_load(), wx[~gap], STUDY, 1, TARGETS)
    late = feats.origin_utc.eq(pd.Timestamp("2018-01-12 10:00", tz="UTC"))
    assert feats.loc[late, "wx_obs_temperature_c"].isna().all()


@pytest.mark.parametrize("horizon", [1, 24])
def test_validator_accepts_every_built_input(horizon):
    feats, inputs = build_features(encoded_load(), weather_grid(), STUDY, horizon, TARGETS)
    for _, kind, frame in availability_frames(feats, inputs, STUDY["load_publication_delay_hours"]):
        validate_availability(frame, kind=kind)


def test_validator_would_catch_a_leaky_lag():
    feats, inputs = build_features(encoded_load(), weather_grid(), STUDY, 24, TARGETS)
    inputs["leak"] = ("load", feats.origin_utc)  # interval ending exactly at the origin
    frames = {n: (k, f) for n, k, f in availability_frames(feats, inputs, STUDY["load_publication_delay_hours"])}
    with pytest.raises(ValueError, match="unavailable"):
        validate_availability(frames["leak"][1], kind="load")


def test_calendar_holidays_and_encodings():
    stamps = pd.Series(pd.to_datetime(["2024-07-04 16:00", "2024-11-29 16:00", "2024-07-08 16:00"], utc=True))
    cal = calendar_features(stamps)
    assert cal.cal_is_federal_holiday.tolist() == [True, False, False]
    assert cal.cal_is_nerc_holiday.tolist() == [True, False, False]
    assert cal.cal_is_day_after_thanksgiving.tolist() == [False, True, False]
    assert cal.cal_hour.tolist() == [12, 11, 12]  # NYC local hour (EDT, EST, EDT)
    assert cal.cal_hour_of_week.between(0, 167).all()


def test_feature_sets_by_name():
    feats, _ = build_features(encoded_load(), weather_grid(), STUDY, 24, TARGETS,
                              forecast=pd.DataFrame({"valid_time_utc": TARGETS + H, "fc_temperature_c": 1.0,
                                                     "fc_dewpoint_c": 0.0, "fc_relative_humidity_pct": 50.0,
                                                     "fc_wind_speed_m_s": 2.0}))
    a, b, c = (feature_columns(feats, n) for n in ("A", "B", "C_retrospective_h24"))
    assert set(a) < set(b) < set(c)
    assert not any(x.startswith(("naive_", "benchmark_", "y_")) for x in c)
    x = operational_h24_inputs(feats)
    assert list(x.columns) == c and (x.wx_tgt_temperature_c == 1.0).all()


# ---------------- checks on your real feature tables (skipped in GitHub Actions)
GOLD = ROOT / "data/gold"
needs_gold = pytest.mark.skipif(not (GOLD / "features_h24.parquet").exists(),
                                reason="run scripts/build_features.py first")


@needs_gold
def test_real_h24_table_has_no_load_from_origin_or_later():
    feats = pd.read_parquet(GOLD / "features_h24.parquet")
    load = pd.read_parquet(ROOT / "data/silver/nyiso/load_hourly_2017_2025.parquet").set_index("interval_end_utc").load_mw
    delay = STUDY["load_publication_delay_hours"]
    for k in STUDY["load_lags_origin_relative"]["h24"]:
        assert k >= delay
        source = load.reindex(feats.origin_utc - k * H).to_numpy()
        assert (feats[f"load_L{k}"].to_numpy() == source).all()
    assert (feats.naive_daily.to_numpy() == load.reindex(feats.target_end_utc - 48 * H).to_numpy()).all()
    assert len(feats) == 70128 and feats.y_load_mw.notna().all()


@needs_gold
def test_real_tables_split_roles_and_feature_sets():
    sets = json.loads((GOLD / "feature_sets.json").read_text())
    assert set(sets) == {"h1", "h24"} and "C_operational_h1" in sets["h1"]
    for h in (1, 24):
        feats = pd.read_parquet(GOLD / f"features_h{h}.parquet")
        roles = feats.groupby("target_local_year").split_role.first().to_dict()
        assert roles[2025] == "holdout" and roles[2018] == "train_initial" and roles[2021] == "validation_test"
