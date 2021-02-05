"""Extract NAIP and DEM data for CNN that predicts slope and aspect of region from NAIP pixels."""

import ee
# call authenticate if have not run any recent jobs
# ee.Authenticate()
ee.Initialize()

# small shards needed to avoid `computed value too large` errors
N_SHARDS = 100
N_SAMPLES_PER_SHARD = 5000
KERNEL_SIZE = 32


# area of interest
yosemite = ee.Geometry.Rectangle(
    -119.67,
    37.55,
    -119.18,
    37.84
)

naip = ee.ImageCollection('USDA/NAIP/DOQQ')
naip = naip.filterBounds(yosemite)
naip = naip.filter(ee.Filter.date('2018-01-01', '2020-12-31'))
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


for shard in range(N_SHARDS):
  samples = image_array.sample(
      region=yosemite,
      scale=1,  # NAIP resolution
      numPixels=N_SAMPLES_PER_SHARD
  ).map(reduce_terrain)

  task = ee.batch.Export.table.toDrive(
      # see https://gis.stackexchange.com/questions/324121/
      # put folder 'yosemite_shards' anywhere in google drive
      collection=samples,
      folder='yosemite_shards',
      description='yosemite_shard_' + str(shard),  # doubles as filename
      fileFormat='TFRecord'
  )
  task.start()
