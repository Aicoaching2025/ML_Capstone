from pathlib import Path
import pandas as pd
import pytest
from validation.sample import validate_sample

FIXTURE = Path(__file__).parent / "fixtures/synthetic_zone_j_hourly.csv"


def test_dst_repeated_hour_is_distinct_in_utc():
    frame = validate_sample(pd.read_csv(FIXTURE))
    local = frame.interval_start_utc.dt.tz_convert("America/New_York")
    repeated = local.dt.strftime("%Y-%m-%d %H:%M").eq("2024-11-03 01:00")
    assert repeated.sum() == 2
    assert local[repeated].map(lambda value: value.utcoffset()).nunique() == 2


def test_reject_duplicate_interval():
    frame = pd.read_csv(FIXTURE)
    with pytest.raises(ValueError, match="Duplicate"):
        validate_sample(pd.concat([frame, frame.iloc[[0]]]))


def test_reject_wrong_interval_length():
    frame = pd.read_csv(FIXTURE)
    frame.loc[0, "interval_end_utc"] = "2024-11-02T02:00:00Z"
    with pytest.raises(ValueError, match="one hour"):
        validate_sample(frame)


def test_reject_missing_hour():
    with pytest.raises(ValueError, match="contiguous"):
        validate_sample(pd.read_csv(FIXTURE).drop(index=5))
