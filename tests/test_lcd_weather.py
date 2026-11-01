import pandas as pd
from cleaning.lcd_weather import metar_utc


def test_month_rollover_uses_metar_utc_day():
    assert metar_utc('2024-01-31T23:51:00', 'METAR KNYC 010451Z TEST', 'KNYC') == pd.Timestamp('2024-02-01T04:51Z')


def test_year_rollover_uses_metar_utc_day():
    assert metar_utc('2024-12-31T23:51:00', 'METAR KNYC 010451Z TEST', 'KNYC') == pd.Timestamp('2025-01-01T04:51Z')


def test_fall_repeated_date_retains_distinct_metar_times():
    one=metar_utc('2024-11-03T01:51:00', 'METAR KNYC 030551Z TEST', 'KNYC')
    two=metar_utc('2024-11-03T01:51:00', 'METAR KNYC 030651Z TEST', 'KNYC')
    assert one == pd.Timestamp('2024-11-03T05:51Z')
    assert two == pd.Timestamp('2024-11-03T06:51Z')


def test_missing_or_wrong_station_token_remains_unresolved():
    assert pd.isna(metar_utc('2024-01-15T00:51:00', '', 'KNYC'))
    assert pd.isna(metar_utc('2024-01-15T00:51:00', 'METAR KJFK 150551Z TEST', 'KNYC'))


def test_trace_is_not_zero_and_invalid_humidity_is_missing():
    from cleaning.lcd_weather import parse_weather_values
    row={'HourlyDryBulbTemperature':'10','HourlyDewPointTemperature':'5',
         'HourlyRelativeHumidity':'150','HourlyWindSpeed':'', 'HourlyPrecipitation':'T'}
    result=parse_weather_values(pd.DataFrame([row]))
    assert pd.isna(result.loc[0,'precipitation_mm'])
    assert result.loc[0,'precipitation_trace']
    assert result.loc[0,'precipitation_mm_state']=='trace'
    assert pd.isna(result.loc[0,'relative_humidity_pct'])
    assert result.loc[0,'relative_humidity_pct_state']=='outside_sanity_range'


def test_hour_selection_uses_last_inside_interval_without_crossing_end():
    from cleaning.lcd_weather import select_hourly_observations
    frame=pd.DataFrame({'station_id':['A']*3,'observation_time_utc':pd.to_datetime([
        '2024-01-15T10:10Z','2024-01-15T10:51Z','2024-01-15T11:00Z'],utc=True),
        'source_row_number':[1,2,3]})
    result=select_hourly_observations(frame)
    assert result.source_row_number.tolist()==[2,3]
    assert result.interval_start_utc.dt.hour.tolist()==[10,11]


def test_core_fallback_keeps_station_tuple_and_does_not_fill_wind():
    from cleaning.lcd_weather import select_core_station
    frame=pd.DataFrame({'station_id':['primary','backup'],
        'interval_start_utc':pd.to_datetime(['2024-01-15T10:00Z']*2,utc=True),
        'temperature_c':[float('nan'),6.0],'dewpoint_c':[1.0,2.0],
        'relative_humidity_pct':[60.0,65.0],'wind_speed_m_s':[7.0,float('nan')]})
    result=select_core_station(frame,['primary','backup'])
    assert result.loc[0,'station_id']=='backup'
    assert result.loc[0,'temperature_c']==6.0
    assert result.loc[0,'dewpoint_c']==2.0
    assert result.loc[0,'station_fallback_used']
    assert pd.isna(result.loc[0,'wind_speed_m_s'])
