import datetime
import math
from matplotlib.dviread import Page
import numpy as np
import matplotlib.pyplot as plt
# import environment
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
# from .models import Track
from .ingestion import AISPage
from datetime import datetime
from core.utils import load_sentinel_creds
optical_eval = """
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
SAR_eval = '''
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
def create_sentinel_config():
    config = SHConfig()
    clientid,clientsecret,instance_id = load_sentinel_creds()
    config.sh_client_id = clientid
    config.sh_client_secret = clientsecret
    config.sh_token_url = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
    config.sh_base_url = "https://sh.dataspace.copernicus.eu"
    
    config.instance_id = instance_id
    return config
# def get_true_color_image(bbox_coords, start_date, end_date, is_optical = False,min_overlap:float = 0.7):
#     """
#     Fetches the least cloudy true-color (RGB) Sentinel-2 image for a given
#     bounding box and time interval.

#     Args:
#         bbox_coords (tuple): A tuple of four floats representing the bounding box
#                              in WGS84 coordinates: (min_lon, min_lat, max_lon, max_lat).
#         start_date (str): The start of the time interval in 'YYYY-MM-DD' format.
#         end_date (str): The end of the time interval in 'YYYY-MM-DD' format.
#         search_term (str): The type of satalite image, s2l2a for optical colour, s1iw SAR
    
#     Returns:
#         tuple: A tuple containing:
#             - np.ndarray: The image as a NumPy array (height, width, 3).
#             - str: The acquisition date of the image in 'YYYY-MM-DD' format.
#         Returns (None, None) if no images are found.
#     """
#     # --- Configuration for Copernicus Data Space Ecosystem ---
    
#     config = create_sentinel_config()

#     # --- 1. Define Bounding Box and Time Interval ---
#     bbox = BBox(bbox=bbox_coords, crs=CRS.WGS84)
#     time_interval = (start_date, end_date)
#     if is_optical:
#         search_term = 's2l2a'
#         evalscript_true_color = optical_eval
#     else:
#         search_term='s1iw'
#         evalscript_true_color = SAR_eval
#     # --- 2. Search for the least cloudy scene ---
#     try:
#         # Define the data collection to ensure it uses the Copernicus endpoint
#         if is_optical:
#             data_collection = DataCollection.SENTINEL2_L2A.define_from(
#                 search_term, service_url="https://sh.dataspace.copernicus.eu"
#             )
#         else:
#             data_collection = DataCollection.SENTINEL1_IW.define_from(
#                 search_term, service_url="https://sh.dataspace.copernicus.eu"
#             )
#         catalog = SentinelHubCatalog(config=config)
#         search_iterator = catalog.search(
#             data_collection,
#             bbox=bbox,
#             time=time_interval,
#         )
        
#         all_results = list(search_iterator)
#         if not all_results:
#             print("No scenes found for the given criteria.")
#             return None, None
        
#         best_scenes_iterator = list(filter(
#         lambda x: compute_bbox_crossover( bbox_coords,x['bbox']) > min_overlap, 
#         all_results
#     ))
#         best_scenes = list(best_scenes_iterator)
#         # print(f'Found {len(best_scenes)} scenes with > {min_overlap*100}% overlap')
#         for best_scene in best_scenes:
#             overlap = compute_bbox_crossover(best_scene['bbox'],bbox_coords)
#             # print(f'Showing scene with {overlap*100}% overlap')
#             acquisition_date = best_scene["properties"]["datetime"].split("T")[0]
#         if is_optical:
#             cloud_cover = best_scene["properties"]["eo:cloud_cover"]
#         else:
#             cloud_cover = 0
#         # print(f"Found scene with {cloud_cover}% cloud cover on {acquisition_date}")

#     except Exception as e:
#         print(f"Error searching for scenes: {e}")
#         return None, None


#     # --- 3. Define the request for the true-color image ---
#     # An evalscript to return true-color RGB bands.
#     # It selects bands 4 (Red), 3 (Green), and 2 (Blue) and scales them.
#     imgs = []
#     for best_scene in best_scenes_iterator:

#         acquisition_date = best_scene["properties"]["datetime"]
#         original_bbox = bbox_coords
#         # print(best_scene['bbox'])
#         # print("SIZE ",bbox_to_dimensions(original_bbox, 10))

#         size = bbox_to_dimensions(BBox(bbox = original_bbox, crs = CRS.WGS84), 10)
#         # print("SIZE ",size)
        
#         # print(size[0]>2500)
        
#         if size[0] > 2500 or size[1] > 2500: # need to request smaller chunk
#             print('bbox needs breaking down ',size,bbox)
#             subboxes = []
#             # print("BOUNDING BOX" ,best_scene['bbox'])

#             scaleX = math.floor(size[0]/500)
#             scaleY = math.floor(size[1]/500)
#             try:
#                 lon_offset = (original_bbox[2]-original_bbox[0])/(scaleX)
#             except ZeroDivisionError:
#                 lon_offset = 0
#                 scaleX = 1
#             try:
#                 lat_offset = (original_bbox[3]-original_bbox[1])/scaleY
#             except ZeroDivisionError:
#                 lat_offset = 0
#                 scaleY = 1
#             # print(f"Scaling request down by factors {scaleX} and {scaleY}")
            
#             for i in range (scaleX):
#                 for j in range(scaleY):
#                     if lat_offset ==0:
#                         miny = original_bbox[1]
#                         maxy = original_bbox[3]
#                     else:
#                         miny = original_bbox[1] + j*lat_offset
#                         maxy = original_bbox[1] + (j+1)*lat_offset
                    
#                     if lon_offset ==0:
#                         minx = original_bbox[0]
#                         maxx = original_bbox[2]
#                     else:
#                         maxx = original_bbox[0] + (i+1)*lon_offset
#                         minx = original_bbox[0] + i*lon_offset
#                     if maxx > original_bbox[2]:
#                         maxx = original_bbox[2]
#                     if maxy> original_bbox[3]:
#                         maxy = original_bbox[3]
#                     subboxes.append([minx,miny,maxx,maxy])
#             print(f"Created {len(subboxes)} sub-boxes for downloading")
#             imgs_parts = []
#             for box in subboxes:
#                 # return
#                 parsed_date =  acquisition_date.split('T')[0]
#                 # print('date ',parsed_date, 'type ',type(parsed_date))

#                 part = get_true_color_image(box, parsed_date, parsed_date, is_optical=is_optical,min_overlap=0.0)
#                 if part:
#                     imgs_parts.append(part)
#             return imgs_parts
#         else:
#             request = SentinelHubRequest(
#                 evalscript=evalscript_true_color,
#                 input_data=[
#                     SentinelHubRequest.input_data(
#                         data_collection=data_collection, # Use the defined collection
#                         time_interval=(best_scene['properties']['datetime'], best_scene['properties']['datetime']),
#                     )
#                 ],
#                 responses=[SentinelHubRequest.output_response("default", MimeType.TIFF)],
#                 bbox=bbox,
#                 size =bbox_to_dimensions(bbox, 10),
#                 config=config,
#             )

#             # --- 4. Get the data ---
#             try:
#                 image_data = request.get_data()[0]
#                 imgs.append({'img':image_data, 'date':acquisition_date,'bbox':best_scene['bbox']})
#             except Exception as e:
#                 print(f"Error downloading image data: {e}")
#                 return None
#         return imgs

import math
from concurrent.futures import ThreadPoolExecutor, as_completed

def _single_download_request(bbox_coords, best_scene, data_collection, evalscript, config):
    """Worker function: Downloads a single tile."""
    from sentinelhub import BBox, CRS, SentinelHubRequest, bbox_to_dimensions
    # print('bbox single thread ',bbox_coords)
    bbox = BBox(bbox=bbox_coords[:4], crs=CRS.WGS84)
    size = bbox_to_dimensions(bbox, 10)
    
    request = SentinelHubRequest(
        evalscript=evalscript,
        input_data=[
            SentinelHubRequest.input_data(
                data_collection=data_collection,
                time_interval=(best_scene['properties']['datetime'], best_scene['properties']['datetime']),
            )
        ],
        responses=[SentinelHubRequest.output_response("default", MimeType.TIFF)],
        bbox=bbox,
        size=size,
        config=config,
    )
    # Return a dict so we know which bbox this data belongs to
    return {'img': request.get_data()[0], 'date': best_scene["properties"]["datetime"], 'bbox': bbox_coords, 'row':bbox_coords[4],'col':bbox_coords[5]}

def get_true_color_image(bbox_coords, start_date, end_date, is_optical=False, min_overlap:float=0.7, max_workers=8):
    config = create_sentinel_config()
    bbox = BBox(bbox=bbox_coords, crs=CRS.WGS84)
    
    # 1. Setup Collection and Evalscript
    if is_optical:
        search_term, data_col_type, evalscript = 's2l2a', DataCollection.SENTINEL2_L2A, optical_eval
    else:
        search_term, data_col_type, evalscript = 's1iw', DataCollection.SENTINEL1_IW, SAR_eval

    data_collection = data_col_type.define_from(search_term, service_url="https://sh.dataspace.copernicus.eu")
    catalog = SentinelHubCatalog(config=config)
    
    # 2. Search Once
    all_results = list(catalog.search(data_collection, bbox=bbox, time=(start_date, end_date)))
    if not all_results: return None
    best_scenes = [s for s in all_results if compute_bbox_crossover(bbox_coords, s['bbox']) > min_overlap]
    if not best_scenes: return None
    
    best_scene = best_scenes[0]
    size = bbox_to_dimensions(bbox, 10)

    # 3. Handle Tiling
    if size[0] > 2500 or size[1] > 2500:
        nx = math.ceil(size[0] / 2000)
        ny = math.ceil(size[1] / 2000)
        print(f"THREADED GRID: Dispatching {nx*ny} tiles across {max_workers} threads...")

        lon_step = (bbox_coords[2] - bbox_coords[0]) / nx
        lat_step = (bbox_coords[3] - bbox_coords[1]) / ny
        
        sub_boxes = []
        for i in range(nx):
            for j in range(ny):
                sub_boxes.append((
                    bbox_coords[0] + i * lon_step,
                    bbox_coords[1] + j * lat_step,
                    bbox_coords[0] + (i+1) * lon_step,
                    bbox_coords[1] + (j+1) * lat_step,
                    i,j
                ))

        # 4. The Thread Pool Execution
        imgs = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Create a dictionary to map futures to their box index (to maintain order if needed)
            future_to_box = {
                executor.submit(_single_download_request, box, best_scene, data_collection, evalscript, config): box 
                for box in sub_boxes
            }
            
            for future in as_completed(future_to_box):
                try:
                    result = future.result()
                    imgs.append(result)
                    print(f"  Finished {len(imgs)}/{len(sub_boxes)}...")
                except Exception as e:
                    print(f"  Tile download failed: {e}")
        
        return imgs

    # Single download if small
    return [_single_download_request(bbox_coords, best_scene, data_collection, evalscript, config)]
import numpy as np

# def stitch_tiles(tiles):
#     """
#     Stitches a list of dictionaries [{'img': ndarray, 'bbox': tuple}, ...] 
#     into a single cohesive image.
#     """
#     if not tiles:
#         return None

#     # 1. Find the global bounds of all tiles
#     all_bboxes = np.array([t['bbox'] for t in tiles])
#     rows = np.max(all_bboxes[:,4])+1
#     cols = np.max(all_bboxes[:,5])+1

#     maxwidth = np.max(np.array([t['img'].shape[1] for t in tiles]))
#     maxheight = np.max(np.array([t['img'].shape[0] for t in tiles]))
#     print(maxwidth,maxheight)
#     canvas = np.zeros((int(rows*maxheight),int(cols*maxwidth),2))
#     for t in tiles:
#         h, w = t['img'].shape[:2]

#         y_start = int(t['row'] * maxheight)
#         x_start = int(t['col'] * maxwidth)

#         # Use y_start + h and x_start + w
#         # This makes the slice on the left EXACTLY match the shape on the right
#         canvas[y_start : y_start + h, x_start : x_start + w, :] = t['img']
#     return canvas

# def stitch_tiles(tiles):
#     if not tiles:
#         return None

#     # 1. Filter out fails
#     tiles = [t for t in tiles if t is not None]
    
#     # 2. Get Grid Counts
#     num_rows = int(max(t['row'] for t in tiles)) + 1
#     num_cols = int(max(t['col'] for t in tiles)) + 1

#     # 3. Find Max Dimensions (Height, Width)
#     max_h = int(max(t['img'].shape[0] for t in tiles))
#     max_w = int(max(t['img'].shape[1] for t in tiles))
#     channels = tiles[0]['img'].shape[2]
    
#     # 4. Create the Canvas
#     canvas = np.zeros((num_rows * max_h, num_cols * max_w, channels), dtype=tiles[0]['img'].dtype)

#     for t in tiles:
#         h, w = t['img'].shape[:2]
#         r, c = t['row'], t['col']
        
#         # --- THE FIX ---
#         # Invert the row so Row 0 (South) becomes the bottom of the image
#         actual_row = (num_rows - 1) - r 
        
#         y_off = actual_row * max_h
#         x_off = c * max_w
        
#         # Dynamic slice to prevent broadcast errors
#         canvas[y_off : y_off + h, x_off : x_off + w, :] = t['img']

#     return canvas
def stitch_tiles(tiles):
    if not tiles:
        return None

    # Filter out failed downloads
    tiles = [t for t in tiles if t is not None]
    
    # 1. Swap the Grid Counts logic
    # If it was rotated, what you thought were rows might be columns
    max_idx_1 = int(max(t['row'] for t in tiles)) + 1
    max_idx_2 = int(max(t['col'] for t in tiles)) + 1

    # 2. Get Dimensions (H, W)
    tile_h = int(max(t['img'].shape[0] for t in tiles))
    tile_w = int(max(t['img'].shape[1] for t in tiles))
    
    # 3. Create the Canvas
    # We swap these: use max_idx_1 for width and max_idx_2 for height
    canvas = np.zeros((max_idx_2 * tile_h, max_idx_1 * tile_w, 2), dtype=tiles[0]['img'].dtype)

    for t in tiles:
        h, w = t['img'].shape[:2]
        r, c = int(t['row']), int(t['col'])
        
        # 4. SWAP THE OFFSETS
        # Instead of row controlling Y, let col control Y and row control X
        y_off = c * tile_h
        x_off = r * tile_w
        
        # Apply the tile using dynamic slicing to the new swapped offsets
        canvas[y_off : y_off + h, x_off : x_off + w, :] = t['img']

    return canvas

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

def plot_image_patches(tiles):
    if not tiles:
        print("No tiles to plot!")
        return

    num_tiles = len(tiles)
    cols = 4  # Set how many tiles per row in the plot
    rows = math.ceil(num_tiles / cols)

    fig, axes = plt.subplots(rows, cols, figsize=(20, rows * 4))
    axes = axes.flatten() # Flatten to 1D to loop easily

    for i, t in enumerate(tiles):
        ax = axes[i]
        # SAR Data: Display VV channel (index 0) and clip for contrast
        # clipping at -25 to 0 dB makes features (ships/land) visible
        img_data = np.clip(t['img'][:, :, 0], -25, 0)
        # img_data = t['img'][:, :, 0]
        
        ax.imshow(img_data, cmap='gray')
        
        # Display BBox and Grid Index
        bbox_str = ", ".join([f"{c:.3f}" for c in t['bbox'][:4]])
        ax.set_title(f"Row: {t['row']}, Col: {t['col']}\nBBox: [{bbox_str}]", fontsize=10)
        ax.axis('off')

    # Hide any unused subplots
    for j in range(i + 1, len(axes)):
        axes[j].axis('off')

    plt.tight_layout()
    plt.show()
if __name__ == '__main__':
    # --- Example Usage ---
    # Bounding box for the area around the Golden Gate Bridge, San Francisco
    golden_gate_bbox = (-6.484680,53.215902,-4.534607,53.460255) #full ferry
    # golden_gate_bbox = (-5.484680,53.215902,-4.534607,53.460255)

    
    # Time interval
    start_time = "2023-06-01"
    end_time = "2023-06-10"
    # data = get_image_AIS_pairs(golden_gate_bbox,start_time,end_time)
    # d = next(data)
    # print(len(list(d[1].get_all_tracks())))
    # print(d[-2])
    # print(d[-1])
    # print(d[0].shape)
    # plt.imshow(d[0][:,:,0])

    # plt.show()
    imgs = list(get_true_color_image(golden_gate_bbox,start_time,end_time))
    plot_image_patches(imgs)
    big = stitch_tiles(imgs)
    # Rotate big image 90 degrees clockwise
    big_rotated = np.rot90(big, k=-1) 

    plt.imshow(big_rotated[:, :, 0], cmap='gray')

    # plt.imshow(big[:, :, 0], cmap='gray')    
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