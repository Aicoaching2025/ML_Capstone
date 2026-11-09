"""Step 7: NOAA LCD v2 per-station-year CSVs (about 8-9 MB each) for 2017-2025.

Run from the repository root:  uv run python scripts/acquire_noaa_lcd.py
Safe to rerun: valid files are skipped and partial downloads resume.
"""
import argparse
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from acquisition.download import ROOT, NotFound, fetch, record, valid_lcd_csv  # noqa: E402

cfg = yaml.safe_load((ROOT / "configs/sources.yaml").read_text())["observations"]
names = {v: k for k, v in cfg["station_identifiers"].items()}
ap = argparse.ArgumentParser()
ap.add_argument("--years", default="{}-{}".format(*cfg["full_history_years"]))
ap.add_argument("--out", default="data/bronze/noaa/lcdv2")
a = ap.parse_args()
y0, y1 = (int(x) for x in (a.years.split("-") if "-" in a.years else [a.years] * 2))
out = ROOT / a.out
failed = []
for station in names:
    for year in range(y0, y1 + 1):
        url = cfg["station_year_url_template"].format(yyyy=year, station=station)
        dest = out / f"LCD_{station}_{year}.csv"
        try:
            meta = fetch(url, dest, valid_lcd_csv)
        except (NotFound, RuntimeError) as e:
            print(f"FAILED {dest.name}: {e}"); failed.append(dest.name); continue
        record(dest, meta, source_product="NOAA LCD v2 station-year CSV", requested_period=year,
               station_or_zone=station, provider="NOAA NCEI",
               notes=f"{names[station]}; per-station-year file, not bulk archive")
        print(("skip " if meta["skipped"] else "got  ") + dest.name)
print(f"\nNOAA done. Failed: {len(failed)}" + (f" -> rerun to retry: {failed}" if failed else ""))
sys.exit(1 if failed else 0)
