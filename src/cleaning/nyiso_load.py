"""Strict pilot decoder for NYISO P-58C records.

Hour-start interpretation is recorded in the audit, not inferred by this parser.
No publication timestamp or historical first-vintage claim is manufactured.
"""
from datetime import timedelta
import numpy as np
import pandas as pd

SOURCE_COLUMNS = ["Time Stamp", "Time Zone", "Name", "PTID", "Integrated Load"]


def decode_integrated_load(raw: pd.DataFrame) -> pd.DataFrame:
    if list(raw.columns) != SOURCE_COLUMNS:
        raise ValueError(f"Unexpected NYISO schema: {list(raw.columns)}")
    if raw.empty or raw.isna().any().any():
        raise ValueError("Empty source or missing source fields")
    result = raw.copy()
    labels = result["Time Zone"]
    if not labels.isin(["EST", "EDT"]).all():
        raise ValueError("Unknown source timezone label")
    naive = pd.to_datetime(result["Time Stamp"], format="%m/%d/%Y %H:%M:%S", errors="raise")
    if not naive.eq(naive.dt.floor("h")).all():
        raise ValueError("Non-hourly source timestamp")
    # Explicit offsets resolve the repeated hour without order-dependent inference.
    offsets = labels.map({"EST": "-0500", "EDT": "-0400"})
    utc = pd.to_datetime(result["Time Stamp"] + " " + offsets,
                         format="%m/%d/%Y %H:%M:%S %z", utc=True, errors="raise")
    local = utc.dt.tz_convert("America/New_York")
    if not local.dt.strftime("%m/%d/%Y %H:%M:%S").eq(result["Time Stamp"]).all():
        raise ValueError("Timezone label conflicts with NYC clock")
    if not local.dt.strftime("%Z").eq(labels).all():
        raise ValueError("Timezone label conflicts with NYC offset")
    ptid = pd.to_numeric(result["PTID"], errors="raise")
    load = pd.to_numeric(result["Integrated Load"], errors="raise")
    if not np.isfinite(load).all() or not np.isfinite(ptid).all() or not ptid.eq(ptid.astype(int)).all():
        raise ValueError("Invalid numeric source field")
    if result.assign(utc=utc).duplicated(["Name", "utc"]).any():
        raise ValueError("Duplicate zone and UTC timestamp")
    result["source_timestamp"] = result["Time Stamp"]
    result["source_timezone"] = labels
    result["interval_start_utc"] = utc
    result["interval_end_utc"] = utc.map(lambda t: t + timedelta(hours=1))
    result["source_name"] = result["Name"]
    result["source_ptid"] = ptid.astype(int)
    result["load_mw"] = load
    return result
