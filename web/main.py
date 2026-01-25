'''
Module main.py
Flask application providing AIS data visualization and path prediction services.
'''
import io
import os
from datetime import datetime

import numpy as np
import rasterio
from flask import Flask, jsonify, render_template, request, send_file
from PIL import Image

from predictors import CVKF
from ingestion import AISPage



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


    


# @app.route("/api/get_images", methods=["POST"])
# def get_images():
#     '''Fetch satellite images for a specified bounding box and date range.
#     Expects a JSON payload with 'bbox', 'start_date', and 'end_date' keys in a POST request.
#     :return: JSON response containing image metadata or error message
#     '''
        #TODO re-enable this endpoint
#     data = request.get_json()
#     bbox = data["bbox"]
#     start_date = datetime.fromisoformat(data["start_date"])
#     end_date = datetime.fromisoformat(data["end_date"])

#     # Correctly parse the bounding box from the request
#     min_lon = min(point[1] for point in bbox)
#     max_lon = max(point[1] for point in bbox)
#     min_lat = min(point[0] for point in bbox)
#     max_lat = max(point[0] for point in bbox)
#     bbox_list = [min_lon, min_lat, max_lon, max_lat]
    
#     print(f"🌍 Received BBox request for: {bbox_list}")

#     s2 = Sentinel2Downloader(bbox_list, cache_folder=CACHE_FOLDER)

#     # This now calls the method that downloads and merges a full mosaic
#     img_data = s2.get_large_area_images(start_date=start_date, end_date=end_date)
    
#     if not img_data:
#         return jsonify({"message": "No images could be generated for the selected area and date."}), 404

#     info = img_data["info"]
#     return jsonify({
#         "message": "Image mosaic fetched successfully",
#         "img_data": [{
#             "id": info["id"],
#             "bbox": info["bbox"],
#             "meta": info, # contains datetime, etc.
#         }]
#     })

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


if __name__ == "__main__":
    app.run(debug=True)
