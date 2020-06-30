"""Gather NAIP image data as numpy array for cliff features."""

import ee
ee.Initialize()


# Importing datasets
cliffs = ee.FeatureCollection('users/zebengberg/big_walls/cliff_footprints')
cliffs = cliffs.toList(100_000)
naip = ee.ImageCollection('USDA/NAIP/DOQQ')
naip = naip.filter(ee.Filter.date('2010-01-01', '2018-12-31')).mosaic()
naip = naip.reproject(crs='EPSG:4326', scale=1)


def extract_image(cliff):
  """Extract NAIP data as array over cliff footprint."""
  cliff = ee.Feature(cliff)
  footprint = cliff.geometry()
  cliff_image = naip.clip(footprint)

  rect = cliff.bounds().geometry()
  sub_rects = partition_rectangle(rect, 400)
  sub_rects = ee.FeatureCollection(sub_rects)
  sub_rects = sub_rects.filterBounds(footprint)
  # At most 2^18 pixels allowed with sampleRectangle method
  sub_rects = sub_rects.map(lambda r: cliff_image.sampleRectangle(region=r.geometry(),
                                                                  defaultValue=0))
  return sub_rects.toList(2000)



def partition_rectangle(rect, side_length):
  """Partition rectangle into ee.List of subrectangles."""

  # SW, SE, NE corners of rectangle
  p0 = ee.Geometry.Point(ee.List(rect.coordinates().get(0)).get(0))
  p1 = ee.Geometry.Point(ee.List(rect.coordinates().get(0)).get(1))
  p2 = ee.Geometry.Point(ee.List(rect.coordinates().get(0)).get(2))

  # Side lengths of rectangle
  dx = p0.distance(p1)
  dy = p1.distance(p2)

  # Sides of rectangle
  x = ee.Geometry.LineString([p0, p1])
  y = ee.Geometry.LineString([p1, p2])

  # Partitioning LineStrings into MultiLineStrings
  x_cuts = ee.List.sequence(0, dx, side_length)
  y_cuts = ee.List.sequence(0, dy, side_length)
  x = x.cutLines(x_cuts).coordinates()
  y = y.cutLines(y_cuts).coordinates()

  def x_map(x_coord):
    x0 = ee.Number(ee.List(ee.List(x_coord).get(0)).get(0))
    x1 = ee.Number(ee.List(ee.List(x_coord).get(1)).get(0))

    def y_map(y_coord):
      y0 = ee.Number(ee.List(ee.List(y_coord).get(0)).get(1))
      y1 = ee.Number(ee.List(ee.List(y_coord).get(1)).get(1))
      return ee.Feature(ee.Geometry.Rectangle(x0, y0, x1, y1))

    return y.map(y_map)

  return x.map(x_map).flatten()

# Running the job.
cliffs = cliffs.map(extract_image)  # an ee.List of ee.List
cliffs = cliffs.flatten()
cliffs = ee.FeatureCollection(cliffs)

# Exporting results to drive
task = ee.batch.Export.table.toDrive(
    collection=cliffs,
    description='exporting naip data to drive',
    fileFormat='CSV',
    folder='earth-engine',
    fileNamePrefix='naip_data')
task.start()
