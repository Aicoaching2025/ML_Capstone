"""Build one feature row per target hour for a horizon, with leakage excluded by construction.

Timing (contract v0.2): origin O = target_end - h. A load interval ending at E is usable at O
only if E + load_delay <= O, so origin-relative lag L_k is the interval ending at O - k (k >= delay).
Observed weather is usable if its METAR time + weather_delay <= O. Archived forecast weather
(previous_day2) is assumed initialized 48 h before its valid time and published 6 h later.
"""
from __future__ import annotations

import pandas as pd

from features.calendar import calendar_features

H = pd.Timedelta(hours=1)
FC_INIT_LEAD = pd.Timedelta(hours=48)    # previous_day2 definition
FC_PUBLISH_DELAY = pd.Timedelta(hours=6)  # assumed GFS run latency (conservative)
OBS_MAX_AGE = pd.Timedelta(hours=3)      # no stale carry-forward beyond this; missing stays missing


def _degree_hours(temp_c: pd.Series, prefix: str) -> dict:
    return {f"{prefix}hdh_c": (18.3 - temp_c).clip(lower=0), f"{prefix}cdh_c": (temp_c - 18.3).clip(lower=0)}


def split_role(local_year: pd.Series, study: dict) -> pd.Series:
    role = pd.Series("excluded", index=local_year.index)
    role[local_year.isin(study["initial_training_years"])] = "train_initial"
    role[local_year.isin(study["validation_test_years"])] = "validation_test"
    role[local_year.eq(study["holdout_year"])] = "holdout"
    return role


def build_features(load: pd.DataFrame, weather: pd.DataFrame, study: dict, horizon: int,
                   targets: pd.DatetimeIndex, forecast: pd.DataFrame | None = None,
                   p7: pd.DataFrame | None = None) -> tuple[pd.DataFrame, dict]:
    """Return (features, inputs) where inputs holds per-feature source times for availability checks."""
    key = f"h{horizon}"
    delay = pd.Timedelta(hours=study["load_publication_delay_hours"])
    wx_delay = pd.Timedelta(minutes=study["weather_release_delay_minutes"])
    lags = study["load_lags_origin_relative"][key]
    if min(lags) * H < delay:
        raise ValueError(f"lag list {lags} uses load newer than the {delay} publication delay")

    series = load.set_index("interval_end_utc")["load_mw"].sort_index()
    if series.index.duplicated().any():
        raise ValueError("duplicate load interval")
    t = pd.DataFrame({"target_start_utc": targets})
    t["target_end_utc"] = t.target_start_utc + H
    t["origin_utc"] = t.target_end_utc - horizon * H
    t["horizon_hours"] = horizon
    local = t.target_start_utc.dt.tz_convert("America/New_York")
    t["target_local_time"] = local.dt.strftime("%Y-%m-%d %H:%M %Z")
    t["target_local_year"] = local.dt.year
    t["split_role"] = split_role(t.target_local_year, study)
    t["y_load_mw"] = series.reindex(t.target_end_utc).to_numpy()
    inputs = {}

    for k in lags:
        end = t.origin_utc - k * H
        t[f"load_L{k}"] = series.reindex(end).to_numpy()
        inputs[f"load_L{k}"] = ("load", end)
    latest = t.origin_utc - delay
    for w in study["rolling_windows_hours"]:
        rolled = series.rolling(f"{w}h", min_periods=w).mean()  # window ends at the indexed interval end
        t[f"load_roll{w}_mean"] = rolled.reindex(latest).to_numpy()
        inputs[f"load_roll{w}_mean"] = ("load", latest)

    # Seasonal-naive baseline forecasts (Step 11 scores them); values only, not model inputs.
    base = study["baselines"]
    t["naive_persistence"] = series.reindex(latest).to_numpy()
    for name, shift in (("naive_daily", base["daily_naive_shift_hours"][key]),
                        ("naive_weekly", base["weekly_naive_shift_hours"][key])):
        end = t.target_end_utc - shift * H
        t[name] = series.reindex(end).to_numpy()
        inputs[name] = ("load", end)
    inputs["naive_persistence"] = ("load", latest)

    t = pd.concat([t, calendar_features(t.target_start_utc)], axis=1)

    wx = weather.copy()
    vars_ = ["temperature_c", "dewpoint_c", "relative_humidity_pct", "wind_speed_m_s"]
    if horizon == 1:
        obs = wx[wx.core_tuple_valid & wx.observation_time_utc.notna()].copy()
        obs["available_at_utc"] = obs.observation_time_utc + wx_delay
        obs = obs.sort_values("available_at_utc")[["available_at_utc", "observation_time_utc", "source_station", *vars_]]
        m = pd.merge_asof(t[["origin_utc"]].reset_index(), obs, left_on="origin_utc", right_on="available_at_utc",
                          direction="backward", tolerance=OBS_MAX_AGE, allow_exact_matches=True).set_index("index")
        for v in vars_:
            t[f"wx_obs_{v}"] = m[v]
        t = t.assign(**_degree_hours(t.wx_obs_temperature_c, "wx_obs_"))
        t["wx_obs_time_utc"] = m.observation_time_utc
        t["wx_obs_station"] = m.source_station
        t["wx_obs_age_minutes"] = (t.origin_utc - t.wx_obs_time_utc).dt.total_seconds() / 60
        inputs["wx_obs"] = ("observation", t.wx_obs_time_utc, wx_delay)
    else:
        tgt = wx.set_index("interval_start_utc").reindex(t.target_start_utc)
        for v in vars_:
            t[f"wx_tgt_{v}"] = tgt[v].to_numpy()
        t = t.assign(**_degree_hours(t.wx_tgt_temperature_c, "wx_tgt_"))
        t["wx_tgt_station"] = tgt.source_station.to_numpy()
        t["wx_tgt_role"] = "ideal_information_reference_not_available_at_origin"
        if forecast is not None:
            fc = forecast.set_index("valid_time_utc").reindex(t.target_end_utc)
            t["fc_temperature_c"] = fc.fc_temperature_c.to_numpy()
            t["fc_dewpoint_c"] = fc.fc_dewpoint_c.to_numpy()
            t["fc_relative_humidity_pct"] = fc.fc_relative_humidity_pct.to_numpy()
            t["fc_wind_speed_m_s"] = fc.fc_wind_speed_m_s.to_numpy()
            t = t.assign(**_degree_hours(t.fc_temperature_c, "fc_"))
            t["fc_valid_time_utc"] = t.target_end_utc.where(t.fc_temperature_c.notna())
            inputs["fc"] = ("forecast", t.fc_valid_time_utc)
        if p7 is not None:
            t["benchmark_nyiso_p7_mw"] = p7.set_index("interval_start_utc").forecast_mw.reindex(t.target_start_utc).to_numpy()
            t["benchmark_p7_issue_date_local"] = p7.set_index("interval_start_utc").issue_date_local.reindex(t.target_start_utc).to_numpy()
    return t, inputs


def availability_frames(features: pd.DataFrame, inputs: dict, load_delay_hours: int):
    """Yield (name, kind, frame) in the shape validate_availability() expects."""
    delay = pd.Timedelta(hours=load_delay_hours)
    for name, spec in inputs.items():
        kind, times = spec[0], spec[1]
        if kind == "load":
            # Baselines (naive_*) are checked too: a baseline must also be available at the origin.
            f = pd.DataFrame({"origin_utc": features.origin_utc, "interval_end_utc": times.to_numpy(),
                              "available_at_utc": (times + delay).to_numpy()}, index=features.index)
        elif kind == "observation":
            mask = times.notna()
            f = pd.DataFrame({"origin_utc": features.origin_utc[mask], "event_time_utc": times[mask],
                              "available_at_utc": times[mask] + spec[2]})
        else:
            mask = times.notna()
            init = times[mask] - FC_INIT_LEAD
            f = pd.DataFrame({"origin_utc": features.origin_utc[mask], "initialization_time_utc": init,
                              "valid_time_utc": times[mask], "available_at_utc": init + FC_PUBLISH_DELAY})
        yield name, kind, f
