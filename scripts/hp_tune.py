from ultralytics import YOLO
import torch

def run_tuning():
    custom_search_space = {
    # Geometric Unfreezing (the ones that were stuck at 0)
    "degrees": (1e-3, 45.0),    
    "translate": (1e-3, 0.9),  # Set to 0.1 for SAR to keep ships in frame
    "shear": (1e-3, 10.0),     
    "perspective": (1e-5, 0.001),
    
    # Optimization (keeping these active)
    "lr0": (1e-5, 1e-1),
    "lrf": (0.01, 1.0),
    "momentum": (0.6, 0.98),
    "weight_decay": (0.0, 0.001),
}
    # 1. Check for GPU (Just a sanity check)
    if not torch.cuda.is_available():
        print("WARNING: CUDA not available. Tuning on CPU will take forever!")
    else:
        print(f"Tuning on {torch.cuda.get_device_name(0)}")

    # 2. Load the base model
    # Start with 'yolov8n.pt' (Nano). It tunes faster. 
    # The HPs found for Nano usually transfer well to Small/Medium models too.
    model = YOLO('yolov8n.pt') 

    # 3. Define your data path (Update if needed)
    data_path = '/home/links/lf507/Dark-ship-detection/scripts/data.yaml'

    # 4. Run the Evolution (Tuning)
    # This is the heavy lifting.
    model.tune(
        data=data_path,
        
        # GPU / Hardware Settings
        device=0,          # Use first GPU
        workers=8,         # Use 8 CPU threads for data loading (adjust based on your CPU)
        
        # Tuning Settings
        epochs=30,         # Train each "generation" for 30 epochs (enough to see convergence on SSDD)
        iterations=200,     # Try 50 different HP combinations (higher = better results but longer time)
        
        # Optimization
        optimizer='AdamW', # AdamW is generally better for Transformers/YOLOv8 than SGD
        batch=16,          # Keep batch size manageable
        imgsz=640,         # Standard YOLO input size
        
        # Outputs
        plots=True,        # Automatically generate scatter plots of HPs vs. mAP
        save=False,        # False = Don't save checkpoint for every single iteration (saves disk space)
        val=True     ,      # Validate using the 'val' set in data.yaml
        space = custom_search_space,
        resume=True,
        project='runs/detect', 
        name='tune2',
    )

if __name__ == '__main__':
    run_tuning()