"""Step 7: NYISO ISO Load Forecast (P-7, isolf) monthly ZIPs, 2017-12 to 2025-12.

Run from the repository root:  uv run python scripts/acquire_nyiso_forecast.py
Safe to rerun: valid ZIPs are skipped.
"""
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from acquisition.download import ROOT, NotFound, fetch, months, record, valid_zip  # noqa: E402

cfg = yaml.safe_load((ROOT / "configs/sources.yaml").read_text())["nyiso_forecast"]
out = ROOT / "data/bronze/nyiso/isolf"
failed = []
for yyyymm in months(*cfg["period"]):
    url = cfg["archive_url_template"].format(yyyymm=yyyymm)
    dest = out / url.rsplit("/", 1)[1]
    try:
        meta = fetch(url, dest, valid_zip, resumable=False)
    except (NotFound, RuntimeError) as e:
        print(f"FAILED {dest.name}: {e}"); failed.append(dest.name); continue
    record(dest, meta, source_product="ISO Load Forecast (P-7)", requested_period=f"{yyyymm[:4]}-{yyyymm[4:]}",
           station_or_zone="All zones; N.Y.C. column used", provider="NYISO",
           notes="Daily forecast files bundled monthly; 24-hour benchmark only")
    print(("skip " if meta["skipped"] else "got  ") + dest.name)
print(f"\nNYISO forecast done. Failed: {len(failed)}" + (f" -> rerun to retry: {failed}" if failed else ""))
sys.exit(1 if failed else 0)
