"""Build reviewed observed-weather pilot, retrospective hourly representatives and load alignment.

Run: uv run python scripts/build_weather_pilot.py
Availability remains separate: this is not an origin-eligible model feature table.
"""
from pathlib import Path
import hashlib,json
import pandas as pd
import yaml
from cleaning.lcd_weather import metar_utc, parse_weather_values, select_hourly_observations, select_core_station, VARIABLES
ROOT=Path(__file__).resolve().parents[1]
config_path=ROOT/'configs/weather_pilot.yaml'
config=yaml.safe_load(config_path.read_text())
OUT=ROOT/'outputs/data_audit/noaa_weather';OUT.mkdir(parents=True,exist_ok=True)
SILVER=ROOT/'data/silver/noaa';SILVER.mkdir(parents=True,exist_ok=True)
source_manifest=pd.read_csv(ROOT/'data/manifests/downloads.csv',keep_default_na=False)
parts=[];quarantine=[];counts=[]
for station,metadata in config['stations'].items():
    path=ROOT/f'data/bronze/noaa/lcdv2/LCD_{station}_2024.csv'
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    record=source_manifest[source_manifest.local_filename.eq(str(path.relative_to(ROOT)))]
    assert len(record)==1 and record.iloc[0].file_hash_sha256==digest
    raw=pd.read_csv(path,dtype=str,keep_default_na=False)
    assert raw.STATION.eq(station).all() and raw.DATE.str.startswith('2024-').all()
    frame=raw[raw.REPORT_TYPE.eq(config['report_type'])].copy()
    frame['source_row_number']=frame.index+2
    frame['station_id']=station
    frame['station_name']=metadata['name']
    frame['source_file']=str(path.relative_to(ROOT))
    frame['source_sha256']=digest
    frame['observation_time_utc']=pd.to_datetime([metar_utc(date,remark,metadata['icao']) for date,remark in zip(frame.DATE,frame.REM)],utc=True)
    unresolved=frame.observation_time_utc.isna()
    rejected=frame[unresolved].copy();rejected['quarantine_reason']='no_unambiguous_station_matched_METAR_UTC_token'
    quarantine.append(rejected)
    valid=parse_weather_values(frame[~unresolved])
    valid['timestamp_basis']='original_METAR_UTC_token_month_context_from_DATE'
    valid['source_date_discrepancy']=valid.observation_time_utc.ne(pd.to_datetime(valid.DATE).dt.tz_localize('Etc/GMT+5').dt.tz_convert('UTC'))
    counts.append({'station_id':station,'routine_rows':len(frame),'utc_resolved_rows':len(valid),'quarantined_annual_rows':int(unresolved.sum())})
    for name,(start,end) in config['windows'].items():
        lo=pd.Timestamp(start,tz='America/New_York').tz_convert('UTC');hi=pd.Timestamp(end,tz='America/New_York').tz_convert('UTC')
        sample=valid[valid.observation_time_utc.ge(lo)&valid.observation_time_utc.lt(hi)].copy()
        sample['pilot_window']=name
        parts.append(sample)
observations=pd.concat(parts,ignore_index=True)
assert not observations.duplicated(['station_id','observation_time_utc']).any()
value_fields=[field for var in VARIABLES for field in [var,var+'_raw',var+'_state']]
columns=['station_id','station_name','observation_time_utc','DATE','REPORT_TYPE','SOURCE','REM','source_row_number','source_file','source_sha256','timestamp_basis','source_date_discrepancy','pilot_window','precipitation_trace',*value_fields]
observations=observations[columns]
hourly=select_hourly_observations(observations)
load=pd.read_parquet(ROOT/'data/silver/nyiso/zone_j_load_pilot_2024.parquet')
assert len(load)==312 and not load.duplicated('interval_start_utc').any()
assert len(hourly)==len(load)*len(config['stations'])
for station in config['stations']:
    subset=hourly[hourly.station_id.eq(station)]
    assert set(subset.interval_start_utc)==set(load.interval_start_utc)
    assert subset.observation_time_utc.ge(subset.interval_start_utc).all()
    assert subset.observation_time_utc.lt(subset.interval_end_utc).all()
priority=[config['primary_station'],*config['backup_priority']]
core=select_core_station(hourly,priority)
assert len(core)==312 and core.core_tuple_valid.all()
# Preserve all three station series and a clearly labeled retrospective target-weather view.
observations.to_parquet(SILVER/'weather_pilot_observations_2024.parquet',index=False)
hourly.to_parquet(SILVER/'weather_pilot_hourly_by_station_2024.parquet',index=False)
core.to_parquet(SILVER/'weather_pilot_primary_2024.parquet',index=False)
core.to_csv(SILVER/'weather_pilot_primary_2024.csv',index=False)
weather=core[['interval_start_utc','interval_end_utc','observation_time_utc','station_id','source_row_number','source_sha256','station_fallback_used',*VARIABLES,'precipitation_trace']].rename(columns={'interval_end_utc':'weather_interval_end_utc'})
aligned=load.merge(weather,on='interval_start_utc',how='left',validate='one_to_one',indicator=True)
assert aligned['_merge'].eq('both').all()
assert aligned.interval_end_utc.eq(aligned.weather_interval_end_utc).all()
aligned=aligned.drop(columns='_merge')
aligned['weather_role']='retrospective_target_interval_observation_not_origin_available'
aligned.to_parquet(SILVER/'load_weather_pilot_retrospective_2024.parquet',index=False)
pd.concat(quarantine,ignore_index=True).to_csv(OUT/'annual_unresolved_time_quarantine.csv',index=False)
coverage=[]
for station in config['stations']:
    group=hourly[hourly.station_id.eq(station)]
    row={'station_id':station,'rows':len(group)}
    for var in VARIABLES:row[var+'_missing']=int(group[var].isna().sum())
    row['precipitation_trace_rows']=int(group.precipitation_trace.sum())
    coverage.append(row)
pd.DataFrame(coverage).to_csv(OUT/'silver_pilot_coverage.csv',index=False)
result={'status':'step_5_pilot_complete','scope':'312 load intervals and 3 observed-weather stations; not full-history data or operational forecasting features','observations':len(observations),'station_hour_rows':len(hourly),'primary_rows':len(core),'aligned_load_rows':len(aligned),'unmatched_load_rows':0,'fallback_hours':int(core.station_fallback_used.sum()),'core_missing_hours':int((~core.core_tuple_valid).sum()),'selected_station':config['primary_station'],'primary_missing_wind_hours':int(core.wind_speed_m_s.isna().sum()),'annual_timestamp_accounting':counts,'coverage':coverage,'config_sha256':hashlib.sha256(config_path.read_bytes()).hexdigest(),'historical_publication_delay_resolved':False,'origin_features_created':False,'model_training_performed':False,'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in SILVER.glob('*2024*')}}
(OUT/'step5_completion.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))

# Reproducible comparison figure; no lines across the disjoint pilot periods.
import os
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'.mplconfig'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from zoneinfo import ZoneInfo
colors={'USW00094728':'#245B86','USW00014732':'#B26A19','USW00094789':'#744C88'}
styles={'USW00094728':'-','USW00014732':'--','USW00094789':':'}
fig,axes=plt.subplots(3,1,figsize=(12,9),layout='constrained',sharey=True)
for ax,(window,bounds) in zip(axes,config['windows'].items()):
    for station,metadata in config['stations'].items():
        part=hourly[hourly.station_id.eq(station)&hourly.pilot_window.eq(window)].sort_values('interval_start_utc')
        ax.plot([t.to_pydatetime() for t in part.observation_time_utc],part.temperature_c,
                color=colors[station],linestyle=styles[station],linewidth=1.5,label=metadata['name'])
    ax.set_title(f'{window.replace("_"," ").title()} · {bounds[0]} to {bounds[1]} (end exclusive)',loc='left')
    ax.set_ylabel('Observed temperature (°C)')
    ax.grid(axis='y',color='#D9DDE2',linewidth=.6)
    ax.spines[['top','right']].set_visible(False)
    points=hourly[hourly.pilot_window.eq(window)].observation_time_utc
    first,last=points.min(),points.max()
    spacing='48h' if window=='winter' else '24h'
    gap=(last-first).total_seconds()*0.12
    middle=[t for t in pd.date_range(first.ceil(spacing),last.floor(spacing),freq=spacing)
            if (t-first).total_seconds()>gap and (last-t).total_seconds()>gap]
    ticks=pd.DatetimeIndex([first,*middle,last])
    ax.set_xticks([t.to_pydatetime() for t in ticks])
    ax.set_xlim(first.to_pydatetime(),last.to_pydatetime())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d\n%H:%M',tz=ZoneInfo('UTC')))
axes[0].legend(loc='upper right',ncol=3)
axes[-1].set_xlabel('Original METAR observation time · UTC')
fig.suptitle('NYC weather station comparison for the load pilot',fontsize=15,weight='bold')
fig.savefig(OUT/'station_temperature_pilot.png',dpi=160)
plt.close(fig)
