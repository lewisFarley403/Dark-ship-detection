import hashlib
import numpy as np
from pathlib import Path
from PIL import Image

class SentinelWebSerialiser:
    """
    Handles the transformation of SentinelScene data for web applications.
    Saves image arrays as PNGs and returns a JSON-compatible 
    manifest containing Leaflet-ready coordinates and URLs.
    """
    
    def __init__(self, storage_root: str, base_url: str):
        """
        :param storage_root: Local filesystem path where images will be saved.
        :param base_url: The public URL prefix used to access these images.
        """
        self.storage_root = Path(storage_root)
        self.base_url = base_url.rstrip('/')

    def _generate_unique_id(self, timestamp, bbox):
        """Creates a unique ID based on time and location to prevent folder collisions."""
        bbox_str = "_".join(map(str, bbox))
        unique_string = f"{timestamp}_{bbox_str}"
        short_hash = hashlib.md5(unique_string.encode()).hexdigest()[:8]
        clean_time = timestamp.replace(':', '-').replace('.', '-')
        return f"scene_{clean_time}_{short_hash}"

    def _prepare_image(self, img_array):
        """Converts raw satellite arrays (float or uint16) to web-standard uint8 PNG data."""
        # scale to 0-255
        if np.issubdtype(img_array.dtype, np.floating):
            img_array = (np.clip(img_array, 0, 1) * 255).astype(np.uint8)
        

        elif img_array.dtype == np.uint16:
            img_array = (img_array / 256).astype(np.uint8)
            
        return img_array

    def serialise(self, scene) -> dict:
        """
        Main entry point: Saves images and returns the JSON manifest.
        """
        timestamp = scene.get_string_datetime()
        scene_folder_name = self._generate_unique_id(timestamp, scene.bbox_coords)
        full_save_path = self.storage_root / scene_folder_name
        full_save_path.mkdir(parents=True, exist_ok=True)

        web_tiles = []

        if scene.images:
            for tile in scene.images:

                filename = f"tile_{tile['row']}_{tile['col']}.png"
                file_disk_path = full_save_path / filename
                

                processed_img = self._prepare_image(tile['img'])
                Image.fromarray(processed_img).save(file_disk_path)


                # Sentinel format: [min_lon, min_lat, max_lon, max_lat] (W, S, E, N)
                w, s, e, n = tile['bbox']
                
                # Leaflet format: [[south, west], [north, east]]
                leaflet_bounds = [[s, w], [n, e]]

                web_tiles.append({
                    "row": tile['row'],
                    "col": tile['col'],
                    "image_url": f"{self.base_url}/{scene_folder_name}/{filename}",
                    "leaflet_bounds": leaflet_bounds,
                    "raw_bbox": tile['bbox'] # Kept for debugging/analysis
                })


        return {
            "scene_id": scene_folder_name,
            "timestamp": timestamp,
            "request_bbox": scene.bbox_coords,
            "tiles": web_tiles,
            "total_tiles": len(web_tiles)
        }