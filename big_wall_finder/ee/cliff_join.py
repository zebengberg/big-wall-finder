"""Merge big wall data with Mountain Project data. For each cliff-like formation
found, determine nearby routes from Mountain Project data. Mountain Project
route data will eventually be used as a target for modeling.
"""


import ee
from big_wall_finder import definitions
ee.Initialize()


CLIFFS = ee.FeatureCollection(definitions.EE_CLIFFS)
DEFAULT = ee.Dictionary({'n_rock': 0, 'n_views': 0, 'name': ''})


def load_mp_data():
  """Load and process MP data."""
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


def join_mp_to_cliffs():
  """Join MP data to ee cliffs.

  The MP data and the ee cliffs are in a many-to-many relationship. We
  associate each MP area to its closest cliff. If the MP area has no nearby
  cliffs, it is dropped. This function returns a FeatureCollection of MP areas
  which are within 300m of a cliff. The cliff ID is included as a property."""

  mp_data = load_mp_data()

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
  mp_joined = ee_join.apply(mp_data, CLIFFS, dist_filter)

  # adding cliff id for easier access later on
  return mp_joined.map(lambda f: f.set({
      # overwriting 'associated_cliff' key
      'associated_cliff': ee.Feature(f.get('associated_cliff')).id()
  }))


def joined_mp_as_dict():
  """Convert joined FeatureCollection to dictionary whose keys are cliff IDs and
  whose values are accumulated MP data over the cliff."""

  mp_joined = join_mp_to_cliffs()

  def accumulator(cur, acc):
    cur = ee.Feature(cur)
    acc = ee.Dictionary(acc)

    cliff_index = ee.String(cur.get('associated_cliff'))
    n_rock = ee.Number(cur.get('n_rock'))
    n_views = ee.Number(cur.get('n_views'))
    name = ee.String(cur.get('name'))

    d = ee.Dictionary(acc.get(cliff_index, DEFAULT))

    d = d.set('n_rock', n_rock.add(d.get('n_rock')))
    d = d.set('n_views', n_views.add(d.get('n_views')))
    d = d.set('name', name.cat(' - ').cat(d.get('name')))

    return acc.set(cliff_index, d)

  return mp_joined.iterate(accumulator)


def aggregate_mp():
  """For each ee cliff, aggregate associated MP data."""

  mp_dict = ee.Dictionary(joined_mp_as_dict())
  # Now we map over cliffs, aggregating any associated MP data.

  def create_label(cliff):
    index = cliff.id()
    aggregated_mp = ee.Dictionary(mp_dict.get(index, DEFAULT))

    return cliff.set({
        'n_rock': aggregated_mp.get('n_rock'),
        'n_views': aggregated_mp.get('n_views'),
        'name': aggregated_mp.get('name'),
    })

  return CLIFFS.map(create_label)


def join_cliffs_to_mp(cliffs):
  """For each cliff, determine the distance to the closest MP area.

  As before, we have a many-to-many relationship. For each cliff, we set a
  property measuring its distance to nearest MP area within a 800m threshold.
  This property will be used as a measure of cliff accessibility later."""

  mp_data = load_mp_data()
  dist_filter = ee.Filter.withinDistance(
      distance=800,
      leftField='.geo',
      rightField='.geo',
      maxError=200
  )

  # using 'vicinity_n_areas' as key to overwrite it below
  ee_join = ee.Join.saveAll(matchesKey='vicinity_n_areas', outer=True)
  cliffs = ee_join.apply(cliffs, mp_data, dist_filter)

  def aggregate_vicinity_mp_areas(cliff):
    mp_areas = ee.FeatureCollection(ee.List(cliff.get('vicinity_n_areas')))
    return cliff.set({
        'vicinity_n_rock': mp_areas.aggregate_sum('n_rock'),
        'vicinity_n_views': mp_areas.aggregate_sum('n_views'),
        'vicinity_n_areas': mp_areas.size()  # overwriting
    })

  return cliffs.map(aggregate_vicinity_mp_areas)


def main():
  """Run the main job."""
  cliff_joined = aggregate_mp()
  cliff_joined = join_cliffs_to_mp(cliff_joined)

  task1 = ee.batch.Export.table.toDrive(
      collection=cliff_joined,
      description='cliff_joined',  # filename
      fileFormat='CSV',
      folder='earth-engine',
  )

  task2 = ee.batch.Export.table.toAsset(
      collection=cliff_joined,
      description='cliffJoinedAsEEAsset',
      assetId=definitions.EE_JOINED
  )

  # call ee.batch.Task.list() to see current status of exports
  task1.start()
  task2.start()


if __name__ == '__main__':
  main()
