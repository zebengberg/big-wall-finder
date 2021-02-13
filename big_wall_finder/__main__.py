"""Run pipeline."""

import os
import sys
from big_wall_finder import definitions
from big_wall_finder.mp import parse_mp

if not os.path.exists(definitions.MP_SCRAPE_JSON_PATH):
  print('cd into the mountain-project-scraper director')
  print('and run `npm start`')
  sys.exit()

parse_mp.main()
