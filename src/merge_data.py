"""Merge big wall data with Mountain Project data. For each cliff-like formation
found, determine nearby routes from Mountain Project data. Mountain Project
route data will eventually be used as a target for modeling.
"""

import ee
ee.Initialize()

mp = ee.FeatureCollection('users/zebengberg/big_walls/mp_data')
cliffs = ee.FeatureCollection('users/zebengberg/big_walls/ee_data')

def set_mp_score(feature):
  """Use mountain project data to give score based on routes and views."""
  geo = ee.Geometry(feature.get('centroid'))
  disk = geo.buffer(1500)  # looking at mp data within 1.5km of feature
  close_mp = mp.filterBounds(disk)
  num_rock_routes = close_mp.aggregate_sum('num_rock_routes')
  num_views = close_mp.aggregate_sum('num_views')
  score = num_rock_routes.multiply(2000).add(num_views)
  return feature.set('mp_score', score)

def determine_accessibility(feature):
  pass