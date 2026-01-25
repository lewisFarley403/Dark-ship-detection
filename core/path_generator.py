'''
Module test_path.py
Functions to create simulated AIS path datasets for testing Predictors.
'''
from __future__ import annotations

import random
from math import cos, pi, sin
from typing import Sequence

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


from .predictors import linear_motion
from .models import TestPathConfig,PathEntry,PathDatasetConfig,Track



simulation_params = {
    "n": 500,                          
    "node_range": (30, 100),          # Number of points per track (dense enough for curves)
    "time_range": (600, 1800),        # Duration: 10 to 30 minutes

    # Physics (Large Vessels)
    "speed_range": (0, 12.0),       # 5-12 m/s (~10 to 23 knots)
    "tr_range": (-0.008, 0.008),      # Max turn ~0.5 deg/sec (standard rate is ~0.3 deg/sec)

    # Noise / Errors
    "speed_noise_range": (0, 0.05), # Speed fluctuates by 1% to 5% (current/wind)
    "tr_noise_range": (0.0, 0.001),    # Slight rudder adjustments/wobble
    "sensor_noise_range": (5.0, 20.0), # GPS error: 5m (good) to 20m (poor/degraded)
}

class TestTrack(Track):
    '''
    A simple subclass of Track for testing purposes.
    It uses a provided DataFrame instead of loading from AIS data.
    '''
    def __init__(self,_:str,partial_df:pd.DataFrame):
        '''
        Constructor for TestTrack.
        
        :param mmsi: MMSI of the vessel
        :param partial_df: Description
        :type partial_df: pd.DataFrame
        '''

        self.df = partial_df
        self.mmsi = 0  # Dummy MMSI for testing
    def plot(self, points=None,ellipse = None):
        '''
        Plot the track path along with optional points and ellipse.
        

        :param points: Points predicted or of interest to overlay on the track
        :param ellipse: Ellipse patch representing uncertainty to overlay on the track
        :return: None
        '''

        x = self.df['x']
        y = self.df['y']
        # main track path
        plt.plot(x, y, label='Track Path',marker='o', markersize=4)


        if points is not None:
            # np.atleast_2d ensures this works even if you pass a single point [x, y]
            pts_array = np.atleast_2d(points)


            plt.scatter(pts_array[:, 0], pts_array[:, 1], color='red', zorder=2, label='Points')
        if ellipse is not None:
            # Draw a covar matrix ellipse
            plt.gca().add_patch(ellipse)
        max_extent = max(
        np.max(np.abs(x)),
        np.max(np.abs(y))
    )*1.2 # Add some padding but square aspect


        plt.xlim(-max_extent, max_extent)
        plt.ylim(-max_extent, max_extent)

        plt.legend() # Optional: adds a key to the plot
        plt.show()
    def ENU2latlon(self,x:float,y:float)->Sequence[float]:
        '''
        modified from AIS2track Track class to avoid needing lat/lon reference
        :param x: Easting in meters
        :param y: Northing in meters
        :return: (lat, lon) tuple (but it's actually just x,y in meters)
        '''
        # keep in meters
        return x,y

def create_test_path(config:TestPathConfig)->TestTrack:
    '''
    Create a simulated AIS track following a circular arc with noise.

    :param number_of_nodes: Number of AIS points in the track
    '''
    dt = config.time/config.number_of_nodes # uniform dt
    random.seed(config.seed)


    r=np.array([0,0],dtype=float)

    nodes = [[*list(r.copy()),config.heading,0,config.speed]]
    # print(nodes)
    heading = config.heading
    for i in range(config.number_of_nodes):
        step_speed = config.speed+config.speed*random.uniform(-1*config.speed_noise,config.speed_noise)
        step_turn_rate=config.turn_rate+random.uniform(-1*config.turn_rate_noise,config.turn_rate_noise)
        heading = (heading+step_turn_rate*dt)%(2*np.pi)

        v_x =  step_speed * sin(heading)
        v_y = step_speed*cos(heading)
        x_offset = dt*v_x
        y_offset = dt*v_y

        r+=np.array([x_offset,y_offset])
        sensor_noise_vector = np.array([random.uniform(-config.sensor_noise,config.sensor_noise),
                                        random.uniform(-config.sensor_noise,config.sensor_noise)])
        node = [*list(r.copy() + sensor_noise_vector),heading,i*dt,config.speed]
        nodes.append(node)

    df = pd.DataFrame(nodes, columns=['x', 'y', 'Course','ts','Speed'])
    track = TestTrack(0,df)
    return track


def create_test_path_dataset(config: PathDatasetConfig) -> Sequence[PathEntry]:
    _dataset = []
    
    for _ in range(config.n):
        # 1. Pre-calculate the parameters and store them in a dictionary
        params = TestPathConfig(
            number_of_nodes=random.randint(*config.node_range),
            turn_rate=random.uniform(*config.tr_range),
            speed=random.uniform(*config.speed_range),
            speed_noise=random.uniform(*config.speed_noise_range),
            sensor_noise=random.uniform(*config.sensor_noise_range),
            turn_rate_noise=random.uniform(*config.tr_noise_range),
            time=random.uniform(*config.time_range),
            heading=random.uniform(0, 2 * pi),
            seed=random.randint(0, 1000000)  # Random seed for each path
        )
        
        # 2. Call the function using dictionary unpacking
        _path = create_test_path(params)
        
        # 3. Store both the result and the parameters
        _dataset.append({
            "path": _path,
            "params": params
        })
        
    return _dataset

    
if __name__ == '__main__':
    # Pass the dictionary directly as it is a TypedDict
    param_obj: PathDatasetConfig = {
        "n": 100,
        "node_range": (30, 100),
        "time_range": (600, 1800),
        "speed_range": (0, 12.0),
        "tr_range": (-0.008, 0.008),
        "speed_noise_range": (0, 0.05),
        "tr_noise_range": (0.0, 0.001),
        "sensor_noise_range": (5.0, 20.0),
    }

    dataset = create_test_path_dataset(param_obj)
    
    errors = []
    for entry in dataset:
        path = entry["path"]
        # Simple test: Predict last point using linear motion
        # Note: You need to implement get_dt in TestTrack if it's not inherited
        c = linear_motion(path[:-1])
        
        # Calculating dt manually if get_dt isn't standard
        dt_val = path[-1]['ts'] - path[-2]['ts']
        
        pred = c.predict(path[:-1], dt_val)
        pred_coords = np.array([pred[0], pred[1]])
        actual_coords = np.array([path[-1]['x'], path[-1]['y']])
        
        errors.append(np.linalg.norm(pred_coords - actual_coords))

    print(f"Mean Error: {np.mean(errors):.2f} meters")
    plt.boxplot(errors)
    plt.title("Linear Motion Prediction Error on Synthetic Curved Paths")
    plt.ylabel("Distance Error (m)")
    plt.show()


