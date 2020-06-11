"""Split up the western US into small rectangles. Each rectangle is searched for
big walls. For each big wall found, data is collected. Results are exported to
google drive. Use small rectangle to split bigger region into batches; this
avoids error (Too many pixels in region) in calling reduceToVector method.
"""

import ee
ee.Initialize()


# Importing datasets
cliffs = ee.FeatureCollection('users/zebengberg/big_walls/cliff_footprints')
roads = ee.FeatureCollection('TIGER/2016/Roads')
pop = ee.Image("WorldPop/GP/100m/pop/USA_2019")
lith = ee.Image('CSP/ERGo/1_0/US/lithology')

landsat = ee.ImageCollection("LANDSAT/LC08/C01/T1")
landsat = landsat.filterDate('2017-01-01', '2019-12-31')
# Getting rid of clouds
landsat = ee.Algorithms.Landsat.simpleComposite(collection=landsat, asFloat=True)
# Getting bands that might be useful in geology
landsat = landsat.select('B7', 'B6', 'B2', 'B4', 'B5')
# Including some mysterious "band ratios" which could be useful.
landsat = landsat.select('B7', 'B6', 'B2', 'B4', 'B5')
b42 = landsat.select('B4').divide(landsat.select('B2')).rename('B42')
b65 = landsat.select('B6').divide(landsat.select('B5')).rename('B65')
b67 = landsat.select('B6').divide(landsat.select('B7')).rename('B67')
landsat = landsat.addBands(ee.Image([b42, b65, b67]))

# Getting the brightest pixels from sat data; avoids features in the shade
sat_max = ee.ImageCollection('USDA/NAIP/DOQQ')
sat_max = sat_max.filter(ee.Filter.date('2010-01-01', '2018-12-31')).max()
grad_max = sat_max.spectralGradient().rename('D')  # D for derivative

# Getting the most recently captured pixel from sat data; this will give a
# crisper image than sat_max.
sat_mosaic = ee.ImageCollection('USDA/NAIP/DOQQ')
sat_mosaic = sat_mosaic.filter(ee.Filter.date('2010-01-01', '2018-12-31')).mosaic()
grad_mosaic = sat_mosaic.spectralGradient().rename('D')  # D for derivative


def get_data(cliff):
  """Extracting data within cliff geometry."""
  cliff = set_landsat_data(cliff)
  cliff = set_lithology(cliff)
  cliff = set_sat_max(cliff)
  cliff = set_sat_mosaic(cliff)
  cliff = set_population(cliff, 30)
  cliff = set_population(cliff, 60)
  cliff = set_population(cliff, 100)
  cliff = set_road_within_distance(cliff, 500)
  cliff = set_road_within_distance(cliff, 1000)
  cliff = set_road_within_distance(cliff, 1500)
  cliff = set_road_within_distance(cliff, 2000)
  return cliff

def set_landsat_data(feature):
  """Add landsat8 geology-style data as feature property."""
  geo = feature.geometry()
  reducer = ee.Reducer.percentile(percentiles=[20, 35, 50, 65, 80])
  return feature.set(landsat.reduceRegion(reducer=reducer, geometry=geo, scale=10))

def set_lithology(feature):
  """Add lithology data for 1km disk around cliff as a feature property."""
  geo = feature.geometry()
  hist = lith.reduceRegion(reducer='frequencyHistogram', geometry=geo).get('b1')
  hist = ee.Dictionary(hist)
  # ee cannot cast hist to array if it is empty; putting something in it.
  hist = hist.set('something', 1)
  hist_sum = hist.toArray().reduce(reducer='sum', axes=[0]).get([0])
  # Lithology categories that might be relevant to rocky terrain.
  return feature.set({
      'geology_carbonate': ee.Number(hist.get('1', 0)).divide(hist_sum),
      'geology_non_carbonate': ee.Number(hist.get('3', 0)).divide(hist_sum),
      'geology_silicic_residual': ee.Number(hist.get('5', 0)).divide(hist_sum),
      'geology_colluvial_sediment': ee.Number(hist.get('8', 0)).divide(hist_sum),
      'geology_glacial_till_coarse': ee.Number(hist.get('11', 0)).divide(hist_sum),
      'geology_alluvium': ee.Number(hist.get('19', 0)).divide(hist_sum)})

def set_sat_max(feature):
  """Add USDA satellite max data as property feature."""
  geo = feature.geometry()
  reducer = ee.Reducer.percentile(percentiles=[10, 20, 30, 40, 50, 60, 70, 80, 90])
  feature = feature.set(sat_max.reduceRegion(reducer=reducer, geometry=geo, scale=1))
  return feature.set(grad_max.reduceRegion(reducer=reducer, geometry=geo, scale=1))

def set_sat_mosaic(feature):
  """Add USDA satellite mosaic data as property feature."""
  geo = feature.geometry()
  reducer = ee.Reducer.percentile(percentiles=[10, 20, 30, 40, 50, 60, 70, 80, 90])
  feature = feature.set(sat_mosaic.reduceRegion(reducer=reducer, geometry=geo, scale=1))
  return feature.set(grad_mosaic.reduceRegion(reducer=reducer, geometry=geo, scale=1))

def set_population(feature, distance):
  """Add population within specified distance in km of feature."""
  geo = ee.Geometry.Point([feature.get('longitude'), feature.get('latitude')])
  disk = geo.buffer(ee.Number(distance).multiply(1000))
  count = pop.reduceRegion(reducer='sum', geometry=disk)
  count = ee.Number(count.get('population')).toInt()
  return feature.set(f'population_within_{distance}km', count)

def set_road_within_distance(feature, distance):
  """Determine if there is a road within specified distance in m of feature."""
  geo = ee.Geometry.Point([feature.get('longitude'), feature.get('latitude')])
  disk = geo.buffer(distance)
  close_roads = roads.filterBounds(disk)
  is_close_road = close_roads.size().gt(0)
  return feature.set(f'road_within_{distance}m', is_close_road)


# Running the job.
cliffs = cliffs.map(get_data)

# Exporting intermediate results to drive for local download
task1 = ee.batch.Export.table.toDrive(
    collection=cliffs,
    description='exporting big wall data to drive',
    fileFormat='CSV',
    folder='earth-engine',
    fileNamePrefix='ee_data',
)

# Exporting intermediate results as asset to investigate in code editor.
task2 = ee.batch.Export.table.toAsset(
    collection=cliffs,
    description='exporting big wall data as asset',
    assetId='users/zebengberg/big_walls/ee_data'
)

task1.start()
task2.start()
# Call ee.batch.Task.list() to see current status of exports.
