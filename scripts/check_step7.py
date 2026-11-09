"""Step 7 'Done when' check: every expected file exists, is valid, and has a matching manifest row.

Run from the repository root:  uv run python scripts/check_step7.py
"""
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from acquisition.download import (ROOT, months, read_manifest, sha256, valid_lcd_csv,  # noqa: E402
                                  valid_openmeteo_json, valid_zip)

src = yaml.safe_load((ROOT / "configs/sources.yaml").read_text())
obs, load, fc, om = src["observations"], src["load"], src["nyiso_forecast"], src["forecast_weather"]
groups = {
    "NOAA LCD v2": ([ROOT / f"data/bronze/noaa/lcdv2/LCD_{s}_{y}.csv" for s in obs["station_identifiers"].values()
                     for y in range(obs["full_history_years"][0], obs["full_history_years"][1] + 1)], valid_lcd_csv),
    "NYISO load": ([ROOT / f"data/bronze/nyiso/integrated_load/{m}01palIntegrated_csv.zip"
                    for m in months(*load["full_history_months"])], valid_zip),
    "NYISO forecast": ([ROOT / f"data/bronze/nyiso/isolf/{m}01isolf_csv.zip" for m in months(*fc["period"])], valid_zip),
    "Open-Meteo": ([ROOT / f"data/bronze/openmeteo/previous_runs/gfs_previous_day2_central_park_{y}.json"
                    for y in range(int(om["period"][0][:4]), int(om["period"][1][:4]) + 1)], valid_openmeteo_json),
}
manifest = {(r["local_filename"], r["file_hash_sha256"]) for r in read_manifest()}
ok = True
total_bytes = 0
for name, (paths, validate) in groups.items():
    missing = [p.name for p in paths if not p.exists()]
    invalid = [p.name for p in paths if p.exists() and not validate(p)]
    unlisted = [p.name for p in paths if p.exists() and (str(p.relative_to(ROOT)), sha256(p)) not in manifest]
    size = sum(p.stat().st_size for p in paths if p.exists())
    total_bytes += size
    status = "OK " if not (missing or invalid or unlisted) else "FIX"
    ok &= status == "OK "
    print(f"{status} {name:15s} {len(paths) - len(missing):3d}/{len(paths)} files, {size / 1e6:7.1f} MB"
          + (f" | missing {missing}" if missing else "") + (f" | invalid {invalid}" if invalid else "")
          + (f" | not in manifest {unlisted}" if unlisted else ""))
print(f"\nTotal {total_bytes / 1e6:.0f} MB. " + ("Step 7 data complete." if ok else "Rerun the acquire script(s) for groups marked FIX."))
sys.exit(0 if ok else 1)
