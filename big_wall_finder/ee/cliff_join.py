"""Merge big wall data with Mountain Project data. For each cliff-like formation
found, determine nearby routes from Mountain Project data. Mountain Project
route data will eventually be used as a target for modeling.
"""


import ee
from big_wall_finder import definitions
ee.Initialize()


def load_mp_data():
  """Load and process MP data in earth engine."""
  mp_data = ee.FeatureCollection(definitions.MP_DATA)
  rectangle = ee.Geometry.Rectangle(
      definitions.XMIN,
      definitions.YMIN,
      definitions.XMAX,
      definitions.YMAX
  )
  mp_data = mp_data.filterBounds(rectangle)
  mp_data = mp_data.filterMetadata('n_rock', 'greater_than', 0)
  return mp_data


def join():
  """Join MP data to ee cliffs."""

  mp_data = load_mp_data()
  cliffs = ee.FeatureCollection(definitions.EE_CLIFFS)

  # The MP data and the ee cliffs are in a many-to-many relationship.
  # We start by associating each MP area to its closest cliff.
  # If the MP area has no close cliffs, it is dropped.
  # The FeatureCollection `mp_joined` is the result of this operation.

  dist_filter = ee.Filter.withinDistance(
      distance=300,
      leftField='.geo',
      rightField='.geo',
      maxError=50
  )
  ee_join = ee.Join.saveBest(
      matchKey='associated_cliff',
      measureKey='distance_to_mp',
      outer=False  # unjoined MP areas are dropped
  )
  mp_joined = ee_join.apply(mp_data, cliffs, dist_filter)
  # adding cliff id for easier access later on
  mp_joined = mp_joined.map(lambda f: f.set({
      'associated_cliff': ee.Feature(f.get('associated_cliff')).id()
  }))
  return mp_joined, cliffs


def aggregate_mp():
  """For each ee cliff, aggregate associated MP data."""

  mp_joined, cliffs = join()
  # Now we map over cliffs, aggregating any associated MP data.

  def create_mp_label(cliff):
    index = index = cliff.id()
    associated_mp = mp_joined.filterMetadata(
        'associated_cliff', 'equals', index)
    n_rock = associated_mp.aggregate_sum('n_rock')
    n_views = associated_mp.aggregate_sum('n_views')
    names = associated_mp.aggregate_array('name')
    return cliff.set({
        'n_rock': n_rock,
        'n_views': n_views,
        'name': names.join(' - '),
    })

  cliffs = cliffs.map(create_mp_label)
  return cliffs


def main():
  """Run the main job."""
  cliffs = aggregate_mp()

  task = ee.batch.Export.table.toDrive(
      collection=cliffs,
      fileFormat='CSV',
      folder='earth-engine',
      description='cliff_joined'  # filename
  )

  task.start()


if __name__ == '__main__':
  main()
