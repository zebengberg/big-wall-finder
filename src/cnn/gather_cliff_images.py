"""Gather NAIP image data for cliff features."""

import ee
ee.Initialize()


# Importing datasets
cliffs = ee.FeatureCollection('users/zebengberg/big_walls/cliff_data')
cliffs = cliffs.toList(100)
naip = ee.ImageCollection('USDA/NAIP/DOQQ')
naip = naip.filter(ee.Filter.date('2010-01-01', '2018-12-31')).mosaic()


KERNEL_SIZE = 8
kernel_weights = ee.List.repeat(ee.List.repeat(1, KERNEL_SIZE), KERNEL_SIZE)
kernel = ee.Kernel.fixed(KERNEL_SIZE, KERNEL_SIZE, kernel_weights)

def extract_samples(cliff):
  """Extract NAIP arrays over cliff footprint."""
  cliff = ee.Feature(cliff)
  footprint = cliff.geometry()
  naip_array = naip.clip(footprint).neighborhoodToArray(kernel)

  # taking the ceiling to guarantee at least one patch per cliff
  n_patches = ee.Number(cliff.get('pixel_count')).divide(20).ceil()

  # Possible to shard this ... see ee unet example.
  patches = naip_array.sample(
      region=footprint,
      scale=1,
      numPixels=n_patches,  # either use numPixels or factor
      tileScale=1,
      geometries=True)
  patches = patches.map(lambda f: f.set({
      'height': cliff.get('height'),
      'pixel_count': cliff.get('pixel_count'),
      'id': cliff.get('system:index')}))
  return patches.toList(n_patches)


cliffs = cliffs.map(extract_samples)
sizes = cliffs.map(lambda c: ee.List(c).size())
cliffs = cliffs.flatten()
cliffs = ee.FeatureCollection(cliffs)

N_SHARDS = 1
for shard in range(N_SHARDS):
  desc = 'naip_shard_' + str(shard)
  feature_labels = ['B', 'G', 'R', 'N', 'height', 'pixel_count']
  task = ee.batch.Export.table.toDrive(
      collection=cliffs,
      description=desc,
      folder='earth-engine',
      fileNamePrefix=desc,
      fileFormat='TFRecord',
      selectors=feature_labels
  )
  task.start()
