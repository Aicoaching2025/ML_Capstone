"""Step 7: NYISO integrated real-time actual load (P-58C) monthly ZIPs, 2017-01 to 2025-12.

Run from the repository root:  uv run python scripts/acquire_nyiso_load.py
Safe to rerun: valid ZIPs (including the 2024 pilot months) are skipped.
"""
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from acquisition.download import ROOT, NotFound, fetch, months, record, valid_zip  # noqa: E402

cfg = yaml.safe_load((ROOT / "configs/sources.yaml").read_text())["load"]
out = ROOT / "data/bronze/nyiso/integrated_load"
failed = []
for yyyymm in months(*cfg["full_history_months"]):
    url = cfg["archive_url_template"].format(yyyymm=yyyymm)
    dest = out / url.rsplit("/", 1)[1]
    try:
        meta = fetch(url, dest, valid_zip, resumable=False)
    except (NotFound, RuntimeError) as e:
        print(f"FAILED {dest.name}: {e}"); failed.append(dest.name); continue
    record(dest, meta, source_product="Integrated Real-Time Actual Load (P-58C)",
           requested_period=f"{yyyymm[:4]}-{yyyymm[4:]}", station_or_zone="All source zones; N.Y.C. used",
           provider="NYISO", notes="Original monthly ZIP; current retrieved vintage, not first-publication vintage")
    print(("skip " if meta["skipped"] else "got  ") + dest.name)
print(f"\nNYISO load done. Failed: {len(failed)}" + (f" -> rerun to retry: {failed}" if failed else ""))
sys.exit(1 if failed else 0)
