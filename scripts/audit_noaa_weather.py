"""Offline intake audit of user-supplied 2024 LCDv2 station files.

UTC reconstructed from original METAR observation tokens is diagnostic only.
No production weather/load join or availability timestamp is produced.
"""
from pathlib import Path
from datetime import datetime,timedelta,timezone
import hashlib,json,re
import pandas as pd
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/data_audit/noaa_weather';OUT.mkdir(parents=True,exist_ok=True)
BASE=ROOT/'data/bronze/noaa/lcdv2'
STATIONS={'USW00094728':('Central Park','KNYC'),'USW00014732':('LaGuardia','KLGA'),'USW00094789':('JFK','KJFK')}
VARIABLES={'temperature_c':'HourlyDryBulbTemperature','dewpoint_c':'HourlyDewPointTemperature','relative_humidity_pct':'HourlyRelativeHumidity','wind_speed_m_s':'HourlyWindSpeed','precipitation_mm':'HourlyPrecipitation'}
WINDOWS={'winter':('2024-01-15','2024-01-22'),'spring_dst':('2024-03-09','2024-03-12'),'fall_dst':('2024-11-02','2024-11-05')}

from cleaning.lcd_weather import metar_utc

summaries=[];coverage=[];missing=[];timing=[];numeric_tokens=[];hourly_by_station={};diagnostic_parts=[]
for station,(short,icao) in STATIONS.items():
    path=BASE/f'LCD_{station}_2024.csv';raw=pd.read_csv(path,dtype=str,keep_default_na=False)
    assert set(raw.STATION)=={station}
    assert raw.DATE.str.startswith('2024-').all()
    f=raw[raw.REPORT_TYPE.eq('FM-15')].copy()
    f['source_row_number']=f.index+2
    f['observation_time_utc']=pd.to_datetime([metar_utc(date,remark,icao) for date,remark in zip(f.DATE,f.REM)],utc=True)
    source_date=pd.to_datetime(f.DATE)
    fixed=source_date.dt.tz_localize('Etc/GMT+5').dt.tz_convert('UTC')
    resolved=f.observation_time_utc.notna()
    offsets=(f.loc[resolved,'observation_time_utc'].dt.tz_localize(None)-source_date[resolved]).dt.total_seconds()/3600
    f['date_plus_5h_difference_minutes']=(f.observation_time_utc-fixed).dt.total_seconds()/60
    for var,col in VARIABLES.items():
        tokens=f[col]
        vals=pd.to_numeric(tokens,errors='coerce')
        f[var]=vals
        bad=tokens[tokens.ne('')&vals.isna()]
        for token,count in bad.value_counts().items():numeric_tokens.append({'station':station,'field':col,'token':token,'rows':int(count)})
        missing.append({'station':station,'scope':'annual_FM15_rows','variable':var,'rows':len(f),'blank_rows':int(tokens.eq('').sum()),'trace_rows':int(tokens.eq('T').sum()),'other_nonnumeric_rows':int((tokens.ne('')&tokens.ne('T')&vals.isna()).sum())})
    summary={'station':station,'name':short,'source_name':raw.NAME.unique().tolist(),'latitude':raw.LATITUDE.unique().tolist(),'longitude':raw.LONGITUDE.unique().tolist(),'elevation_raw':raw.ELEVATION.unique().tolist(),'all_rows':len(raw),'columns':len(raw.columns),'date_min':raw.DATE.min(),'date_max':raw.DATE.max(),'report_counts':{k:int(v) for k,v in raw.REPORT_TYPE.value_counts().items()},'fm15_rows':len(f),'fm15_raw_date_duplicates':int(f.duplicated('DATE').sum()),'metar_utc_resolved_rows':int(resolved.sum()),'metar_utc_unresolved_rows':int((~resolved).sum()),'duplicate_resolved_utc_rows':int(f.loc[resolved].duplicated('observation_time_utc').sum()),'utc_minus_csv_date_hours':{str(k):int(v) for k,v in offsets.value_counts().sort_index().items()},'fixed_EST_mismatch_rows':int(f.date_plus_5h_difference_minutes.fillna(0).ne(0).sum()),'original_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    summaries.append(summary)
    timing_part=f.loc[resolved & f.date_plus_5h_difference_minutes.ne(0),['STATION','DATE','source_row_number','observation_time_utc','date_plus_5h_difference_minutes','REM']].copy();timing.append(timing_part)
    valid=f[resolved].sort_values(['observation_time_utc','source_row_number']).copy()
    valid['hour_start_utc']=valid.observation_time_utc.dt.floor('h')
    # Diagnostic only: latest FM15 per UTC hour, never an origin-available predictor claim.
    hourly=valid.drop_duplicates('hour_start_utc',keep='last').set_index('hour_start_utc')
    hourly_by_station[station]=hourly
    for name,(start,end) in WINDOWS.items():
        lo=pd.Timestamp(start,tz='America/New_York').tz_convert('UTC');hi=pd.Timestamp(end,tz='America/New_York').tz_convert('UTC')
        expected=pd.date_range(lo,hi,freq='h',inclusive='left')
        window=hourly.reindex(expected)
        present=window.STATION.notna()
        row={'station':station,'window':name,'expected_hours':len(expected),'resolved_observation_hours':int(present.sum()),'hours_without_resolved_observation':int((~present).sum())}
        for var in VARIABLES:
            row[var+'_missing_hours']=int(window[var].isna().sum())
        coverage.append(row)
        observations=valid[valid.observation_time_utc.ge(lo)&valid.observation_time_utc.lt(hi)].copy();observations['pilot_window']=name
        diagnostic_parts.append(observations[['STATION','DATE','REPORT_TYPE','SOURCE','source_row_number','observation_time_utc','pilot_window',*VARIABLES,'HourlyPrecipitation','REM']])
pd.DataFrame(coverage).to_csv(OUT/'pilot_coverage.csv',index=False)
pd.DataFrame(missing).to_csv(OUT/'annual_field_missingness.csv',index=False)
pd.DataFrame(numeric_tokens).to_csv(OUT/'nonnumeric_tokens.csv',index=False)
pd.concat(timing,ignore_index=True).to_csv(OUT/'timestamp_discrepancies.csv',index=False)
pd.concat(diagnostic_parts,ignore_index=True).to_csv(OUT/'pilot_fm15_diagnostic_observations.csv',index=False)
pairs=[]
for other in ['USW00014732','USW00094789']:
    pair=pd.concat([hourly_by_station['USW00094728'].temperature_c.rename('central'),hourly_by_station[other].temperature_c.rename('other')],axis=1)
    for name,(start,end) in WINDOWS.items():
        lo=pd.Timestamp(start,tz='America/New_York').tz_convert('UTC');hi=pd.Timestamp(end,tz='America/New_York').tz_convert('UTC')
        sample=pair.loc[(pair.index>=lo)&(pair.index<hi)].dropna()
        pairs.append({'comparison':f'{STATIONS[other][0]} minus Central Park','window':name,'paired_hours':len(sample),'mean_temperature_difference_c':float((sample.other-sample.central).mean()),'mean_absolute_temperature_difference_c':float((sample.other-sample.central).abs().mean())})
pd.DataFrame(pairs).to_csv(OUT/'station_temperature_comparison.csv',index=False)
result={'status':'intake_audited_timing_requires_review','stations':summaries,'pilot_coverage':coverage,'station_comparison':pairs,'hour_selection':'diagnostic_latest_FM15_within_UTC_hour; not a production predictor rule','units':'SI/metric bulk LCDv2 specification; no Fahrenheit conversion applied','production_join_created':False,'source_download_url_time_verified':False,'historical_availability_resolved':False}
(OUT/'audit_summary.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
