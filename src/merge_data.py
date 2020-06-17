import pandas as pd
import numpy as np
from tqdm import tqdm

def prepare_big_wall_data():
  """Merge and clean the datasets calculated with earth engine.

  See the notebook explore_data.ipynb for a detailed discussion.
  """
  cliff = pd.read_csv('../data/cliff_joined.csv')
  mp = pd.read_csv('../data/mp_joined.csv')

  # Merging cliff with mp.
  print('Merging....')
  cliff['mp_score'] = 0
  cliff['num_views'] = 0
  for i, row in tqdm(cliff.iterrows(), total=cliff.shape[0]):
    filtered = mp[mp.custom_index == row.custom_index]
    mp_count = filtered.shape[0]
    if mp_count:
      cliff.at[i, 'num_views'] = filtered.num_views.sum()
      cliff.at[i, 'mp_score'] = 1000 + filtered.num_rock_routes.sum() + filtered.num_views.sum()

  # Giving mp_score a log-weighting; it now takes on values between 0 and 1.
  # A score with 1 is as good as el cap.
  cliff.mp_score = cliff.mp_score.map(lambda x: 0 if x < 1000 else np.log2(x) / 10 - 1).clip(0, 1)

  # Removing holes; see notebook for visualization.
  print('Cleaning....')
  cliff = cliff[(cliff.height < 2.5 * cliff.pixel_count + 100) & (cliff.pixel_count > 10)]

  # Values in landsat and geology columns do not need scaling. They are already
  # distributed somewhat normally around 0 with standard deviation close to 1. We
  # do remove landsat bands with negative values -- around 70 of these.
  cliff = cliff[(cliff.B2_p20 > 0) & (cliff.B4_p20 > 0) & (cliff.B5_p20 > 0) &
                (cliff.B6_p20 > 0) & (cliff.B7_p20 > 0)]

  # Removing rows with null satellite image values.
  cliff = cliff[cliff.R_p10.notnull()]

  # Reassigning pixel_count to a ratio.
  cliff.pixel_count /= cliff.height

  # Scaling height so that it is contained between 0 and 1.
  cliff.height /= 1000

  # Determining which cliffs are accessible; these will comprise the training set.
  accessible = (cliff.num_views > 1000) | (cliff.vicinity_num_views > 5000) | \
               ((cliff.road_within_500m == 1) & (cliff.population_within_30km > 10_000)) | \
               ((cliff.road_within_1000m == 1) & (cliff.population_within_60km > 100_000)) | \
               ((cliff.road_within_1500m == 1) & (cliff.population_within_100km > 1_000_000)) | \
               ((cliff.road_within_2000m == 1) & (cliff.population_within_100km > 2_000_000))

  cliff['is_accessible'] = accessible

  # Dropping all the stuff we don't need.
  cliff.drop(columns=['road_within_500m',
                      'road_within_1000m',
                      'road_within_1500m',
                      'road_within_2000m',
                      'population_within_30km',
                      'population_within_60km',
                      'population_within_100km',
                      'num_views',
                      'vicinity_num_rock_routes',
                      'vicinity_num_views',
                      'system:index',
                      'custom_index',
                      'vicinity_mp_areas'], inplace=True)

  return cliff


if __name__ == '__main__':
  merged = prepare_big_wall_data()
  print('Writing....')
  merged.to_csv('../data/merged_data.csv', header=True, index=False)
