import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.neighbors import KNeighborsRegressor
from imblearn.over_sampling import SMOTE, SVMSMOTE, ADASYN, RandomOverSampler
from prepare_big_wall_data import prepare_big_wall_data

# Importing data
accessible, inaccessible = prepare_big_wall_data()



def build_x_y(prob=0.9):
  """Create balanced classes by oversampling."""
  X_pred = inaccessible.copy()  # to be used to make predictions

  X = accessible.drop(columns=['latitude', 'longitude', 'mp_score'])
  mask = np.random.rand(len(X)) < prob
  X_train = X[mask]
  X_test = X[~mask]

  # For now, running classification models instead of regression.
  y = accessible.mp_score > 0
  y = y.map(lambda x: 1 if x else 0)
  y_train = y[mask]
  y_test = y[~mask]

  # Oversampling the imbalanced training data.
  X_train, y_train = RandomOverSampler().fit_resample(X_train, y_train)

  return X_train, y_train, X_test, y_test, X_pred


def run_linear():
  """Train and predict with a simple linear regression."""
  X_train, y_train, X_test, y_test, X_pred = build_x_y()
  model = LinearRegression().fit(X_train, y_train)
  print('Linear model fit score: {}\n'.format(model.score(X_test, y_test)))
  y_pred = model.predict(X_pred.drop(columns=['latitude', 'longitude', 'mp_score']))

  print_top_results(X_pred, y_pred, 'linear')
  return y_pred


def run_logistic():
  """Train and predict with a simple logistic classification."""
  X_train, y_train, X_test, y_test, X_pred = build_x_y()
  model = LogisticRegression(max_iter=200).fit(X_train, y_train)
  print('Logistic model fit score: {}\n'.format(model.score(X_test, y_test)))
  
  # Use predict_proba() to get probabilities of hittng a class, not classes themselves.
  # On the otherhand, predict() uses a cutoff at 0.5 to make a choice.
  y_pred = model.predict_proba(X_pred.drop(columns=['latitude', 'longitude', 'mp_score']))
  y_pred = y_pred[:, 1:]

  print_top_results(X_pred, y_pred, 'logistic')
  return y_pred
  

def run_xgb():
  """Train and predict with a boosted gradient tree."""
  X_train, y_train, X_test, y_test, X_pred = build_x_y()
  # dmatrix = xgb.DMatrix(data=X_train, label=y_train)
  # can also use XGBClassifier
  model = xgb.XGBRegressor(objective ='reg:squarederror', colsample_bytree = 0.3, learning_rate = 0.1,
              max_depth = 5, alpha = 10, n_estimators = 10)
  model.fit(X_train, y_train)
  
  # Results
  y_pred = model.predict(X_pred.drop(columns=['latitude', 'longitude', 'mp_score']))

  # Printing and returning
  print_top_results(X_pred, y_pred, 'xgb')
  return y_pred


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

def write_results():
  pass
  # eventually call something like:
  # results.to_csv('../data/results.csv', header=True, index=False)


def print_top_results(X, y, model):
  """Print the inaccessible cliff formations with the highest predicted score."""
  X['score'] = y
  X.height *= 1000
  X.sort_values(by='score', ascending=False, inplace=True)
  X = X[['latitude', 'longitude', 'height', 'mp_score', 'score']]

  print('Top 20 results from {} prediction.\n'.format(model))
  print(X[:40].to_string(index=False))
  print('\n' + '_' * 80)



if __name__ == '__main__':
  # run_linear()
  # run_logistic()
  # run_xgb()
  run_knn()