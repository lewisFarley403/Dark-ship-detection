import optuna
from ultralytics import YOLO
import torch

# Define the simulation parameters
# Ensure this points to your data.yaml file on the SECOND server
DATA_PATH = '/home/links/lf507/Dark-ship-detection/scripts/data.yaml'

def objective(trial):
    # https://docs.ultralytics.com/guides/hyperparameter-tuning/#default-search-space-description
    # Default HPs to match ultranlytics' default values for a fair comparison with their genetic algorithm tuner
    # ============================================================
    # 1. Define the Hyperparameter Search Space
    # ============================================================
    
    # --- Optimization ---
    lr0 = trial.suggest_float("lr0", 1e-5, 1e-1, log=True)
    lrf = trial.suggest_float("lrf", 0.01, 1.0)
    momentum = trial.suggest_float("momentum", 0.6, 0.98)
    weight_decay = trial.suggest_float("weight_decay", 0.0, 0.001)
    warmup_epochs = trial.suggest_float("warmup_epochs", 0.0, 5.0)
    warmup_momentum = trial.suggest_float("warmup_momentum", 0.0, 0.95)

    # --- Loss Weights ---
    box = trial.suggest_float("box", 1.0, 20.0) # seems to be an error on ultralytics website
    cls = trial.suggest_float("cls", 0.2, 4.0)
    dfl = trial.suggest_float("dfl", 0.4, 6.0)

    # --- Augmentations (Color/Visual) ---
    hsv_h = trial.suggest_float("hsv_h", 0.0, 0.1)
    hsv_s = trial.suggest_float("hsv_s", 0.0, 0.9)
    hsv_v = trial.suggest_float("hsv_v", 0.0, 0.9)
    
    # --- Augmentations (Geometric) ---
    degrees = trial.suggest_float("degrees", 0.0, 45.0)
    translate = trial.suggest_float("translate", 0.0, 0.9)
    scale = trial.suggest_float("scale", 0.0, 0.9)
    shear = trial.suggest_float("shear", 0.0, 10.0)
    perspective = trial.suggest_float("perspective", 0.0, 0.001)
    
    # --- Augmentations (Probabilities) ---
    flipud = trial.suggest_float("flipud", 0.0, 1.0)
    fliplr = trial.suggest_float("fliplr", 0.0, 1.0)
    bgr = trial.suggest_float("bgr", 0.0, 1.0)
    mosaic = trial.suggest_float("mosaic", 0.0, 1.0)
    mixup = trial.suggest_float("mixup", 0.0, 1.0)
    copy_paste = trial.suggest_float("copy_paste", 0.0, 1.0)
    
    # --- Training Dynamics ---
    close_mosaic = trial.suggest_int("close_mosaic", 0, 10)

    # ============================================================
    # 2. Run Training
    # ============================================================
    
    # Load a fresh model for every trial
    model = YOLO("yolov8n.pt") 
    
    # Train with suggestions
    # We use a unique 'name' for every trial to avoid file conflicts
    # We keep epochs low (e.g., 20-30) to scan faster, similar to your tune() config
    results = model.train(
        data=DATA_PATH,
        epochs=30,  
        imgsz=640,
        batch=16,
        name=f"optuna_trial_{trial.number}", 
        project="runs/detect/optuna_experiment", # Separate folder for this study
        
        # Inject hyperparameters
        lr0=lr0, lrf=lrf, momentum=momentum, weight_decay=weight_decay,
        warmup_epochs=warmup_epochs, warmup_momentum=warmup_momentum,
        box=box, cls=cls, dfl=dfl,
        hsv_h=hsv_h, hsv_s=hsv_s, hsv_v=hsv_v,
        degrees=degrees, translate=translate, scale=scale, shear=shear, perspective=perspective,
        flipud=flipud, fliplr=fliplr, bgr=bgr,
        mosaic=mosaic, mixup=mixup, copy_paste=copy_paste,
        close_mosaic=close_mosaic,
        
        verbose=False,  # Keep logs clean
        plots=False,    # Don't generate plots for every single trial
        save=False      # Don't save large checkpoint files for every trial
    )
    
    # ============================================================
    # 3. Return Metric
    # ============================================================
    
    # Ultralytics results.fitness is a weighted combination of:
    # [P, R, mAP@0.5, mAP@0.5-0.95]
    # We maximize this value.
    return results.fitness

if __name__ == "__main__":
    # Check GPU
    if torch.cuda.is_available():
        print(f"Starting Optuna on {torch.cuda.get_device_name(0)}")
    
    # Create the Study
    # 'maximize' because higher mAP is better
    study = optuna.create_study(direction="maximize", study_name="yolo_ship_detection")
    
    # Run Optimization
    # n_trials=50 matches your genetic algorithm iterations for a fair comparison
    study.optimize(objective, n_trials=50)

    # Print Best Results
    print("\n==================================================")
    print("OPTUNA STUDY FINISHED")
    print(f"Best Fitness: {study.best_value}")
    print("Best Hyperparameters:")
    for key, value in study.best_params.items():
        print(f"  {key}: {value}")
    print("==================================================")
    
    # Save best params to a yaml file manually for easy use
    import yaml
    with open("best_optuna_params.yaml", "w") as f:
        yaml.dump(study.best_params, f)