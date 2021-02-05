"""Gather NAIP image data for cliff features."""

import ee
import params
ee.Initialize()


# Importing NAIP
naip = ee.ImageCollection('USDA/NAIP/DOQQ')
naip = naip.filter(ee.Filter.date('2010-01-01', '2018-12-31')).mosaic()

# Importing cliffs and doing some filtering.
cliffs = ee.FeatureCollection('users/zebengberg/big_walls/merged_data')
cliffs = cliffs.filterMetadata('mp_score', 'greater_than', 0)
cliffs = cliffs.toList(cliffs.size())

# Giving each cliff a custom immutable index
cliff_ids = ee.List.sequence(0, cliffs.size().subtract(1))
indices = ee.List.sequence(0, cliffs.size().subtract(1))
cliffs = indices.map(lambda i: ee.Feature(cliffs.get(i)).set('cliff_id', i))

# Defining the kernel for the NAIP pixel array
kernel_weights = ee.List.repeat(ee.List.repeat(1, params.KERNEL_SIZE), params.KERNEL_SIZE)
kernel = ee.Kernel.fixed(params.KERNEL_SIZE, params.KERNEL_SIZE, kernel_weights)

def extract_samples(cliff):
  """Extract NAIP arrays over cliff footprint."""
  cliff = ee.Feature(cliff)
  footprint = cliff.geometry()
  naip_array = naip.clip(footprint).neighborhoodToArray(kernel)

  # Taking the ceiling to guarantee at least one patch per cliff.
  # pixel_count is actually the ratio pixel_count / height
  # height has been divided by 1000
  N_SAMPLES_FACTOR = 0.1
  n_patches = ee.Number(cliff.get('pixel_count')) \
              .multiply(cliff.get('height')) \
              .multiply(N_SAMPLES_FACTOR) \
              .multiply(1000) \
              .ceil()


  patches = naip_array.sample(
      region=footprint,
      scale=1,
      numPixels=n_patches,  # either use numPixels or factor
      tileScale=1,
      geometries=True)

  scalar_dict = {k: cliff.get(k) for k in params.SCALAR_KEYS}
  patches = patches.map(lambda f: f.set(scalar_dict))
  return patches.toList(n_patches)


cliffs = cliffs.map(extract_samples)
sizes = cliffs.map(lambda c: ee.List(c).size())
cliffs = cliffs.flatten()
cliffs = ee.FeatureCollection(cliffs)

N_SHARDS = 1
for shard in range(N_SHARDS):
  desc = 'naip_shard_' + str(shard)
  task = ee.batch.Export.table.toDrive(
      collection=cliffs,
      description=desc,
      folder='earth-engine/naip_shards',
      fileNamePrefix=desc,
      fileFormat='TFRecord',
      selectors=params.FEATURES_DICT.keys()
  )
  task.start()
