# Maritime Intelligence: Multi-Sensor "Dark Ship" Detection

A geospatial data fusion and computer vision pipeline designed to identify **"Dark Ships"**—vessels that intentionally deactivate their Automatic Identification System (AIS) transponders to evade sanctions, engage in illegal fishing, or conduct maritime sabotage.

## 🚢 The Challenge: The Asynchronicity Gap

The primary difficulty in dark ship detection is the **temporal and kinematic misalignment** between two disparate data sources:

1.  **AIS Telemetry:** High-frequency, self-reported GPS data. (Often missing or spoofed).
2.  **SAR (Synthetic Aperture Radar):** Satellite imagery that "sees" through clouds and darkness to provide ground truth. (Infrequent captures).

**The Problem:** Because AIS broadcasts and SAR captures rarely coincide, we must predict where a ship *should* be at the exact moment of the satellite overpass. In congested, narrow corridors like the **Irish Sea**, standard linear motion models fail because vessels must perform non-linear maneuvers to follow shipping channels and avoid collisions.

## 🛠 Features & Architecture

### 1. Synthetic Data Generation Engine
Since real-world "ground truth" for covert vessels is virtually non-existent, I built a robust **Synthetic Data Pipeline**. 
* **Path Simulation:** Generates realistic, non-linear vessel trajectories constrained by maritime geography.
* **Track Masking:** Programmatically removes AIS segments to simulate "dark" behavior for model training and validation.
* **Noise Injection:** Simulates sensor drift and latency to stress-test the association logic.

### 2. State Estimation & Association (Kalman Filtering)
* Implemented a **Kalman Filter (KF)** framework to bridge the temporal gap between the last known AIS ping and the SAR timestamp.
* The system uses predictive state estimation to create "search windows" for SAR detections.
* *Note: Currently transitioning to EKF (Extended Kalman Filter) to better model the angular velocity and centripetal acceleration required for channel navigation.*

### 3. Computer Vision (YOLO)
* Utilizes **YOLO-based object detection** to automate vessel identification within SAR imagery.
* Processes raw satellite captures to extract georeferenced bounding boxes for all visible hulls, which are then fed into the fusion pipeline.

## 💻 Tech Stack

* **Language:** Python 3.10+
* **Computer Vision:** PyTorch, YOLOv8
* **Data Science:** NumPy, SciPy, Pandas
* **Geospatial:** GeoPandas, Shapely, PyProj (for coordinate transformations)
* **Simulation:** Custom-built synthetic trajectory engine

## 📊 Pipeline Overview

1.  **Ingestion:** Import raw AIS streams and SAR imagery.
2.  **Inference:** YOLO identifies vessel coordinates in the SAR frame.
3.  **Estimation:** Kalman Filter predicts the expected position of all AIS-transmitting ships at $T_{SAR}$.
4.  **Association:** The system calculates the likelihood of association. Detections in SAR that cannot be mapped to an AIS track are flagged as **Dark Ships**.

## 📈 Roadmap
- [ ] **Non-Linear State Estimation:** Upgrade from Linear KF to Unscented Kalman Filter (UKF) for improved tracking in narrow straits.
- [ ] **Multi-Hypothesis Tracking (MHT):** Improve association accuracy when multiple vessels are in close proximity.
- [ ] **Batch Processing:** Scalable Dockerized architecture for processing large-scale SAR swaths.

---
*Developed as a solution for automated maritime surveillance
