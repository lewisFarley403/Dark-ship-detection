from __future__ import annotations

import json
from abc import ABC, abstractmethod
from math import cos, pi, sin
from pathlib import Path
import numpy as np
from typing import Sequence

from filterpy.kalman import KalmanFilter
from .models import Track,enrich_velocity,KNOT_TO_MPS

from .ingestion import AISPage

class PathPredictor(ABC):
    '''
    Abstract base class for path predictors.
    '''
    def __init__(self,page):
        self.page = page
    @abstractmethod
    def predict(self,path:Track,dt:float):
        '''
        base predict method to be overridden by subclasses
        
        :param path: Track object to predict from
        :param dt: time in seconds to predict ahead
        '''
        pass
    def knots_2_meters_per_second(self,knots:float)->float:
        '''
        Converts knots to meters per second.
        
        :param knots: speed in knots
        :type knots: float
        :return: speed in meters per second
        :rtype: float
        '''
        return knots * KNOT_TO_MPS
    def getVelocityVector(self,ping:dict)->np.ndarray:
        '''
        Gets the velocity vector [v_lat,v_lon] from an AIS ping.
        
        :param ping: A dictionary representing an AIS ping with 'Lat', 'Lon', 'Speed', and 'Course' keys.
        '''
        # return [v_lat, v_lon]

        latlon = [ping['Lat'],ping['Lon']]
        speed = self.knots_2_meters_per_second(ping['Speed'])
        course = ping['Course']
        course = course * (pi/180) #convert to radians
        velocity = speed*np.asarray([sin(course),cos(course)])
        return velocity
    def get_ping_dt(self,ping1:dict,ping2:dict)->float:
        '''
        Docstring for get_ping_dt
        
        :param ping1: A dictionary representing an AIS ping with a 'DTG' key.
        :type ping1: dict
        :param ping2: A dictionary representing an AIS ping with a 'DTG' key.
        :type ping2: dict
        :return: Time difference in seconds
        :rtype: float
        '''
        return (ping2['DTG']-ping1['DTG']).total_seconds()
class KFPredictor(PathPredictor,ABC):
    '''
    Docstring for Kalman Filter Based Predictor
    '''
    def __init__(self,page:AISPage):
        '''
        Constructor
        
        :param page: AIS data page to use for predictions
        '''
        super().__init__(page)
        self.kf = None # for storing the last kalman filter used


    def get_covar_ell(self)->Sequence[float]:
        '''
        Finds the dimensions of covariance ellipse 
        :return Width
        :rtype: float
        :return Height
        :rtype: float
        :return angle
        :rtype: float
        '''


        cov = self.get_covariance()[:2, :2]
        vals, vecs = np.linalg.eigh(cov)
        order = vals.argsort()[::-1]
        vals, vecs = vals[order], vecs[:, order]
        theta = np.degrees(np.arctan2(*vecs[:, 0][::-1]))
        
        # 4 * sqrt for a clear 95% confidence visualization
        width, height = 5 * np.sqrt(np.maximum(vals, 0)) 
        return width,height,theta
    def predict(self,track:Track,dt:float,**kwargs:float)->list:
        '''
        Docstring for predict
        
        :param track: Track obj to predict from
        :type track: Track
        :param dt: Amount of time to predict ahead in seconds
        :param kwargs: Valid parameters for the specific kalman filter
        :type kwargs: float
        :return: Description
        :rtype: list
        '''
        track.add_feature(enrich_velocity)
        path = track.get_data(['x','y','vx','vy'])

        kf = self.create_kf(dt,**kwargs)
        
        kf.x = path[0]
        for i,ping in enumerate(path[1:]):
            step_dt = abs(track.get_dt(i,i+1))
            kf.F = self.get_transition_matrix(step_dt)
            kf.predict()
            kf.update(ping)        
        kf.F=self.get_transition_matrix(dt)
        kf.predict()
        lat,lon,_,_ = kf.x
        pred = [float(lat),float(lon)]
        self.kf = kf # store for later inspection

        return track.ENU2latlon(*pred[:2]) # convert back to lat lon
    @abstractmethod
    def create_kf(self,dt):
        '''
        Creates a filterpy kalman filter. Must override this depending on the type of filter
        
        :param dt: Time to predict in seconds
        '''
        pass
    @abstractmethod
    def get_transition_matrix(self,dt):
        '''
        Creates the transition matrix for states in kf
        
        :param dt: Time to predict in seconds
        '''
        pass



class CVKF(KFPredictor):
    def __init__(self,page:AISPage):
        '''
        Constructor for CVKF, loads the best parameters from bestCVKF.json
        :param page: AISPage object
        '''
        super().__init__(page)
        current_dir = Path(__file__).parent
        with open(current_dir.parent /'bestCVKF.json') as f:
            self.best_params = json.load(f)
    def get_transition_matrix(self,dt:float):
        '''
        creates the transition matrix for constant velocity model to predict ahead by dt seconds        

        :param dt: Amount of time to predict ahead in seconds
        :type dt: float
        '''

        return np.array([
            [1,0,dt,0], # x position
            [0,1,0,dt], # y position
            [0,0,1,0], # keep x velocity the same
            [0,0,0,1] # keep y velocity the same
        ])
    def create_kf(self,dt:float,acc_var:float=0.02,position_variance:float = 0.025,speed_variance:float = 0.025,p:float=1000):
        '''
        Creates a constant velocity Kalman Filter object from filterpy.

        :param dt: Amount of time to predict ahead in seconds
        :param acc_var: Acceleration variance
        :param position_variance: Position variance
        :param speed_variance: Speed variance
        :param p: Initial state covariance
        '''

        transition_matrix = self.get_transition_matrix(dt)
        dim_x = 4
        dim_z = 4
        kf = KalmanFilter(dim_x = dim_x,dim_z = dim_z)
        kf.F = transition_matrix
        kf.H = np.eye(4) # 4x4 identity matrix, just says map each new input state vector to the new state vector; dont modify it in any way.
        kf.P = np.eye(4) * p # unifiorm initial uncertainty in all states

        # Make R have 2 scales to account for the uncertainty in velocity and position measurements
        kf.R = np.array([
            [position_variance,0,0,0], # metric m^2
            [0,position_variance,0,0], # metric m^2
            [0,0,speed_variance,0], # metric m^2/s^2
            [0,0,0,speed_variance] # metric m^2/s^2
        ])
        # Process noise covariance matrix Q
        kf.Q = acc_var * np.array([
            [0.25*dt**4,0,0.5*dt**3,0],
            [0,0.25*dt**4,0,0.5*dt**3],
            [0.5*dt**3,0,dt**2,0],
            [0,0.5*dt**3,0,dt**2]
        ])
        return kf
    
    def predict_with_best(self,track:Track,dt:float)->list:
        '''
        Predicting using the best parameters found from optimisation.
        

        :param track: track to predict from
        :type track: Track
        :param dt: Amount of time to predict ahead in seconds
        :type dt: float
        :return: Predicted [lat,lon]
        :rtype: list
        '''
        return self.predict(track,dt,**self.best_params)
    def get_covariance(self) -> np.ndarray:
        '''
        Getter for final state covariance matrix from last prediction.
    
        :return: The final state covariance matrix from the last prediction
        :rtype: ndarray
        '''
        return self.kf.P
    
class linear_motion(PathPredictor):
    '''
    Class for a model from the literature that assumes constant velocity motion
    '''
    def __init__(self,page):
        super().__init__(page)
    def predict(self,track:Track,dt:float)->list:


        track.add_feature(enrich_velocity)
        path = track.get_data(['x','y','vx','vy'])
        last = path[-1]

        dx = last[2]*dt
        dy = last[3]*dt
        x = last[0]+dx
        y=last[1]+dy
        return [x,y,last[2],last[3]]
