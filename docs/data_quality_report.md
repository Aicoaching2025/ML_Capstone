# Data quality report

## Setup status

Only a synthetic 48-row fixture has been prepared. Real NYISO and NOAA data have not been acquired or audited.

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
