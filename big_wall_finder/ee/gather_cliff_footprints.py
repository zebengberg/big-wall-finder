"""Split up the western US into small rectangles. Each rectangle is searched for
big walls. For each big wall found, data is collected. Results are exported to
google drive. Use small rectangle to split bigger region into batches; this
avoids error (Too many pixels in region) in calling reduceToVector method.
"""

import ee
import numpy as np
ee.Initialize()

# Completely arbitrary thresholds based on intuition and data limits.
STEEP_THRESHOLD = 70  # degrees
HEIGHT_THRESHOLD = 50  # meters

# Importing datasets
dem = ee.Image('USGS/NED')
usa = ee.FeatureCollection("USDOS/LSIB_SIMPLE/2017")
usa = usa.filter(ee.Filter.eq('country_co', 'US'))

# Building up elevation layers.
slope = ee.Terrain.slope(dem).rename('slope')
is_steep = ee.Terrain.slope(dem).gt(STEEP_THRESHOLD)
dem_masked = dem.updateMask(is_steep)
# The image steep has two bands: the first is 0 or 1, second is the elevation
is_steep = is_steep.addBands(dem_masked.toInt())

# Calculating heights of each connected region of steep terrain.
cliffs = is_steep.reduceConnectedComponents(reducer='minMax')
cliffs = cliffs.select('elevation_max').subtract(cliffs.select('elevation_min'))
cliffs = cliffs.updateMask(cliffs.gt(HEIGHT_THRESHOLD))


def get_cliffs(rectangle):
  """Search within rectangle at DEM resolution to find cliffs."""
  # Getting the geometry and height of all cliffs within the rectangle.
  # Using height as a label for connectedness.
  features = cliffs.reduceToVectors(
      reducer='countEvery',
      geometry=rectangle,
      scale=10,
      geometryType='polygon')
  # Renaming elevation properties.
  features = features.select(['label', 'count'], ['height', 'pixel_count'])

  # Buffering and simplifying the geometry of each calculated cliff. This serves
  # several purposes:
  # - Buffering converts each MultiPolygon object to a Polygon object by
  #   eliminating intersections at single vertices, thereby simplifying the
  #   geometry.
  # - Reduces the number of vertices within each Polygon, thereby greatly reducing
  #   the exported CSV file size.
  # - Smooths the boundaries of the cliff geometries, more closely resembling
  #   what is happening in the real world.
  # - Relaxes the somewhat artificial STEEP_THRESHOLD.
  # - Improves runtime of merge_data.py
  features = features.map(lambda f: f.setGeometry(f.buffer(10).geometry().simplify(maxError=50)))
  features = features.map(set_lat_long)
  features = features.map(set_slope)
  # Here features is a FeatureCollection object. Casting it to a list.
  return features.toList(2000)  # maximum number of features per rectangle


def set_lat_long(feature):
  """Set the latitude and longitude of the feature centroid."""
  centroid = feature.geometry().centroid(10 ** -2)
  return feature.set({'latitude': centroid.coordinates().get(1),
                      'longitude': centroid.coordinates().get(0)})

def set_slope(feature):
  """Get slope-angle of feature at various percentiles."""
  geo = feature.geometry()
  reducer = ee.Reducer.percentile(percentiles=[10, 20, 30, 40, 50, 60, 70, 80, 90])
  return feature.set(slope.reduceRegion(reducer=reducer, geometry=geo, scale=10))


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


# Exporting intermediate results to drive for local download
task1 = ee.batch.Export.table.toDrive(
    collection=results,
    description='exporting big wall data to drive',
    fileFormat='CSV',
    folder='earth-engine',
    fileNamePrefix='cliff_footprints',
)

# Exporting intermediate results as asset to investigate in code editor.
task2 = ee.batch.Export.table.toAsset(
    collection=results,
    description='exporting big wall data as asset',
    assetId='users/zebengberg/big_walls/cliff_footprints'
)

task1.start()
task2.start()
# Call ee.batch.Task.list() to see current status of exports.
