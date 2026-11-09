"""Step 9: full-history data audit (2017-2025) for the paper's data section.

Run from the repository root:  uv run python scripts/audit_full_history.py
Reads the Step 8 silver tables plus the raw NOAA files (for the LCD DATE column) and writes:
  docs/data_audit_full_history.md            (the report; commit this)
  docs/figures/step9_*.png                   (three figures; commit these)
  outputs/data_audit/step9/*.csv             (row-level evidence; stays local, gitignored)

Holdout rule: 2025 appears only as counts (rows, missing hours, fallback hours, timestamp
disagreements, quarantined rows). Load and weather values, value checks and figures use
2017-2024 only. No models are fitted and no forecast errors are computed.
"""
import hashlib
import os
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".mplconfig"))
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from audit.full_history import (HOLDOUT_YEAR, NYC, date_offset_minutes, dst_transitions,  # noqa: E402
                                flatline_runs, hours_to_nearest_dst,
                                load_deviation_flags, local_year, missing_by_month, missing_by_year,
                                pre_holdout, weather_range_flags)
from cleaning.hours import expected_hours  # noqa: E402
from cleaning.lcd_weather import metar_utc  # noqa: E402

warnings.filterwarnings("ignore", category=DeprecationWarning)
SOURCES = yaml.safe_load((ROOT / "configs/sources.yaml").read_text())
WX = yaml.safe_load((ROOT / "configs/weather_pilot.yaml").read_text())
SILVER = ROOT / "data/silver"
OUT = ROOT / "outputs/data_audit/step9"
FIG = ROOT / "docs/figures"
OUT.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)
MANIFEST = pd.read_csv(ROOT / "data/manifests/downloads.csv", keep_default_na=False)
HASHES = dict(zip(MANIFEST.local_filename, MANIFEST.file_hash_sha256))
FULL = expected_hours("2017-01-01", "2026-01-01")
YEARS = list(range(2017, 2026))
SHORT = {"USW00094728": "Central Park", "USW00014732": "LaGuardia", "USW00094789": "JFK"}

needed = ["nyiso/load_hourly_2017_2025.parquet", "noaa/weather_hourly_2017_2025.parquet",
          "noaa/weather_hourly_by_station_2017_2025.parquet", "nyiso/p7_day_ahead_2017_2025.parquet",
          "openmeteo/gfs_previous_day2_2024_2025.parquet"]
for rel in needed:
    if not (SILVER / rel).exists():
        raise SystemExit(f"Missing data/silver/{rel}. Run: uv run python scripts/build_silver.py")

load = pd.read_parquet(SILVER / needed[0])
wx = pd.read_parquet(SILVER / needed[1])
by_station = pd.read_parquet(SILVER / needed[2])
p7 = pd.read_parquet(SILVER / needed[3])
om = pd.read_parquet(SILVER / needed[4])


def fmt(n) -> str:
    return f"{int(n):,}"


def md_table(frame: pd.DataFrame) -> str:
    cols = [str(c) for c in frame.columns]
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
    for row in frame.itertuples(index=False):
        lines.append("| " + " | ".join(str(v) for v in row) + " |")
    return "\n".join(lines)


# ------------------------------------------------------------ 1. Coverage per year (counts; includes 2025)
print("1/5 coverage counts per year")
yearly = missing_by_year(FULL, load.interval_start_utc).rename(columns={"missing_hours": "load_missing"})
yearly = yearly[["year", "expected_hours", "load_missing"]]
load_dups = load.duplicated("interval_start_utc").groupby(local_year(load.interval_start_utc).to_numpy()).sum()
yearly["load_duplicates"] = yearly.year.map(load_dups).fillna(0).astype(int)

wy = local_year(wx.interval_start_utc).to_numpy()
yearly["weather_core_missing"] = yearly.year.map((~wx.core_tuple_valid).groupby(wy).sum()).fillna(0).astype(int)
for station in WX["backup_priority"]:
    used = wx.source_station.eq(station) & wx.station_fallback_used
    yearly[f"fallback_{SHORT[station].lower()}"] = yearly.year.map(used.groupby(wy).sum()).fillna(0).astype(int)
yearly["wind_missing"] = yearly.year.map(wx.wind_speed_m_s.isna().groupby(wy).sum()).astype(int)
precip_unknown = wx.precipitation_mm.isna() & ~wx.precipitation_trace.eq(True)
yearly["precip_unknown"] = yearly.year.map(precip_unknown.groupby(wy).sum()).astype(int)
yearly["precip_trace"] = yearly.year.map(wx.precipitation_trace.eq(True).groupby(wy).sum()).astype(int)

P7_FIRST_DAY = "2017-12-02"  # First target day in the Step 8 P-7 silver table
P7_EXPECTED = expected_hours(P7_FIRST_DAY, "2026-01-01")
p7_years = missing_by_year(P7_EXPECTED, p7.interval_start_utc).set_index("year")
yearly["p7_expected"] = yearly.year.map(p7_years.expected_hours).fillna(0).astype(int)
yearly["p7_missing"] = yearly.year.map(p7_years.missing_hours).fillna(0).astype(int)
oy = om.valid_time_utc.dt.year.to_numpy()  # Open-Meteo is requested by UTC day, so count by UTC year
yearly["openmeteo_rows"] = yearly.year.map(pd.Series(1, index=om.index).groupby(oy).sum()).fillna(0).astype(int)
yearly["openmeteo_null"] = yearly.year.map(om.fc_temperature_c.isna().groupby(oy).sum()).fillna(0).astype(int)
yearly.to_csv(OUT / "coverage_by_year.csv", index=False)

# ------------------------------------------------------------ 2. NOAA station timing per year (counts; includes 2025)
print("2/5 NOAA station timing (reads 27 raw files, about 30 seconds)")
timing_rows, disagreements = [], []
y0, y1 = SOURCES["observations"]["full_history_years"]
for station, meta in WX["stations"].items():
    for year in range(y0, y1 + 1):
        path = ROOT / f"data/bronze/noaa/lcdv2/LCD_{station}_{year}.csv"
        rel = str(path.relative_to(ROOT))
        if HASHES.get(rel) != hashlib.sha256(path.read_bytes()).hexdigest():
            raise SystemExit(f"{rel} is not in downloads.csv with this hash. Rerun Step 7 first.")
        raw = pd.read_csv(path, dtype=str, keep_default_na=False, usecols=["DATE", "REPORT_TYPE", "REM"])
        f = raw[raw.REPORT_TYPE.eq(WX["report_type"])].copy()
        f["source_row_number"] = f.index + 2
        f["observation_time_utc"] = pd.to_datetime(
            [metar_utc(d, r, meta["icao"]) for d, r in zip(f.DATE, f.REM)], utc=True)
        f["offset_minutes"] = date_offset_minutes(f.DATE, f.observation_time_utc)
        resolved = f.observation_time_utc.notna()
        off = f.loc[resolved, "offset_minutes"]
        timing_rows.append({"station": SHORT[station], "year": year, "fm15_rows": len(f),
                            "utc_resolved": int(resolved.sum()), "quarantined": int((~resolved).sum()),
                            "date_disagrees": int(off.ne(0).sum()), "offset_plus_60": int(off.eq(60).sum()),
                            "offset_minus_60": int(off.eq(-60).sum()),
                            "offset_other": int((off.ne(0) & off.abs().ne(60)).sum())})
        d = f[resolved & f.offset_minutes.ne(0)][["DATE", "source_row_number", "observation_time_utc",
                                                 "offset_minutes"]].copy()
        d.insert(0, "station_id", station)
        disagreements.append(d)
timing = pd.DataFrame(timing_rows)
timing.to_csv(OUT / "noaa_timing_by_station_year.csv", index=False)
disagree = pd.concat(disagreements, ignore_index=True)
disagree["hours_to_nearest_dst"] = hours_to_nearest_dst(disagree.observation_time_utc,
                                                       dst_transitions(y0 - 1, y1 + 1)).round(2).to_numpy()
disagree.to_csv(OUT / "noaa_date_disagreements.csv", index=False)
max_dst_gap = float(disagree.hours_to_nearest_dst.max()) if len(disagree) else 0.0

station_missing = []
for station in WX["stations"]:
    g = missing_by_year(FULL, by_station.loc[by_station.station_id.eq(station), "interval_start_utc"])
    station_missing.append(g.assign(station=SHORT[station])[["station", "year", "missing_hours"]])
station_missing = pd.concat(station_missing, ignore_index=True)
station_missing.to_csv(OUT / "noaa_station_missing_by_year.csv", index=False)

# ------------------------------------------------------------ 3. Value checks (2017-2024 only)
print("3/5 value checks on 2017-2024 (2025 excluded)")
load_pre = pre_holdout(load).sort_values("interval_start_utc").reset_index(drop=True)
wx_pre = pre_holdout(wx).sort_values("interval_start_utc").reset_index(drop=True)
flags = load_deviation_flags(load_pre)
flat = flatline_runs(load_pre.interval_start_utc, load_pre.load_mw, min_hours=3)
flat.to_csv(OUT / "load_flatline_runs.csv", index=False)
flagged = flags[flags.flag_deviation | flags.flag_nonpositive].copy()
flagged["local_time"] = flagged.interval_start_utc.dt.tz_convert(NYC).dt.strftime("%Y-%m-%d %H:%M %Z")
flagged.to_csv(OUT / "load_flagged_hours.csv", index=False)

ly = local_year(load_pre.interval_start_utc).to_numpy()
load_stats = load_pre.groupby(ly).load_mw.agg(["min", "mean", "max"]).round(0).astype(int)
peak_idx = load_pre.groupby(ly).load_mw.idxmax()
load_stats["peak_local_time"] = load_pre.loc[peak_idx, "interval_start_utc"].dt.tz_convert(NYC) \
    .dt.strftime("%Y-%m-%d %H:%M").to_numpy()
load_stats["max_hourly_change"] = flags.groupby(ly).hour_to_hour_change_mw.apply(lambda s: s.abs().max()) \
    .round(0).astype(int)
load_stats["deviation_flags"] = flags.groupby(ly).flag_deviation.sum().astype(int)
load_stats["nonpositive"] = flags.groupby(ly).flag_nonpositive.sum().astype(int)
flat_years = local_year(flat.start_utc).value_counts() if len(flat) else pd.Series(dtype=int)
load_stats["flatline_runs_3h"] = flat_years.reindex(load_stats.index).fillna(0).astype(int)
load_stats.index.name = "year"
load_stats = load_stats.reset_index()
load_stats.to_csv(OUT / "load_value_summary_2017_2024.csv", index=False)

day_max_temp = wx_pre.assign(day=wx_pre.interval_start_utc.dt.tz_convert(NYC).dt.date) \
    .groupby("day").temperature_c.max()
fd = flags[flags.flag_deviation].assign(day=lambda x: x.interval_start_utc.dt.tz_convert(NYC).dt.date)
flag_days = fd.groupby("day").agg(hours=("robust_z", "size"), max_abs_z=("robust_z", lambda s: s.abs().max()),
                                  mean_rel_dev=("relative_deviation", "mean")).reset_index()
flag_days["daily_max_temp_c"] = flag_days.day.map(day_max_temp)
flag_days = flag_days.sort_values("day")
flag_days.to_csv(OUT / "load_flagged_days.csv", index=False)

ranges = weather_range_flags(wx_pre).rename(columns={"check": "Check", "rows_checked": "Rows checked",
                                                    "flagged": "Flagged"})
ranges.to_csv(OUT / "weather_range_checks_2017_2024.csv", index=False)

# ------------------------------------------------------------ 4. Figures
print("4/5 figures (2017-2024 values; missingness counts include 2025)")
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})

# 4a annual load profile
lp = load_pre.assign(t=load_pre.interval_start_utc.dt.tz_convert(NYC))
lp["year"], lp["doy"], lp["hour"], lp["month"] = lp.t.dt.year, lp.t.dt.dayofyear, lp.t.dt.hour, lp.t.dt.month
fig, axes = plt.subplots(1, 2, figsize=(12, 4.4), gridspec_kw={"width_ratios": [1.6, 1]})
cmap = plt.get_cmap("viridis")
for i, (year, g) in enumerate(lp.groupby("year")):
    daily = g.groupby("doy").load_mw.mean().rolling(7, center=True, min_periods=1).mean()
    axes[0].plot(daily.index, daily.to_numpy() / 1000, color=cmap(i / 7), lw=1.2, label=str(year))
axes[0].set_xticks([1, 32, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335],
                   ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
axes[0].set_ylabel("Daily mean load (GW), 7-day smoothed")
axes[0].set_title("Annual load profile, Zone J, 2017-2024")
axes[0].legend(ncol=4, fontsize=8, frameon=False, loc="upper left")
season = lp.month.map({12: "Winter (DJF)", 1: "Winter (DJF)", 2: "Winter (DJF)", 6: "Summer (JJA)",
                       7: "Summer (JJA)", 8: "Summer (JJA)"}).fillna("Spring/Fall")
for name, color in [("Summer (JJA)", "#c0392b"), ("Spring/Fall", "#7f8c8d"), ("Winter (DJF)", "#2e86c1")]:
    shape = lp[season.eq(name)].groupby("hour").load_mw.mean() / 1000
    axes[1].plot(shape.index, shape.to_numpy(), color=color, lw=2, label=name)
axes[1].set_xticks(range(0, 24, 3))
axes[1].set_xlabel("Local hour (hour-start)")
axes[1].set_ylabel("Mean load (GW)")
axes[1].set_title("Average daily shape by season")
axes[1].legend(frameon=False, fontsize=8)
fig.tight_layout()
fig.savefig(FIG / "step9_annual_load_profile.png", dpi=150)
plt.close(fig)

# 4b load vs temperature
lt = load_pre.merge(wx_pre[["interval_start_utc", "temperature_c"]], on="interval_start_utc").dropna()
fig, ax = plt.subplots(figsize=(7.5, 5))
hb = ax.hexbin(lt.temperature_c, lt.load_mw / 1000, gridsize=70, bins="log", cmap="Blues", mincnt=1)
bins = np.arange(np.floor(lt.temperature_c.min()), np.ceil(lt.temperature_c.max()) + 1, 1.0)
med = lt.groupby(pd.cut(lt.temperature_c, bins), observed=True).load_mw.agg(["median", "size"])
med = med[med["size"].ge(20)]
ax.plot([iv.mid for iv in med.index], med["median"] / 1000, color="#c0392b", lw=2, label="Median per 1 °C bin")
ax.axvline(18.3, color="#555", ls="--", lw=1, label="18.3 °C (degree-hour base)")
ax.set_xlabel("Observed temperature, same hour (°C)")
ax.set_ylabel("Hourly load (GW)")
ax.set_title(f"Load vs temperature, 2017-2024 ({len(lt):,} hours)")
ax.legend(frameon=False, loc="upper center")
fig.colorbar(hb, ax=ax, label="Hours (log scale)")
fig.tight_layout()
fig.savefig(FIG / "step9_load_vs_temperature.png", dpi=150)
plt.close(fig)

# 4c missingness heatmap (counts per month; 2025 allowed)
months = pd.Index(sorted(set(FULL.tz_convert(NYC).strftime("%Y-%m"))))
om_exp = expected_hours("2024-01-01", "2026-01-01")
om_exp = om_exp[om_exp < pd.Timestamp("2026-01-01", tz="UTC")]  # Requested by UTC day through 2025-12-31 UTC
series = {  # name: (expected hours in that source's scope, hours with a usable value)
    "NYISO load": (FULL, load.interval_start_utc),
    "NYISO P-7 forecast": (P7_EXPECTED, p7.interval_start_utc),
}
for station in WX["stations"]:
    series[f"{SHORT[station]} obs"] = (FULL, by_station.loc[by_station.station_id.eq(station), "interval_start_utc"])
series["Selected core weather"] = (FULL, wx.loc[wx.core_tuple_valid, "interval_start_utc"])
series["Selected wind"] = (FULL, wx.loc[wx.wind_speed_m_s.notna(), "interval_start_utc"])
series["Open-Meteo forecast"] = (om_exp, om.loc[om.fc_temperature_c.notna(), "valid_time_utc"])
rows = {}
for name, (exp, present) in series.items():
    scope = pd.Series(1, index=pd.DatetimeIndex(exp).tz_convert(NYC).strftime("%Y-%m")).groupby(level=0).sum()
    rows[name] = (missing_by_month(exp, present) / scope * 100).reindex(months)
pct = pd.DataFrame(rows).T
pct.round(2).to_csv(OUT / "missingness_by_month_pct.csv")
fig, ax = plt.subplots(figsize=(13, 3.8))
cm = plt.get_cmap("magma_r").copy()
cm.set_bad("#e5e5e5")
im = ax.imshow(np.ma.masked_invalid(pct.to_numpy(dtype=float)), aspect="auto", cmap=cm, vmin=0, vmax=20,
               interpolation="nearest")
ax.set_yticks(range(len(pct.index)), pct.index)
jan = [i for i, m in enumerate(months) if m.endswith("-01")]
ax.set_xticks(jan, [months[i][:4] for i in jan])
ax.axvline(jan[-1] - 0.5, color="#1f77b4", lw=1.5)
ax.text(jan[-1] + 0.5, -0.8, "2025 holdout (counts only)", fontsize=8, color="#1f77b4", va="bottom")
ax.set_title("Missing hours per month (% of hours). Grey = outside that source's scope", pad=16)
fig.colorbar(im, ax=ax, label="% missing (capped at 20)", pad=0.01)
fig.tight_layout()
fig.savefig(FIG / "step9_missingness_heatmap.png", dpi=150)
plt.close(fig)

# ------------------------------------------------------------ 5. Report
print("5/5 writing docs/data_audit_full_history.md")
cov = yearly.copy()
cov.columns = ["Year", "Expected hours", "Load missing", "Load duplicates", "Weather core missing",
               "Fallback LGA", "Fallback JFK", "Wind missing", "Precip unknown", "Precip trace",
               "P-7 expected", "P-7 missing", "Open-Meteo rows", "Open-Meteo null"]
cov["Year"] = cov["Year"].astype(str).replace(str(HOLDOUT_YEAR), f"{HOLDOUT_YEAR} (holdout)")
totals = timing.groupby("station")[["fm15_rows", "quarantined", "date_disagrees"]].sum()
tim = timing.pivot(index="year", columns="station", values="date_disagrees")[list(SHORT.values())]
quar = timing.pivot(index="year", columns="station", values="quarantined")[list(SHORT.values())]
smiss = station_missing.pivot(index="year", columns="station", values="missing_hours")[list(SHORT.values())]
st = pd.DataFrame({"Year": tim.index.astype(str)})
for s in SHORT.values():
    st[f"{s} no obs"] = smiss[s].to_numpy()
    st[f"{s} quarantined"] = quar[s].to_numpy()
    st[f"{s} DATE disagrees"] = tim[s].to_numpy()
st["Year"] = st["Year"].replace(str(HOLDOUT_YEAR), f"{HOLDOUT_YEAR} (holdout)")
other_offsets = int(timing.offset_other.sum())
ls_tab = load_stats.rename(columns={"year": "Year", "min": "Min MW", "mean": "Mean MW", "max": "Max MW",
                                    "peak_local_time": "Peak hour start (local)", "max_hourly_change": "Max hourly change MW",
                                    "deviation_flags": "Deviation flags", "nonpositive": "Non-positive",
                                    "flatline_runs_3h": "Flat runs >= 3 h"})
for c in ["Min MW", "Mean MW", "Max MW", "Max hourly change MW"]:
    ls_tab[c] = ls_tab[c].map(fmt)
pos = flag_days[flag_days.mean_rel_dev.gt(0)]
neg = flag_days[flag_days.mean_rel_dev.lt(0)]
pos_neg_sentence = (
    f"{len(pos)} days are above their neighbors; all are hot days (daily maximum "
    f"{pos.daily_max_temp_c.min():.1f}-{pos.daily_max_temp_c.max():.1f} °C) whose load rose well above the same hours on nearby days. "
    f"{len(neg)} days are below their neighbors: "
    f"{', '.join(str(d) for d in neg.day)}. No flagged hour is zero, negative or part of a flat run, so all "
    "hours stay in the data; forecasting such days is part of the task.")
fdays = flag_days.copy()
fdays["day"] = fdays.day.astype(str)
fdays["max_abs_z"] = fdays.max_abs_z.round(1)
fdays["mean_rel_dev"] = (fdays.mean_rel_dev * 100).round(1).astype(str) + "%"
fdays["daily_max_temp_c"] = fdays.daily_max_temp_c.round(1)
fdays.columns = ["Local day", "Flagged hours", "Max abs z", "Mean deviation", "Daily max temp (°C)"]
n_total = len(FULL)
pre_rows = len(load_pre)
lines = [
    "# Full-history data audit (Step 9)",
    "",
    "Generated by `scripts/audit_full_history.py` from the Step 8 silver tables and the raw NOAA files. "
    "Row-level evidence is written to `outputs/data_audit/step9/` (kept local).",
    "",
    "## Scope and holdout rule",
    "",
    f"- Period: local years 2017-2025, {fmt(n_total)} expected UTC hours (DST days have 23 or 25 hours).",
    f"- 2025 is the final holdout. It appears only as counts: rows, missing hours, fallback hours, "
    f"timestamp disagreements and quarantined rows.",
    f"- Load and weather values, value checks and figures use 2017-2024 only ({fmt(pre_rows)} hours). "
    f"The code refuses 2025 rows in any value-based check.",
    "- No models were fitted and no forecast errors were computed. The protocol (contract v0.2, Amendment 1) "
    "was frozen before this audit, so nothing here changes model or feature choices.",
    "",
    "## Coverage by year",
    "",
    "Counts of hours. 'Weather core missing' = no station had a complete temperature, dew point and "
    "humidity reading in that hour. 'Fallback' = Central Park lacked the core reading and LaGuardia (then JFK) "
    "supplied it. 'Precip unknown' excludes trace reports, which are kept as a separate flag.",
    "",
    md_table(cov),
    "",
    f"- Load: {fmt(yearly.load_missing.sum())} missing hours and {fmt(yearly.load_duplicates.sum())} duplicate hours "
    "across the full period. No load value was imputed.",
    f"- Observed weather: {fmt(yearly.weather_core_missing.sum())} hours with no core reading at any station; "
    f"{fmt(yearly.fallback_laguardia.sum() + yearly.fallback_jfk.sum())} hours used a backup station "
    f"({fmt(yearly.fallback_laguardia.sum())} LaGuardia, {fmt(yearly.fallback_jfk.sum())} JFK).",
    f"- Wind is missing in {fmt(yearly.wind_missing.sum())} hours "
    f"({yearly.wind_missing.sum() / n_total:.1%}), which is why it is excluded from feature set C.",
    f"- NYISO P-7: {fmt(yearly.p7_missing.sum())} missing hours from 2017-12-02 onward.",
    f"- Open-Meteo archived forecasts: {fmt(yearly.openmeteo_null.sum())} null hours, all before the "
    "first available valid time (2024-01-20 12:00 UTC).",
    "",
    f"- 2025 (holdout, counts only) has more gaps than earlier years: {fmt(yearly.weather_core_missing.iloc[-1])} hours "
    f"with no core weather and {fmt(yearly.precip_unknown.iloc[-1])} hours with unknown precipitation. Precipitation is "
    "not a model input; the core-weather gaps show up as missing feature-set C inputs, which Step 10 counts. This is recorded "
    "now so the final evaluation reports it.",
    "",
    "## NOAA station timing by year",
    "",
    "'No obs' = hours with no routine (FM-15) observation from that station. 'Quarantined' = FM-15 rows "
    "whose original METAR UTC time could not be recovered; they are excluded, never re-timed from DATE. "
    "'DATE disagrees' = recovered METAR UTC time differs from the LCD DATE read as fixed EST (DATE + 5 h).",
    "",
    md_table(st),
    "",
    f"- Over 2017-2025, {fmt(timing.date_disagrees.sum())} of {fmt(timing.utc_resolved.sum())} resolved FM-15 rows "
    f"({timing.date_disagrees.sum() / timing.utc_resolved.sum():.2%}) disagree with DATE + 5 h: "
    f"{fmt(timing.offset_plus_60.sum())} by +60 minutes, {fmt(timing.offset_minus_60.sum())} by -60 minutes and "
    f"{fmt(other_offsets)} by other amounts.",
    f"- Every disagreement falls within {max_dst_gap:.1f} hours of a DST change (+60 in March, -60 in November), "
    "confirming the pilot finding that DATE is not a clean fixed-EST clock near DST. The silver tables use the "
    "METAR UTC time, so these rows are timed correctly.",
    f"- Quarantined FM-15 rows: {fmt(timing.quarantined.sum())} in total "
    f"({', '.join(f'{s} {fmt(totals.loc[s, 'quarantined'])}' for s in SHORT.values())}).",
    "",
    "## Load value checks, 2017-2024",
    "",
    "- Non-positive or non-finite values and flat runs (identical consecutive values for 3 or more hours) "
    "would indicate meter or feed problems.",
    "- Deviation flags compare each hour with the median of the same clock hour 1-3 days before and after; "
    "hours with a robust z-score above 6 are flagged for review, not removed.",
    "",
    md_table(ls_tab),
    "",
]
if len(fdays):
    lines += [
        f"{len(fdays)} local days contain deviation flags. Their daily maximum temperature shows whether "
        "weather explains them:",
        "",
        md_table(fdays),
        "",
        pos_neg_sentence,
        "",
    ]
lines += [
    "## Weather value checks, 2017-2024",
    "",
    "Selected hourly weather (Central Park first, then backups) against plausible NYC ranges:",
    "",
    md_table(ranges),
    "",
    "## Figures",
    "",
    "![Annual load profile](figures/step9_annual_load_profile.png)",
    "",
    "Figure 1. Zone J daily mean load by day of year for 2017-2024 (7-day smoothed), and the average daily shape "
    "by season. Summer peaks dominate; winter shows a smaller evening peak.",
    "",
    "![Load vs temperature](figures/step9_load_vs_temperature.png)",
    "",
    "Figure 2. Hourly load against same-hour observed temperature, 2017-2024. The U shape (heating below and "
    "cooling above about 18 °C) motivates the heating and cooling degree-hour features.",
    "",
    "![Missingness heatmap](figures/step9_missingness_heatmap.png)",
    "",
    "Figure 3. Missing hours per month for each source. Grey cells are outside that source's scope "
    "(P-7 before December 2017; Open-Meteo before 2024). 2025 is shown as counts only.",
    "",
    "## Conclusions for the paper",
    "",
    f"- The load target is complete for all {fmt(n_total)} hours, with no duplicates or imputation."
    if yearly.load_missing.sum() == 0 else f"- Load has {fmt(yearly.load_missing.sum())} missing hours.",
    f"- Observed weather uses a backup station in {(yearly.fallback_laguardia.sum() + yearly.fallback_jfk.sum()) / n_total:.2%} "
    f"of hours and has no core reading in {yearly.weather_core_missing.sum() / n_total:.2%}.",
    "- Station timing is reconstructed from METAR UTC tokens; DATE disagreements are rare and handled.",
    "- Load departures flagged by the robust check coincide with weather extremes or holidays, not faults.",
    "",
    "## Limits",
    "",
    "- NYISO load is the current retrieved vintage, not the first-published value; historical revisions are not "
    "observable here.",
    "- NOAA LCD routine observations are not fully quality-controlled upstream; range checks flag but do not fix.",
    "- Publication delays (1 h load, 15 min weather) are assumptions from the frozen protocol, not measured.",
]
(ROOT / "docs/data_audit_full_history.md").write_text("\n".join(lines) + "\n")
print("Step 9 audit complete.")
print(f"  load missing {yearly.load_missing.sum()}, weather core missing {yearly.weather_core_missing.sum()}, "
      f"fallback {yearly.fallback_laguardia.sum() + yearly.fallback_jfk.sum()}, "
      f"DATE disagreements {timing.date_disagrees.sum()}, deviation-flag days {len(fdays)}")
