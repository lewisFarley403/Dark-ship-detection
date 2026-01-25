import datetime
from matplotlib.dviread import Page
import numpy as np
import matplotlib.pyplot as plt
import environment
from sentinelhub import (
    SHConfig,
    SentinelHubRequest,
    DataCollection,
    MimeType,
    CRS,
    BBox,
    SentinelHubCatalog,
    bbox_to_dimensions
)
from shapely.geometry import box,Point
from predictors import Track,AISPage
from datetime import datetime
from core.utils import load_sentinel_creds


def get_true_color_image(bbox_coords, start_date, end_date, is_optical = False,min_overlap:float = 0.7):
    """
    Fetches the least cloudy true-color (RGB) Sentinel-2 image for a given
    bounding box and time interval.

    Args:
        bbox_coords (tuple): A tuple of four floats representing the bounding box
                             in WGS84 coordinates: (min_lon, min_lat, max_lon, max_lat).
        start_date (str): The start of the time interval in 'YYYY-MM-DD' format.
        end_date (str): The end of the time interval in 'YYYY-MM-DD' format.
        search_term (str): The type of satalite image, s2l2a for optical colour, s1iw SAR
    
    Returns:
        tuple: A tuple containing:
            - np.ndarray: The image as a NumPy array (height, width, 3).
            - str: The acquisition date of the image in 'YYYY-MM-DD' format.
        Returns (None, None) if no images are found.
    """
    # --- Configuration for Copernicus Data Space Ecosystem ---
    
    config = SHConfig()
    clientid,clientsecret = load_sentinel_creds(config)
    config.sh_client_id = clientid
    config.sh_client_secret = clientsecret
    config.sh_token_url = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
    config.sh_base_url = "https://sh.dataspace.copernicus.eu"
    
    # This is your personal Instance ID from the "Configuration Utility".
    config.instance_id = "29e22b00-5743-4b99-9035-de16e8c95f02"

    # --- 1. Define Bounding Box and Time Interval ---
    bbox = BBox(bbox=bbox_coords, crs=CRS.WGS84)
    time_interval = (start_date, end_date)
    if is_optical:
        search_term = 's2l2a'
    else:
        search_term='s1iw'
    # --- 2. Search for the least cloudy scene ---
    try:
        # Define the data collection to ensure it uses the Copernicus endpoint
        if is_optical:
            data_collection = DataCollection.SENTINEL2_L2A.define_from(
                search_term, service_url="https://sh.dataspace.copernicus.eu"
            )
        else:
            data_collection = DataCollection.SENTINEL1_IW.define_from(
                search_term, service_url="https://sh.dataspace.copernicus.eu"
            )
        catalog = SentinelHubCatalog(config=config)
        search_iterator = catalog.search(
            data_collection,
            bbox=bbox,
            time=time_interval,
            # fields={"include": ["id", "properties.datetime", "properties.eo:cloud_cover"], "exclude": []},
        )
        
        all_results = list(search_iterator)
        # print(f'Results Found : {len(all_results)}')
        # # print(list(all_results[0].keys()))
        # print(bbox_coords)
        # print(all_results[0]['bbox'])
        # print(compute_bbox_crossover(bbox_coords,all_results[0]['bbox']))
        if not all_results:
            print("No scenes found for the given criteria.")
            return None, None

        # Find the result with the minimum cloud cover
        # best_scene = min(all_results, key=lambda x: x["properties"]["eo:cloud_cover"])
        # best_scene = max(all_results, key=lambda x: compute_bbox_crossover(x['bbox'],bbox_coords))
        best_scenes_iterator = list(filter(
        lambda x: compute_bbox_crossover( bbox_coords,x['bbox']) > min_overlap, 
        all_results
    ))
        best_scenes = list(best_scenes_iterator)
        print(f'Found {len(best_scenes)} scenes with > {min_overlap*100}% overlap')
        for best_scene in best_scenes:
            overlap = compute_bbox_crossover(best_scene['bbox'],bbox_coords)
            # print(f'Showing scene with {overlap*100}% overlap')
            acquisition_date = best_scene["properties"]["datetime"].split("T")[0]
        if is_optical:
            cloud_cover = best_scene["properties"]["eo:cloud_cover"]
        else:
            cloud_cover = 0
        # print(f"Found scene with {cloud_cover}% cloud cover on {acquisition_date}")

    except Exception as e:
        print(f"Error searching for scenes: {e}")
        return None, None


    # --- 3. Define the request for the true-color image ---
    # An evalscript to return true-color RGB bands.
    # It selects bands 4 (Red), 3 (Green), and 2 (Blue) and scales them.
    if is_optical:
        evalscript_true_color = """
            //VERSION=3
            function setup() {
                return {
                    input: ["B04", "B03", "B02"],
                    output: { bands: 3 }
                };
            }

            function evaluatePixel(sample) {
                return [2.5 * sample.B04, 2.5 * sample.B03, 2.5 * sample.B02];
            }
        """
    else:
        evalscript_true_color='''
        // VERSION: 3
        function setup() {
        return {
            input: ["VV", "VH"],
            output: { bands: 2, sampleType: "FLOAT32" }
        };
        }

        function evaluatePixel(sample) {
        const vv = 10 * Math.log10(sample.VV);
        const vh = 10 * Math.log10(sample.VH);
        return [vv, vh];
        }
        '''
    imgs = []
    for best_scene in best_scenes_iterator:
        # acquisition_date = best_scene["properties"]["datetime"].split("T")[0]
        acquisition_date = best_scene["properties"]["datetime"]
        print(best_scene['bbox'])
        request = SentinelHubRequest(
            evalscript=evalscript_true_color,
            input_data=[
                SentinelHubRequest.input_data(
                    data_collection=data_collection, # Use the defined collection
                    time_interval=(best_scene['properties']['datetime'], best_scene['properties']['datetime']),
                )
            ],
            responses=[SentinelHubRequest.output_response("default", MimeType.TIFF)],
            bbox=bbox,
            config=config,
        )

        # --- 4. Get the data ---
        try:
            image_data = request.get_data()[0]
            imgs.append({'img':image_data, 'date':acquisition_date,'bbox':best_scene['bbox']})
        except Exception as e:
            print(f"Error downloading image data: {e}")
            return None
    return imgs
def compute_bbox_area(bbox):
    """Compute area of a bounding box (lon_min, lat_min, lon_max, lat_max)."""
    minx, miny, maxx, maxy = bbox
    return abs((maxx - minx) * (maxy - miny))

def compute_bbox_crossover(img, bbox):
    """Return fraction of img bbox that overlaps with another bbox."""
    poly1 = box(*img)
    poly2 = box(*bbox)

    intersection = poly1.intersection(poly2)

    if intersection.is_empty:
        return 0.0  # no overlap

    overlap_area = intersection.area
    total_area = poly1.area

    return overlap_area / total_area

def get_image_AIS_pairs(target_bbox,start:datetime, end:datetime,is_optical = False,min_overlap = 0.7):
    '''
    Creates a list of all satellite images between the datetimes and the corresponding AIS trackd
    
    :param start: Description
    :type start: Datetime
    :param end: Description
    :type end: Datetime
    '''
    satellite_data = get_true_color_image(target_bbox,start,end,is_optical=is_optical,min_overlap=min_overlap)
    for satallite in satellite_data:
        # print('bbox')
        # print(satallite)
        bbox = satallite['bbox']
        bbox_obj = box(*bbox)
        # print(bbox)
        img = satallite['img']
        str_date = (satallite['date'])
        # print(str_date)
        # print('str time ',str_date)
        date = datetime.strptime(str_date, "%Y-%m-%dT%H:%M:%SZ")

        # print(f'date {date}')

        page = AISPage(date)

        filtered_page = page.filter_bbox(bbox).filter_datetime(date)
        # print(filtered_page.full_ais_df[['Lat', 'Lon']].describe())

        yield img,filtered_page,date,bbox_obj.intersection(box(*target_bbox))
if __name__ == '__main__':
    # --- Example Usage ---
    # Bounding box for the area around the Golden Gate Bridge, San Francisco
    golden_gate_bbox = (-6.484680,53.215902,-4.534607,53.460255)
    
    # Time interval
    start_time = "2023-06-01"
    end_time = "2023-06-10"
    data = get_image_AIS_pairs(golden_gate_bbox,start_time,end_time)
    d = next(data)
    print(len(list(d[1].get_all_tracks())))
    print(d[-2])
    print(d[-1])
    plt.imshow(d[0][:,:,1])

    plt.show()

    # print(f"Fetching image for bbox {golden_gate_bbox} between {start_time} and {end_time}")
    
    # # Fetch the image and date
    # true_color_image = get_true_color_image(golden_gate_bbox, start_time, end_time,is_optical=False)
    # print(true_color_image[0][0].shape)
    # date_taken = true_color_image[0][-1]

    # # If successful, display the image
    # if true_color_image is not None and date_taken is not None:
    #     print(f"\nImage successfully retrieved.")
    #     print(f"Date taken: {date_taken}")

    #     # Display the image using matplotlib
    #     plt.figure(figsize=(10, 10))
    #     plt.imshow(true_color_image[0][0][:,:,1])
    #     plt.title(f"Sentinel-2 True-Color Image\nDate: {date_taken}")
    #     plt.xlabel("Longitude")
    #     plt.ylabel("Latitude")
    #     plt.grid(False)
    #     plt.show()