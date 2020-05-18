"""Merge big wall data with Mountain Project data. For each cliff-like formation
found, determine nearby routes from Mountain Project data. Mountain Project
route data will eventually be used as a target for modeling.
"""

import ee
ee.Initialize()

mp = ee.FeatureCollection('users/zebengberg/big_walls/mp_data')
cliffs = ee.FeatureCollection('users/zebengberg/big_walls/ee_data')


MP_THRESHOLD = 200
cliffs = cliffs.set({
    'num_rock_routes': 0,
    'num_views': 0,
    'distance_to_mp': MP_THRESHOLD
})

def set_closest_cliff_id(f):
  """Find the id of the closest cliff and set it as a property, or return None."""
  close_cliffs = cliffs.filterBounds(f.buffer(MP_THRESHOLD).geometry())
  close_cliffs.set({'dist': MP_THRESHOLD})
  close_cliffs = close_cliffs.map(lambda c: c.set({'dist': c.distance(f.geometry())}))

  close_cliffs = close_cliffs.sort('dist')
  closest_cliff = close_cliffs.first()  # might be None
  return ee.Algorithms.If(  # returns None if closest_cliff None
      closest_cliff,
      f.set({
          'index': ee.Feature(closest_cliff).id(),
          'distance_to_mp': closest_cliff.get('dist')
      })
  )

def set_mp_data(f):
  """Add MP data associated to each cliff as a property."""
  mp_area = indices.filterMetadata('index', 'equals', f.id()).first()  # might be None
  return ee.Algorithms.If(
      mp_area,
      f.set({
          'num_rock_routes':
              ee.Number(f.get('num_rock_routes')).add(mp_area.get('num_rock_routes')),
          'num_views':
              ee.Number(f.get('num_views')).add(mp_area.get('num_views')),
          'distance_to_mp':
              ee.Number(mp_area.get('distance_to_mp')).min(mp_area.get('distance_to_mp'))
      }),
      f)

indices = mp.map(set_closest_cliff_id, True)  # dropping nulls
merged = cliffs.map(set_mp_data)



# Exporting results to drive for local download
task = ee.batch.Export.table.toDrive(
    collection=merged,
    description='merging mp and big wall data',
    fileFormat='CSV',
    folder='earth-engine',
    fileNamePrefix='merged_data',
)

# Exporting as an ee asset in order to run the merge_data script.
asset_task = ee.batch.Export.table.toAsset(
    collection=merged,
    description='exporting big wall data as asset',
    assetId='users/zebengberg/big_walls/merged_data'
)

task.start()
t = task.status()
for k, v in t.items():
  print('{}: {}'.format(k, v))
asset_task.start()
# Call ee.batch.Task.list() to see current status of exports.




# TODO: write functions below; add additional is_accessible boolean property to merged 

def set_mp_score(feature):
  """Use MP data to give score based on routes and views."""
  geo = ee.Geometry(feature.get('centroid'))
  disk = geo.buffer(1500)  # looking at mp data within 1.5km of feature
  close_mp = mp.filterBounds(disk)
  num_rock_routes = close_mp.aggregate_sum('num_rock_routes')
  num_views = close_mp.aggregate_sum('num_views')
  score = num_rock_routes.multiply(2000).add(num_views)
  return feature.set('mp_score', score)

def determine_accessibility(feature):
  """Determine if a feature is accessible with MP, population, and road data. """