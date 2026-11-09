# Data quality report

## Setup status

The synthetic setup fixture is verified. A real 2024 NYISO load pilot has now been acquired and structurally audited; NOAA and archived forecast-weather pilots remain pending. Earlier entries below describe their status at that time.

The local smoke test checks UTC interval consistency, uniqueness, hourly continuity, zone, numeric validity, positive synthetic load, and a CSV-to-Parquet round trip. Unit checks verify DST behavior and rejection of malformed intervals and duplicate rows.

Local execution evidence is generated in `outputs/data_audit/local_smoke.json` (ignored by Git). Databricks execution and export must be verified separately using the setup guide. A prepared notebook is not evidence of a successful remote run.

## Production audit still required

Source identity; interval labeling; publication/revision timing; station identifiers; weather time conventions; missingness; forecast vintages; full-period coverage; exclusions; and licensing.

## Verified local execution on November 1 2026

- Python 3.12.13; pandas 2.3.3; NumPy 2.5.4; PyArrow 24.0.0; HTTPX 0.28.1; pytest 9.2.0.
- Four validation tests passed.
- CSV validation, MW-to-GW transformation, expected summary, and Parquet round trip passed for 48 synthetic rows.
- Sample SHA-256: `1eb441a7209fab2e1188384f9ad4667ac94d179c5d3a01c86fd09792aab8ddad`.
- Git ignore checks confirmed that the environment, raw/cleaned data, generated evidence, and `.env` are excluded.
- Databricks notebook syntax checked locally; remote execution/export remains pending. GitHub publication and Actions remain pending.
- PyArrow emitted sandbox hardware-discovery notices, but the Parquet round trip completed successfully.

## Forecast timing validation — November 1, 2026

Added reusable target construction and explicit availability checks. The local suite now contains 16 passing tests. New cases cover both horizons across spring/fall DST transitions; missing or naive timestamps; off-hour and duplicate origins; unsupported horizons; completed but unpublished observations/load; future forecast initialization; and invalid forecast lead times. Equality at the forecast origin is accepted only when an explicit availability timestamp supports it.

The installed pandas/NumPy combination emits timedelta deprecation warnings during timestamp arithmetic; assertions pass. These tests use invented timestamps and establish code behavior only. Source publication delays, revision limitations, latest eligible weather-run selection, and target/weather alignment remain unresolved. No real-data acquisition, model fitting, or holdout-error inspection occurred.

```markdown
## Databricks smoke test verified on November 1 2026

The synthetic 48-row sample was successfully uploaded to Databricks Free Edition, validated, written to and read from a Delta table, and transformed from MW to GW. MLflow logged the experiment successfully.

- MLflow run ID: `bc891dd7b32d45d3b4bfef0518a5bab2`
- Delta table: `workspace.ml_capstone_setup.synthetic_zone_j_smoke`
- Mean load: 6,150 MW
- Sample SHA-256: `1eb441a7209fab2e1188384f9ad4667ac94d179c5d3a01c86fd09792aab8ddad`

The exported JSON evidence and transformed CSV were downloaded and verified locally. The comparison passed, confirming that Databricks results match the local fixture.

This verifies the synthetic cross-platform smoke test only. Real NYISO and NOAA data quality, forecast availability, and forecasting performance remain unverified.
```
## NYISO load pilot audit on November 1 2026

Three official monthly hourly archives (January, March, November 2024) were downloaded with actual retrieval timestamps, SHA-256 hashes, and archive/member lineage. They contain 2,208 NYC hours; the selected windows contain 312 hours (168 winter, 71 spring-DST, 73 fall-DST). No NYC UTC gaps or duplicate intervals were found in those months, and selected load values contain no missing/nonfinite/nonpositive values. No data were imputed or excluded.

The source label is N.Y.C., PTID 61761. Explicit EST/EDT labels preserve the 23-hour spring day and 25-hour fall day. Hour-start labeling is supported by an official five-minute numerical cross-check and the GridStatus implementation; an explicit NYISO CSV-schema statement was not obtained. Exact historical publication delays, original revision vintages, and redistribution terms remain unresolved. No forecasting lags were constructed and no 2025 data were accessed.

The suite contains 20 passing tests after adding four strict NYISO parser tests. Existing availability tests emit dependency deprecation warnings; no failures occurred. See [the full audit](nyiso_load_pilot_audit.md) for evidence, plots, limitations, and reproduction commands.

## NOAA weather intake audit on November 1 2026

Three user-supplied LCDv2 2024 files for the intended stations were copied unchanged into Bronze and hashed. Actual project intake times are recorded separately; original download URLs/times remain unknown. The diagnostic audit recovered original METAR UTC times and found ten fixed-EST conversion discrepancies per station near DST. All stations cover 312 diagnostic pilot-hour bins with no missing temperature/dew point/humidity; Central Park has 34 missing wind values. Precipitation trace tokens are preserved and not treated as measured zeros. No production weather/load join or availability timestamp was created. All 24 tests pass. See [the weather intake audit](noaa_weather_pilot_audit.md) for remaining decisions.

## Step 5 observed-weather pilot completion on November 1 2026

Frozen configuration and the offline build now produce 936 station-hour representatives, 312 Central Park primary records, and 312 one-to-one retrospective load/weather matches with no missing core temperature/dew point/humidity tuple or fallback. Original METAR UTC resolves pilot DATE discrepancies; unmatched annual records remain quarantined. Central Park's 34 missing wind values remain missing, and precipitation traces are distinct from zero. No imputation or operational feature availability was fabricated. All 27 tests pass. See the weather pilot audit for completed policies, source limitations, and later-stage tasks.

## Full-history audit (Step 9) on November 8 2026

The pilot audits are now generalized to all of 2017-2025. See [the full-history audit](data_audit_full_history.md) for tables, figures and limits; `scripts/audit_full_history.py` regenerates it from the Step 8 silver tables in about 35 seconds.

- NYISO Zone J load: all 78,888 expected hours present, no duplicates, nothing imputed. Over 2017-2024 there are no zero, negative or flat-run values. The robust deviation check flags 84 hours on 11 days, and these line up with heat days or the 2021 Independence Day weekend rather than feed faults.
- Observed weather: 140 hours (0.18%) have no core temperature, dew point and humidity reading at any station. 195 hours (0.25%) use a backup station (193 LaGuardia, 2 JFK). Wind is missing in 12.7% of hours.
- Station timing: 258 of 236,210 resolved FM-15 rows (0.11%) disagree with LCD DATE read as fixed EST. All fall within 4.2 hours of a DST change. The silver tables use METAR UTC times, so these rows are timed correctly. 47 rows without a recoverable METAR time remain quarantined.
- NYISO P-7: no missing hours from 2017-12-02. Open-Meteo: 468 null hours, all before 2024-01-20 12:00 UTC.
- 2025 holdout: counts only. It has 108 hours with no core weather and 3,035 hours with unknown precipitation, which is more than earlier years. This is recorded now so the final evaluation can report it. No 2025 load or weather values were summarized or plotted.
- Weather range checks on 2017-2024 found no out-of-range temperature, dew point, humidity, wind or precipitation values, and no dew point above temperature.
