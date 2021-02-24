"""Determine regions of steep terrain in the western US."""

import ee
from big_wall_finder import definitions
ee.Initialize()


# building elevation layers and masks
dem = ee.Image('USGS/NED')
slope = ee.Terrain.slope(dem).rename('slope')
steep_terrain = slope.gt(definitions.STEEP_THRESHOLD)
dem = dem.updateMask(steep_terrain)

# giving steep_terrain a second band
# the first band is a boolean 0 or 1, second is the elevation
steep_terrain = steep_terrain.addBands(dem.toInt())

# calculating heights of each connected region of steep terrain
cliffs = steep_terrain.reduceConnectedComponents(reducer='minMax')
cliffs = cliffs.select('elevation_max').subtract(
    cliffs.select('elevation_min'))
cliffs = cliffs.updateMask(cliffs.gt(definitions.HEIGHT_THRESHOLD))


def build_rectangles():
  """Build an ee.List of rectangles covering the western US."""

  xmin, xmax, dx = -125, -102, 0.25
  ymin, ymax, dy = 31, 49, 0.25

  rectangles = ee.List.sequence(xmin, xmax, dx).map(
      lambda x: ee.List.sequence(ymin, ymax, dy).map(
          lambda y: ee.Geometry.Rectangle(ee.List(
              [x, y, ee.Number(x).add(dx), ee.Number(y).add(dy)]
          ))
      )
  )

  rectangles = rectangles.flatten()
  rectangles = rectangles.map(lambda f: ee.Feature(ee.Geometry(f)))
  rectangles = ee.FeatureCollection(rectangles)

  usa = ee.FeatureCollection("USDOS/LSIB_SIMPLE/2017")
  usa = usa.filter(ee.Filter.eq('country_co', 'US'))
  rectangles = rectangles.filterBounds(usa)

  # casting back to a List of geometries rather than a FeatureCollection
  # get_cliffs cannot be mapped over a FeatureCollection
  rectangles = rectangles.toList(200000)  # 200000 > number of rectangles
  return rectangles.map(lambda f: ee.Feature(f).geometry())


def get_cliffs(rectangle):
  """Search within rectangle at DEM resolution to find cliffs."""
  # getting the geometry and height of all cliffs within the rectangle
  # using height as a label for connectedness
  features = cliffs.reduceToVectors(
      reducer='countEvery',
      geometry=rectangle,
      scale=10,
      geometryType='polygon'
  )

  # renaming elevation properties
  features = features.select(['label', 'count'], ['height', 'pixel_count'])

  # buffering and simplifying the geometry of each calculated cliff
  # buffering serves several purposes:
  # - converts each MultiPolygon object to a Polygon object by
  #   eliminating intersections at single vertices, thereby simplifying the
  #   geometry
  # - reduces the number of vertices within each Polygon, thereby reducing
  #   the exported CSV file size
  # - smooths the boundaries of the cliff geometries, more closely resembling
  #   what is happening in the real world
  # - relaxes the somewhat artificial STEEP_THRESHOLD
  # - improves runtime of merge_data

  features = features.map(lambda f: f.setGeometry(
      f.buffer(10).geometry().simplify(maxError=50)
  ))
  features = features.map(set_lat_long)
  features = features.map(set_elevation)
  features = features.map(set_slope)

  # here features is a FeatureCollection object
  # casting it to a list using maximum 2000 features per rectangle
  return features.toList(2000)


def set_lat_long(feature):
  """Set the latitude and longitude of the feature centroid."""
  centroid = feature.geometry().centroid(1e-2)
  return feature.set({
      'latitude': centroid.coordinates().get(1),
      'longitude': centroid.coordinates().get(0)
  })


def set_elevation(feature):
  """Set the mean elevation of the cliff."""
  geo = feature.geometry()
  mean_ele = steep_terrain.select('elevation').reduceRegion(
      reducer='mean',
      geometry=geo,
      scale=10
  )
  return feature.set(mean_ele)


def set_slope(feature):
  """Get slope-angle of feature at various percentiles."""
  geo = feature.geometry()
  reducer = ee.Reducer.percentile(
      percentiles=[10, 20, 30, 40, 50, 60, 70, 80, 90]
  )
  percentiles = slope.reduceRegion(reducer=reducer, geometry=geo, scale=10)
  return feature.set(percentiles)


def main():
  """Run the main job."""
  rectangles = build_rectangles()
  results = rectangles.map(get_cliffs, True)  # dropping nulls
  results = results.flatten()  # flattening list of rectangles
  results = ee.FeatureCollection(results)  # casting from ee.List

  # export results to drive for local download
  task1 = ee.batch.Export.table.toDrive(
      collection=results,
      description='exporting big wall data to drive',
      fileFormat='CSV',
      folder='earth-engine',
      fileNamePrefix='cliff_footprints',
  )

  # export results to ee asset
  task2 = ee.batch.Export.table.toAsset(
      collection=results,
      description='exporting big wall data as asset',
      assetId=definitions.EE_CLIFF_FOOTPRINTS
  )

  # call ee.batch.Task.list() to see current status of exports
  task1.start()
  task2.start()


if __name__ == '__main__':
  gather()
