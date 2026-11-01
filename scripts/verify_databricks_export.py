"""Verify downloaded remote evidence without claiming it has already run."""
import argparse
import json
from pathlib import Path
import pandas as pd
from validation.sample import validate_sample

parser = argparse.ArgumentParser()
parser.add_argument("evidence", type=Path)
parser.add_argument("results", type=Path)
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
expected = json.loads((root / "tests/fixtures/expected_smoke.json").read_text())
evidence = json.loads(args.evidence.read_text())
assert all(evidence.get(key) == value for key, value in expected.items())
assert evidence["status"] == "passed"
assert evidence["mlflow_run_id"] and evidence["delta_table"]
remote = pd.read_csv(args.results)
# Spark exports timestamps with an explicit offset instead of the fixture's Z.
for field in ["interval_start_utc", "interval_end_utc"]:
    remote[field] = pd.to_datetime(remote[field], utc=True).dt.strftime("%Y-%m-%dT%H:%M:%SZ")
remote = validate_sample(remote)
local = validate_sample(pd.read_csv(root / "tests/fixtures/synthetic_zone_j_hourly.csv"))
local["load_gw"] = local.load_mw / 1000
pd.testing.assert_frame_equal(remote[local.columns], local, check_dtype=False)
print("PASS: downloaded Databricks evidence and transformed rows match the local fixture.")
