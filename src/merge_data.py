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

# Giving each cliff an immutable custom index that won't change as individual
# cliff Features are moved from one Collection to another.
cliffs = cliffs.map(lambda f: f.set('custom_index', f.get('system:index')))

# We only care about rock climbing as opposed to bouldering and winter climbing
# for the first join.
mp_routes = mp.filterMetadata('num_rock_routes', 'greater_than', 0)


# Critical threshold used to determine association between MP areas and cliffs.
# Because we save the distance from MP to closest cliff, we have some flexibility
# to filter by distance later within pandas.
MP_THRESHOLD = 300

# We start by associating each MP area to its closest cliff. If the MP area has
# no close cliffs, it is dropped.
filter1 = ee.Filter.withinDistance(distance=MP_THRESHOLD, leftField='.geo',
                                   rightField='.geo', maxError=50)
join1 = ee.Join.saveBest(matchKey='closest_cliff', measureKey='distance_to_mp')
joined1 = join1.apply(mp_routes, cliffs, filter1)

# The resulting FeatureCollection does not fit nicely into a table; export as
# CSV fails. Here we pull out the cliff joined to each MP area.
close_cliffs = joined1.map(lambda f: ee.Feature(f.get('closest_cliff')).set({
    'num_rock_routes': f.get('num_rock_routes'),
    'num_views': f.get('num_views')}))

# delete later
task = ee.batch.Export.table.toDrive(
    collection=close_cliffs,
    description='intermediate results',
    fileFormat='CSV',
    folder='earth-engine',
    fileNamePrefix='close_cliffs',
)
task.start()


# We have now associated each MP area to either 0 or 1 cliffs. Each cliff may
# have any number of MP areas associated to it. We build another join to sum the
# MP area data for each cliff. Now each cliff holds a whole list of MP areas
# associated to it. For many cliffs, this list is empty.
def aggregate_associated_mp_areas(f):
  """Extract and aggregate mp data from feature arising in join."""
  mp_areas = ee.List(f.get('mp_areas'))
  return ee.Algorithms.If(
      mp_areas.size(),
      f.set({
          'num_rock_routes': ee.FeatureCollection(mp_areas).aggregate_sum('num_rock_routes'),
          'num_views': ee.FeatureCollection(mp_areas).aggregate_sum('num_views'),
          'distance_to_mp': ee.FeatureCollection(mp_areas).aggregate_min('distance_to_mp')}),
      f.set({
          'num_rock_routes': 0,
          'num_views': 0,
          'distance_to_mp': None
      }))

filter2 = ee.Filter.equals(leftField='custom_index', rightField='custom_index')
join2 = ee.Join.saveAll(matchesKey='mp_areas', outer=True)
joined2 = join2.apply(cliffs, close_cliffs, filter2)
joined2 = joined2.map(aggregate_associated_mp_areas)

# delete later
task = ee.batch.Export.table.toDrive(
    collection=joined2,
    description='intermediate results',
    fileFormat='CSV',
    folder='earth-engine',
    fileNamePrefix='joined2',
)
task.start()


# We now use one more join to look at MP activity within a larger vicinity of
# the cliff. Unlike the first join, here cliffs are primary and mp is secondary.
# The geometry settings are different here as well: our distance threshold and
# the allowable error are much larger, which results in simplified polygons.
# This will be used as a measure of accessibility on the pandas-side of things.
def aggregate_vicinity_mp_areas(f):
  """Extract and aggregate mp data within vicinity of feature."""
  mp_areas = ee.List(f.get('vicinity_mp_areas'))
  return ee.Algorithms.If(
      mp_areas.size(),
      f.set({
          'vicinity_num_rock_routes':
              ee.FeatureCollection(mp_areas).aggregate_sum('num_rock_routes'),
          'vicinity_num_views':
              ee.FeatureCollection(mp_areas).aggregate_sum('num_views')}),
      f.set({
          'vicinity_num_rock_routes': 0,
          'vicinity_num_views': 0,
      }))

filter3 = ee.Filter.withinDistance(distance=600, leftField='.geo',
                                   rightField='.geo', maxError=200)
join3 = ee.Join.saveAll(matchesKey='vicinity_mp_areas', outer=True)
joined3 = join3.apply(joined2, mp, filter3)
joined3 = joined3.map(aggregate_vicinity_mp_areas)


# Exporting results to drive for local download
task = ee.batch.Export.table.toDrive(
    collection=joined3,
    description='merging mp and big wall data',
    fileFormat='CSV',
    folder='earth-engine',
    fileNamePrefix='merged_data',
)

task.start()
t = task.status()
for k, v in t.items():
  print('{}: {}'.format(k, v))
# Call ee.batch.Task.list() to see current status of exports.
