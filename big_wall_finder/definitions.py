"""Define configurations and paths used in modules."""

import os

ROOT_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(ROOT_DIR, 'data')
MP_SCRAPE_JSON_PATH = os.path.join(
    ROOT_DIR,
    'mp',
    'mountain-project-scraper',
    'clean-data.json'
)
MP_DATA_PATH = os.path.join(DATA_DIR, 'mp_data.csv')
