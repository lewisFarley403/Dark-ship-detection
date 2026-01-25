from ultralytics import YOLO

def main():
    # 1. Load the weights from your COMPLETED run
    # (We use 'last.pt' so we don't lose the progress from the end of the run)
    model = YOLO('runs/detect/yolo_small_dataset_run12/weights/last.pt')

    # 2. Start a NEW training session
    # We do NOT use resume=True. We just treat this as a new run with pre-trained weights.
    results = model.train(
        data='./data.yaml',
        epochs=100,        # This means "train for 100 MORE epochs"
        imgsz=640,
        batch=16,
        device='mps',      # or 'mps'/'cpu'
        
        # Optional: You might want to lower the learning rate slightly since
        # the model is already partially trained, but since your graphs were 
        # still dropping steeply, the default (lr0=0.01) is probably fine.
        lr0=0.005,         
        name='yolo_extended_run' # Give it a new name to keep logs separate
    )

if __name__ == '__main__':
    main()