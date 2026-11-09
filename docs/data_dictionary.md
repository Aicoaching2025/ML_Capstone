# Data dictionary

Status: full-history silver tables (Step 8) and feature tables (Step 10) are documented at the end. Earlier sections describe the setup fixture and pilots.

| Field | Type | Meaning |
| --- | --- | --- |
| interval_start_utc | UTC timestamp | Inclusive beginning of hourly interval |
| interval_end_utc | UTC timestamp | Exclusive end, exactly one elapsed hour later |
| zone | string | J in the synthetic fixture |
| load_mw | float | Synthetic hourly load in MW; not NYISO observations |
| temperature_c | float | Synthetic temperature; not an eligible future-weather predictor |
| load_gw | float | Smoke-test transformation: load_mw / 1000 |

The 48-row fixture covers the November 2024 fall DST transition. All values are invented solely for setup verification. Do not use it for research findings or source feasibility claims.

## NYISO hourly load pilot

See [the pilot audit](nyiso_load_pilot_audit.md) for interval evidence and limits. Original columns remain unchanged in Bronze. Silver contains 312 selected NYC intervals.

| Field | Meaning |
| --- | --- |
| interval_start_utc | UTC start under the corroborated hour-start interpretation |
| interval_end_utc | Start plus one elapsed hour |
| zone | Study label J |
| load_mw | Source Integrated Load, interpreted as time-weighted hourly MW |
| source_timestamp | Original MM/DD/YYYY HH:MM:SS text |
| source_timezone | Original EST or EDT label |
| source_name | Original N.Y.C. label |
| source_ptid | Original numeric identifier 61761 |
| pilot_window | winter, spring_dst, or fall_dst |
| source_file | Repository-relative extracted CSV path |
| source_file_sha256 | Hash of original member bytes |
| source_archive_sha256 | Hash of parent ZIP bytes |
| retrieved_at_utc | Actual archive retrieval time, not historical publication time |
| quality_flag | Structural-check status, not physical measurement certification |
| interval_interpretation | Evidence basis for hour-start mapping |
| availability_basis | Unresolved historical publication timing; no available_at_utc manufactured |

## Step 5 observed-weather Silver fields

`station_id`, `station_name`, `DATE`, `REPORT_TYPE`, `SOURCE`, `REM`, `source_row_number`, `source_file`, and `source_sha256` retain station/report/file lineage. `observation_time_utc` comes from the original METAR UTC token. `timestamp_basis` records the recovery rule and `source_date_discrepancy` flags disagreement with a simple DATE+5h conversion.

`interval_start_utc` and `interval_end_utc` identify the half-open UTC hour containing the selected observation. They do not make that observation available at interval start. Each numeric variable has `_raw` and `_state` companions. `precipitation_trace` distinguishes trace from numeric zero and unknown. `station_fallback_used` and `core_tuple_valid` expose selection status. The load-aligned file has `weather_role = retrospective_target_interval_observation_not_origin_available`.

## Full-history silver tables (Step 8)

Built by `scripts/build_silver.py` from the Step 7 raw files. All times are UTC; hourly intervals are half-open `[start, end)`. Units: MW, °C, %, m/s, mm.

`data/silver/nyiso/load_hourly_2017_2025.parquet` (78,888 rows, one per hour):

| Field | Meaning |
| --- | --- |
| interval_start_utc, interval_end_utc | Hour-start interpretation of the NYISO timestamp |
| source_timestamp, source_timezone | Original local timestamp text and EST/EDT label |
| source_ptid | 61761 (N.Y.C.) |
| load_mw | Integrated real-time actual load, current retrieved vintage |
| source_archive, source_member, source_archive_sha256 | Monthly ZIP, CSV member and ZIP hash |

`data/silver/noaa/weather_hourly_by_station_2017_2025.parquet` (one row per station-hour with an FM-15 observation): `station_id`, `station_name`, `observation_time_utc` (from the METAR token), the hour interval, each variable with `_raw` and `_state` companions, `precipitation_trace`, and file lineage (`source_file`, `source_row_number`, `source_sha256`).

`data/silver/noaa/weather_hourly_2017_2025.parquet` (78,888 rows, one per hour):

| Field | Meaning |
| --- | --- |
| interval_start_utc, interval_end_utc | Load-aligned hour |
| source_station | Station that supplied the core tuple (Central Park first, then LaGuardia, then JFK); empty if none |
| observation_time_utc | METAR UTC time of the selected observation |
| core_tuple_valid | True when temperature, dew point and humidity are all present |
| station_fallback_used | True when a backup station supplied the core tuple |
| temperature_c, dewpoint_c, relative_humidity_pct | Core variables |
| wind_speed_m_s | Optional; missing stays missing |
| precipitation_mm, precipitation_trace | Numeric amount and separate trace flag; trace is not zero |
| source_file, source_row_number, source_sha256 | Lineage of the selected observation |

`data/silver/nyiso/p7_day_ahead_2017_2025.parquet` (70,848 rows from 2017-12-02): `interval_start_utc`, `interval_end_utc`, `target_local_date`, `issue_date_local` (target day minus one), `source_timestamp`, `forecast_mw`, `source_member`, `source_archive_sha256`. Benchmark only, never a model input.

`data/silver/openmeteo/gfs_previous_day2_2024_2025.parquet` (17,544 rows): `valid_time_utc`, `fc_temperature_c`, `fc_dewpoint_c`, `fc_relative_humidity_pct`, `fc_wind_speed_km_h`, `fc_wind_speed_m_s`, `fc_precipitation_mm_prev_hour` (sum over the preceding hour), `forecast_lead`, `source_file`, `source_sha256`.

## Feature tables (Step 10)

Built by `scripts/build_features.py`: `data/gold/features_h1.parquet` (43 columns) and `data/gold/features_h24.parquet` (49 columns), 70,128 rows each (one per target hour, 2018-2025). Feature-set membership is in `data/gold/feature_sets.json` and `src/features/sets.py`.

| Field or prefix | Meaning |
| --- | --- |
| target_start_utc, target_end_utc | Target hour |
| origin_utc | Forecast origin = target end minus horizon |
| horizon_hours | 1 or 24 |
| target_local_time, target_local_year | New York local time and year of the target |
| split_role | train_initial (2018-2020), validation_test (2021-2024) or holdout (2025) |
| y_load_mw | Target load |
| load_L{k} | Load for the interval ending k hours before the origin (h1: 1, 2, 23, 47, 167; h24: 1, 24, 144) |
| load_roll{w}_mean | Mean load over the w hours ending at the latest usable interval (w = 3, 24, 168) |
| naive_persistence, naive_daily, naive_weekly | Baseline forecasts (daily shift 24 h at h1, 48 h at h24; weekly 168 h) |
| cal_* | Target calendar: hour, day of week, month, day of year, hour of week, weekend, federal, NERC and day-after-Thanksgiving holidays, and sin/cos encodings |
| wx_obs_* (h1) | Latest observation with METAR time + 15 min at or before the origin, at most 3 h old; includes `wx_obs_time_utc`, `wx_obs_station`, `wx_obs_age_minutes` |
| wx_tgt_* (h24) | Observed weather in the target hour. Ideal-information reference, not available at the origin (`wx_tgt_role`) |
| fc_* (h24) | Archived GFS forecast for the target end, 2024-2025 only; `fc_valid_time_utc` |
| *_hdh_c, *_cdh_c | Heating and cooling degree-hours: max(0, 18.3 - T) and max(0, T - 18.3) |
| benchmark_nyiso_p7_mw, benchmark_p7_issue_date_local (h24) | NYISO day-ahead forecast, benchmark only |
