# NOAA observed weather intake and pilot audit

**Date:** November 1, 2026  
**Disposition:** Step 5 observed-weather pilot complete. Pilot timestamp normalization, scalar handling, station selection, and hourly rules are frozen in `configs/weather_pilot.yaml`. Historical publication delay and full-history recovery remain later tasks.

## Files and station identities

The user supplied these three LCDv2 station-year files from Downloads. Exact copies and SHA-256 hashes are preserved under `data/bronze/noaa/lcdv2/`; the originals in Downloads were not modified.

| Station | Identifier | All records | FM-15 records | Latitude | Longitude |
| --- | --- | ---: | ---: | ---: | ---: |
| Central Park | USW00094728 | 11,608 | 8,767 | 40.77898 | -73.96925 |
| LaGuardia | USW00014732 | 13,525 | 8,781 | 40.7792 | -73.88 |
| JFK | USW00094789 | 13,169 | 8,760 | 40.6386 | -73.7622 |

All files have 125 columns, a single expected station identifier, and DATE values spanning January 1 through December 31, 2024. That date span does not prove complete hourly or variable coverage.

Files mix FM-15, special FM-16, daily SOD, monthly SOM, and (at the airports) FM-12 reports. Therefore total row counts are not hourly coverage counts. This diagnostic uses FM-15 only, preserving other reports in Bronze for later review. No daily/monthly summary is used as an origin-available predictor.

## Provenance

The existing download manifest now contains each supplied file's hash and project-relative path. Original download URLs and exact original download times were not supplied and remain blank rather than fabricated. Per-file `.intake.json` sidecars record actual project ingestion timestamps and original user-supplied paths. Ingestion is not retrieval from NOAA and neither establishes historical availability.

The local `lcdv2_DOCUMENTATION.pdf` was inspected for dataset version, bulk units, report metadata, and time conventions. Its station-year metric table specifies Celsius for temperature/dew point, percent for humidity, m/s for wind, and mm for precipitation. No Fahrenheit conversion was applied. The documentation's LST/no-DST statement is in its PDF-summary section; it must not be applied to CSV DATE blindly. Its elevation descriptions are internally inconsistent, so elevation is preserved as raw metadata and not used as a model feature.

## Timestamp finding requiring attention

The raw CSV DATE field is timezone-naive. The original METAR messages in REM contain explicit UTC day/hour/minute tokens such as `150551Z`. Those tokens allow an independent timing cross-check.

Across parseable FM-15 messages, most UTC observation times equal DATE plus five hours, consistent with standard-time labeling. However, **each station has ten records differing by an hour from that simple conversion**, concentrated around the DST transitions. Two raw DATE duplicates also occur in each station's annual FM-15 subset. Do not assume either a uniform NYC daylight-observing timezone or a uniform fixed offset reproduces all source messages.

Example from Central Park: DATE `2024-03-10T00:51:00` accompanies METAR token `100651Z`, which denotes March 10, 06:51 UTC rather than the 05:51 UTC produced by a simple five-hour conversion. The repeated November DATE `2024-11-03T01:51:00` accompanies distinct 05:51 and 06:51 UTC messages.

The diagnostic reconstructs UTC from the original METAR token, using DATE only to choose the nearby month/year. Unmatched messages remain unresolved; there is no timezone fallback. The script does not infer what caused the discrepancies or certify that a provider bug occurred.

| Station | Annual FM-15 rows with recovered UTC | Rows without recovered UTC | Recovered rows disagreeing with DATE + 5h |
| --- | ---: | ---: | ---: |
| Central Park | 8,743 | 24 | 10 |
| LaGuardia | 8,667 | 114 | 10 |
| JFK | 8,075 | 685 | 10 |

Unresolved-message counts describe this parser and available REM text, not confirmed absent weather observations. Other report types or original upstream data may recover additional times. No duplicate recovered UTC observation timestamps were found per station.

## Pilot coverage

For inspection only, retain the latest recovered FM-15 observation within each UTC hour and compare the UTC bins with the load pilot windows. This produces a retrospective diagnostic, not a production hourly average, target-aligned weather feature, or a forecast-origin availability rule. Observations at minute 51 cannot be treated as known at the beginning of the same hour.

| Station | Expected pilot hours | Hours with resolved FM-15 observation | Missing temperature | Missing dew point | Missing humidity | Missing wind |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Central Park | 312 | 312 | 0 | 0 | 0 | 34 |
| LaGuardia | 312 | 312 | 0 | 0 | 0 | 0 |
| JFK | 312 | 312 | 0 | 0 | 0 | 0 |

Each station covers 168 winter, 71 spring-DST, and 73 fall-DST diagnostic hours. No missing values were imputed. No station substitution was performed.

Central Park wind is missing for 23 winter, 7 spring, and 4 fall pilot hours. Full-year FM-15 missingness is separately tabulated in `annual_field_missingness.csv`; the small pilot must not stand in for a full-period quality assessment.

## Precipitation and quality handling

The hourly precipitation column contains both blanks and `T` trace tokens. The diagnostic keeps numeric mm values, preserves the original token, and leaves trace values numerically unresolved. A trace is not the same as missing data or a measured zero. Reported numeric-unavailable precipitation counts therefore combine categories that must remain distinguished before modeling.

Accumulation windows and overlapping subhourly precipitation must be resolved before summing or joining precipitation. Do not sum all special and routine reports together.

The audit preserves original SOURCE, REPORT_TYPE, REM, and source row numbers. The selected scalar fields contain blanks, numeric values, and precipitation trace tokens; absence of suffix flags is not a certification that upstream QC passed. LCDv2 does not expose a simple complete set of independent per-variable quality flags in these selected columns. Underlying GHCNh flag definitions and applicable filtering need further review.

## Station comparison and provisional choices

Paired temperature differences are tabulated in `station_temperature_comparison.csv`. LaGuardia's mean difference from Central Park ranges from -0.11 to +0.62 C across the three windows; JFK's from -0.07 to +0.15 C. Mean absolute differences are nonzero, so replacement is not measurement-equivalent.

Central Park remains the primary temperature/dew point/humidity candidate. Both airports remain comparison/backup candidates. Do not replace missing Central Park wind automatically. Prefer evaluating a core temperature/dew point feature set first, or define and justify a separate airport-wind feature later. A station fallback rule must preserve station identity and be frozen before comparative model evaluation.

## Reproduce and inspect

```bash
uv run python scripts/intake_noaa_weather.py
uv run python scripts/audit_noaa_weather.py
uv run pytest
```

The first command expects the original files in Downloads; after intake, the audit uses only preserved project copies and requires no network access. The audit writes diagnostics under `outputs/data_audit/noaa_weather/`, excluded from Git:

- `audit_summary.json`
- `pilot_coverage.csv`
- `annual_field_missingness.csv`
- `nonnumeric_tokens.csv`
- `timestamp_discrepancies.csv`
- `pilot_fm15_diagnostic_observations.csv`
- `station_temperature_comparison.csv`

Four synthetic parser tests cover month/year rollover, distinct repeated fall times, and unresolved/wrong-station messages. All 24 project tests passed; pre-existing availability tests still emit dependency warnings.

## Follow-up beyond the completed pilot

1. Recover original download provenance if available; actual project intake and hashes are already preserved, without invented history.
2. When expanding to full history, investigate unmatched original messages and other report types. The pilot uses only UTC-token-resolved records and has complete core coverage.
3. For operational forecasts, establish reporting/publication delay and perform origin-based selection in Step 7. No retrospective target-interval observation is automatically eligible at its forecast origin.
4. Review upstream GHCNh quality flags if richer QC is needed. Current flags describe documented scalar checks, not provider certification.

Observed data do not establish that archived issued forecasts are available. The forecast-weather pilot remains separate. This audit uses only user-supplied 2024 station files; a token can reference an adjacent UTC date at a calendar boundary, but no separate 2025 weather file or load holdout was accessed.


## Step 5 completion and frozen policies

The completed build produces 936 station-hour rows (312 per station), 312 primary rows, and a one-to-one retrospective alignment with all 312 NYISO pilot intervals. No target intervals are lost or duplicated. All core temperature/dew point/humidity values pass the declared pilot scalar rules. No station fallback or imputation was required.

### Canonical time

Use the station-matched DDHHMMZ token in the original METAR message, with nearest-month context from DATE. NWS describes the Z token as UTC: [NWS weather-observation guidance](https://www.weather.gov/lot/weather_observations_faq). This resolves the pilot's DST-edge DATE discrepancies without guessing a uniform CSV offset. Preserve the original DATE, REM, recovered UTC, and discrepancy flag. Records lacking a recoverable token go into a quarantine output; no fixed-offset fallback is used.

All 312 pilot intervals per station have a resolved routine message. Across the annual routine records, 24 Central Park, 114 LaGuardia, and 685 JFK rows remain in the unresolved-time quarantine. These are parser/source-message limitations, not proved missing weather hours. The annual files are retained unchanged.

### Hourly representative

Select the latest FM-15 observation strictly within each UTC interval `[start, end)`. Preserve the actual observation time and the representative interval separately. This is a point observation representing the interval, not a time-weighted hourly average. Daily/monthly summaries and special reports are excluded from this pilot extract rather than mixed into it.

A minute-51 observation is not known at minute 00. The aligned load/weather table is explicitly retrospective; Step 7 must select only measurements available by each forecasting origin. No availability time is fabricated here.

### Station and missingness rule

Primary: Central Park USW00094728. Backups, in order: LaGuardia USW00014732, then JFK USW00094789. Select a complete temperature/dew point/humidity tuple from one station in the same interval. Preserve its station identity and whether fallback occurred. If no complete tuple exists, mark it missing. Do not interpolate across future observations or carry a future value backward.

Pilot fallback count is zero. Keep selected-station wind as recorded; 34 Central Park values remain missing. Wind is optional. Do not silently import airport wind into Central Park's series.

### Scalar quality and precipitation rule

Keep raw scalar tokens and parsed-value states. Basic sanity limits are temperature -90 to 60 C, dew point -100 to 60 C, humidity 0–100%, wind 0–100 m/s, and precipitation 0–1000 mm. A dew point more than 1 C above dry-bulb temperature is flagged and left missing. These broad checks identify obvious invalidity, not outliers for automatic removal and not full NOAA QC. All pilot core values pass them. Preserve original SOURCE/REPORT_TYPE/REM because the CSV does not expose complete upstream per-variable flags.

Trace precipitation retains `precipitation_trace = true`, raw `T`, and a missing numeric amount rather than a fabricated amount or measured zero. Central Park has 16 trace pilot values, LaGuardia 26, and JFK 24; all remaining selected pilot precipitation tokens are numeric. Do not sum overlapping reports or reinterpret these amounts as exact load-hour accumulations. Precipitation stays optional until accumulation alignment is specified for its intended model use.

### Outputs and verification

Run `uv run python scripts/build_weather_pilot.py` after the preserved source files and NYISO pilot exist. It requires no network and writes:

- `data/silver/noaa/weather_pilot_observations_2024.parquet`: original-message-resolved pilot observations and scalar states.
- `data/silver/noaa/weather_pilot_hourly_by_station_2024.parquet`: 936 station-hour representatives.
- `data/silver/noaa/weather_pilot_primary_2024.parquet` and `.csv`: 312 selected primary rows with source provenance.
- `data/silver/noaa/load_weather_pilot_retrospective_2024.parquet`: 312 one-to-one load/weather alignment rows, labeled retrospective.
- `outputs/data_audit/noaa_weather/step5_completion.json`: counts, configuration hash, and output hashes.
- `annual_unresolved_time_quarantine.csv`, `silver_pilot_coverage.csv`, and `station_temperature_pilot.png` in the same audit folder.

All 27 tests pass, including month/year rollover, repeated fall times, trace handling, invalid humidity, last-within-interval selection, and intact-station fallback without wind imputation. Existing availability tests emit dependency deprecation warnings without failures. No model was fitted and no separate 2025 source file or holdout was accessed.

Step 5 is complete for the requested observed-weather pilot. This does not complete the archived forecast-weather pilot (Step 6), origin availability integration (Step 7), or full-history acquisition (Step 8).

![Station temperature comparison](../outputs/data_audit/noaa_weather/station_temperature_pilot.png)

The comparison plot uses actual recovered observation times, separate pilot panels, shared Celsius axes, and distinct colors/line styles. The rendered figure was inspected for readable labels and visible series.
