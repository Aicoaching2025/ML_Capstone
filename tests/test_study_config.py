"""Amendment 1 guards: configured features must respect the frozen availability rules."""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
STUDY = yaml.safe_load((ROOT / "configs/study.yaml").read_text())
SOURCES = yaml.safe_load((ROOT / "configs/sources.yaml").read_text())


def test_contract_version_and_scope():
    assert STUDY["contract_version"] == "0.2"
    assert STUDY["holdout_year"] == 2025
    assert STUDY["holdout_year"] not in STUDY["validation_test_years"]
    assert max(STUDY["validation_test_years"]) < STUDY["holdout_year"]
    assert STUDY["optional_lstm"] is False


def test_load_lags_respect_publication_delay():
    delay = STUDY["load_publication_delay_hours"]
    for horizon, lags in STUDY["load_lags_origin_relative"].items():
        assert min(lags) >= delay, (horizon, lags)


def test_target_relative_equivalents_are_eligible():
    # Target starts at O + (h - 1); target-relative lag t-k ends at O + h - k = O - L.
    delay = STUDY["load_publication_delay_hours"]
    for h in STUDY["horizons_hours"]:
        for k in (STUDY["baselines"]["daily_naive_shift_hours"][f"h{h}"],
                  STUDY["baselines"]["weekly_naive_shift_hours"][f"h{h}"]):
            assert k - h >= delay, (h, k)


def test_forecast_weather_lead_is_available_at_24h_origin():
    variables = SOURCES["forecast_weather"]["variables"]
    assert variables and all(v.endswith("_previous_day2") for v in variables)


def test_full_history_acquisition_approved():
    assert SOURCES["load"]["full_history_acquisition_approved"] is True
    assert SOURCES["nyiso_forecast"]["zone_column"] == "N.Y.C."
