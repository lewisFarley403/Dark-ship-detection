from ultralytics import YOLO
import torch
import sys

# --- Main Training Function ---
def main():
    """
    This script trains a YOLOv8 object detection model on a custom dataset.
    All key hyperparameters are exposed for easy tuning.
    """
    # Check for available hardware accelerators (CUDA, MPS, or CPU)
    if torch.cuda.is_available():
        device = 'cuda'
    elif sys.platform == 'darwin' and torch.backends.mps.is_available():
        # Check for Apple Metal Performance Shaders (MPS) on macOS
        device = 'mps'
    else:
        device = 'cpu'
    print(f"Using device: {device}")

    # 1. Load a pre-trained model
    # 'yolov8n.pt' is the smallest and fastest model.
    # For more accuracy, you can use 'yolov8s.pt', 'yolov8m.pt', etc.
    model = YOLO('yolov8n.pt')

    # 2. Train the model with tunable hyperparameters
    try:
        results = model.train(
            # --- Essential Parameters ---
            data='./data.yaml',         # Path to your dataset configuration file
            epochs=100,               # Total number of training epochs
            imgsz=640,                # Input image size
            device=device,            # Device to run on (auto-detected)
            batch=16,                 # Number of images per batch (-1 for auto-batch)
            name='yolo_final_run', # Renamed for clarity
            workers = 0,

            # --- Optimization Hyperparameters ---
            optimizer='Adam',       # Adam can sometimes perform better on smaller datasets
            lr0=0.005,              # A slightly lower learning rate can help prevent overfitting
            lrf=0.01,               # Final learning rate factor (final_lr = lr0 * lrf)
            momentum=0.937,         # SGD momentum/Adam beta1
            weight_decay=0.0005,    # Optimizer weight decay

            # --- AGGRESSIVE AUGMENTATION for Small Datasets ---
            degrees=15.0,           # Increased image rotation (+/- 15 deg)
            translate=0.1,          # Image translation (+/- fraction)
            scale=0.6,              # Increased image scale (+/- gain)
            shear=2.0,              # Added image shear (+/- 2 deg)
            perspective=0.001,      # Added slight image perspective
            flipud=0.3,             # Added up-down flip (30% chance), useful for aerial/satellite images
            fliplr=0.5,             # Image flip left-right (probability)
            mosaic=1.0,             # Mosaic augmentation is highly recommended for small datasets
            mixup=0.1,              # Added MixUp augmentation (10% chance) as a strong regularizer

            # --- Training Strategy ---
            patience=30,            # Stop a bit earlier if no improvement to prevent overfitting
            warmup_epochs=3.0,      # Number of warmup epochs (can be a fraction)
            close_mosaic=10         # Disable mosaic augmentation for the last N epochs
        )
        print("Training completed successfully.")
        print(f"Results saved to: {results.save_dir}")

    except Exception as e:
        print(f"An error occurred during training: {e}")


# --- Script Execution ---
if __name__ == '__main__':
    # This ensures the main function is called only when the script is executed directly
    main()

