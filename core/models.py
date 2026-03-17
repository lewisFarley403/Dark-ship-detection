'''
models module
Defines data structures for test path configurations and datasets.
'''
from __future__ import annotations


from typing import Sequence,TypedDict,Callable,TYPE_CHECKING

from dataclasses import dataclass
from datetime import datetime as dt
from math import cos

import numpy as np
import pandas as pd
KNOT_TO_MPS = 1852.0 / 3600.0  # exact




@dataclass
class TestPathConfig:
    '''
    Configuration parameters for creating a test path.
        
    :param number_of_nodes: Number of nodes used to construct the path
    :type number_of_nodes: int

    :param turn_rate: The rate the vessel is turning (radians per second)
    :type turn_rate: float

    :param speed: Speed of the vessel in meters per second
    :type speed: float

    :param speed_noise: Parameter controlling speed variation as a multiplier of speed
    :type speed_noise: float

    :param sensor_noise: parameter controlling positional noise in meters
    :type sensor_noise: float

    :param turn_rate_noise: Parameter controlling turn rate variation in radians per second
    :type turn_rate_noise: float

    :param time: Total time duration of the path in seconds
    :type time: float

    :param heading: Initial heading of the vessel in radians
    :type heading: float

    :param seed: Random seed for reproducibility
    :type seed: int
    '''
    number_of_nodes: int
    turn_rate: float
    speed: float
    speed_noise: float = 0.0
    sensor_noise: float = 0.0
    turn_rate_noise: float = 0.0
    time: float = 100.0
    heading: float = 0.0
    seed: int = 42

class PathEntry(TypedDict):
    '''
    Class to define the structure of a path entry in the dataset.
    '''
    path: Track                # Maps the string key 'path' to a Track object
    params: TestPathConfig   # Maps the string key 'params' to a TestPathConfig object
class PathDatasetConfig(TypedDict):
    '''
    Configuration for creating a dataset of test paths.

    :param n: Number of paths to generate
    :type n: int
    :param node_range: Range for the number of nodes in each path
    :type node_range: tuple[int, int]
    :param tr_range: Range for turn rates in radians per second
    :type tr_range: tuple[float, float]
    :param speed_range: Range for vessel speeds in meters per second
    :type speed_range: tuple[float, float]
    :param speed_noise_range: Range for speed noise as a multiplier of speed
    :type speed_noise_range: tuple[float, float]
    :param sensor_noise_range: Range for sensor noise in meters
    :type sensor_noise_range: tuple[float, float]
    :param tr_noise_range: Range for turn rate noise in radians per second
    :type tr_noise_range: tuple[float, float]
    :param time_range: Range for total path duration in seconds
    :type time_range: tuple[float, float]

    '''
    n: int
    node_range: tuple[int, int]
    tr_range: tuple[float, float]
    speed_range: tuple[float, float]
    speed_noise_range: tuple[float, float]
    sensor_noise_range: tuple[float, float]
    tr_noise_range: tuple[float, float]
    time_range: tuple[float, float]

class Track:
    '''
    Represents the AIS track of a single vessel.
    '''
    def __init__(self,mmsi:str,partial_df:pd.DataFrame):
        '''
        constructs a Track object

        :param mmsi: The unique identifier for the ship
        :type mmsi: str
        :param partial_df: The DataFrame containing AIS data for this ship
        '''
        self.mmsi = mmsi
        self.df = partial_df
        self.origin_lat = self.df.iloc[0]['Lat']
        self.origin_lon = self.df.iloc[0]['Lon']
        self._compute_enu()
        self.EARTH_RADIUS_M =  6_371_000 #m, the radius of earth
    def _latlon2ENU(self,lat,lon): # pylint: disable=invalid-name
        '''
        Converts latitude and longitudes to x-y coordinate space relative to an origin.
        The x-y plane is measured in meters
        :param lat: Latitude component of the coordinate to be transformed
        :param lon: Longitude component of the coordinate to be transformed
        :return [x,y]: Transformed vector pointing from the relative
                        origin to target point in meters
        '''
        lat_0,lon_0,lat,lon = map(np.radians,[self.origin_lat,self.origin_lon,lat,lon])
        x = (lon-lon_0) * cos(lat_0) * self.EARTH_RADIUS_M
        y = (lat-lat_0) * self.EARTH_RADIUS_M
        return [x,y]
    def ENU2latlon(self,x,y): # pylint: disable=invalid-name
        '''
        Converts x-y coordinates in meters back to 
        latitude and longitude relative to the track origin.
        
        :param x: X component in meters (north)
        :param y: Y component in meters (east)
        '''
        lat_0,lon_0= map(np.radians,[self.origin_lat,self.origin_lon])
        lon = x/(self.EARTH_RADIUS_M * np.cos(lon_0)) + lon_0
        lat = y/self.EARTH_RADIUS_M + lat_0
        lat,lon = map(np.degrees,[lat,lon])
        return [lat,lon]
    def _compute_enu(self):
        """Standardise df Lat/Lon to Meters relative to track start."""
        R = 6_371_000  # Earth Radius in meters
        lat0, lon0 = map(np.radians, [self.origin_lat, self.origin_lon])
        lats = np.radians(self.df['Lat'])
        lons = np.radians(self.df['Lon'])
        self.df['x'] = (lons - lon0) * np.cos(lat0) * R
        self.df['y'] = (lats - lat0) * R

        # time stamp in seconds
        self.df['ts'] = self.df['DTG'].astype(np.int64) // 10e9 # convert to seconds
    def add_feature(self, func:Callable[[pd.DataFrame],None]) -> Track:
        """Apply an enrichment function to the dataframe.
        :param func: A function that takes a DataFrame and adds new features to it.
        """
        func(self.df)
        return self

    def get_data(self, cols:Sequence[str]):
        """Extract specific columns for the Predictor.
        :param cols: List of column names to extract.
        :return: Numpy array of the requested columns.
        
        """
        return self.df[cols].values
    def time_subrack(self, time:dt)->Track:
        '''
        Docstring for time_subrack
        
        :param self: Description
        :param time: datetime obj
        '''
        new_df = self.df [self.df['DTG'] <= time]
        return Track(self.mmsi,new_df)
    def get_dt(self,i1:int,i2:int) -> float:
        '''
        Calculate the time difference between 2 pings in seconds
        
        :param i1: Description
        :type i1: int
        :param i2: Description
        :type i2: int
        '''
        t1 = self.df.iloc[i1]['ts']
        t2 = self.df.iloc[i2]['ts']
        return (t2-t1)
    def __getitem__(self, key: int|slice) -> pd.Series|Track:
        """
        Enables standard indexing and slicing.
        - track[-1] returns the last row (pd.Series)
        - track[:-1] returns a new Track object with all rows except the last
        """
        result = self.df.iloc[key]
        
        if isinstance(result, pd.DataFrame):
            # .copy() to ensure independent data
            return self.__class__(self.mmsi, result.copy())

        # just return the data row
        return result
    def __len__(self)->int:
        return len(self.df['ts'])
    def get_latest_msg_timestamp(self):
        return list(self.df['DTG'])[-1]
    def __str__(self):
        return self.df
    def __repr__(self):
        return str(self.df)

def enrich_velocity(df:pd.DataFrame)->None:
    '''
    Function that adds velocity components to a dataframe of AIS pings.
    
    :param df: dataframe to enrich
    :type df: pd.DataFrame
    :return: None
    :rtype: None
    '''
    speed_ms = df['Speed'] * KNOT_TO_MPS
    course_rad = np.radians(df['Course'])
    df['vx'] = speed_ms * np.cos(course_rad)
    df['vy'] = speed_ms * np.sin(course_rad)