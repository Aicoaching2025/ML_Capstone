# Platform setup and verification

## What is ready and what remains

The local environment and smoke pipeline can be run now. Git is initialized, but no remote was configured when setup began. GitHub publishing and the Databricks smoke run are not verified until the steps below succeed. No GitHub token, Databricks credential, paid plan, cloud account, or weather subscription is needed for the local checks.

## Run the local verification

Open Terminal and run:

```bash
cd /Users/candace/Documents/ChatGPT/ML_Capstone
uv sync --locked --python 3.12uv
uv run pytest
uv run python scripts/local_smoke.py
```

Expected: four tests pass, then a JSON record with `status: passed`, 48 rows, total load 295200.0 MW (a diagnostic sum, not energy), mean load 6150.0 MW, and maximum 7300.0 MW. The generated evidence records actual package versions. No remote HTTP request occurs in this smoke test.

## Publish to GitHub

Use your own GitHub account. Starting private is recommended while you review course and data-sharing requirements; the final proposal calls for a public reproducibility repository later.

1. Sign in to [GitHub](https://github.com/).
2. Select the **+** menu in the upper-right corner, then **New repository**.
3. Choose your personal account as Owner. Enter `ML_Capstone` as Repository name.
4. Enter a description such as `NYC Zone J electricity load forecasting research for DATA 698`.
5. Select **Private** for initial development.
6. Leave **Add a README**, **Add .gitignore**, and **Choose a license** unselected. These options must not create an extra initial commit in this workflow.
7. Click **Create repository**.
8. Copy the HTTPS repository URL shown on the empty repository page.
9. In Terminal, inspect and commit the local project:

```bash
cd /Users/candace/Documents/ChatGPT/ML_Capstone
git status --short
git add .gitignore .python-version README.md pyproject.toml uv.lock configs docs src notebooks tests scripts .github data/bronze/.gitkeep data/silver/.gitkeep data/manifests/.gitkeep outputs/data_audit/.gitkeep
git diff --cached --stat
git diff --cached --check
git diff --cached
```

Review the staged content. It should contain the synthetic fixture, not real source data or credentials. Then:

```bash
git commit -m "Set up reproducible capstone environment and smoke checks"
git branch -M main
```

If Git requests an identity, set repository-local values, replacing the examples with your name and your GitHub no-reply address from **GitHub Settings → Emails**:

```bash
git config user.name "YOUR NAME"
git config user.email "YOUR GITHUB NO-REPLY EMAIL"
```

Retry the commit if it previously failed. To connect and publish, replace `YOUR_USERNAME` below:

```bash
git remote add origin https://github.com/YOUR_USERNAME/ML_Capstone.git
git push -u origin main
```

If `origin` already exists, inspect `git remote -v` and use the existing correct remote rather than adding another. GitHub does not accept your account password for Git-over-HTTPS. If authentication fails, use GitHub Desktop as described below; do not paste a token into chat or embed one in the remote URL.

10. Refresh the repository page. Confirm the README, `uv.lock`, contract, and notebook are present; `.venv` and generated Parquet should be absent.
11. Open **Actions → Local reproducibility checks**. Confirm the latest run is green. If workflows are disabled by policy, record that limitation rather than treating them as passed.

### GitHub Desktop alternative

If Terminal authentication is unfamiliar, install [GitHub Desktop](https://desktop.github.com/) from the official site, sign in, then choose **File → Add Local Repository** and select this project folder. Review Changes, create the initial commit if needed, and select **Publish repository** with **Keep this code private** checked. If you already created the empty remote, use **Repository → Repository Settings → Remote** to set its URL and push. Do not create a second unrelated repository or copy data into a new folder.

Official reference: [Adding locally hosted code to GitHub](https://docs.github.com/en/migrations/importing-source-code/using-the-command-line-to-import-source-code/adding-locally-hosted-code-to-github).

## Run the Databricks Free Edition smoke test

### Create or open the workspace

1. Open the [Databricks Free Edition page](https://www.databricks.com/learn/free-edition).
2. Choose **Get started** or the Free Edition signup link. Use Free Edition, not a paid cloud trial.
3. Sign in or complete the account flow yourself, including any verification and terms acceptance.
4. Open the workspace. No AWS/Azure/GCP account is required for this managed Free Edition workflow.

Reference: [Free Edition signup documentation](https://docs.databricks.com/aws/en/getting-started/free-edition).

### Import and initialize the notebook

1. In the left sidebar, open **Workspace** and your user folder.
2. Create a folder named `ML_Capstone` if desired.
3. Open the folder menu and choose **Import**. Select **File** and upload `notebooks/00_databricks_smoke.ipynb` from this project.
4. Open the imported notebook and select available **Serverless** compute.
5. Run the first code cell only. It determines the current catalog and creates the dedicated `ml_capstone_setup` schema and `smoke_files` volume.
6. If the current catalog is not writable, use **Catalog** to identify a catalog where your account can create a schema. Set `CATALOG` in the notebook to that exact name and rerun the cell. Do not change permissions or move to a paid workspace to bypass the issue.
7. Record the printed path, which has this form:

```text
/Volumes/YOUR_CATALOG/ml_capstone_setup/smoke_files
```

### Upload the shared sample

1. Open **Catalog** in the sidebar.
2. Expand the catalog printed by the notebook, then `ml_capstone_setup`.
3. Open **Volumes → smoke_files**.
4. Choose **Upload** or **Upload to this volume**.
5. Upload both files directly into the volume root:
   - `tests/fixtures/synthetic_zone_j_hourly.csv`
   - `tests/fixtures/expected_smoke.json`
6. Confirm both filenames appear. Do not use legacy DBFS root instructions or upload real research data for this check.

Reference: [Work with files in Unity Catalog volumes](https://docs.databricks.com/aws/en/volumes/volume-files).

### Run Delta, transformation, and MLflow checks

1. Return to the notebook and run the remaining cells in order.
2. The notebook verifies the exact uploaded CSV hash, UTC intervals, repeated DST hour, and expected values.
3. It creates and reads the Delta table `YOUR_CATALOG.ml_capstone_setup.synthetic_zone_j_smoke`.
4. It adds `load_gw = load_mw / 1000` and verifies the Delta readback.
5. It logs a run named `synthetic_setup_smoke` to the notebook's MLflow experiment, including metrics, fixture hash, summary artifact, and runtime versions.
6. It retrieves the logged run and downloads its summary artifact to verify that tracking works.
7. Confirm the final output says `status: passed` and includes a run ID and Delta table name.
8. Open the notebook's **Experiments** panel or linked experiment. Confirm the run and its `smoke_summary.json` and `runtime.json` artifacts exist.

The notebook overwrites only its dedicated synthetic setup table on reruns. It does not overwrite research tables. Its runtime is managed by Databricks; record the logged versions instead of assuming they match the local lockfile.

Reference: [MLflow notebook experiments](https://docs.databricks.com/aws/en/mlflow/experiments).

### Export code and results

1. Use the notebook **File → Export** menu (or notebook menu → Export) and choose **IPython notebook (.ipynb)**. Include outputs if the interface offers that option.
2. Save it locally as `outputs/data_audit/databricks_smoke_executed.ipynb`.
3. Return to **Catalog → YOUR_CATALOG → ml_capstone_setup → Volumes → smoke_files**.
4. Download `databricks_smoke.json` and `databricks_smoke_result.csv` into the local `outputs/data_audit/` folder.
5. Run:

```bash
cd /Users/candace/Documents/ChatGPT/ML_Capstone
uv run python scripts/verify_databricks_export.py outputs/data_audit/databricks_smoke.json outputs/data_audit/databricks_smoke_result.csv
```

Expected: `PASS: downloaded Databricks evidence and transformed rows match the local fixture.`

6. Confirm the exported notebook opens locally as a nonempty file. For a structural check:

```bash
uv run python -c 'import json; from pathlib import Path; n=json.loads(Path("outputs/data_audit/databricks_smoke_executed.ipynb").read_text()); assert n["nbformat"] == 4 and n["cells"]; print("Notebook export readable")'
```

7. Record the run ID, execution time, workspace/catalog, and verification outcome in `docs/data_quality_report.md`. Keep generated exports out of Git; their directory is already ignored.

Reference: [Import and export notebooks](https://docs.databricks.com/aws/en/notebooks/notebook-export-import).

## Local-download fallback for future source data

If a source domain is blocked in Free Edition, download locally using the reviewed acquisition script, preserve the original file in Bronze, record URL/retrieval time/hash in a manifest, validate and extract a compact file locally, upload that extract into a managed volume, and record the source-to-extract lineage. Uploading a file does not establish historical availability. No source downloader has been implemented yet because source endpoints and timing semantics remain unaudited.

## Completion checklist

- [ ] Local locked installation succeeds on the intended machine.
- [ ] Four validation tests and local smoke test pass.
- [ ] GitHub repository contains reviewed code/configuration/fixtures and has no raw data or secrets.
- [ ] GitHub Actions passes, or a concrete policy limitation is recorded.
- [ ] Databricks reads the identical hashed sample.
- [ ] Delta write/read and MW-to-GW transformation pass.
- [ ] MLflow run and artifacts are visible and retrievable.
- [ ] Notebook and evidence files are downloaded successfully.
- [ ] The local export verifier confirms matching transformed rows.

Step 2 is fully complete only after local and remote checks succeed. Do not mark the Databricks boxes based solely on the prepared notebook.
