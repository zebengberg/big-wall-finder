"""Run pipeline."""

import os
import ee
from big_wall_finder import definitions
from big_wall_finder.mp import parse_mp
from big_wall_finder.ee import cliff_footprints, cliff_data

ee.Initialize()


if not os.path.exists(definitions.MP_SCRAPE_JSON_PATH):
  print('cd into the mountain-project-scraper director')
  print('and run `npm start`')

elif 'mp_data' not in definitions.get_ee_assets():
  if not os.path.exists(definitions.MP_DATA_PATH):
    parse_mp.main()
  print('Manually upload mp data as earth engine asset.')
  print('Use path `big_wall_data/mp_data`.')

elif 'cliff_footprints' not in definitions.get_ee_assets():
  cliff_footprints.main()

elif 'cliff_data' not in definitions.get_ee_assets():
  cliff_data.main()