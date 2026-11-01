import pandas as pd
import pytest

from validation.availability import forecast_targets, validate_availability


@pytest.mark.parametrize("horizon", [1, 24])
@pytest.mark.parametrize("origin", ["2024-03-09T15:00:00Z", "2024-11-02T14:00:00Z"])
def test_target_horizon_uses_elapsed_hours_across_dst(horizon, origin):
    row = forecast_targets(pd.Series([origin]), horizon).iloc[0]
    assert row.target_end_utc - row.origin_utc == pd.Timedelta(hours=horizon)
    assert row.target_end_utc - row.target_start_utc == pd.Timedelta(hours=1)
    if horizon == 1:
        assert row.target_start_utc == row.origin_utc
    else:
        local_origin = row.origin_utc.tz_convert("America/New_York")
        local_end = row.target_end_utc.tz_convert("America/New_York")
        assert local_origin.hour != local_end.hour


@pytest.mark.parametrize("origin", ["2024-01-01 00:00", None, "2024-01-01T00:30:00Z"])
def test_reject_ambiguous_or_unaligned_origin(origin):
    with pytest.raises(ValueError):
        forecast_targets(pd.Series([origin]), 1)


def test_reject_duplicate_origins_and_unsupported_horizon():
    origins = pd.Series(["2024-01-01T00:00Z"] * 2)
    with pytest.raises(ValueError, match="Duplicate"):
        forecast_targets(origins, 1)
    for horizon in (True, 1.0, 2, 48):
        with pytest.raises(ValueError, match="must be 1 or 24"):
            forecast_targets(origins.iloc[:1], horizon)


@pytest.mark.parametrize("kind,event_field", [("load", "interval_end_utc"), ("observation", "event_time_utc")])
def test_reject_completed_but_unpublished_input(kind, event_field):
    frame = pd.DataFrame({
        "origin_utc": ["2024-01-01T14:00Z"],
        "available_at_utc": ["2024-01-01T14:05Z"],
        event_field: ["2024-01-01T14:00Z"],
    })
    with pytest.raises(ValueError, match="unavailable"):
        validate_availability(frame, kind=kind)
    frame["available_at_utc"] = "2024-01-01T14:00Z"
    assert len(validate_availability(frame, kind=kind)) == 1
    frame[event_field] = "2024-01-01T15:00Z"
    with pytest.raises(ValueError, match="precedes"):
        validate_availability(frame, kind=kind)


def test_forecast_allows_future_valid_time_but_rejects_future_run():
    frame = pd.DataFrame({
        "origin_utc": ["2024-01-01T14:00Z"],
        "available_at_utc": ["2024-01-01T13:00Z"],
        "initialization_time_utc": ["2024-01-01T12:00Z"],
        "valid_time_utc": ["2024-01-02T13:00Z"],
    })
    assert len(validate_availability(frame, kind="forecast")) == 1
    frame["initialization_time_utc"] = "2024-01-01T15:00Z"
    with pytest.raises(ValueError, match="precedes"):
        validate_availability(frame, kind="forecast")


def test_reject_missing_availability_and_negative_forecast_lead():
    with pytest.raises(ValueError, match="Missing required"):
        validate_availability(pd.DataFrame(), kind="load")
    frame = pd.DataFrame({
        "origin_utc": ["2024-01-01T14:00Z"],
        "available_at_utc": [None],
        "initialization_time_utc": ["2024-01-01T12:00Z"],
        "valid_time_utc": ["2024-01-01T11:00Z"],
    })
    with pytest.raises(ValueError, match="timezone-aware"):
        validate_availability(frame, kind="forecast")
    frame["available_at_utc"] = "2024-01-01T13:00Z"
    with pytest.raises(ValueError, match="valid time precedes"):
        validate_availability(frame, kind="forecast")
