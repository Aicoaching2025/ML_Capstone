# Data dictionary

Status: setup fixture only. Production source fields await the Bucket 1 audit.

| Field | Type | Meaning |
| --- | --- | --- |
| interval_start_utc | UTC timestamp | Inclusive beginning of hourly interval |
| interval_end_utc | UTC timestamp | Exclusive end, exactly one elapsed hour later |
| zone | string | J in the synthetic fixture |
| load_mw | float | Synthetic hourly load in MW; not NYISO observations |
| temperature_c | float | Synthetic temperature; not an eligible future-weather predictor |
| load_gw | float | Smoke-test transformation: load_mw / 1000 |

The 48-row fixture covers the November 2024 fall DST transition. All values are invented solely for setup verification. Do not use it for research findings or source feasibility claims.
