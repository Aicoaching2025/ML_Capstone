# Data dictionary

Status: synthetic setup fixture and audited NYISO load pilot. Other source fields await their Bucket 1 audits.

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
