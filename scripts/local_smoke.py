"""Run from the repository root: uv run python scripts/local_smoke.py."""
from pathlib import Path
import hashlib
import json
import platform
from datetime import datetime, timezone
import importlib.metadata
import httpx
import pandas as pd
import yaml
from validation.sample import validate_sample

root = Path(__file__).resolve().parents[1]
source = root / "tests/fixtures/synthetic_zone_j_hourly.csv"
frame = validate_sample(pd.read_csv(source))
frame["load_gw"] = frame.load_mw / 1000
output = root / "data/silver/synthetic_smoke.parquet"
output.parent.mkdir(parents=True, exist_ok=True)
frame.to_parquet(output, index=False)
pd.testing.assert_frame_equal(frame, pd.read_parquet(output))
with (root / "configs/study.yaml").open() as handle:
    assert yaml.safe_load(handle)["horizon_anchor"] == "target_interval_end"
with httpx.Client(timeout=10) as client:
    assert client.timeout.connect == 10  # No external request needed for setup.
summary = {
    "fixture": "synthetic, not research data",
    "rows": len(frame),
    "total_load_mw": float(frame.load_mw.sum()),
    "mean_load_mw": float(frame.load_mw.mean()),
    "max_load_mw": float(frame.load_mw.max()),
    "sample_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
}
expected = json.loads((root / "tests/fixtures/expected_smoke.json").read_text())
assert summary == expected, (summary, expected)
evidence = {**summary, "status": "passed", "executed_at_utc": datetime.now(timezone.utc).isoformat(),
            "python": platform.python_version(),
            "packages": {name: importlib.metadata.version(name) for name in
                         ["pandas", "numpy", "pyarrow", "httpx", "pytest", "PyYAML"]}}
destination = root / "outputs/data_audit/local_smoke.json"
destination.parent.mkdir(parents=True, exist_ok=True)
destination.write_text(json.dumps(evidence, indent=2) + "\n")
print(json.dumps(evidence, indent=2))
