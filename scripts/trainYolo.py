from ultralytics import YOLO
import torch
import sys
from pathlib import Path

import yaml
# --- Main Training Function ---
def main():
    """
    This script trains a YOLOv8 object detection model on a custom dataset.
    All key hyperparameters are exposed for easy tuning.
    """
    current_dir = Path(__file__).resolve().parent
    parent_dir = current_dir.parent

    # 2. Point to the file inside that same folder
    yaml_path = current_dir / "data.yaml"
    # Check for available hardware accelerators (CUDA, MPS, or CPU)
    if torch.cuda.is_available():
        print("CUDA is available. Using GPU for training.")
        device = 'cuda'
    elif sys.platform == 'darwin' and torch.backends.mps.is_available():
        # Check for Apple Metal Performance Shaders (MPS) on macOS
        device = 'mps'
    else:
        device = 'cpu'
    print(f"Using device: {device}")
    with open(parent_dir/'runs/detect/tune/best_hyperparameters.yaml', 'r') as f:
        best_hps = yaml.safe_load(f)

    # 1. Load a pre-trained model
    # 'yolov8n.pt' is the smallest and fastest model.
    # For more accuracy, you can use 'yolov8s.pt', 'yolov8m.pt', etc.
    model = YOLO('yolov8n.pt')

    # 2. Train the model with tunable hyperparameters
    try:
        results = model.train(
            # --- Essential Parameters ---
            data=yaml_path,         # Path to your dataset configuration file
            epochs=200,               # Total number of training epochs
            imgsz=640,                # Input image size
            device=device,            # Device to run on (auto-detected)
            batch=16,                 # Number of images per batch (-1 for auto-batch)
            name='good_hp_run', # Renamed for clarity
            workers = 0,
            patience = 50,
            # --- Optimization Hyperparameters ---
            **best_hps  # Unpack the best hyperparameters from the YAML file
        )
        print("Training completed successfully.")
        print(f"Results saved to: {results.save_dir}")

    except Exception as e:
        print(f"An error occurred during training: {e}")


# --- Script Execution ---
if __name__ == '__main__':
    # This ensures the main function is called only when the script is executed directly
    main()

