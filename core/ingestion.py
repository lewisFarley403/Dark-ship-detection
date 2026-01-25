from __future__ import annotations

import json
from datetime import datetime as dt
from typing import Sequence
import pandas as pd
import numpy as np




class AISPage:
    '''
    Represents a hour of AIS data for a specific datetime.
    '''
    def __init__(self,datetime:dt):
        '''
        Docstring for __init__
        
        :param datetime: The datetime of the AIS data to load
        :type datetime: dt object
        '''
        self.AIS_DATA_PATH='./AIS'
        self.headers = self.get_headers()
        self.datetime = datetime
        self.csv_path = self.get_csv_dir()
        self.full_ais_df = self.load_ais(self.csv_path)
        self.grouped_data = self.full_ais_df.groupby('MMSI')
    def get_full_df(self):
        '''
        Returns the full AIS dataframe for the page.
        
        :return: Full AIS dataframe
        :rtype: pd.DataFrame'''
        return self.full_ais_df
    def get_ais_dicts (self):
        '''returns full AIS pings for each vessel in the page as a dict of lists of dicts
         :return: dict mapping mmsi to list of pings
         :rtype: dict'''
        mmsi_ping_map = {mmsi:ship_data.sort_values('DTG').to_dict(orient='records') for mmsi, ship_data in self.full_ais_df.groupby('MMSI')}
        return mmsi_ping_map
        
    def load_ais(self,csv_path:str):
        '''
        Loads AIS data from a CSV file into a pandas DataFrame.
        
        :param csv_path: CSV file path containing AIS data
        '''
        df=pd.read_csv(csv_path,header = None, names = self.headers)
        # remove any search and rescue
        df = df[df['Type'] != 'AIR']
        df= df.fillna("") # replaces missing data with empty string so it can be sent to frontend
        df['DTG'] = pd.to_datetime(df['DTG']) # This ensures pandas reads this as a datetime obj for sorting or whatever, rather than a string
        return df
    def get_headers(self):
        '''
        Opens and reads the AIS headers from the Headers.txt file.
        
        :return: List of AIS data headers'''
        with open(f'{self.AIS_DATA_PATH}/Headers.txt') as f:
            txt = f.read()
        return txt.split(',')
    def get_csv_dir(self):
        '''
        Constructs the CSV file path based on the datetime of the AIS data.
        
        :return: CSV file path'''
        return f"{self.AIS_DATA_PATH}/{self.datetime.strftime('%Y')}{self.datetime.strftime('%m')}/{self.datetime.strftime('%Y')}-{self.datetime.strftime('%m')}-{self.datetime.strftime('%d')} {self.datetime.strftime('%H')}0000.csv"
    def get_track(self, mmsi:str):
        '''
        Returns a Track object for a specific MMSI.
        
        :param mmsi: The unique identifier for the ship whose track is to be retrieved
        :return: Track object for the specified MMSI
        :rtype: Track or None if MMSI not found
        '''
        if mmsi not in self.grouped_data.groups:
            return None
        return Track(mmsi, self.grouped_data.get_group(mmsi).copy())

    def get_all_tracks(self):
        '''
        Generator that yields Track objects for every ship in the file.
        
        :yield: Track object for each ship
        :rtype: Track
        '''
        for mmsi, group_df in self.grouped_data:
            yield Track(mmsi, group_df)
    def get_paths(self):
        '''
        Returns a dictionary mapping MMSI to Track objects for all ships in the AIS data. Used for API calls.
        
        :return: Dictionary mapping MMSI to Track objects
        :rtype: dict
        '''
        return {mmsi:ship_data.sort_values('DTG').to_dict(orient='records') for mmsi, ship_data in self.full_ais_df.groupby('MMSI')}
    def filter_cols(self,function:callable) -> AISPage:
        '''
        Applys a function to filter or modify the AIS dataframe.
        

        :param function: Description
        '''
        function(self.full_ais_df)

        return self  # allow chaining
    def filter_bbox(self,bbox:Sequence[float]):
        '''
        Filters the AIS data to only include points within the bounding box.
        
        :param bbox: A tuple (min_lon, min_lat, max_lon, max_lat)
        '''
        min_lon, min_lat, max_lon, max_lat = bbox
        self.full_ais_df = self.full_ais_df[
            (self.full_ais_df['Lon'] >= min_lon) &
            (self.full_ais_df['Lon'] <= max_lon) &
            (self.full_ais_df['Lat'] >= min_lat) &
            (self.full_ais_df['Lat'] <= max_lat)
        ]
        return self  # Allow chaining
    def filter_datetime(self,start:dt,end:dt):
        '''
        Filters the AIS data to only include points within the datetime range.
        
        :param start: Start datetime
        :param end: End datetime
        '''
        self.full_ais_df = self.full_ais_df[
            (self.full_ais_df['DTG'] >= start) &
            (self.full_ais_df['DTG'] <= end)
        ]
        return self  # Allow chaining
    def filter_datetime(self,end:dt):
        '''
        Filters the AIS data to only include points before the datetime.
        
        :param end: End datetime
        '''
        self.full_ais_df = self.full_ais_df[
            (self.full_ais_df['DTG'] <= end)
        ]
        return self  # Allow chaining