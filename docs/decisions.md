# Research decisions

| Date | Decision | Rationale | Holdout errors viewed |
| --- | --- | --- | --- |
| 2026-11-01 | Horizon measured to target interval end | Makes issuance and target boundaries explicit | No |
| 2026-11-01 | Python 3.12 with uv.lock; local-first portable setup | Stable local baseline independent of managed runtime | No |
| 2026-11-01 | Use a synthetic fixture for platform smoke tests | Verify infrastructure without implying real-data validation | No |
| 2026-11-01 | Do not select a forecast provider or assume publication delays yet | Requires source pilot | No |
| 2026-11-01 | Databricks smoke test uses managed volume and dedicated setup table | Avoid legacy DBFS assumptions and isolate test objects | No |
| 2026-11-01 | Require explicit timezone-aware availability timestamps in timing validation | Reject unavailable inputs without inventing source delays; preserve elapsed-hour horizons across DST | No |

Record subsequent changes, rationale, affected experiments, and whether final-holdout performance was viewed.

## NYISO pilot decisions on November 1 2026

- Acquire only January, March, and November 2024 hourly integrated-load months for the pilot; no 2025 access.
- Preserve original ZIP bytes, archive/member hashes, and actual retrieval timestamps.
- Identify Zone J using source N.Y.C. / PTID 61761 and official zone mapping.
- Use explicit EST/EDT offsets checked against America/New_York, preserving both repeated fall hours.
- Adopt supported hour-start interpretation from the numerical cross-check and reference implementation; retain this evidentiary qualification.
- Acquire one auxiliary January five-minute archive for two extracted days, without replacing the hourly target.
- Retain January 15–21 but call it winter inspection, since it includes MLK Day.
- Leave historical publication/revision assumptions unresolved for the availability-rule stage.
- Add Matplotlib to the locked environment for the requested standalone research figure.
- No holdout errors viewed; no models fitted; full-history acquisition remains unapproved.

## NOAA intake decisions on November 1 2026

- Preserve user-supplied 2024 LCDv2 files without altering the Downloads originals. Record hashes and actual intake times; do not fabricate original download provenance.
- Separate FM-15 diagnostics from daily/monthly/special records.
- Recover original-message UTC for diagnostic checks and flag DATE discrepancies; do not silently apply one timezone to all CSV timestamps.
- Leave unmatched messages unresolved and precipitation traces distinct from zero.
- Retain Central Park as the core-temperature candidate; do not substitute airport wind silently.
- Defer production Silver weather extraction and availability claims until timing/QC/fallback rules are frozen. No separate 2025 data file or holdout accessed.

## Step 5 completion decisions on November 1 2026

- Freeze pilot rules in configs/weather_pilot.yaml: station-matched original METAR UTC, no guessed offset fallback, routine FM-15, last observation within each half-open UTC hour.
- Central Park is primary for a complete temperature/dew point/humidity tuple; fallback is LaGuardia then JFK within the same interval, with provenance. No fallback was needed in the pilot.
- Keep missing wind missing; retain precipitation trace state without fabricating mm. Both variables are optional.
- Preserve source/remarks/raw scalar states and apply documented broad sanity checks, without claiming complete upstream QC.
- Build a clearly retrospective one-to-one load/weather alignment, not origin-eligible model features. Leave publication delay for Step 7.
- Step 5 pilot is complete; full-year unresolved-message recovery and original download provenance remain limitations for expansion. No model fitting or separate 2025 data access.

## Amendment 1 decisions on November 6 2026

| Date | Decision | Rationale | Holdout errors viewed |
| --- | --- | --- | --- |
| 2026-11-06 | Freeze revised proposal as contract v0.2 (Amendment 1) | Align configs, contract, and proposal before full-history work | No |
| 2026-11-06 | Load usable at O only through the interval ending O - 1h; zero-delay sensitivity | Live P-58B posting lagged about 15-20 min; historical delay unverifiable | No |
| 2026-11-06 | Origin-relative lags; 24-hour daily naive uses a 48-hour shift | t-1 (1 h) and t-24 (24 h) are unavailable under the load rule | No |
| 2026-11-06 | Observed weather usable if logged at least 15 min before O; zero-minute sensitivity | No published NCEI dissemination times | No |
| 2026-11-06 | Forecast weather: Open-Meteo GFS previous_day2, all weather variables, 2024-2025 | previous_day1 can postdate a 24-hour origin; fixed-lead archives start in 2024 | No |
| 2026-11-06 | 24-hour observed-weather results labeled an ideal-information reference | Future observations are not available at O | No |
| 2026-11-06 | Add NYISO P-7 day-ahead forecast as 24-hour benchmark | Operational comparison point | No |
| 2026-11-06 | Test years 2021-2024; holdout 2025; 2017 warm-up only | Expanding window by year | No |
| 2026-11-06 | SARIMAX on trailing two-year windows; LSTM deferred; DM tests for primary comparisons only | Protect schedule | No |
| 2026-11-06 | Approve full-history acquisition via per-file downloads | Bulk archives were too large and failed | No |

## Step 7 acquisition decisions on November 8 2026

| Date | Decision | Rationale | Holdout errors viewed |
| --- | --- | --- | --- |
| 2026-11-08 | Acquire full history with per-file, resumable, hashed downloads (scripts/acquire_*.py) | Bulk archives failed; reruns download nothing new | No |
| 2026-11-08 | Raw files stay in data/bronze (git-ignored); provenance in data/manifests/downloads.csv | Reproducibility without committing data | No |
| 2026-11-08 | Open-Meteo GFS previous_day2 coverage begins 2024-01-20T12:00 UTC; earlier hours stay missing (no imputation) | Provider archive start; operational sub-study scored from that time | No |
| 2026-11-08 | 2025 files downloaded but not opened for modelling until the holdout chunk | Protect final holdout | No |

## Step 8 silver-table decisions on November 8 2026

| Date | Decision | Rationale | Holdout errors viewed |
| --- | --- | --- | --- |
| 2026-11-08 | Fix METAR UTC parser to accept tokens glued to a prefix (e.g. MET055METAR) | Pilot regex missed about 35% of 2025 rows and 670 JFK rows in April 2024; time rule itself unchanged | No |
| 2026-11-08 | Silver tables cover local 2017-01-01 to 2026-01-01 on a full UTC hour grid; missing hours kept as rows and listed in outputs/data_audit/step8 | Missing data visible, never hidden or imputed | No |
| 2026-11-08 | P-7 benchmark uses the file issued the local day before the target day; issue time within that day is not published | Day-ahead benchmark as NYISO publishes it; not origin-matched, reported as such | No |
| 2026-11-08 | Open-Meteo precipitation is the preceding-hour sum; wind converted from km/h to m/s to match NOAA | Consistent units and interval meaning | No |
| 2026-11-08 | 2025 rows built for counts only; no 2025 statistics or errors inspected | Protect final holdout | No |

## Step 10 feature decisions on November 8 2026

| Date | Decision | Rationale | Holdout errors viewed |
| --- | --- | --- | --- |
| 2026-11-08 | One row per target hour, 2018-2025 (70,128 rows per horizon); origin = target end minus horizon | Matches the horizon anchor in study.yaml | No |
| 2026-11-08 | Load lags and rolling means read from study.yaml and checked with validate_availability() on every row | Leakage excluded by construction; test uses encoded synthetic load | No |
| 2026-11-08 | 1-hour weather: latest Central Park-first observation with METAR time + 15 min <= origin, at most 3 h old | No stale carry-forward; typical age 69 minutes | No |
| 2026-11-08 | Wind kept as a column but excluded from feature set C | Optional under the frozen weather rule; about 12% missing | No |
| 2026-11-08 | Forecast weather matched at valid time = target end; assumed initialization 48 h before and published 6 h after | previous_day2 definition plus conservative GFS latency | No |
| 2026-11-08 | Holidays from pandas USFederalHolidayCalendar plus NERC subset and day after Thanksgiving | Same holidays as the holidays package; no new dependency | No |
| 2026-11-08 | Naive baseline values stored in the tables; scored in Step 11 | Baselines pass the same availability checks | No |

