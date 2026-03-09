# # tests/test_sentinel_downloader.py
# import pytest
# from sentinelhub import BBox, CRS
# from core.sentinel_downloader import get_true_color_image, create_sentinel_config

# def test_create_sentinel_config_returns_config():
#     """Check that the config generator doesn't crash and returns the right object."""
#     config = create_sentinel_config()
#     assert config is not None
#     # If you updated your imports to sentinelhub.config, test that it worked!
#     assert type(config).__name__ == 'SHConfig' 

# def test_bbox_creation_for_downloader():
#     """Ensure a BBox can be properly structured for your downloader."""
#     # Dummy coordinates for a small patch of ocean
#     coords = (12.5, 45.1, 12.6, 45.2)
#     bbox = BBox(bbox=coords, crs=CRS.WGS84)
    
#     assert bbox is not None
#     assert bbox.crs == CRS.WGS84
    
# def test_