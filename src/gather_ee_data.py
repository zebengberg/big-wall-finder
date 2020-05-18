"""Split up the western US into small rectangles. Each rectangle is searched for
big walls. For each big wall found, data is collected. Results are exported to
google drive. Use small rectangle to split bigger region into batches; this
avoids error (Too many pixels in region) in calling reduceToVector method.
"""

import ee
import numpy as np
ee.Initialize()

# Set these particular thresholds so that resulting csv stays within GitHub's
# 100mb limit for files.
STEEP_THRESHOLD = 70
HEIGHT_THRESHOLD = 100

# Importing datasets
dem = ee.Image('USGS/NED')

roads = ee.FeatureCollection('TIGER/2016/Roads')

pop = ee.ImageCollection('CIESIN/GPWv411/GPW_Population_Count')
pop = pop.first().select('population_count')

lith = ee.Image('CSP/ERGo/1_0/US/lithology')

landsat = ee.ImageCollection("LANDSAT/LC08/C01/T1")
landsat = landsat.filterDate('2017-01-01', '2019-12-31')
# Getting rid of clouds
landsat = ee.Algorithms.Landsat.simpleComposite(collection=landsat, asFloat=True)
# Getting bands that might be useful in geology
landsat = landsat.select('B7', 'B6', 'B2', 'B4', 'B5')

usa = ee.FeatureCollection("USDOS/LSIB_SIMPLE/2017")
usa = usa.filter(ee.Filter.eq('country_co', 'US'))

# Building up elevation layers.
steep = ee.Terrain.slope(dem).gt(STEEP_THRESHOLD)
dem_masked = dem.updateMask(steep)
# The image steep has two bands: the first is 0 or 1, second is the elevation
steep = steep.addBands(dem_masked.toInt())

# Calculating heights of each connected region of steep terrain.
cliffs = steep.reduceConnectedComponents(reducer='minMax')
cliffs = cliffs.select('elevation_max').subtract(cliffs.select('elevation_min'))
cliffs = cliffs.updateMask(cliffs.gt(HEIGHT_THRESHOLD))


def get_cliffs(rectangle):
  """Search within rectangle at high resolution scale to find cliffs."""
  # Getting the geometry and height of all cliffs within the rectangle.
  # Using height as a label for connectedness.
  features = cliffs.reduceToVectors(
      reducer='countEvery',
      geometry=rectangle,
      scale=10,
      geometryType='polygon'
  )
  # Renaming elevation properties.
  features = features.select(['label', 'count'], ['height', 'pixel_count'])

  # Getting data for each polygonal cliff geometry.
  features = features.map(set_landsat_data)

  # Setting the cliff's centroid
  features = features.map(lambda f: f.set('centroid', f.geometry().centroid(10 ** -2)))
  features = features.map(lambda f: f.set(
      'latitude', ee.Geometry(f.get('centroid')).coordinates().get(1),
      'longitude', ee.Geometry(f.get('centroid')).coordinates().get(0)))
  # Need lithology to be unmasked to avoid critical errors.
  features = features.map(lambda f: f.set(
      'centroid_lith',
      lith.reduceRegion(reducer='first', geometry=f.get('centroid')
  ).get('b1')))
  features = features.filter(ee.Filter.notNull(['centroid_lith']))
  features = features.map(set_lithology)
  features = features.map(lambda f: set_population(f, 30))
  features = features.map(lambda f: set_population(f, 100))
  features = features.map(lambda f: set_population(f, 200))
  features = features.map(lambda f: set_road_within_distance(f, 500))
  features = features.map(lambda f: set_road_within_distance(f, 1000))
  features = features.map(lambda f: set_road_within_distance(f, 1500))
  features = features.map(lambda f: set_road_within_distance(f, 2000))
  features = features.map(lambda f: set_road_within_distance(f, 3000))


  # Here features is a FeatureCollection object. Casting it to a list.
  return features.toList(2000)  # maximum number of features per rectangle


def set_population(feature, distance):
  """Add population within specified distance in km of feature."""
  geo = ee.Geometry(feature.get('centroid'))
  disk = geo.buffer(ee.Number(distance).multiply(1000))
  count = pop.reduceRegion(reducer='sum', geometry=disk)
  count = ee.Number(count.get('population_count')).toInt()
  return feature.set('population_within_{}km'.format(distance), count)


def set_road_within_distance(feature, distance):
  """Determine if there is a road within specified distance in m of feature."""
  geo = ee.Geometry(feature.get('centroid'))
  disk = geo.buffer(distance)
  close_roads = roads.filterBounds(disk)
  is_close_road = close_roads.size().gt(0)
  return feature.set('road_within_{}m'.format(distance), is_close_road)


def set_lithology(feature):
  """Add lithology data for 1km disk around cliff as a feature property."""
  geo = ee.Geometry(feature.get('centroid'))
  disk = geo.buffer(1000)
  hist = lith.reduceRegion(reducer='frequencyHistogram', geometry=disk).get('b1')
  hist = ee.Dictionary(hist)
  hist_sum = hist.toArray().reduce(reducer='sum', axes=[0]).get([0])
  # Lithology categories that might be relevant to rocky terrain.
  lith_dict = {
      'geology_carbonate': ee.Number(hist.get('1', 0)).divide(hist_sum),
      'geology_non_carbonate': ee.Number(hist.get('3', 0)).divide(hist_sum),
      'geology_silicic_residual': ee.Number(hist.get('5', 0)).divide(hist_sum),
      'geology_colluvial_sediment': ee.Number(hist.get('8', 0)).divide(hist_sum),
      'geology_glacial_till_coarse': ee.Number(hist.get('11', 0)).divide(hist_sum),
      'geology_alluvium': ee.Number(hist.get('19', 0)).divide(hist_sum)}
  return feature.set(lith_dict)


def set_landsat_data(feature):
  """Add landsat8 geology-style data as feature property."""
  geo = feature.geometry()
  bands = landsat.reduceRegion(reducer='median', geometry=geo, scale=10)
  # Including some mysterious "band ratios" which could be useful.
  bands = bands.set('B42', ee.Number(bands.get('B4')).divide(bands.get('B2')))
  bands = bands.set('B65', ee.Number(bands.get('B6')).divide(bands.get('B5')))
  bands = bands.set('B67', ee.Number(bands.get('B6')).divide(bands.get('B7')))
  return feature.set(bands)


# Building an ee.List of rectangles objects.
x0, x1, dx = -125, -102, 0.25
y0, y1, dy = 31, 49, 0.25

rectangles = [ee.Geometry.Rectangle(x, y, x + dx, y + dy)
              for x in np.arange(x0, x1, dx) for y in np.arange(y0, y1, dx)]

rectangles = ee.FeatureCollection(rectangles)
rectangles = rectangles.filterBounds(usa)

# Casting to an ee.List of geometries rather than an ee.FeatureCollection since
# the get_cliffs() function cannot be mapped over ee.FeatureCollection.
rectangles = rectangles.toList(200000)
rectangles = rectangles.map(lambda f: ee.Feature(f).geometry())

# Running the main job.
results = rectangles.map(get_cliffs, True)  # dropping nulls
results = results.flatten()
results = ee.FeatureCollection(results)  # casting from ee.List

# Exporting results to drive for local download
task = ee.batch.Export.table.toDrive(
    collection=results,
    description='exporting big wall data to drive',
    fileFormat='CSV',
    folder='earth-engine',
    fileNamePrefix='ee_data',
)

# Exporting as an ee asset in order to run the merge_data script.
asset_task = ee.batch.Export.table.toAsset(
    collection=results,
    description='exporting big wall data as asset',
    assetId='users/zebengberg/big_walls/ee_data'
)

task.start()
t = task.status()
for k, v in t.items():
  print('{}: {}'.format(k, v))
asset_task.start()
# Call ee.batch.Task.list() to see current status of exports.