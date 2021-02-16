"""Test MP data."""

import ee
ee.Initialize()


def test_mp_data():
  """Print counts of MP data within certain geometries."""
  ee_root_dir = ee.data.getAssetRoots()[0]['id']
  mp_data = ee.FeatureCollection(ee_root_dir + '/big_wall_finder/mp_data')
  yosemite_geo = ee.Geometry.Rectangle(-119.7, 37.0, -119.5, 38.0)
  yosemite = mp_data.filterBounds(yosemite_geo)
  print('Number of yosemite areas:', yosemite.size().getInfo())

  desert_geo = ee.Geometry.Rectangle(-116.7, 37.0, -116.5, 38.0)
  desert = mp_data.filterBounds(desert_geo)
  assert desert.size().getInfo() == 0


if __name__ == '__main__':
  test_mp_data()
