"""Merge big wall data with Mountain Project data. For each cliff-like formation
found, determine nearby routes from Mountain Project data. Mountain Project
route data will eventually be used as a target for modeling.
"""

import ee
ee.Initialize()

mp = ee.FeatureCollection('users/zebengberg/big_walls/mp_data')
cliffs = ee.FeatureCollection('users/zebengberg/big_walls/ee_data')

# Rectangle from gather_ee_data.py used to clip MP data to region of interest.
x0, x1 = -125, -102
y0, y1 = 31, 49
rectangle = ee.Geometry.Rectangle(x0, y0, x1, y1)
mp = mp.filterBounds(rectangle)

# We only care about rock climbing as opposed to bouldering and winter climbing
# for the first join.
mp_routes = mp.filterMetadata('num_rock_routes', 'greater_than', 0)

# Giving each cliff an immutable custom index that won't change as individual
# cliff Features are moved from one Collection to another. We later use this
# within pandas. For some reason, Earth Engine really struggled trying to join
# cliffs with mp_targets server-side.
cliffs = cliffs.toList(cliffs.size())
indices = ee.List.sequence(0, cliffs.size().subtract(1))
cliffs = indices.map(lambda i: ee.Feature(cliffs.get(i)).set('custom_index', i))
cliffs = ee.FeatureCollection(cliffs)

# We start by associating each MP area to its closest cliff. If the MP area has
# no close cliffs, it is dropped. Our threshold is 300m.
dist_filter = ee.Filter.withinDistance(distance=300, leftField='.geo',
                                       rightField='.geo', maxError=50)
join = ee.Join.saveBest(matchKey='closest_cliff', measureKey='distance_to_mp')
mp_targets = join.apply(mp_routes, cliffs, dist_filter)

# Here we pull out the cliff index joined to each MP area.
mp_targets = mp_targets.map(lambda f: f.set({
    'custom_index': ee.Feature(f.get('closest_cliff')).get('custom_index'),
    'distance_to_mp': ee.Feature(f.get('closest_cliff')).get('distance_to_mp')}))

# We now use another join to look at MP activity within a larger vicinity of
# the cliff. Unlike the first join, here cliffs are primary and mp is secondary.
# The geometry settings are different here as well: our distance threshold and
# the allowable error are much larger, which results in simplified polygons.
# This will be used as a measure of accessibility on the pandas-side of things.
def aggregate_vicinity_mp_areas(f):
  """Extract and aggregate mp data within vicinity of cliff feature."""
  mp_areas = ee.FeatureCollection(ee.List(f.get('vicinity_mp_areas')))
  return f.set({
      'vicinity_num_rock_routes': mp_areas.aggregate_sum('num_rock_routes'),
      'vicinity_num_views': mp_areas.aggregate_sum('num_views')})

# Using a threshold of 800m for vicinity cliffs.
dist_filter = ee.Filter.withinDistance(distance=800, leftField='.geo',
                                       rightField='.geo', maxError=200)
join = ee.Join.saveAll(matchesKey='vicinity_mp_areas', outer=True)
cliffs = join.apply(cliffs, mp, dist_filter)
cliffs = cliffs.map(aggregate_vicinity_mp_areas)


# Exporting results to drive for local download
task1 = ee.batch.Export.table.toDrive(
    collection=mp_targets,
    description='joined mp',
    fileFormat='CSV',
    folder='earth-engine',
    fileNamePrefix='ee_joined')

task2 = ee.batch.Export.table.toDrive(
    collection=cliffs,
    description='joined cliffs',
    fileFormat='CSV',
    folder='earth-engine',
    fileNamePrefix='mp_joined')

task1.start()
task2.start()
t1 = task1.status()
for k, v in t1.items():
  print(f'{k}: {v}')
t2 = task2.status()
for k, v in t2.items():
  print(f'{k}: {v}')
# Call ee.batch.Task.list() to see current status of exports.
