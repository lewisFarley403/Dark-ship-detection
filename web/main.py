'''
Module main.py
Flask application providing AIS data visualization and path prediction services.
'''
import io
import os
from datetime import datetime,timedelta

import numpy as np
import rasterio
from flask import Flask, jsonify, render_template, request, send_file
from PIL import Image
import pandas as pd 

from .serialisers import SentinelWebSerialiser
from core.predictors import CVKF
from core.ingestion import AISPage
from core.sentinel_downloader import SentinelScene,get_true_color_image,get_image_AIS_pairs
from core.utils import parse_datetime_to_str
from pathlib import Path
current_dir = Path(__file__).resolve().parent
parent_dir = current_dir.parent
from core.sentinel_downloader import get_true_color_image
from ultralytics import YOLO
model = YOLO('./models/runs/detect/good_hp_run2/weights/best.pt')


app = Flask(__name__)
# The cache folder should be consistent with the one used in Sentinel2Downloader
CACHE_FOLDER = "cache"
@app.route('/vis')
def vis():
    '''
    Return the AIS visualization page
    :return: Rendered HTML template for AIS visualization
    '''
    return render_template('AIS.html')
@app.route('/api/get_paths',methods = ['POST'])
def make_path():
    '''Return AIS paths for a given time period. Method expects a JSON payload with 'start_date' key and a POST request
    :return: JSON response containing AIS paths
    '''
    data = request.get_json()
    start = data['start_date']
    start = datetime.strptime(start,'%Y-%m-%dT%H:%M')

    ais = AISPage(start)
    return jsonify(ais.get_ais_dicts())

@app.route("/")
def home():
    '''
    Returns the home page of the application.
    :return: Rendered HTML template for the home page
    '''
    return render_template("download.html")
@app.route('/api/predict_path',methods = ['POST'])
def predict_course():
    '''
    Predict the future course of a vessel using CVKF based on provided AIS data.
    Expects a JSON payload with 'node_data', 'predictor', and 'dt' keys in a POST request.
    :return: JSON response containing the predicted position
    '''
    data = request.get_json()
    print(data)

    node_data = data['node_data']
    # predictor = data['predictor'] TODO implement multiple predictors
    dt = float(data['dt'])
    mmsi = node_data['MMSI']

    date_obj = datetime.strptime(node_data['DTG'],"%a, %d %b %Y %H:%M:%S GMT")
    page = AISPage(date_obj)
    track = page.get_track(mmsi)
    subtrack = track.time_subrack(date_obj)
    cvkf = CVKF(subtrack[:-1])
    output = cvkf.predict_with_best(subtrack,dt)
    return jsonify({'prediction':output})


    


@app.route("/api/get_images", methods=["POST"])
def get_images():
    '''Fetch satellite images for a specified bounding box and date range.
    Expects a JSON payload with 'bbox', 'start_date', and 'end_date' keys in a POST request.
    :return: JSON response containing image metadata or error message
    '''
    # TODO re-enable this endpoint
    data = request.get_json()
    bbox = data["bbox"]
    start_date = datetime.fromisoformat(data["start_date"])
    min_lon = min(point[1] for point in bbox)
    max_lon = max(point[1] for point in bbox)
    min_lat = min(point[0] for point in bbox)
    max_lat = max(point[0] for point in bbox)
    bbox_list = [min_lon, min_lat, max_lon, max_lat]
    end_date = datetime.fromisoformat(data["end_date"])
    # two_weeks_before = start_date - timedelta(weeks=2)
    two_weeks_after = parse_datetime_to_str(start_date + timedelta(weeks=2))
    start_date = parse_datetime_to_str(start_date)

    pair = list(get_image_AIS_pairs(bbox_list,start_date,two_weeks_after))[0] # we want the one closest to the start date
    dt = pd.Timedelta(minutes=59) # time between ais and sat, prolly make adjustable in future
    target = pd.to_datetime(pair[2])
    scene = pair[0]
    scene.download()
    pair_df = pair[1].get_full_df()
    rows = pair_df[(pair_df['DTG'] - target).abs()<dt]
    print(len(rows))
    mmsis = list(set(rows['MMSI'])) # all unique mmsi
    pings = []
    for mmsi in mmsis:
        msg = rows[rows['MMSI'] == mmsi].iloc[0] # if there is more than 1, they are very close together so it doesnt matter
        coord = [float(msg['Lat']),float(msg['Lon'])]
        pings.append({'mmsi':mmsi, 'coord':coord})
    serialiser = SentinelWebSerialiser('./web/static/img_cache','/static/img_cache')
    web_payload = serialiser.serialise(scene)

    web_payload['pings'] = pings
    ai_pings = scene.detect_vessels(model)
    web_payload['ai_pings']=ai_pings
    print(f'AI found {len(ai_pings)} vessels')
    return jsonify(web_payload)

# In app.py

@app.route("/api/image_overlay")
def image_overlay():
    '''
    Serve a cached GeoTIFF image as a PNG for overlaying on maps.
    Expects a query parameter 'id' specifying the image identifier.
    :return: PNG image file or error message
    '''
    product_id = request.args.get("id")
    if not product_id:
        return "Missing product id", 400

    safe_id = product_id.replace("/", "_").replace(":", "_")
    img_path = os.path.join(CACHE_FOLDER, "img_cache", f"{safe_id}.tiff")

    if not os.path.exists(img_path):
        return "Image not found in cache", 404

    try:
        # 1. Open the GeoTIFF with rasterio. It's now a simple 8-bit RGB.
        with rasterio.open(img_path) as src:
            # Read the UINT8 data directly
            img_array = src.read()
            # Transpose from (bands, height, width) to (height, width, bands)
            img_array = np.moveaxis(img_array, 0, -1)

        # 2. Create PIL Image and serve it. No scaling or normalization is needed.
        img_pil = Image.fromarray(img_array)
        img_byte_arr = io.BytesIO()
        img_pil.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)

        return send_file(img_byte_arr, mimetype="image/png")

    except Exception as e:
        print(f"Error converting TIFF to PNG: {e}")
        return "Failed to process image file", 500
@app.route("/training", methods=["GET"])
def train_model():
    '''
    Allows the visualisation of training progress and results. Expects a POST request to trigger the training process.
    '''
    all_runs = os.listdir(parent_dir/'runs/detect')
    return render_template("training.html", runs=all_runs)
@app.route("/api/training_data", methods=["GET"])
def get_training_data():
    '''
    Fetches training data for a specific training run to be visualized on the frontend.
    :param run_name: Name of the training run (e.g., 'tune2')
    :return: JSON response containing training metrics or error message
    '''
    run_name = request.args.get("run")
    run_path = parent_dir / 'runs/detect' / run_name / 'results.csv'
    if not run_path.exists():
        return jsonify({"message": "Training data not found for the specified run."}), 404

    try:
        # Read the CSV file and extract relevant metrics
        import pandas as pd
        df = pd.read_csv(run_path)
        # For simplicity, we return all columns. In practice, you might want to filter this.
        data = df.to_dict(orient='list')
        print(list(data.keys()))
        return jsonify(data)

    except Exception as e:
        print(f"Error reading training data: {e}")
        return jsonify({"message": "Failed to read training data."}), 500
if __name__ == "__main__":
    app.run(debug=True)
