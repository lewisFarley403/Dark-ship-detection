import pytest
import pandas as pd
from datetime import datetime as dt
from unittest.mock import patch, mock_open, MagicMock

# Adjust this import to match your module name if it's not ingestion.py
from core.ingestion import AISPage 

# --- Fixtures ---

@pytest.fixture
def mock_headers():
    return "MMSI,DTG,Lat,Lon,Type,Other"

@pytest.fixture
def dummy_ais_data():
    return pd.DataFrame({
        'MMSI': ['123', '123', '456', '789'],
        'DTG': ['2023-10-27 10:00:00', '2023-10-27 10:30:00', '2023-10-27 10:15:00', '2023-10-27 11:00:00'],
        'Lat': [50.1, 50.2, 51.0, 52.0],
        'Lon': [-4.1, -4.0, -3.5, -2.0],
        'Type': ['SHIP', 'SHIP', 'SHIP', 'AIR'], # 'AIR' should be filtered out
        'Other': ['A', 'B', 'C', 'D']
    })

@pytest.fixture
def mock_ais_page(dummy_ais_data, mock_headers):
    """
    Creates an AISPage instance with mocked file I/O so we don't need real CSVs.
    """
    test_dt = dt(2023, 10, 27, 10)
    
    with patch('pathlib.Path.open', mock_open(read_data=mock_headers)), \
         patch('pandas.read_csv', return_value=dummy_ais_data), \
         patch('ingestion.get_data_path', return_value=MagicMock()): # Mock get_data_path
         
        page = AISPage(test_dt)
        return page

# --- Tests ---

def test_initialization(mock_ais_page):
    assert mock_ais_page.datetime == dt(2023, 10, 27, 10)
    assert 'MMSI' in mock_ais_page.headers
    # Check that 'AIR' type was successfully filtered out during load_ais
    assert 'AIR' not in mock_ais_page.full_ais_df['Type'].values

def test_get_full_df(mock_ais_page):
    df = mock_ais_page.get_full_df()
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 3 # 4 original rows - 1 'AIR' row

def test_get_ais_dicts(mock_ais_page):
    ais_dicts = mock_ais_page.get_ais_dicts()
    assert isinstance(ais_dicts, dict)
    assert '123' in ais_dicts
    assert isinstance(ais_dicts['123'], list)
    assert ais_dicts['123'][0]['MMSI'] == '123'

@patch('ingestion.Track') # Mock the Track model so we don't need to import its dependencies
def test_get_track(MockTrack, mock_ais_page):
    # Test valid MMSI
    track = mock_ais_page.get_track('123')
    assert track is not None
    MockTrack.assert_called_once()
    
    # Test invalid MMSI
    assert mock_ais_page.get_track('999') is None

@patch('ingestion.Track')
def test_get_all_tracks(MockTrack, mock_ais_page):
    tracks = list(mock_ais_page.get_all_tracks())
    assert len(tracks) == 2 # MMSI 123 and 456 (789 was AIR)
    # NOTE: This test might fail on your current code due to the group_df.to_frame() issue identified earlier!

def test_filter_bbox(mock_ais_page):
    # bbox format: min_lon, min_lat, max_lon, max_lat, _, _
    bbox = (-4.5, 50.0, -3.9, 50.5, 0, 0)
    mock_ais_page.filter_bbox(bbox)
    
    df = mock_ais_page.get_full_df()
    assert len(df) == 2 # Only the two rows for MMSI 123 are in this box
    assert all(df['MMSI'] == '123')

def test_filter_datetime_single_arg(mock_ais_page):
    # Since the second filter_datetime overwrites the first, we test the `end` only logic
    end_time = pd.to_datetime('2023-10-27 10:20:00')
    mock_ais_page.filter_datetime(end=end_time)
    
    df = mock_ais_page.get_full_df()
    assert len(df) == 2 # 10:00:00 and 10:15:00
    assert max(df['DTG']) <= end_time

def test_len_dunder(mock_ais_page):
    # .size returns total number of elements (rows * columns)
    expected_size = len(mock_ais_page.full_ais_df) * len(mock_ais_page.full_ais_df.columns)
    assert len(mock_ais_page) == expected_size