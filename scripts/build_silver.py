"""Step 8: build full-history silver tables (2017-2025) from the Step 7 raw files.

Run from the repository root:  uv run python scripts/build_silver.py
Reads only data/bronze (raw files listed in data/manifests/downloads.csv) and writes:
  data/silver/nyiso/load_hourly_2017_2025.parquet
  data/silver/noaa/weather_hourly_by_station_2017_2025.parquet
  data/silver/noaa/weather_hourly_2017_2025.parquet
  data/silver/nyiso/p7_day_ahead_2017_2025.parquet
  data/silver/openmeteo/gfs_previous_day2_2024_2025.parquet
  outputs/data_audit/step8/*.csv (every missing hour and quarantined row)
  docs/silver_build_summary.md (counts only; no model results)
No models are fitted and no forecast errors are computed.
"""
import hashlib
import io
import json
import sys
import warnings
import zipfile
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from cleaning.hours import NYC, expected_hours, missing_hours  # noqa: E402
from cleaning.lcd_weather import (VARIABLES, metar_utc, parse_weather_values,  # noqa: E402
                                  select_core_station, select_hourly_observations)
from cleaning.nyiso_forecast import decode_isolf, select_day_ahead  # noqa: E402
from cleaning.nyiso_load import decode_integrated_load  # noqa: E402
from cleaning.openmeteo import flatten_previous_runs  # noqa: E402

warnings.filterwarnings("ignore", message=".*generic.*unit.*", category=DeprecationWarning)
SOURCES = yaml.safe_load((ROOT / "configs/sources.yaml").read_text())
WX = yaml.safe_load((ROOT / "configs/weather_pilot.yaml").read_text())
AUDIT = ROOT / "outputs/data_audit/step8"
AUDIT.mkdir(parents=True, exist_ok=True)
MANIFEST = pd.read_csv(ROOT / "data/manifests/downloads.csv", keep_default_na=False)
HASHES = dict(zip(MANIFEST.local_filename, MANIFEST.file_hash_sha256))
FULL = expected_hours("2017-01-01", "2026-01-01")
summary = {}


def checked(path: Path) -> str:
    """Return sha256 and require that it matches a manifest row (provenance check)."""
    rel = str(path.relative_to(ROOT))
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if HASHES.get(rel) != digest:
        raise SystemExit(f"{rel} is not in downloads.csv with this hash. Rerun Step 7 first.")
    return digest


def write(frame: pd.DataFrame, rel: str) -> None:
    out = ROOT / rel
    out.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(out, index=False)
    print(f"  wrote {rel} ({len(frame):,} rows)")


# ---------------------------------------------------------------- 1. NYISO actual load
print("1/4 NYISO load")
parts = []
for path in sorted((ROOT / "data/bronze/nyiso/integrated_load").glob("*palIntegrated_csv.zip")):
    yyyymm = path.name[:6]
    if not ("201701" <= yyyymm <= "202512"):
        continue
    digest = checked(path)
    with zipfile.ZipFile(path) as z:
        for member in sorted(z.namelist()):
            decoded = decode_integrated_load(pd.read_csv(io.BytesIO(z.read(member))))
            nyc = decoded[decoded.source_name.eq(SOURCES["load"]["source_name"])].copy()
            nyc["source_archive"] = path.name
            nyc["source_member"] = member
            nyc["source_archive_sha256"] = digest
            parts.append(nyc)
load = pd.concat(parts, ignore_index=True).sort_values("interval_start_utc")
assert set(load.source_ptid) == {SOURCES["load"]["source_ptid"]}, "unexpected PTID for N.Y.C."
dups = load[load.duplicated("interval_start_utc", keep=False)]
dups.to_csv(AUDIT / "load_duplicate_hours.csv", index=False)
assert dups.empty, f"{len(dups)} duplicate load hours; see outputs/data_audit/step8/load_duplicate_hours.csv"
load = load[load.interval_start_utc.isin(FULL)]
gaps = missing_hours(FULL, load.interval_start_utc)
gaps.to_csv(AUDIT / "load_missing_hours.csv", index=False)
load = load[["interval_start_utc", "interval_end_utc", "source_timestamp", "source_timezone", "source_ptid",
             "load_mw", "source_archive", "source_member", "source_archive_sha256"]].reset_index(drop=True)
write(load, "data/silver/nyiso/load_hourly_2017_2025.parquet")
summary["load"] = {"expected_hours": len(FULL), "rows": len(load), "missing_hours": len(gaps), "duplicate_hours": 0}

# ---------------------------------------------------------------- 2. NOAA observed weather
print("2/4 NOAA weather (about 1 minute)")
obs_parts, quarantine, accounting = [], [], []
y0, y1 = SOURCES["observations"]["full_history_years"]
for station, meta in WX["stations"].items():
    for year in range(y0, y1 + 1):
        path = ROOT / f"data/bronze/noaa/lcdv2/LCD_{station}_{year}.csv"
        digest = checked(path)
        raw = pd.read_csv(path, dtype=str, keep_default_na=False)
        assert raw.STATION.eq(station).all()
        frame = raw[raw.REPORT_TYPE.eq(WX["report_type"])].copy()
        frame["source_row_number"] = frame.index + 2
        frame["station_id"] = station
        frame["station_name"] = meta["name"]
        frame["source_file"] = path.name
        frame["source_sha256"] = digest
        frame["observation_time_utc"] = pd.to_datetime(
            [metar_utc(d, r, meta["icao"]) for d, r in zip(frame.DATE, frame.REM)], utc=True)
        bad = frame.observation_time_utc.isna()
        q = frame[bad].copy()
        q["quarantine_reason"] = "no_unambiguous_station_matched_METAR_UTC_token"
        quarantine.append(q[["station_id", "source_file", "source_row_number", "DATE", "REM", "quarantine_reason"]])
        accounting.append({"station_id": station, "year": year, "fm15_rows": len(frame),
                           "utc_resolved": int((~bad).sum()), "quarantined": int(bad.sum())})
        obs_parts.append(parse_weather_values(frame[~bad]))
obs = pd.concat(obs_parts, ignore_index=True)
obs = obs[obs.observation_time_utc.ge(FULL[0]) & obs.observation_time_utc.lt(FULL[-1] + pd.Timedelta(hours=1))]
dup_obs = obs[obs.duplicated(["station_id", "observation_time_utc"], keep=False)]
dup_obs[["station_id", "source_file", "source_row_number", "observation_time_utc"]].to_csv(
    AUDIT / "weather_duplicate_observations.csv", index=False)
assert dup_obs.empty, "duplicate station observation times; see weather_duplicate_observations.csv"
pd.concat(quarantine, ignore_index=True).to_csv(AUDIT / "weather_quarantined_rows.csv", index=False)
pd.DataFrame(accounting).to_csv(AUDIT / "weather_timestamp_accounting.csv", index=False)
value_fields = [f for v in VARIABLES for f in (v, v + "_raw", v + "_state")]
keep = ["station_id", "station_name", "observation_time_utc", "source_file", "source_row_number",
        "source_sha256", "precipitation_trace", *value_fields]
hourly = select_hourly_observations(obs[keep])
write(hourly, "data/silver/noaa/weather_hourly_by_station_2017_2025.parquet")
station_gaps = []
for station in WX["stations"]:
    g = missing_hours(FULL, hourly.loc[hourly.station_id.eq(station), "interval_start_utc"])
    g.insert(0, "station_id", station)
    station_gaps.append(g)
pd.concat(station_gaps, ignore_index=True).to_csv(AUDIT / "weather_station_missing_hours.csv", index=False)
priority = [WX["primary_station"], *WX["backup_priority"]]
core = select_core_station(hourly, priority).set_index("interval_start_utc").reindex(FULL)
core.index.name = "interval_start_utc"
core = core.reset_index()
core["interval_end_utc"] = core.interval_start_utc + pd.Timedelta(hours=1)
core["core_tuple_valid"] = core.core_tuple_valid.astype("boolean").fillna(False).astype(bool)
core["station_fallback_used"] = core.station_fallback_used.astype("boolean").fillna(False).astype(bool)
core = core.rename(columns={"station_id": "source_station"})
weather = core[["interval_start_utc", "interval_end_utc", "source_station", "observation_time_utc",
                "core_tuple_valid", "station_fallback_used", *VARIABLES, "precipitation_trace",
                "source_file", "source_row_number", "source_sha256"]]
write(weather, "data/silver/noaa/weather_hourly_2017_2025.parquet")
core_gaps = weather.loc[~weather.core_tuple_valid, ["interval_start_utc"]].copy()
core_gaps["local_time"] = core_gaps.interval_start_utc.dt.tz_convert(NYC).dt.strftime("%Y-%m-%d %H:%M %Z")
core_gaps.to_csv(AUDIT / "weather_core_missing_hours.csv", index=False)
summary["weather"] = {
    "expected_hours": len(FULL), "rows": len(weather), "core_missing_hours": len(core_gaps),
    "fallback_hours": int(weather.station_fallback_used.sum()),
    "rows_by_source_station": {str(k): int(v) for k, v in weather.source_station.value_counts().items()},
    "quarantined_fm15_rows": int(sum(a["quarantined"] for a in accounting)),
    "station_missing_hours": {s: int(len(g)) for s, g in zip(WX["stations"], station_gaps)},
}

# ---------------------------------------------------------------- 3. NYISO P-7 day-ahead forecast
print("3/4 NYISO P-7 forecast")
parts = []
for path in sorted((ROOT / "data/bronze/nyiso/isolf").glob("*isolf_csv.zip")):
    digest = checked(path)
    with zipfile.ZipFile(path) as z:
        for member in sorted(z.namelist()):
            issue = member[:8]
            d = decode_isolf(pd.read_csv(io.BytesIO(z.read(member))), issue_date=issue)
            d["source_member"] = member
            d["source_archive_sha256"] = digest
            parts.append(d)
p7 = select_day_ahead(pd.concat(parts, ignore_index=True))
first_target = (pd.Timestamp(SOURCES["nyiso_forecast"]["period"][0] + "-01") + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
p7_expected = expected_hours(first_target, "2026-01-01")
p7 = p7[p7.interval_start_utc.isin(p7_expected)].reset_index(drop=True)
p7_gaps = missing_hours(p7_expected, p7.interval_start_utc)
p7_gaps.to_csv(AUDIT / "p7_missing_hours.csv", index=False)
write(p7, "data/silver/nyiso/p7_day_ahead_2017_2025.parquet")
summary["p7"] = {"first_target_day": first_target, "expected_hours": len(p7_expected), "rows": len(p7),
                 "missing_hours": len(p7_gaps), "daily_files": len(parts)}

# ---------------------------------------------------------------- 4. Open-Meteo forecast weather
print("4/4 Open-Meteo forecast weather")
parts = []
for path in sorted((ROOT / "data/bronze/openmeteo/previous_runs").glob("gfs_previous_day2_*_[0-9][0-9][0-9][0-9].json")):
    digest = checked(path)
    f = flatten_previous_runs(json.loads(path.read_text()))
    f["source_file"] = path.name
    f["source_sha256"] = digest
    parts.append(f)
om = pd.concat(parts, ignore_index=True).sort_values("valid_time_utc").reset_index(drop=True)
assert not om.valid_time_utc.duplicated().any()
first, last = SOURCES["forecast_weather"]["period"]
om_expected = pd.date_range(pd.Timestamp(first, tz="UTC"), pd.Timestamp(last, tz="UTC") + pd.Timedelta(hours=23), freq="h")
assert len(om) == len(om_expected) and om.valid_time_utc.reset_index(drop=True).equals(pd.Series(om_expected, name="valid_time_utc"))
null_rows = om[om.fc_temperature_c.isna()]
null_rows[["valid_time_utc"]].to_csv(AUDIT / "openmeteo_null_hours.csv", index=False)
write(om, "data/silver/openmeteo/gfs_previous_day2_2024_2025.parquet")
first_valid = om.loc[om.fc_temperature_c.notna(), "valid_time_utc"].min()
summary["openmeteo"] = {"expected_hours": len(om_expected), "rows": len(om), "null_hours": len(null_rows),
                        "first_non_null_utc": first_valid.strftime("%Y-%m-%dT%H:%M")}

# ---------------------------------------------------------------- summary
(AUDIT / "step8_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
s = summary
lines = [
    "# Silver build summary (Step 8)", "",
    "Generated by `scripts/build_silver.py`. Counts only: no models fitted and no forecast errors computed.",
    "Every missing hour is listed in `outputs/data_audit/step8/` (regenerate locally; raw and silver data stay out of Git).", "",
    "| Table | Expected hours | Rows | Missing or null hours |", "| --- | --- | --- | --- |",
    f"| NYISO N.Y.C. actual load, 2017-2025 | {s['load']['expected_hours']:,} | {s['load']['rows']:,} | {s['load']['missing_hours']} |",
    f"| Observed weather (core tuple), 2017-2025 | {s['weather']['expected_hours']:,} | {s['weather']['rows']:,} | {s['weather']['core_missing_hours']} |",
    f"| NYISO P-7 day-ahead, from {s['p7']['first_target_day']} | {s['p7']['expected_hours']:,} | {s['p7']['rows']:,} | {s['p7']['missing_hours']} |",
    f"| Open-Meteo GFS previous_day2, 2024-2025 | {s['openmeteo']['expected_hours']:,} | {s['openmeteo']['rows']:,} | {s['openmeteo']['null_hours']} (first value {s['openmeteo']['first_non_null_utc']} UTC) |",
    "", "## Weather station use", "",
    f"- Hours using a backup station: {s['weather']['fallback_hours']:,}",
    f"- Hours by source station: {s['weather']['rows_by_source_station']}",
    f"- Hours with no FM-15 observation, by station: {s['weather']['station_missing_hours']}",
    f"- FM-15 rows quarantined (no station-matched METAR UTC time): {s['weather']['quarantined_fm15_rows']}",
    "", "## Rules applied", "",
    "- Load: N.Y.C. (PTID 61761), explicit EST/EDT labels to UTC hour start; both fall-back hours kept.",
    "- Weather: FM-15 only, METAR UTC token, last observation in each UTC hour, complete core tuple from Central Park then LaGuardia then JFK; no imputation.",
    "- P-7: file issued on the local day before each target local day; repeated fall-back hour mapped EDT then EST.",
    "- Open-Meteo: values unchanged; nulls kept; precipitation is the preceding-hour sum; wind also given in m/s.",
]
(ROOT / "docs/silver_build_summary.md").write_text("\n".join(lines) + "\n")
print("\n" + json.dumps(summary, indent=2))
ok = s["load"]["missing_hours"] == 0 and s["p7"]["missing_hours"] == 0
print("\nStep 8 silver tables built." + ("" if ok else " Some hours are missing: see outputs/data_audit/step8/."))
