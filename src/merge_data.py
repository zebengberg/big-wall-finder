"""Merge big wall data with Mountain Project data. For each cliff-like formation
found, determine nearby routes from Mountain Project data. Mountain Project
route data will eventually be used as a target for modeling.
"""

import ee
ee.Initialize()

mp = ee.FeatureCollection('users/zebengberg/big_walls/mp_data')
cliffs = ee.FeatureCollection('users/zebengberg/big_walls/ee_data')

# Starting by simplifying the geometry of each calculated cliff. Doing this will
# greatly improve the runtime of the join relying on the distance filter. Setting
# a larger maxError value smooths to a larger extent. Putting in a small buffer
# then simplifying forces all geometry to be polygon rather than multipolygon.
cliffs = cliffs.map(lambda f: f.setGeometry(f.buffer(10).geometry().simplify(maxError=50)))


# Critical threshold used to determine association between MP areas and cliffs.
MP_THRESHOLD = 200

# We start by associating each MP area to its closest cliff. If the MP area has
# no close cliffs, it is dropped.
filt = ee.Filter.withinDistance(distance=MP_THRESHOLD, leftField='.geo',
                                rightField='.geo', maxError=50)
join = ee.Join.saveBest(matchKey='closest_cliff', measureKey='distance_to_mp')
joined = join.apply(mp, cliffs, filt)

# The resulting FeatureCollection does not fit nicely into a table; export as
# CSV fails. Here we pull out the cliff joined to each MP area.
close_cliffs = joined.map(lambda f: ee.Feature(f.get('closest_cliff')).set({
    'num_rock_routes': f.get('num_rock_routes'),
    'num_views': f.get('num_views'),
}))


# We have now associated each MP area to either 0 or 1 cliffs. Each cliff may
# have any number of MP areas associated to it. We build another join to sum the
# MP area data for each cliff.

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
          'distance_to_mp': MP_THRESHOLD  # actual distance is greater than this
      }))

filt = ee.Filter.equals(leftField='system:index', rightField='system:index')
join = ee.Join.saveAll(matchesKey='mp_areas', outer=True)
joined = join.apply(cliffs, close_cliffs, filt)
merged = joined.map(aggregate_associated_mp_areas)


# For each cliff, we determine its accessibility score. We'll use this to
# distinguish cliffs which are likely to have been explored.
def set_accessibility(f):
  """Determine if a feature is accessible from MP, population, and road data. """
  cond1 = ee.Number(f.get('road_within_1000m'))
  cond2 = ee.Number(f.get('population_within_30km')).gt(50000)
  cond3 = ee.Number(f.get('population_within_100km')).gt(1000000)
  # Checking if surrounding zone has been explored on documented on MP.
  cond4 = ee.Number(get_mp_score_in_disk(f)).gt(10000)
  cond = cond1.And(cond2.Or(cond3)).Or(cond4)
  return f.set({'is_accessible': cond})

# Function below may be as performant as a join, especially with huge maxError.
# https://developers.google.com/earth-engine/best_practices#join-vs.-map-filter
def get_mp_score_in_disk(f):
  """Use MP data to give score based on routes and views in a disk around feature."""
  # looking at mp data within 500m of feature
  blob = f.geometry().buffer(500).simplify(maxError=200)
  close_mp = mp.filterBounds(blob)
  num_rock_routes = close_mp.aggregate_sum('num_rock_routes')
  num_views = close_mp.aggregate_sum('num_views')
  return num_rock_routes.multiply(1000).add(num_views)

# Now setting accessibility for cliffs.
merged = merged.map(set_accessibility)

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
    description='merging mp and big wall data',
    assetId='users/zebengberg/big_walls/merged_data'
)

task.start()
t = task.status()
for k, v in t.items():
  print('{}: {}'.format(k, v))
# asset_task.start()
# Call ee.batch.Task.list() to see current status of exports.
