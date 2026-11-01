"""Diagnostic UTC recovery from original METAR tokens, not publication timing."""
from datetime import datetime, timedelta, timezone
import re
import pandas as pd


def metar_utc(date_text,remark,icao):
    match=re.search(r'\b(?:METAR|SPECI)\s+(?:COR\s+)?'+icao+r'\s+(?:COR\s+)?(\d{6})Z\b',remark)
    if not match:return pd.NaT
    token=match.group(1);day,hour,minute=int(token[:2]),int(token[2:4]),int(token[4:6])
    if not (1<=day<=31 and hour<24 and minute<60):return pd.NaT
    # DATE supplies month/year context only; UTC day/hour/minute comes from DDHHMMZ.
    approximate=datetime.fromisoformat(date_text).replace(tzinfo=timezone.utc)+timedelta(hours=5)
    candidates=[]
    for offset in [-1,0,1]:
        anchor=pd.Timestamp(approximate).normalize().replace(day=1)+pd.DateOffset(months=offset)
        try:candidate=datetime(anchor.year,anchor.month,day,hour,minute,tzinfo=timezone.utc)
        except ValueError:continue
        candidates.append(candidate)
    closest=min(candidates,key=lambda x:abs((x-approximate).total_seconds()))
    if abs((closest-approximate).total_seconds())>12*3600:return pd.NaT
    return closest



VARIABLES = {
    'temperature_c': 'HourlyDryBulbTemperature',
    'dewpoint_c': 'HourlyDewPointTemperature',
    'relative_humidity_pct': 'HourlyRelativeHumidity',
    'wind_speed_m_s': 'HourlyWindSpeed',
    'precipitation_mm': 'HourlyPrecipitation',
}


def parse_weather_values(raw):
    """Conservative scalar validation; preserve raw tokens and distinct trace state.

    Range checks are research sanity checks, not a reconstruction of NOAA QC.
    Missing or rejected fields remain missing; no imputation is performed.
    """
    result = raw.copy()
    limits = {'temperature_c': (-90, 60), 'dewpoint_c': (-100, 60),
              'relative_humidity_pct': (0, 100), 'wind_speed_m_s': (0, 100),
              'precipitation_mm': (0, 1000)}
    for name, source in VARIABLES.items():
        tokens = raw[source].astype(str).str.strip()
        values = pd.to_numeric(tokens, errors='coerce')
        low, high = limits[name]
        invalid = values.notna() & ~values.between(low, high)
        state = pd.Series('numeric', index=raw.index, dtype='object')
        state.loc[tokens.eq('')] = 'missing'
        state.loc[tokens.ne('') & values.isna()] = 'unparsed_token'
        state.loc[invalid] = 'outside_sanity_range'
        if name == 'precipitation_mm':
            state.loc[tokens.eq('T')] = 'trace'
        result[name] = values.mask(invalid)
        result[name + '_raw'] = tokens
        result[name + '_state'] = state
    inconsistent = result.dewpoint_c.notna() & result.temperature_c.notna() & result.dewpoint_c.gt(result.temperature_c + 1.0)
    result.loc[inconsistent, 'dewpoint_c'] = float('nan')
    result.loc[inconsistent, 'dewpoint_c_state'] = 'dewpoint_exceeds_temperature_tolerance'
    result['precipitation_trace'] = result.precipitation_mm_state.eq('trace')
    return result


def select_hourly_observations(observations):
    """Last routine observation in each [hour start, hour end) per station.

    Retrospective representative observation, not an hourly mean or origin feature.
    """
    frame = observations.copy()
    if frame.observation_time_utc.isna().any():
        raise ValueError('Unresolved observation timestamps must be quarantined first')
    if frame.duplicated(['station_id', 'observation_time_utc']).any():
        raise ValueError('Duplicate station/observation UTC time requires review')
    frame['interval_start_utc'] = frame.observation_time_utc.dt.floor('h')
    frame['interval_end_utc'] = frame.interval_start_utc.map(lambda value: value + timedelta(hours=1))
    frame = frame.sort_values(['station_id', 'observation_time_utc', 'source_row_number'])
    return frame.drop_duplicates(['station_id', 'interval_start_utc'], keep='last').reset_index(drop=True)


def select_core_station(hourly, priority):
    """Select an intact temperature/dewpoint/RH tuple, preserving station provenance.

    Backup selection is retrospective at the same interval. No temporal filling or
    independent airport wind substitution occurs. Missing core tuples stay missing.
    """
    if hourly.duplicated(['station_id', 'interval_start_utc']).any():
        raise ValueError('Expected unique station/hour rows')
    unknown = set(hourly.station_id) - set(priority)
    if unknown:
        raise ValueError(f'Unknown station priority: {unknown}')
    frame = hourly.copy()
    frame['_rank'] = frame.station_id.map({station: rank for rank, station in enumerate(priority)})
    frame['_missing_core'] = frame[['temperature_c', 'dewpoint_c', 'relative_humidity_pct']].isna().any(axis=1)
    frame = frame.sort_values(['interval_start_utc', '_missing_core', '_rank'])
    chosen = frame.drop_duplicates('interval_start_utc', keep='first').copy()
    chosen['station_fallback_used'] = chosen.station_id.ne(priority[0]) & ~chosen._missing_core
    chosen['core_tuple_valid'] = ~chosen._missing_core
    # If no station offers a complete tuple, do not present a partial tuple as valid.
    chosen.loc[chosen._missing_core, ['temperature_c', 'dewpoint_c', 'relative_humidity_pct']] = float('nan')
    return chosen.drop(columns=['_rank', '_missing_core']).reset_index(drop=True)
