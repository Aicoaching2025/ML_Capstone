# NYISO Zone J load pilot audit

**Audit date:** November 1, 2026  
**Scope:** January, March, and November 2024 hourly Integrated Real-Time Actual Load archives; three specified pilot windows.  
**Outcome:** Acquisition, provenance, UTC conversion, completeness, and DST checks passed. Hour-start labeling is a supported working interpretation; precise historical publication/revision timing remains unresolved. No model features were built and no 2025 data were accessed.

## Data acquired

The three original ZIPs are preserved unchanged under `data/bronze/nyiso/integrated_load/`. They contain 92 daily CSV files across all 11 source load zones. The archives contain 2,208 NYC hourly records in total; the requested pilot windows contain 312 of those records.

| Month | Daily CSV files | All-zone rows | NYC hours | Expected NYC hours | Missing NYC UTC hours |
| --- | ---: | ---: | ---: | ---: | ---: |
| January 2024 | 31 | 8,184 | 744 | 744 | 0 |
| March 2024 | 31 | 8,173 | 743 | 743 | 0 |
| November 2024 | 30 | 7,931 | 721 | 721 | 0 |

An additional January 2024 five-minute actual-load ZIP is preserved under `data/bronze/nyiso/timing_check/`. Only January 15 and 16 were extracted for the interval-label cross-check. This auxiliary product does not replace the hourly integrated target.

[The download manifest](../data/manifests/downloads.csv) records the four archive URLs, actual UTC retrieval timestamps, paths, and SHA-256 hashes. [The hourly member manifest](../data/manifests/nyiso_pilot_archive_members.csv) associates every extracted hourly CSV with its parent archive and both hashes. Raw-folder `lineage.json` files also preserve extraction relationships, including the auxiliary sample.

Original daily historical URLs for the auxiliary product returned HTTP 404. Its official monthly archive succeeded. Acquisition scripts cache originals; rerunning them does not silently refresh a historical vintage.

## Source schema and target identification

The original CSV columns are:

```text
Time Stamp, Time Zone, Name, PTID, Integrated Load
```

| Property | Finding |
| --- | --- |
| Product | NYISO Integrated Real-Time Actual Load, report P-58C, dataset path `palIntegrated` |
| NYC source label | `N.Y.C.` |
| NYC PTID | `61761`, consistent throughout the three retrieved hourly archives |
| Study zone | J; NYISO's zone mapping identifies N.Y.C. as Zone J |
| Timestamp text | `MM/DD/YYYY HH:MM:SS` |
| Timezone text | Explicit `EST` or `EDT` in the separate `Time Zone` column |
| Numerical target | `Integrated Load`, parsed as floating point; original source values retained |
| Research unit | MW, interpreting the product as time-weighted hourly average power per NYISO's product description; the CSV itself has no units field |
| Example normal day | January 15: 264 all-zone rows and 24 NYC rows |
| Example original record | `01/15/2024 00:00:00, EST, N.Y.C., 61761, 5019.6911` |

This target is an hourly load value, not the maximum instantaneous demand within an hour. Integrating MW over elapsed hours would produce MWh; summing the load column alone is not labeled energy.

## Timestamp interpretation and UTC conversion

**Working interpretation: the source timestamp is the beginning of the hourly interval.** This interpretation is supported by two checks, rather than claimed as an explicit NYISO CSV-schema guarantee:

1. The GridStatus project's published implementation maps the hourly integrated-load dataset to a 60-minute interval beginning at the source timestamp. This is corroborating implementation evidence, not a NYISO-issued specification.
2. A direct numerical cross-check compares January 15 hourly values against arithmetic means of the official five-minute load sample. All hypotheses use the same 23 source labels, 01:00–23:00, with auxiliary coverage for each shifted interval.

| Interpretation of hourly label H | Five-minute comparison bin | MAE against hourly integrated values, MW |
| --- | --- | ---: |
| Hour ending | H−1 hour through H | 170.18 |
| Hour beginning | H through H+1 hour | 19.45 |
| One hour later, negative control | H+1 through H+2 hours | 137.20 |

The hour-beginning result supports the working alignment. It is not an exact reconstruction of NYISO's integration: the auxiliary records include irregular dispatch points, with 12–14 records per compared bin, and the diagnostic uses an unweighted arithmetic mean. The remaining difference is not interpreted as a target-data defect.

The parser preserves original timestamp/zone labels, maps `EST` to UTC−05:00 and `EDT` to UTC−04:00, and checks the resulting local clock and offset against `America/New_York`. It rejects unknown or inconsistent labels. Interval end is start plus one **elapsed** UTC hour.

Examples:

| Original source start | UTC start | UTC end |
| --- | --- | --- |
| March 10, 01:00 EST | March 10, 06:00 UTC | March 10, 07:00 UTC |
| March 10, 03:00 EDT | March 10, 07:00 UTC | March 10, 08:00 UTC |
| November 3, 01:00 EDT | November 3, 05:00 UTC | November 3, 06:00 UTC |
| November 3, 01:00 EST | November 3, 06:00 UTC | November 3, 07:00 UTC |

The hour-start interpretation is recorded explicitly in the Silver output. Retain the ability to amend it if a more explicit provider specification becomes available. No forecasting lags or joined weather features are approved by this audit.

## Pilot completeness and DST findings

Dates below refer to source interval starts in NYC local time.

| Pilot window | Local dates, inclusive | Hours | Missing UTC hours | Duplicate UTC intervals | Missing load values |
| --- | --- | ---: | ---: | ---: | ---: |
| Winter inspection | January 15–21 | 168 | 0 | 0 | 0 |
| Spring DST | March 9–11 | 71 | 0 | 0 | 0 |
| Fall DST | November 2–4 | 73 | 0 | 0 | 0 |

- March 10 contains 23 NYC rows: no nonexistent 02:00 local start was inserted.
- November 3 contains 25 NYC rows: both 01:00 starts were retained, distinguished by `EDT` and `EST`.
- A naïve local-time key would mark the fall-back pair as duplicates. The correct zone-plus-UTC key is unique.
- Across the three full monthly files, source-required fields contain no nulls and zone-plus-UTC keys have no duplicates.
- Across the 312 selected pilot targets, there are no nonfinite, missing, zero, or negative load values. No observations were imputed or removed.
- Complete coverage of these months does not establish complete eight-year coverage.

The January window includes Martin Luther King Jr. Day on January 15. Retain the requested dates as a winter inspection window, but do not call the entire week an ordinary nonholiday baseline. This pilot also does not establish that its weather was climatologically normal.

## Load plots and value ranges

| Window | Minimum MW | Maximum MW | Mean MW |
| --- | ---: | ---: | ---: |
| Winter | 4,697.48 | 7,199.59 | 6,109.02 |
| Spring DST | 4,172.31 | 5,963.10 | 5,064.07 |
| Fall DST | 3,793.71 | 5,826.40 | 4,665.19 |

![Zone J hourly integrated load for the three pilot windows](../outputs/data_audit/nyiso_pilot/zone_j_load_pilot.png)

The plots use separate panels and a common MW scale. They do not connect the absent months. The rendered PNG was inspected for readable labels and visible data. Daily load cycles are visible without an obvious discontinuity caused by losing the repeated fall hour. Visual plausibility does not independently verify physical measurement accuracy.

The plot and detailed CSV/JSON outputs are generated locally and ignored by Git. A cloned repository can recreate them from the acquisition and audit commands below.

## Publication, revisions, and remaining limits

NYISO's Market Participants User's Guide describes this as time-weighted hourly zonal load posted after each hour. That does not establish a fixed minute-level release delay, nor when every historical revision became available.

The downloaded archives are the versions served on the retrieval date. Their CSVs do not contain per-row first-publication times or revision histories. HTTP last-modified headers and archive-list update timestamps are not substitutes for those histories. The audit therefore leaves `load_publication_delay_hours` unresolved and does not create `available_at_utc` values.

Before feature engineering, document an evidence-based or explicitly assumed conservative load delay and disclose the use of revised historical predictor values if original vintages cannot be recovered. Final retrieved load can be evaluated as a target without pretending it was the exact predictor history available operationally in 2024.

The audit does not establish settlement-quality accuracy or unrestricted redistribution rights. Keep raw downloads out of Git and review NYISO's terms before public data redistribution. No new full-history acquisition is implied by this pilot.

## Reproduce and inspect

Run in Mac Terminal from the project root:

```bash
uv sync --locked --python 3.12
uv run python scripts/acquire_nyiso_pilot.py
uv run python scripts/acquire_nyiso_timing_check.py
uv run python scripts/audit_nyiso_pilot.py
uv run pytest
```

Downloads require network access on first run. Cached reruns verify existing original bytes and lineage. The offline audit checks archive/member hashes, source schema, timezone consistency, target completeness, numerical validity, zone identity, and the auxiliary alignment comparison. Tests use small invented rows for the strict parser, including both DST transitions and rejection of inconsistent offsets and duplicates.

Primary outputs:

- `data/silver/nyiso/zone_j_load_pilot_2024.parquet` and `.csv`: 312 pilot rows, with source fields and lineage.
- `outputs/data_audit/nyiso_pilot/audit_summary.json`: machine-readable audit results and Silver file hash.
- `monthly_counts.csv`, `daily_counts.csv`, `window_summary.csv`, `dst_transition_rows.csv`, and `interval_alignment_check.csv` in the same audit directory.
- `zone_j_load_pilot.png` and `.svg` in the same audit directory.

## Evidence references

- [NYISO P-58C official archive index](https://mis.nyiso.com/public/P-58Clist.htm) and exact original archive URLs in the manifest: product identity and downloaded observations.
- [NYISO zone mapping](https://www.nyiso.com/documents/20142/2216170/VirtualBidPriceDifferentialMatrix.pdf/93600218-f82a-b533-9b7e-f561255e3ebe): N.Y.C., Zone J, PTID 61761.
- [NYISO Market Participants User's Guide, section 5.6.2](https://www.nyiso.com/documents/20142/3625950/mpug.pdf): hourly integrated product and posting description. The official PDF endpoint presented a robot-check page during this audit; the relevant passage was available through the official-domain search index. No full PDF was archived or represented as fully inspected.
- [GridStatus source implementation](https://opensource.gridstatus.io/en/latest/_modules/gridstatus/nyiso.html): supporting hour-start interpretation and explicit timezone handling. This is an implementation reference, not provider certification.

## Stage 4 disposition

The requested pilot acquisition and structural/DST audit are complete. The working hour-start interpretation has empirical and implementation support, with its evidentiary limit preserved. Exact historical publication delays, revision vintages, and redistribution terms remain open; these must not be treated as resolved before operational feature construction or public raw-data distribution.
