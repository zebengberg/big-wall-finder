"""Extract NAIP and DEM data for CNN that predicts slope and aspect of region from NAIP pixels."""

import ee
# call authenticate if have not run any recent jobs
# ee.Authenticate()
ee.Initialize()

# small shards needed to avoid `computed value too large` errors
N_TRAIN_SHARDS = 200
N_EVAL_SHARDS = 50
N_SAMPLES_PER_SHARD = 5000
KERNEL_SIZE = 32


# area of interest
xmin = -119.7
xmax = -119.1
ymin = 37.5
ymax = 37.9
delta_x = 0.01

yosemite = ee.Geometry.Rectangle(xmin, ymin, xmax, ymax)
coords = ee.List.sequence(ymin, ymax, 2 * delta_x)
train_rectangles = coords.map(lambda coord: ee.Geometry.Rectangle(
    ee.List([
        xmin,
        coord,
        xmax,
        ee.Number(coord).add(delta_x)
    ])))
train_geometry = ee.Geometry.MultiPolygon(train_rectangles)
eval_rectangles = coords.map(lambda coord: ee.Geometry.Rectangle(
    ee.List([
        xmin,
        ee.Number(coord).add(delta_x),
        xmax,
        ee.Number(coord).add(delta_x).add(delta_x)
    ])))
eval_geometry = ee.Geometry.MultiPolygon(eval_rectangles)


naip = ee.ImageCollection('USDA/NAIP/DOQQ')
naip = naip.filterBounds(yosemite)
naip = naip.filterDate('2018-01-01')
# at this point, the ImageCollection contains a single image
naip = naip.max()  # grabbing that single image

dem = ee.Image('USGS/NED')
slope_image = ee.Terrain.slope(dem)
aspect_image = ee.Terrain.aspect(dem)

# concatenating input features with targets
image = ee.Image.cat([naip, slope_image, aspect_image])

# the size of each CNN image
weights = ee.List.repeat(ee.List.repeat(1, KERNEL_SIZE), KERNEL_SIZE)
kernel = ee.Kernel.fixed(KERNEL_SIZE, KERNEL_SIZE, weights)
image_array = image.neighborhoodToArray(kernel)


def reduce_terrain(feature: ee.Feature):
  """Convert slope and aspect targets to number by taking mean."""
  slope = ee.Array(feature.get('slope'))
  slope = slope.toList()
  slope = slope.flatten()
  slope = slope.reduce(ee.Reducer.mean())

  aspect = ee.Array(feature.get('aspect'))
  aspect = aspect.toList()
  aspect = aspect.flatten()
  aspect = aspect.reduce(ee.Reducer.mean())

  return feature.set({'slope': slope, 'aspect': aspect})


def make_shards(arg: str):
  """Make train or eval shards."""
  if arg == 'train':
    n_shards = N_TRAIN_SHARDS
    region = train_geometry
  elif arg == 'eval':
    n_shards = N_EVAL_SHARDS
    region = eval_geometry
  else:
    raise ValueError('Unknown arg')

  for shard in range(n_shards):
    samples = image_array.sample(
        region=region,
        scale=1,  # NAIP resolution
        numPixels=N_SAMPLES_PER_SHARD
    ).map(reduce_terrain)

    task = ee.batch.Export.table.toDrive(
        # see https://gis.stackexchange.com/questions/324121/
        # put folder 'yosemite_shards' anywhere in google drive
        collection=samples,
        folder='yosemite_shards',
        description='yosemite_' + arg + '_' + str(shard),  # filename
        fileFormat='TFRecord'
    )
    task.start()


if __name__ == '__main__':
  make_shards('train')
  make_shards('eval')
