"""For each cliff, extract samples of NAIP data."""

from big_wall_finder import definitions
import ee
ee.Initialize()


naip = ee.ImageCollection('USDA/NAIP/DOQQ')
naip = naip.filterDate('2010-01-01', '2025-01-01')
naip = naip.sort('system:time_start', False)  # reverse chronological

size = definitions.NAIP_KERNEL_SIZE
weights = ee.List.repeat(ee.List.repeat(1, size), size)
kernel = ee.Kernel.fixed(size, size, weights)


def extract_naip(cliff):
  """Extract samples of NAIP array from cliff."""
  cliff = ee.Feature(cliff)
  local_naip = naip.filterBounds(cliff.geometry())  # local ee.ImageCollection
  local_naip = local_naip.toList(3)  # 3 most recent images

  # for most cliffs, local_naip.size() == 3
  n_samples = cliff.area().multiply(0.001).divide(local_naip.size()).ceil()

  def extract_samples_from_image(image):
    image = ee.Image(image)
    s = image.spectralGradient().rename('S')
    # image = image.addBands(s)
    image = image.neighborhoodToArray(kernel)
    sample = image.sample(
        scale=1,
        numPixels=n_samples,
        region=cliff.geometry(),
        geometries=True
    )
    return sample.toList(n_samples)

  local_naip = local_naip.map(extract_samples_from_image)
  local_naip = local_naip.flatten()
  local_naip = local_naip.map(
      lambda f: ee.Feature(f).set({'cliff_id': cliff.id()})
  )
  return local_naip


def extract_naip2(cliff):
  sample = naip.mosaic().neighborhoodToArray(kernel).sample(
      region=ee.Feature(cliff).geometry(),
      scale=1,
      numPixels=100,
      geometries=True
  )
  return sample.toList(100)


def main():
  """Run the main job."""
  footprints = ee.FeatureCollection(definitions.EE_CLIFF_FOOTPRINTS)
  footprints = footprints.toList(100)
  footprints = footprints.map(extract_naip2)
  footprints = footprints.flatten()
  footprints = ee.FeatureCollection(footprints)

  task = ee.batch.Export.table.toDrive(
      collection=footprints,
      folder='earth-engine',
      description='naip_test',  # filename
      fileFormat='TFRecord'
  )
  task.start()


if __name__ == '__main__':
  main()
