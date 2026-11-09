"""Feature-set membership (A, B, C) by name, per contract v0.2 / Amendment 1."""
import pandas as pd

# Wind is optional (frozen weather rule) and about 12% missing, so it is kept as a column but not in set C.
WEATHER_VARS = ["temperature_c", "dewpoint_c", "relative_humidity_pct", "hdh_c", "cdh_c"]
# C_operational_h24 scores the C_retrospective_h24 model with archived forecasts:
# column wx_tgt_<v> is replaced by fc_<v> at scoring time.
FORECAST_FOR_TARGET = {f"wx_tgt_{v}": f"fc_{v}" for v in WEATHER_VARS}


def feature_columns(frame: pd.DataFrame, name: str) -> list[str]:
    load = [c for c in frame.columns if c.startswith("load_")]
    cal = [c for c in frame.columns if c.startswith("cal_")]
    sets = {"A": load, "B": load + cal}
    if "wx_obs_temperature_c" in frame.columns:
        sets["C_operational_h1"] = load + cal + [f"wx_obs_{v}" for v in WEATHER_VARS]
    if "wx_tgt_temperature_c" in frame.columns:
        sets["C_retrospective_h24"] = load + cal + [f"wx_tgt_{v}" for v in WEATHER_VARS]
        sets["C_operational_h24"] = sets["C_retrospective_h24"]  # same model; inputs swapped, see FORECAST_FOR_TARGET
    if name not in sets:
        raise KeyError(f"Feature set {name!r} not available here; choose from {sorted(sets)}")
    return sets[name]


def operational_h24_inputs(frame: pd.DataFrame) -> pd.DataFrame:
    """Return the C_retrospective_h24 inputs with forecast weather swapped in (2024-2025 rows)."""
    cols = feature_columns(frame, "C_retrospective_h24")
    x = frame[cols].copy()
    for tgt, fc in FORECAST_FOR_TARGET.items():
        x[tgt] = frame[fc]
    return x
