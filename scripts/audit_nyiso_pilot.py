"""Offline reproducible audit of the approved 2024 NYISO load pilot.

Requires cached files from acquire_nyiso_pilot.py and acquire_nyiso_timing_check.py.
Writes no forecasting features and reads no 2025 data.
"""
from pathlib import Path
from datetime import timedelta
import csv,hashlib,json,os
import numpy as np
import pandas as pd
from cleaning.nyiso_load import decode_integrated_load

ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'.mplconfig'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from zoneinfo import ZoneInfo

BASE=ROOT/'data/bronze/nyiso/integrated_load'
OUT=ROOT/'outputs/data_audit/nyiso_pilot';OUT.mkdir(parents=True,exist_ok=True)
SILVER=ROOT/'data/silver/nyiso';SILVER.mkdir(parents=True,exist_ok=True)
WINDOWS={'winter':('2024-01-15','2024-01-22'),'spring_dst':('2024-03-09','2024-03-12'),'fall_dst':('2024-11-02','2024-11-05')}
manifest=pd.read_csv(ROOT/'data/manifests/downloads.csv',keep_default_na=False)
frames=[];lineage=[];month_summaries=[]
for month in ['202401','202403','202411']:
    archive=BASE/f'{month}01palIntegrated_csv.zip'
    digest=hashlib.sha256(archive.read_bytes()).hexdigest()
    meta=manifest[manifest.local_filename.eq(str(archive.relative_to(ROOT)))]
    assert len(meta)==1 and meta.iloc[0].file_hash_sha256==digest
    members=json.loads((BASE/'extracted'/month/'lineage.json').read_text())
    month_frames=[]
    for member in members:
        path=ROOT/member['local_filename']
        assert hashlib.sha256(path.read_bytes()).hexdigest()==member['member_sha256']
        assert member['archive_sha256']==digest
        raw=pd.read_csv(path)
        decoded=decode_integrated_load(raw)
        decoded['source_file']=str(path.relative_to(ROOT))
        decoded['source_file_sha256']=member['member_sha256']
        decoded['source_archive_sha256']=digest
        decoded['retrieved_at_utc']=meta.iloc[0].retrieved_at_utc
        month_frames.append(decoded)
        lineage.append(member)
    month_frame=pd.concat(month_frames,ignore_index=True)
    nyc=month_frame[month_frame.source_name.eq('N.Y.C.')].sort_values('interval_start_utc')
    assert set(nyc.source_ptid)=={61761}
    start=pd.Timestamp(month+'01',tz='America/New_York')
    finish=start+pd.offsets.MonthBegin(1)
    expected=pd.date_range(start.tz_convert('UTC'),finish.tz_convert('UTC'),freq='h',inclusive='left')
    assert pd.DatetimeIndex(nyc.interval_start_utc).equals(expected)
    month_summaries.append({'month':month,'daily_files':len(members),'all_zone_rows':len(month_frame),'nyc_rows':len(nyc),'expected_nyc_hours':len(expected),'missing_utc_hours':len(expected.difference(nyc.interval_start_utc)),'duplicate_zone_utc_rows':int(month_frame.duplicated(['Name','interval_start_utc']).sum()),'source_null_cells':int(month_frame[['Time Stamp','Time Zone','Name','PTID','Integrated Load']].isna().sum().sum()),'zone_count':int(month_frame.Name.nunique())})
    frames.append(month_frame)
all_data=pd.concat(frames,ignore_index=True)
assert all_data.groupby('source_name').source_ptid.nunique().eq(1).all()
assert all_data.groupby('source_ptid').source_name.nunique().eq(1).all()
nyc=all_data[all_data.source_name.eq('N.Y.C.')].copy()
pilot_parts=[];windows=[]
for name,(start,end) in WINDOWS.items():
    lo=pd.Timestamp(start,tz='America/New_York').tz_convert('UTC')
    hi=pd.Timestamp(end,tz='America/New_York').tz_convert('UTC')
    subset=nyc[nyc.interval_start_utc.ge(lo)&nyc.interval_start_utc.lt(hi)].sort_values('interval_start_utc').copy()
    expected=pd.date_range(lo,hi,freq='h',inclusive='left')
    assert pd.DatetimeIndex(subset.interval_start_utc).equals(expected)
    subset['pilot_window']=name
    windows.append({'window':name,'local_start_inclusive':start,'local_end_exclusive':end,'rows':len(subset),'expected_hours':len(expected),'min_load_mw':float(subset.load_mw.min()),'max_load_mw':float(subset.load_mw.max()),'mean_load_mw':float(subset.load_mw.mean()),'nonpositive_load_rows':int(subset.load_mw.le(0).sum()),'duplicate_utc_rows':int(subset.duplicated('interval_start_utc').sum())})
    pilot_parts.append(subset)
pilot=pd.concat(pilot_parts,ignore_index=True).sort_values('interval_start_utc').reset_index(drop=True)
pilot['zone']='J'
pilot['quality_flag']='passed_pilot_structural_checks'
pilot['interval_interpretation']='hour_start_supported_by_crosscheck_and_reference_implementation'
pilot['availability_basis']='unresolved_no_historical_publication_timestamp'
columns=['interval_start_utc','interval_end_utc','zone','load_mw','source_timestamp','source_timezone','source_name','source_ptid','pilot_window','source_file','source_file_sha256','source_archive_sha256','retrieved_at_utc','quality_flag','interval_interpretation','availability_basis']
pilot=pilot[columns]
pilot.to_parquet(SILVER/'zone_j_load_pilot_2024.parquet',index=False)
pilot.to_csv(SILVER/'zone_j_load_pilot_2024.csv',index=False)
local=pilot.interval_start_utc.dt.tz_convert('America/New_York')
daily=pilot.groupby(local.dt.strftime('%Y-%m-%d')).size().rename_axis('local_date').reset_index(name='rows')
daily['expected_hours']=daily.local_date.map(lambda day:len(pd.date_range(pd.Timestamp(day,tz='America/New_York').tz_convert('UTC'),(pd.Timestamp(day)+timedelta(days=1)).tz_localize('America/New_York').tz_convert('UTC'),freq='h',inclusive='left')))
assert daily.rows.eq(daily.expected_hours).all()
daily.to_csv(OUT/'daily_counts.csv',index=False)
pd.DataFrame(month_summaries).to_csv(OUT/'monthly_counts.csv',index=False)
pd.DataFrame(windows).to_csv(OUT/'window_summary.csv',index=False)
pilot[local.dt.strftime('%Y-%m-%d').isin(['2024-03-10','2024-11-03'])].to_csv(OUT/'dst_transition_rows.csv',index=False)
# Export archive/member lineage as reviewable provenance metadata, not raw observations.
with (ROOT/'data/manifests/nyiso_pilot_archive_members.csv').open('w',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=list(lineage[0]),lineterminator="\n");writer.writeheader();writer.writerows(lineage)
# Auxiliary timing comparison: same 23 common labels for each hypothesis.
timing=ROOT/'data/bronze/nyiso/timing_check'
aux=[]
aux_archive=timing/'20240101pal_csv.zip'
aux_digest=hashlib.sha256(aux_archive.read_bytes()).hexdigest()
aux_record=manifest[manifest.local_filename.eq(str(aux_archive.relative_to(ROOT)))]
assert len(aux_record)==1 and aux_record.iloc[0].file_hash_sha256==aux_digest
aux_lineage=json.loads((timing/'lineage.json').read_text())
for member in aux_lineage:
    assert member['archive_sha256']==aux_digest
    assert hashlib.sha256((ROOT/member['local_filename']).read_bytes()).hexdigest()==member['member_sha256']
for day in ['20240115','20240116']:
    path=timing/f'{day}pal.csv';raw=pd.read_csv(path);raw=raw[raw.Name.eq('N.Y.C.')].copy()
    assert raw['Time Zone'].eq('EST').all()
    raw['t']=pd.to_datetime(raw['Time Stamp'],format='%m/%d/%Y %H:%M:%S')
    aux.append(raw)
five=pd.concat(aux,ignore_index=True).sort_values('t')
assert not five.duplicated(['t','Name']).any()
five['Load']=pd.to_numeric(five.Load,errors='raise')
means=five.groupby(five.t.dt.floor('h')).Load.mean()
counts=five.groupby(five.t.dt.floor('h')).size()
hourly=nyc[nyc.source_timestamp.str.startswith('01/15/2024')].copy()
hourly['label']=pd.to_datetime(hourly.source_timestamp,format='%m/%d/%Y %H:%M:%S')
common=hourly[hourly.label.dt.hour.ge(1)].copy() # 01:00–23:00, all hypotheses have auxiliary coverage.
comparisons=[]
for shift,label in [(-1,'hour_ending_hypothesis'),(0,'hour_beginning_hypothesis'),(1,'one_hour_later_negative_control')]:
    bins=common.label.map(lambda x:x+timedelta(hours=shift))
    approx=bins.map(means)
    assert approx.notna().all()
    comparisons.append({'interpretation':label,'comparison_hours':len(common),'mae_mw_vs_5min_arithmetic_mean':float((approx-common.load_mw).abs().mean()),'min_five_min_records_per_bin':int(bins.map(counts).min()),'max_five_min_records_per_bin':int(bins.map(counts).max())})
pd.DataFrame(comparisons).to_csv(OUT/'interval_alignment_check.csv',index=False)
# Plot disjoint windows separately, avoiding lines across months of absent data.
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10})
fig,axes=plt.subplots(3,1,figsize=(12,9),layout='constrained',sharey=True)
for ax,(name,(start,end)) in zip(axes,WINDOWS.items()):
    part=pilot[pilot.pilot_window.eq(name)]
    ax.plot([value.to_pydatetime() for value in part.interval_start_utc],part.load_mw,color='#245B86',linewidth=1.6)
    ax.set_title({'winter':'Winter inspection week · January 15–21, 2024 (includes MLK Day)','spring_dst':'Spring DST inspection · March 9–11, 2024','fall_dst':'Fall DST inspection · November 2–4, 2024'}[name],loc='left')
    ax.set_ylabel('Hourly load (MW)')
    ax.grid(axis='y',color='#D9DDE2',linewidth=.6)
    ax.spines[['top','right']].set_visible(False)
    locator=mdates.AutoDateLocator(minticks=4,maxticks=8,tz=ZoneInfo('America/New_York'))
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d\n%H:%M %Z',tz=ZoneInfo('America/New_York')))
    ax.set_xlim(part.interval_start_utc.iloc[0].to_pydatetime(),part.interval_start_utc.iloc[-1].to_pydatetime())
axes[-1].set_xlabel('Target interval start · America/New_York; UTC used for interval checks')
fig.suptitle('NYISO Zone J hourly integrated load pilot',fontsize=15,weight='bold')
fig.savefig(OUT/'zone_j_load_pilot.png',dpi=180)
fig.savefig(OUT/'zone_j_load_pilot.svg')
plt.close(fig)
summary={'status':'structural_checks_passed','monthly_counts':month_summaries,'windows':windows,'pilot_rows':len(pilot),'missing_target_values':int(pilot.load_mw.isna().sum()),'duplicate_zone_utc_rows':int(pilot.duplicated(['zone','interval_start_utc']).sum()),'nonpositive_load_rows':int(pilot.load_mw.le(0).sum()),'interval_alignment_check':comparisons,'interval_label_status':'supported_hour_start_interpretation_not_explicit_provider_schema_confirmation','publication_delay_hours':None,'historical_vintages_available':None,'holdout_2025_accessed':False,'silver_sha256':hashlib.sha256((SILVER/'zone_j_load_pilot_2024.parquet').read_bytes()).hexdigest()}
(OUT/'audit_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
