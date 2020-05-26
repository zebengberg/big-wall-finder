import pandas as pd
import numpy as np
from tqdm import tqdm

def prepare_big_wall_data():
  """Merge and clean the datasets calculated with earth engine.

  See the notebook explore_data.ipynb for a detailed discussion.
  """
  df = pd.read_csv('../data/ee_joined.csv')
  mp = pd.read_csv('../data/mp_joined.csv')

  # Merging df with mp.
  print('Merging....')
  df['mp_score'] = 0
  df['num_views'] = 0
  for i, row in tqdm(df.iterrows(), total=df.shape[0]):
    filtered = mp[mp.custom_index == row.custom_index]
    mp_count = filtered.shape[0]
    if mp_count:
      df.at[i, 'num_views'] = filtered.num_views.sum()
      df.at[i, 'mp_score'] = 1000 + filtered.num_rock_routes.sum() + filtered.num_views.sum()

  # Giving mp_score a log-weighting; it now takes on values between 0 and 1.
  # A score with 1 is as good as el cap.
  df.mp_score = df.mp_score.map(lambda x: 0 if x < 1000 else np.log2(x) / 10 - 1).clip(0, 1)

  # Removing holes; see notebook for visualization.
  print('Cleaning....')
  df = df[(df.height < 2.5 * df.pixel_count + 100) & (df.pixel_count > 10)]

  # Values in landsat and geology columns do not need scaling. They are already
  # distributed somewhat normally around 0 with standard deviation close to 1. We
  # do remove landsat bands with negative values -- around 11 of these.
  df = df[(df.B2 > 0) & (df.B4 > 0) & (df.B5 > 0) & (df.B6 > 0) & (df.B7 > 0)]

  # Reassigning pixel_count to a ratio.
  df.pixel_count /= df.height

  # Scaling height so that it is contained between 0 and 1.
  df.height /= 1000

  # Determining which cliffs are accessible; these will comprise the training set.
  accessible = (df.num_views > 1000) | (df.vicinity_num_views > 5000) | \
               ((df.road_within_500m == 1) & (df.population_within_30km > 10_000)) | \
               ((df.road_within_1000m == 1) & (df.population_within_100km > 500_000)) | \
               ((df.road_within_1500m == 1) & (df.population_within_100km > 1_000_000)) | \
               ((df.road_within_2000m == 1) & (df.population_within_100km > 2_000_000))

  df['is_accessible'] = accessible

  # Dropping all the stuff we don't need.
  df.drop(columns=['road_within_500m',
                   'road_within_1000m',
                   'road_within_1500m',
                   'road_within_2000m',
                   'road_within_3000m',
                   'population_within_30km',
                   'population_within_100km',
                   'population_within_200km',
                   'num_views',
                   'vicinity_num_rock_routes',
                   'vicinity_num_views',
                   'system:index',
                   'custom_index',
                   'centroid',
                   'centroid_lith',
                   'vicinity_mp_areas'], inplace=True)

  return df


if __name__ == '__main__':
  merged = prepare_big_wall_data()
  print('Writing....')
  merged.to_csv('../data/merged_data.csv', header=True, index=False)
