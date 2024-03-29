"""Define configurations and paths used in modules."""

import os
import ee
ee.Initialize()

# filepaths
ROOT_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(ROOT_DIR, 'data')
MP_SCRAPE_JSON_PATH = os.path.join(
    ROOT_DIR,
    'mp',
    'mountain-project-scraper',
    'clean-data.json'
)
MP_DATA_PATH = os.path.join(DATA_DIR, 'mp_data.csv')
NAIP_DATA_DIR = os.path.join(DATA_DIR, 'naip_shards')


# arbitrary thresholds based on intuition and data limits
STEEP_THRESHOLD = 70  # degrees
HEIGHT_THRESHOLD = 50  # meters
XMIN, XMAX, DX = -125, -102, 0.25
YMIN, YMAX, DY = 31, 49, 0.25


# parameters used in cliff_naip
NAIP_KERNEL_SIZE = 15  # 1m pixels
NAIP_SAMPLE_FRAC = 0.003  # for sampling
N_SHARDS = 100


# interacting with ee assets
EE_ASSET_DIR = ee.data.getAssetRoots()[0]['id'] + '/big_wall_data'
EE_CLIFF_FOOTPRINTS = EE_ASSET_DIR + '/cliff_footprints'
EE_CLIFFS = EE_ASSET_DIR + '/cliff_data'
EE_JOINED = EE_ASSET_DIR + '/cliff_joined'
MP_DATA = EE_ASSET_DIR + '/mp_data'


def get_ee_assets():
  """List asset names within big_wall_data directory."""
  assets = ee.data.listAssets({'parent': EE_ASSET_DIR})
  assets = assets['assets']
  assets = [a['id'] for a in assets]
  return [a.split('/')[-1] for a in assets]
