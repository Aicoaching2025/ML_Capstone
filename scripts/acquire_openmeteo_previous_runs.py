"""Step 7: Open-Meteo Previous Runs API, GFS previous_day2 forecasts for Central Park, 2024-2025.

Run from the repository root:  uv run python scripts/acquire_openmeteo_previous_runs.py
One request per year (2 total) keeps well under the free rate limit. Raw JSON is saved unchanged.
"""
import sys
import time
from pathlib import Path
from urllib.parse import urlencode

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from acquisition.download import ROOT, NotFound, fetch, record, valid_openmeteo_json  # noqa: E402

cfg = yaml.safe_load((ROOT / "configs/sources.yaml").read_text())["forecast_weather"]
out = ROOT / "data/bronze/openmeteo/previous_runs"
first, last = cfg["period"]
failed = []
for year in range(int(first[:4]), int(last[:4]) + 1):
    start, end = max(first, f"{year}-01-01"), min(last, f"{year}-12-31")
    params = {"latitude": cfg["location"]["latitude"], "longitude": cfg["location"]["longitude"],
              "start_date": start, "end_date": end, "hourly": ",".join(cfg["variables"]),
              "models": cfg["model"], "timezone": cfg["timezone"]}
    url = f"{cfg['endpoint']}?{urlencode(params)}"
    dest = out / f"gfs_previous_day2_central_park_{year}.json"
    try:
        meta = fetch(url, dest, valid_openmeteo_json, resumable=False)
    except (NotFound, RuntimeError) as e:
        print(f"FAILED {dest.name}: {e}"); failed.append(dest.name); continue
    record(dest, meta, source_product="Open-Meteo Previous Runs API", requested_period=f"{start}..{end}",
           station_or_zone=cfg["location"]["name"], provider="Open-Meteo", model=cfg["model"],
           notes="previous_day2 = predicted 48 h before valid time; raw JSON; CC BY 4.0")
    print(("skip " if meta["skipped"] else "got  ") + dest.name)
    if not meta["skipped"]:
        time.sleep(2)
print(f"\nOpen-Meteo done. Failed: {len(failed)}" + (f" -> rerun to retry: {failed}" if failed else ""))
sys.exit(1 if failed else 0)
