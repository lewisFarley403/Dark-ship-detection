#pylint: disable=invalid-name
'''
Module HPtune.py 
Hyperparameter tuning for the CVKF model using Optuna.
'''
import numpy as np
import optuna

from core.predictors import CVKF
from core.path_generator import create_test_path_dataset

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





def objective(trial: optuna.trial.Trial) -> float:
    '''
    Objective function for bayesian hyperparameter optimization using Optuna.
    It runs the CVKF on a set of simulated AIS tracks with parameters suggested by the trial.
    The function returns the RMSE of the predicted positions against ground truth.
    
    :param trial: An Optuna trial object that suggests hyperparameter values.
    :return rmse: The root mean square error of the CVKF predictions.
    '''
    # Load Data
    dataset = create_test_path_dataset(**simulation_params) #TODO fix this so it works with the dataclasses

    # We use 'log=True' because these values often span orders of magnitude
    p_val     = trial.suggest_float("p", 1, 10000, log=True)
    acc_var   = trial.suggest_float("acc_var", 0.0001, 100.0, log=True)

    # Measurement variances usually shouldn't vary wildly, but we tune them anyway
    pos_var   = trial.suggest_float("position_variance", 0.001, 50.0)
    speed_var = trial.suggest_float("speed_variance", 0.001, 0.1)
    kf = CVKF('dummy')

    # Run the filter with these suggested parameters
    estimates = np.asarray([np.asarray(kf.predict(data['path'][:-1],abs(data['path'].get_dt(-1,-2)), p=p_val, acc_var=acc_var, position_variance=pos_var, speed_variance=speed_var)[:2]) for data in dataset])
    true_pos = np.asarray([np.asarray(data['path'][-1][:2]) for data in dataset])

    rmse = np.sqrt(np.mean((true_pos - estimates) ** 2))

    return rmse
if __name__ == "__main__":
    study = optuna.create_study(direction="minimize")
    study.optimize(objective, n_trials=1000)

    # 4. Print results
    print(f"Best values: {study.best_params}")
    print(f"Best error: {study.best_value}")
