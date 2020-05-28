import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.neighbors import KNeighborsRegressor
from sklearn.metrics import r2_score
from imblearn.over_sampling import SMOTE, SVMSMOTE, ADASYN, RandomOverSampler

# Importing data
df = pd.read_csv('../data/merged_data.csv')
accessible = df[df.is_accessible]
inaccessible = df[~df.is_accessible]



def create_train_test(train_size=0.9):
  """Create balanced classes by oversampling."""

  # Discretizing the continuous target variable mp_score to create 10 integer classes
  X = accessible.drop(columns=['latitude', 'longitude', 'is_accessible', '.geo'])
  y = np.ceil(10 * accessible.mp_score).astype('int32')

  # Grabbing an equal number of samples from each class
  model = RandomOverSampler()
  X, y = model.fit_resample(X, y)

  # Going back to the continuous targets which we're kept in X. Using the
  # model indices to reset y.
  indices = model.sample_indices_
  y = X.mp_score[indices]
  X.drop('mp_score', axis=1, inplace=True)

  # Building the train test split.
  mask = np.random.rand(len(X)) < train_size
  X_train = X[mask]
  X_test = X[~mask]
  y_train = y[mask]
  y_test = y[~mask]
  return X_train, y_train, X_test, y_test


def get_predictions(model, X_test=None, y_test=None, display=False):
  """Print the inaccessible cliff formations with the highest predicted score."""
  
  results = inaccessible.drop(columns=['is_accessible', '.geo'])
  X_pred = results.drop(columns=['latitude', 'longitude', 'mp_score'])
  results['score'] = model.predict(X_pred)
  results.height *= 1000
  results = results[['latitude', 'longitude', 'height', 'mp_score', 'score']]
  results.sort_values(by='score', ascending=False, inplace=True)

  if display:
    print('\n' + '_' * 80 + '\n')
    print(f'Model: {model.name}')
    if X_test is None and y_test is None:
      print('Pass X_test and y_test if you want to model score.')
    else:
      y_test_pred = model.predict(X_test)
      print(f'Fit score: {r2_score(y_test, y_test_pred)}')
    number_to_print = 20
    print(f'Top {number_to_print} results from {model.name} prediction.\n')
    print(results[:number_to_print].to_string(index=False))
    print('\n' + '_' * 80)

  return results

def run_linear(display=False):
  """Train a simple linear regression."""
  X_train, y_train, X_test, y_test = create_train_test()
  model = LinearRegression()
  model.fit(X_train, y_train)
  model.name = 'linear'
  return get_predictions(model, X_test, y_test, display)

def run_lasso(display=False):
  """Train a lasso linear regression."""
  X_train, y_train, X_test, y_test = create_train_test()
  model = Lasso(alpha=0.001)
  model.fit(X_train, y_train)
  model.name = 'lasso'
  return get_predictions(model, X_test, y_test, display)

def run_ridge(display=False):
  """Train a lasso linear regression."""
  X_train, y_train, X_test, y_test = create_train_test()
  model = Ridge(alpha=100)
  model.fit(X_train, y_train)
  model.name = 'ridge'
  return get_predictions(model, X_test, y_test, display)
    
def run_xgb(display=False):
  """Train a boosted gradient tree."""
  print('\n' + '_' * 80 + '\n')
  X_train, y_train, X_test, y_test = create_train_test()
  model = xgb.XGBRegressor(objective ='reg:squarederror', colsample_bytree = 0.3,
  learning_rate = 0.1, max_depth = 5, alpha = 10, n_estimators = 10)
  model.fit(X_train, y_train)
  model.name = 'boosted tree'
  return get_predictions(model, X_test, y_test, display)







# Old stuff below.
def run_knn(k=40):
  """Predict with k-nearest neighbor regressor."""
  X_train, y_train, X_test, y_test, X_pred = build_x_y(1)
  model = KNeighborsRegressor(n_neighbors=k, weights='distance')
  model.fit(X_train, y_train)

  # Results
  y_pred = model.predict(X_pred.drop(columns=['latitude', 'longitude', 'mp_score']))

  # Printing and returning
  print_top_results(X_pred, y_pred, 'knn')
  return y_pred


def run_random_forest():
  pass

def run_neural_network():
  pass

def write_results(y):
  df = pd.read_csv('../data/ee_data.csv')
  # Dropping columns we don't care about.
  results = df[['height', 'latitude', 'longitude', 'mp_score', 'pixel_count', '.geo']]
  predictions = pd.Series(data=y, index=inaccessible.index, name='prediction')
  results = results.join(predictions)
  results.drop(columns=['latitude', 'longitude']).to_csv('../data/results.csv',
    header=True, index=False)
  results.drop(columns=['.geo', 'pixel_count']).to_csv('../data/simplified_results.csv',
    header=True, index=False)


def print_top_results(X, y, model):
  """Print the inaccessible cliff formations with the highest predicted score."""
  X['score'] = y
  X.height *= 1000
  X.sort_values(by='score', ascending=False, inplace=True)
  X = X[['latitude', 'longitude', 'height', 'mp_score', 'score']]

  print('Top 20 results from {} prediction.\n'.format(model))
  print(X[:20].to_string(index=False))
  print('\n' + '_' * 80)



if __name__ == '__main__':
  y_pred = run_xgb()
  write_results(y_pred)
  # run_linear()
  # run_logistic()
  # run_xgb()
  # run_knn()