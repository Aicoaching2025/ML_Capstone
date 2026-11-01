# Source inventory

**Project:** NYC Zone J electricity load forecasting  
**Researcher:** Candace Grant  
**Created:** November 1, 2026  
**Status:** NYISO load pilot acquired and structurally audited; NOAA and forecast sources remain pending.

This inventory records intended sources and the evidence needed before using them in forecasting experiments. It complements [the research contract](research_contract.md) and `configs/sources.yaml`. It does not establish that an archive has complete coverage or that a historical input was available at a forecast origin.

Unknown details are deliberately marked **Unresolved — requires audit**. Replace them only after inspecting official documentation and actual pilot files. Record the supporting URL, file, or audit output beside each resolved detail. Do not infer historical availability from a download timestamp.

## Status definitions

| Status | Meaning |
| --- | --- |
| Planned | A research choice or candidate, not a verified source property |
| Unresolved — requires audit | Evidence has not yet established the detail |
| Pilot verified | Documentation and a downloaded sample support the detail; record evidence |
| Approved for acquisition | Pilot requirements passed and scope is recorded in the decisions log |
| Rejected or superseded | Retain the reason and replacement source, if any |

## NYISO hourly load

**Pilot audit:** November 1, 2026. See [the full audit](nyiso_load_pilot_audit.md).

| Field | Current specification or audit requirement |
| --- | --- |
| Provider/product | NYISO Integrated Real-Time Actual Load, P-58C / palIntegrated; pilot acquired |
| Role | Hourly target and, after availability rules are resolved, historical load predictors |
| Official archive index | <https://mis.nyiso.com/public/P-58Clist.htm> |
| Exact downloadable URLs | January/March/November 2024 URLs recorded in `data/manifests/downloads.csv` |
| Geography and source identifiers | Zone J, NYC; source label `N.Y.C.`, PTID `61761`; observed throughout pilot and checked against NYISO mapping |
| Source columns | `Time Stamp`, `Time Zone`, `Name`, `PTID`, `Integrated Load` |
| Units | MW under the time-weighted hourly-power interpretation; source CSV itself has no units field |
| Source timestamp | `MM/DD/YYYY HH:MM:SS`; explicit EST/EDT field |
| Source timezone | NYC daylight-observing local time; offsets checked against America/New_York |
| Interval label | Supported hour-start interpretation from five-minute numerical cross-check and GridStatus implementation; not explicit provider CSV-schema confirmation |
| DST behavior | March 10 has 23 NYC rows; November 3 has 25. Repeated 01:00 retained with different offsets. |
| Requested study coverage | 2018–2025 planned; not yet acquired |
| Acquired coverage | Three full months: January, March, November 2024; 2,208 NYC records |
| Selected pilot windows | January 15–21 (168 hours); March 9–11 (71); November 2–4 (73); 312 total |
| Completeness | No missing NYC UTC hours in the three months; no duplicate zone/UTC keys; no missing/nonfinite/nonpositive selected target values |
| Revisions and vintages | Unresolved — archives are current retrieved versions, without historical first-publication or revision timestamps |
| Publication timing | NYISO guide says posted after each hour; precise historical delay remains unresolved |
| Predictor availability rule | Unresolved — do not assign availability from retrieval or interval end automatically |
| Format/access | HTTPS ZIP archives containing daily CSVs; immutable originals and extraction lineage retained |
| Usage and redistribution terms | Unresolved — review before public raw-data redistribution; raw files remain out of Git |
| Audit evidence | Pilot report, download/member manifests, scripts, strict parser tests, Silver pilot, generated plots/count tables |
| Approval status | Pilot structural/DST checks passed; full-history acquisition not approved |

### Remaining load decisions

- Preserve the evidence qualification on hour-start interpretation; amend if an explicit provider schema becomes available.
- Resolve publication-delay and revision assumptions before engineering predictive lags.
- The January window includes MLK Day; it is a winter inspection window, not a fully ordinary nonholiday week.
- Verify full-history coverage and source terms before expanding acquisition or redistributing data.

## NOAA observed weather

**Status:** Step 5 observed-weather pilot complete. [Full report](noaa_weather_pilot_audit.md); exact rules in `configs/weather_pilot.yaml`.

| Field | Established pilot specification |
| --- | --- |
| Provider and dataset | NOAA NCEI LCD v2; user-supplied 2024 station-year CSVs |
| Source page | <https://www.ncei.noaa.gov/products/land-based-station/local-climatological-data> |
| Primary | Central Park, USW00094728, KNYC; latitude 40.77898, longitude -73.96925 |
| First backup | LaGuardia, USW00014732, KLGA; latitude 40.7792, longitude -73.88 |
| Second backup | JFK, USW00094789, KJFK; latitude 40.6386, longitude -73.7622 |
| Units | Temperature/dew point C, humidity %, wind m/s, precipitation mm under bulk LCDv2 metric specification |
| Report selection | Routine FM-15 only for this pilot; preserve other types in Bronze |
| Canonical timestamp | Original station-matched METAR UTC token, DATE used only for nearby month/year context |
| Timestamp exceptions | Preserve DATE discrepancies; quarantine unmatched UTC tokens without guessed offset fallback |
| Hourly selection | Latest observation strictly inside half-open UTC hour; point representative, not mean |
| Primary core variables | HourlyDryBulbTemperature, HourlyDewPointTemperature, HourlyRelativeHumidity |
| Optional variables | HourlyWindSpeed, HourlyPrecipitation; missing wind remains missing; trace separate from zero |
| Quality handling | Raw tokens, source and remarks retained; documented numeric sanity checks; no full upstream-QC certification |
| Missingness and fallback | No temporal imputation. Complete same-interval core tuple: Central Park, then LGA, then JFK; preserve station identity |
| Pilot result | 936 station-hour rows; 312 primary and load-aligned rows; no missing core tuple; zero fallback hours |
| Source files and provenance | Immutable copies in data/bronze/noaa/lcdv2; hashes in downloads.csv; project intake sidecars |
| Original URL and download time | Unknown for supplied files; not invented. Candidate source page is not presented as verified exact download URL. |
| Publication delay | Unresolved; Step 7. No origin-eligible forecast features created. |
| Elevation | Preserved raw; documentation has inconsistent elevation-unit descriptions; not used |
| Full-history readiness | Pending unmatched-message review and eight-year coverage audit; no annual completeness claim |
| Source terms | Review before public raw-data redistribution; raw files remain excluded from Git |

## Archived issued weather forecasts

| Field | Current specification or audit requirement |
| --- | --- |
| Provider | Unresolved — requires archive pilot |
| Model and version | Unresolved — requires audit; select an explicit model and record relevant historical changes |
| Candidate access route | Open-Meteo Previous Runs: <https://open-meteo.com/en/docs/previous-runs-api> |
| Alternative archive entry point | NOAA GFS archive information: <https://registry.opendata.aws/noaa-gfs-bdp-pds/> |
| Candidate status | Discovery options only; neither is approved by this inventory |
| Role | Future weather inputs eligible at each load-forecast origin |
| Initial variables | Temperature first; add dew point/humidity or other variables only after checking historical coverage and timing |
| Exact endpoint and request parameters | Unresolved — requires audit; preserve model, coordinates, dates, variables, timezone, and lead-offset parameters |
| Archive dates | Unresolved — requires actual returned coverage for every selected variable and model |
| Initialization and issue times | Unresolved — requires audit; determine what metadata the product exposes |
| Valid times | Unresolved — requires audit; determine whether values represent instants, interval averages, or accumulations |
| Forecast lead definition | Unresolved — requires audit. Distinguish initialization-to-valid-time lead from load origin-to-target-end horizon. |
| Publication/availability time | Unresolved — requires audit; record observed/documented timing or a justified assumption |
| Availability basis | Unresolved — requires audit; label verified release timestamps separately from assumed release delays |
| Run selection rule | Unresolved — requires audit; use the latest eligible run under a frozen, reproducible rule |
| Location extraction | Unresolved — requires audit. Record requested coordinates, returned grid coordinates, resolution, and nearest-point/interpolation method. |
| Interval alignment | Unresolved — requires audit. Map weather values to the load target interval, whose end defines the horizon. |
| Missing values and fallback | Unresolved — requires audit; do not replace missing issued forecasts with future observations silently |
| Pilot scope | One winter and one summer sample in 2024, plus an archive-start boundary sample after candidate coverage is established |
| Operational experiment period | Unresolved — freeze after coverage and timing audit; may be shorter than 2018–2025 |
| Model changes | Unresolved — identify changes that could affect comparability through time |
| Access limits and usage terms | Unresolved — verify request limits, attribution, redistribution, and any cost before bulk acquisition |
| Audit evidence | Pending: original request/response files, manifests, coverage table, traced origin/target examples, and scope decision |
| Approval status | Not selected; no operational weather availability claim yet |

### Forecast acceptance criteria

- Establish that the product contains issued forecasts rather than observations, reanalysis, or a stitched series that does not preserve the required lead semantics.
- Verify actual coverage rather than inferring it from a general provider claim.
- Show a complete origin-to-target example with a weather run eligible at issuance.
- Explain any release-delay assumption and the resulting limitation.
- Define spatial extraction and hourly alignment consistently.
- Compare weather ablations on the same eligible timestamps and overlap period.
- If an archive fails, document a shorter operational period or a different source before full acquisition.

## Calendar

| Field | Current specification or audit requirement |
| --- | --- |
| Source type | Deterministic calendar and documented holiday rules; no downloaded observational feed required |
| Date/time tooling | Python/pandas environment recorded in `uv.lock`; record the actual executed versions in run metadata |
| Holiday package and version | Unresolved — select and document before feature generation; no holiday package is currently specified |
| Holiday jurisdiction | US holiday calendar planned; exact calendar definition must be selected explicitly |
| Holiday rules | Unresolved — specify included holidays, rule changes, and whether any NYC-specific additions are justified |
| Observed holidays | Unresolved — specify whether actual dates, substitute observed dates, or separate indicators are used |
| Calendar timezone | `America/New_York` under the research contract |
| Chronology/storage timezone | UTC under the research contract |
| Target calendar anchor | Target interval start converted to NYC local time |
| Planned features | Hour, weekday, month, holiday indicators, cyclic encodings, and selected interactions |
| DST rule | Derive local features from unambiguous UTC timestamps; retain distinct repeated hours and do not fabricate nonexistent hours |
| Information availability | Deterministic future calendar features are known in advance; any data-learned transformation uses training data only |
| Validation | Pending: weekend/weekday, actual/observed holiday, year boundary, spring DST, and fall DST examples |
| Provenance | Record package, calendar name, version, timezone data version, feature code commit, and custom rule definitions |
| Approval status | Timezone/anchor specified; holiday implementation pending |

## Provenance requirements

Create `data/manifests/downloads.csv` when beginning source acquisition. Each downloaded source file needs a traceable entry containing at least:

```csv
source_url,retrieved_at_utc,local_filename,file_hash_sha256,source_product,requested_period,station_or_zone,provider,model,notes
```

- Use timezone-aware UTC retrieval timestamps and SHA-256 hashes of original downloaded bytes.
- Record repository-relative local paths and exact requested periods.
- Preserve original ZIP archives and associate extracted members with their parent archive.
- Record dataset/model versions and complete nonsecret request parameters where relevant.
- Keep API keys, authorization headers, signed URLs, and other credentials out of committed manifests. For authenticated requests, record a sanitized endpoint and nonsecret parameters sufficient to reconstruct the request using separately managed credentials.
- Link cleaned extracts to source hashes, transformation code/configuration, and documented exclusions.
- Treat calendar provenance as software/rule metadata rather than inventing a source-file download.

The synthetic setup fixture is not a NYISO or NOAA pilot and must not be listed as real source evidence.

## Audit and approval record

For each source, complete this record before approving full acquisition:

| Field | Entry |
| --- | --- |
| Source/product/model | Pending |
| Audit date and researcher | Pending |
| Documentation and pilot paths | Pending |
| Manifest records | Pending |
| Coverage verified | Pending |
| Timestamp/interval interpretation | Pending |
| Availability rule and evidence | Pending |
| Missingness/quality limitations | Pending |
| Usage/redistribution terms | Pending |
| Decision and approved period | Pending |
| Related decisions log entry | Pending |

Update `configs/sources.yaml` and `docs/decisions.md` after source approval so configuration and documentation remain consistent. Inventory completion alone does not establish that source acquisition or quality validation is complete.
