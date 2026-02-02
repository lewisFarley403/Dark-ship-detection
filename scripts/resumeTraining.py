from ultralytics import YOLO
import sys
from pathlib import Path

def main(run_name):
    project_root = Path(__file__).resolve().parent.parent 
    
    # 2. Construct the full path to the weights file
    # This assumes standard YOLO structure: runs/detect/<name>/weights/last.pt
    weights_path = project_root / 'runs' / 'detect' / run_name / 'weights' / 'last.pt'
    model = YOLO(weights_path)
    current_dir = Path(__file__).resolve().parent

    # 2. Point to the file inside that same folder
    yaml_path = current_dir / "data.yaml"

    # 2. Start a NEW training session
    # We do NOT use resume=True. We just treat this as a new run with pre-trained weights.
    results = model.train(
        data=yaml_path,
        epochs=100,        # This means "train for 100 MORE epochs"
        imgsz=640,
        batch=16,
        device='cuda',      # or 'mps'/'cpu'
        
        # Optional: You might want to lower the learning rate slightly since
        # the model is already partially trained, but since your graphs were 
        # still dropping steeply, the default (lr0=0.01) is probably fine.
        lr0=0.005,         
        name='yolo_extended_run' # Give it a new name to keep logs separate
    )

if __name__ == '__main__':
    name = sys.argv[1]
    main(name)