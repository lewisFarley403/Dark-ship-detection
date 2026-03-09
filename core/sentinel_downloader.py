import datetime
import math
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from copy import deepcopy

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.dviread import Page
from sentinelhub import (
    BBox,
    CRS,
    DataCollection,
    MimeType,
    SentinelHubCatalog,
    SentinelHubRequest,
    SHConfig,
    bbox_to_dimensions,
)
import cv2
from shapely.geometry import Point, box
import numpy as np

from core.utils import load_sentinel_creds
from .ingestion import AISPage
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
# SAR_eval = '''
#     // VERSION: 3
#     function setup() {
#     return {
#         input: ["VV", "VH"],
#         output: { bands: 2, sampleType: "FLOAT32" }
#     };
#     }

#     function evaluatePixel(sample) {
#     const vv = 10 * Math.log10(sample.VV+0.0001);
#     const vh = 10 * Math.log10(sample.VH+0.0001);
#     return [vv, vh];
#     }
#         '''

SAR_eval = '''
    // VERSION: 3
    function setup() {
    return {
        input: ["VV"], // Only need VV for ship detection usually
        // 1. Change to AUTO or UINT8 to get 0-255 range
        output: { bands: 3, sampleType: "AUTO" } 
    };
    }

    function evaluatePixel(sample) {
    // 2. Convert to dB
    let val = 10 * Math.log10(sample.VV + 0.00001);
    
    // 3. Clip and Normalize (Map -25dB...0dB to 0...1)
    const min_db = -25;
    const max_db = 0;
    val = (val - min_db) / (max_db - min_db);
    
    // 4. Clamp to ensure 0-1 range
    if (val < 0) val = 0;
    if (val > 1) val = 1;
    
    // 5. Return RGB (Duplicate channels) scaled to 255
    // Sentinel Hub "AUTO" or "UINT8" expects 0-1 floats or 0-255 ints. 
    // Returning 0-1 floats with AUTO handles the conversion to 0-255 automatically.
    return [val, val, val]; 
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
def get_true_color_image(bbox_coords:tuple[float,float,float,float], start_date:str, end_date:str, is_optical:bool=False, min_overlap:float=0.7, max_workers:int=8):
    config = create_sentinel_config()
    bbox = BBox(bbox=bbox_coords, crs=CRS.WGS84)
    

    if is_optical:
        search_term, data_col_type, evalscript = 's2l2a', DataCollection.SENTINEL2_L2A, optical_eval
    else:
        search_term, data_col_type, evalscript = 's1iw', DataCollection.SENTINEL1_IW, SAR_eval

    data_collection = data_col_type.define_from(search_term, service_url="https://sh.dataspace.copernicus.eu")
    catalog = SentinelHubCatalog(config=config)
    

    all_results = list(catalog.search(data_collection, bbox=bbox, time=(start_date, end_date)))
    if not all_results: 
        return None
    best_scenes = [s for s in all_results if compute_bbox_crossover(bbox_coords, s['bbox']) > min_overlap]
    if not best_scenes: 
        return None
    
    # best_scene = best_scenes[0]
    results = []
    # for best_scene in best_scenes:
    #     scene = SentinelScene(best_scene,bbox_coords,config,evalscript,data_collection)
    #     # print('best scene ',best_scene)
    #     results.append(scene)
    results = [SentinelScene(best_scene,bbox_coords,config,evalscript,data_collection) for best_scene in best_scenes]
    return results






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
        # print(satallite)
        full_bbox = satallite.get_image_bbox() # This gives the full image bbox regardless of if it is far too big
        # print(full_bbox)
        box_full = box(*full_bbox)
        target_box = box(*target_bbox)
        bbox_obj= box_full.intersection(target_box)
        # print(bbox)
        # bbox_obj = box(*bbox)
        # print(bbox)
        bbox = bbox_obj.bounds
        date = satallite.get_datetime()
        # print(str_date)
        # print('str time ',str_date)
        # date = datetime.strptime(str_date, "%Y-%m-%dT%H:%M:%SZ")

        # print(f'date {date}')

        page = AISPage(date)

        filtered_page = page.filter_bbox(bbox).filter_datetime(date)
        # print(filtered_page.full_ais_df[['Lat', 'Lon']].describe())

        yield satallite,filtered_page,date,bbox_obj.intersection(box(*target_bbox))

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

class SentinelScene:
    '''This class represents a satellite photo that is taken on a specific date and bbox
    It provides one interface to interact with single tile and multitile images.
    It is important that some operations are remain multitile (ship detection) while others are stitched (plotting)'''
    def __init__(self, catalog_entry, bbox_coords, config, evalscript,data_collection):
        self.metadata = catalog_entry
        self.bbox_coords = bbox_coords
        self.config = config
        self.evalscript = evalscript
        self.data_collection = data_collection
        self.images = None # Will hold our data later
        
    def download(self, max_workers=8):
        """The user calls this exactly when they are ready for the data."""
        size = bbox_to_dimensions(BBox(self.bbox_coords,crs=CRS.WGS84), 10)
        
        if size[0] > 2500 or size[1] > 2500:
            self.images = self._download_tiled(max_workers)
        else:
            self.images = [self._download_single()] # Wrap in list for consistency
            
        return self.images
    def _get_sentinel_bbox(self,bbox_coords):
        return BBox(bbox=bbox_coords[:4], crs=CRS.WGS84)
    def _get_size(self,bbox_coords):
        bbox = self._get_sentinel_bbox(bbox_coords[:4])
        return bbox_to_dimensions(bbox, 10)
    def _download_tiled(self, max_workers):
        size = self._get_size(self.bbox_coords)



        nx = math.ceil(size[0] / 2000)
        ny = math.ceil(size[1] / 2000)
        print(f"THREADED GRID: Dispatching {nx*ny} tiles across {max_workers} threads...")

        lon_step = (self.bbox_coords[2] - self.bbox_coords[0]) / nx
        lat_step = (self.bbox_coords[3] - self.bbox_coords[1]) / ny
        
        sub_boxes = []
        for i in range(nx):
            for j in range(ny):
                sub_boxes.append((
                    self.bbox_coords[0] + i * lon_step,
                    self.bbox_coords[1] + j * lat_step,
                    self.bbox_coords[0] + (i+1) * lon_step,
                    self.bbox_coords[1] + (j+1) * lat_step,
                    i,j
                ))


        imgs = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:

            future_to_box = {
                executor.submit(self._single_download_request, box): box 
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
    def _download_single(self):
        imgs = [self._single_download_request(self.bbox_coords)]
        return imgs
    def _single_download_request(self,bbox_coords):
        """Worker function: Downloads a single tile."""
        # print('bbox single thread ',bbox_coords)
        size = self._get_size(bbox_coords)
        
        request = SentinelHubRequest(
            evalscript=self.evalscript,
            input_data=[
                SentinelHubRequest.input_data(
                    data_collection=self.data_collection,
                    time_interval=(self.metadata['properties']['datetime'], self.metadata['properties']['datetime']),
                )
            ],
            responses=[SentinelHubRequest.output_response("default", MimeType.TIFF)],
            bbox=self._get_sentinel_bbox(bbox_coords),
            size=size,
            config=self.config,
        )

        return {'img': request.get_data()[0], 'date': self.metadata["properties"]["datetime"], 'bbox': bbox_coords[:4], 'row':bbox_coords[4],'col':bbox_coords[5]}
    def stitch(self):
        
        """Stitches the downloaded tiles into a single seamless numpy array."""
        if not self.images:
            print("No images downloaded yet. Call download() first.")
            return None
            

        if len(self.images) == 1:
            return self.images[0]['img']


        # 'i' (longitude/cols) as 'row', 'j' (latitude/rows) as 'col'
        nx = max(tile['row'] for tile in self.images) + 1
        ny = max(tile['col'] for tile in self.images) + 1


        grid = [[None for _ in range(nx)] for _ in range(ny)]

        for tile in self.images:
            i = tile['row'] # Longitude step (X-axis)
            j = tile['col'] # Latitude step (Y-axis)
            
            # Flip the geographic Y-axis to match the Image Y-axis
            img_row = ny - 1 - j 
            img_col = i
            
            grid[img_row][img_col] = tile['img']

        stitched_rows = []
        for r in range(ny):
            # 1. Find the minimum height among all tiles in this specific row
            min_height = min(img.shape[0] for img in grid[r])
            
            # 2. Crop all tiles in this row to that exact minimum height
            # We use the ellipsis (...) so this works for both 2D and 3D arrays!
            cropped_tiles = [img[:min_height, ...] for img in grid[r]]
            
            # 3. Stitch tiles left-to-right to form a complete row
            row_image = np.concatenate(cropped_tiles, axis=1) 
            stitched_rows.append(row_image)
            

        min_width = min(row_img.shape[1] for row_img in stitched_rows)
        cropped_rows = [row_img[:, :min_width, ...] for row_img in stitched_rows]


        final_image = np.concatenate(cropped_rows, axis=0) 
        
        return final_image
    
    def plot_points(self,points:list[Point],radius = 10,bgr_color = (255, 0, 0),thickness = 10):
        mod_scene = deepcopy(self)
        for point in points:
            subimg_index = None
            for i,img in enumerate(mod_scene.images):
                if box(*img['bbox']).contains(point) == True: # This may change with a new class subimage
                    subimg_index = i
                    print('plotting in image ',i)
                    break
                
            if subimg_index == None:
                return None # maybe raise an except
            min_lon, min_lat, max_lon, max_lat = mod_scene.images[subimg_index]['bbox']
            img_height, img_width = mod_scene.images[subimg_index]['img'].shape[:2] # height is shape[0], width is shape[1]

            point_lon = point.x
            point_lat = point.y

            # 2. X Pixel (Columns: Left to Right)
            # Fraction of the way across the longitude range * Image Width
            lon_fraction = (point_lon - min_lon) / (max_lon - min_lon)
            pixel_x = int(lon_fraction * img_width)

            # 3. Y Pixel (Rows: Top to Bottom) -> THE FLIPPED AXIS
            # Fraction of the way DOWN from the max_lat (Northern edge) * Image Height
            lat_fraction = (max_lat - point_lat) / (max_lat - min_lat)
            pixel_y = int(lat_fraction * img_height)
            print(f'circle at {pixel_x},{pixel_y}')
            cv2.circle(
                        mod_scene.images[subimg_index]['img'], 
                        (pixel_x, pixel_y), # (x, y) center
                        radius=radius, 
                        color=bgr_color, 
                        thickness=thickness
                    )
        return mod_scene
            

    def get_search_bbox(self):
        return self.bbox_coords
    def get_image_bbox(self):
        return self.metadata['bbox']
    def get_datetime(self):
        '''returns datetime obj'''
        return datetime.strptime(self.get_string_datetime(), "%Y-%m-%dT%H:%M:%SZ")

    def get_string_datetime(self):
        return self.metadata['properties']['datetime']

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