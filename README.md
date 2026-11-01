# NYC electricity load forecasting capstone

Candace Grant · DATA 698 · Fall 2026

This project studies NYISO Zone J hourly electricity demand at rolling 1-hour and 24-hour horizons. The horizon is measured from issuance to the **end** of the target interval. See [the research contract](docs/research_contract.md).

## Current status

The local project scaffold, dependency lockfile, synthetic sample, validation checks, and Databricks smoke notebook are prepared. Real data acquisition and forecasting experiments have not begun. Databricks execution and GitHub publication require separate verification; local success does not imply remote success.

## Local setup

Install uv from its [official installation instructions](https://docs.astral.sh/uv/getting-started/installation/). Git and Python 3.12 are already available on the original development Mac. On a new machine, uv can provision Python 3.12 if needed.

```bash
cd /Users/candace/Documents/ChatGPT/ML_Capstone
uv sync --locked --python 3.12
uv run pytest
uv run python scripts/local_smoke.py
```

For a cloned copy, change into that clone's directory instead. `uv sync` creates `.venv`; activation is unnecessary with `uv run`. Commit `uv.lock` so others install the resolved versions. The lockfile controls the local environment, not the managed Databricks runtime.

The local smoke test reads the 48-row **synthetic** fixture, validates hourly UTC intervals, converts MW to GW, writes/reads Parquet, and checks expected summary values. Results appear in `outputs/data_audit/local_smoke.json`; generated Parquet appears in `data/silver/synthetic_smoke.parquet`. Both outputs are ignored by Git.

See [the exact platform setup guide](docs/platform_setup.md) for GitHub, Databricks upload/Delta/MLflow/export steps, troubleshooting, and completion evidence.

## Organization

- `configs/`: study parameters and unresolved source-audit decisions.
- `docs/`: research contract, data dictionary, quality report, decisions, setup instructions.
- `src/acquisition/`, `src/cleaning/`, `src/validation/`: reusable Python code. Production acquisition and cleaning await source audit.
- `notebooks/`: platform smoke notebook and future explanatory notebooks.
- `tests/fixtures/`: small, invented setup data safe to commit.
- `data/bronze/`, `data/silver/`: raw and cleaned data, excluded from Git.
- `data/manifests/`: reviewed provenance metadata; do not place secrets or signed URLs here.
- `outputs/data_audit/`: generated audit evidence, excluded from Git.
- `scripts/`: local smoke test and remote export verifier.

## Data and credentials

Do not commit real raw data, credentials, `.env` files, private keys, or large outputs. `.gitignore` covers normal locations but does not inspect arbitrary file content. Review `git diff --cached` before committing. Source configurations deliberately contain no credentials and do not assume unverified archive availability.

The fixture is not NYISO or NOAA data and supports no research conclusions. No software license has been selected yet; choose one before inviting external reuse.
