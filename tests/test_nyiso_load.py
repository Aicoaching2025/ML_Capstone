"""Invented minimal rows test parsing, not a copy of research observations."""
import pandas as pd
import pytest
from cleaning.nyiso_load import SOURCE_COLUMNS, decode_integrated_load


def frame(rows):
    return pd.DataFrame(rows, columns=SOURCE_COLUMNS)


def test_fall_repeated_hour_keeps_both_offsets():
    result = decode_integrated_load(frame([
        ['11/03/2024 01:00:00', 'EDT', 'N.Y.C.', 61761, 4000.0],
        ['11/03/2024 01:00:00', 'EST', 'N.Y.C.', 61761, 3900.0],
    ]))
    assert result.interval_start_utc.dt.strftime('%H:%M').tolist() == ['05:00', '06:00']
    assert result.interval_end_utc.dt.strftime('%H:%M').tolist() == ['06:00', '07:00']


def test_spring_skip_is_contiguous_in_utc():
    result = decode_integrated_load(frame([
        ['03/10/2024 01:00:00', 'EST', 'N.Y.C.', 61761, 4000.0],
        ['03/10/2024 03:00:00', 'EDT', 'N.Y.C.', 61761, 4100.0],
    ]))
    assert result.interval_start_utc.dt.strftime('%H:%M').tolist() == ['06:00', '07:00']


def test_reject_wrong_offset_in_summer():
    with pytest.raises(ValueError, match='conflicts'):
        decode_integrated_load(frame([['07/15/2024 12:00:00', 'EST', 'N.Y.C.', 61761, 4000.0]]))


def test_reject_duplicate_utc_interval():
    row = ['01/15/2024 00:00:00', 'EST', 'N.Y.C.', 61761, 4000.0]
    with pytest.raises(ValueError, match='Duplicate'):
        decode_integrated_load(frame([row, row]))
