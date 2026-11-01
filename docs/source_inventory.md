# Source inventory

**Project:** NYC Zone J electricity load forecasting  
**Researcher:** Candace Grant  
**Created:** November 1, 2026  
**Status:** Initial inventory; production sources have not yet passed pilot audits.

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

| Field | Current specification or audit requirement |
| --- | --- |
| Provider | NYISO; planned source |
| Product | Integrated Real-Time Actual Load; planned hourly target product |
| Role | Target variable and eligible historical load predictors |
| Discovery URL | <https://oasis.nyiso.com/> |
| Candidate archive index | <https://mis.nyiso.com/public/P-58Clist.htm>; inspect and verify pilot files before approving acquisition |
| Exact downloadable archive URLs | Unresolved — requires audit. Record each actual file URL in the download manifest; an index URL is not a file URL. |
| Geography | Zone J, New York City; planned scope |
| Exact source zone identifier | Unresolved — requires audit. Preserve the actual label/code and evidence mapping it to Zone J. |
| Units | MW under the research contract; verify the source field and hourly integrated definition. Do not silently substitute energy in MWh. |
| Source column names | Unresolved — requires audit |
| Interval labels | Unresolved — requires audit. Determine whether the timestamp denotes interval start, interval end, or another convention. |
| Source timezone | Unresolved — requires audit. Inspect timestamp and timezone/offset fields and official documentation. |
| DST behavior | Unresolved — requires audit. Examine spring and fall transitions before converting to UTC. |
| Revision policy and vintage | Unresolved — requires audit. Determine whether downloaded records are preliminary, revised, or final and whether prior vintages can be recovered. |
| Publication timing | Unresolved — requires audit. Distinguish interval completion, first publication, and subsequent revision. |
| Predictor availability rule | Unresolved — requires audit. Establish an evidence-based delay or explicitly labeled conservative assumption. |
| Requested historical coverage | 2018–2025, NYC local calendar dates; planned scope |
| Actual coverage | Unresolved — requires audit; report gaps and exclusions |
| Pilot periods | January 15–21, March 9–11, and November 2–4, 2024; planned inspection windows |
| Format and access method | Unresolved — requires audit; preserve original files and archive membership |
| Usage and redistribution terms | Unresolved — requires audit; record official terms and attribution requirements |
| Audit evidence | Pending: downloaded pilot, manifest rows, metadata notes, UTC/DST audit, and load plot |
| Approval status | Planned; not approved for full-period acquisition |

### Load acceptance criteria

- Confirm the hourly integrated product rather than silently using five-minute actual load.
- Verify the source identifier for Zone J, numerical units, and interval boundaries.
- Preserve original timestamps and resolve both DST transitions without losing distinct intervals.
- Quantify missing and duplicate records; investigate unusual values before excluding them.
- Document publication-delay and revision limitations before engineering load features.

## NOAA observed weather

| Field | Current specification or audit requirement |
| --- | --- |
| Provider | NOAA National Centers for Environmental Information; planned source |
| Dataset | Local Climatological Data version 2; planned dataset, verify actual download version |
| Discovery and documentation entry point | <https://www.ncei.noaa.gov/products/land-based-station/local-climatological-data> |
| Exact download URLs | Unresolved — requires audit; record per-file URLs in the manifest |
| Role | Eligible observed weather history, retrospective event labels, and separately labeled future-observed-weather sensitivity experiment |
| Primary station candidate | Central Park; selection remains conditional on coverage and relevance |
| Backup station candidates | LaGuardia and JFK; compare before choosing a substitution rule |
| Exact station identifiers | Unresolved — requires audit. Record the identifier used by the selected dataset version, not just a station name or identifier from another system. |
| Coordinates and elevation | Unresolved — requires audit; record latitude, longitude, coordinate convention, elevation, and source metadata |
| Variables | Planned: temperature, dew point, relative humidity, wind speed, and precipitation where suitable |
| Exact field names and units | Unresolved — requires audit for each variable; preserve source units and document conversion |
| Quality flags | Unresolved — requires audit. Identify flags, missing-value codes, trace precipitation, and excluded observation types. |
| Timestamp convention | Unresolved — requires audit. Determine UTC, fixed local standard time, or daylight-observing local time for the exact downloaded product. |
| Observation timing within each hour | Unresolved — requires audit. Identify routine/special reports and multiple records per hour. |
| Hourly selection or aggregation | Unresolved — requires audit. Specify a causal rule for predictors and a documented rule for retrospective interval summaries. |
| Observation availability delay | Unresolved — requires audit; do not equate observation time with public availability automatically |
| Missingness and station substitution | Unresolved — requires audit by variable and period; preserve contributing station identity |
| Requested coverage | Same load pilot windows, followed by approved 2018–2025 coverage |
| Actual station/variable coverage | Unresolved — requires audit |
| Usage and redistribution terms | Unresolved — requires audit; record attribution and source terms |
| Audit evidence | Pending: station metadata, pilot files, manifest rows, variable dictionary, missingness and station-comparison outputs |
| Approval status | Planned; station selection and full-period acquisition pending |

### Station metadata register

| Candidate | Exact dataset station ID | Latitude | Longitude | Elevation and units | Metadata evidence | Pilot status |
| --- | --- | --- | --- | --- | --- | --- |
| Central Park | Unresolved | Unresolved | Unresolved | Unresolved | Pending | Not acquired |
| LaGuardia | Unresolved | Unresolved | Unresolved | Unresolved | Pending | Not acquired |
| JFK | Unresolved | Unresolved | Unresolved | Unresolved | Pending | Not acquired |

### Weather variable register

| Variable | Source field | Source units | Analysis units | Flags and missing codes | Hourly rule |
| --- | --- | --- | --- | --- | --- |
| Air temperature | Unresolved | Unresolved | Degrees Celsius | Unresolved | Unresolved |
| Dew point | Unresolved | Unresolved | Degrees Celsius | Unresolved | Unresolved |
| Relative humidity | Unresolved | Unresolved | Percent | Unresolved | Unresolved |
| Wind speed | Unresolved | Unresolved | Metres per second | Unresolved | Unresolved |
| Precipitation | Unresolved | Unresolved | Millimetres with explicit accumulation interval | Unresolved | Unresolved |

Heating/cooling degree-hours are derived features, not an additional source. Their initial reference is 18.3°C under the research contract. Future observed weather must remain separate from operational predictors.

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
