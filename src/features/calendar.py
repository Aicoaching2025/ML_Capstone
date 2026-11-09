"""Calendar features for the target hour, in NYC local time."""
import numpy as np
import pandas as pd
from pandas.tseries.holiday import USFederalHolidayCalendar

NYC = "America/New_York"
# NERC holidays: the six days NERC/ISOs treat as off-peak holidays.
NERC = {"New Year's Day", "Memorial Day", "Independence Day", "Labor Day", "Thanksgiving Day", "Christmas Day"}


def calendar_features(target_start_utc: pd.Series) -> pd.DataFrame:
    local = pd.DatetimeIndex(target_start_utc).tz_convert(NYC)
    days = local.normalize().tz_localize(None)
    names = USFederalHolidayCalendar().holidays(days.min() - pd.Timedelta(days=7),
                                                days.max() + pd.Timedelta(days=7), return_name=True)
    federal = set(names.index)
    nerc = set(names[names.isin(NERC)].index)
    thanksgiving = set(names[names.eq("Thanksgiving Day")].index)
    hour, dow, month, doy = local.hour, local.dayofweek, local.month, local.dayofyear
    two_pi = 2 * np.pi
    out = pd.DataFrame({
        "cal_hour": hour, "cal_dow": dow, "cal_month": month, "cal_doy": doy,
        "cal_hour_of_week": dow * 24 + hour,  # hour x weekday interaction (0-167)
        "cal_is_weekend": dow >= 5,
        "cal_is_federal_holiday": days.isin(federal),
        "cal_is_nerc_holiday": days.isin(nerc),
        "cal_is_day_after_thanksgiving": (days - pd.Timedelta(days=1)).isin(thanksgiving),
        "cal_hour_sin": np.sin(two_pi * hour / 24), "cal_hour_cos": np.cos(two_pi * hour / 24),
        "cal_dow_sin": np.sin(two_pi * dow / 7), "cal_dow_cos": np.cos(two_pi * dow / 7),
        "cal_doy_sin": np.sin(two_pi * (doy - 1) / 365.25), "cal_doy_cos": np.cos(two_pi * (doy - 1) / 365.25),
    })
    out.index = target_start_utc.index
    return out
