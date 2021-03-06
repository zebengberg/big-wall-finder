


import json
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from xgboost import XGBRegressor
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.neighbors import KNeighborsRegressor
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import RandomizedSearchCV
from imblearn.over_sampling import RandomOverSampler #, SMOTE, SVMSMOTE, ADASYN
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Dropout
from tensorflow.keras.wrappers.scikit_learn import KerasRegressor
from tensorflow.keras.optimizers import Adam, SGD, RMSprop



class Model():
  """Apply various ML models on cliff data."""

  # Static variables and class methods
  data = pd.read_csv('../data/merged_data.csv')
  accessible = data[data.is_accessible]

  models = {'linear': LinearRegression,
            'ridge': Ridge,
            'lasso': Lasso,
            'knn': KNeighborsRegressor,
            'tree': DecisionTreeRegressor,
            'forest': RandomForestRegressor,
            'xgb': XGBRegressor,
            'neural': None}

  best_params = None
  if os.path.exists('best_params.json'):
    with open('best_params.json') as f:
      best_params = json.load(f)

    # Adding in a few extra "best" parameters
    best_params['forest']['n_estimators'] = 500
    best_params['forest']['n_jobs'] = -1
    best_params['xgb']['n_estimators'] = 500
    best_params['xgb']['n_jobs'] = -1

    # Putting in temporarily empty 'neural' params
    best_params['neural'] = {}


  @classmethod
  def tune_all_hyperparameters(cls, n_iter, save=True):
    """Search over random hyperparameters for each model and save best."""
    best_params = {}
    for model_name in cls.models:
      m = cls(model_name)
      params = m.test_random_hyperparameters(n_iter=n_iter)
      best_params[model_name] = params
      m.model.set_params(**params)
      m.print_evaluate_hyperparameters()
    if save:
      if os.path.exists('best_params.json'):
        os.rename('best_params.json', 'best_params_old.json')
      with open('best_params.json', 'w') as f:
        json.dump(best_params, f, indent=2)

    return best_params


  def __init__(self, name, params=None):
    self.name = name
    self.X_train, self.X_test, self.y_train, self.y_test = self.set_train_test()

    if name in self.__class__.models:
      if name == 'neural':
        # Using vanilla tf.keras model
        def build_fn(dropout_rate=0, optimizer='adam', activation='relu',
                     neurons=100, learning_rate=0.01):
          model = Sequential()
          model.add(Dense(neurons, input_dim=self.X_train.shape[1],
                          activation=activation))
          model.add(Dropout(dropout_rate))
          model.add(Dense(1))
          opt_dict = {'adam': Adam(learning_rate=learning_rate),
                      'sgd': SGD(learning_rate=learning_rate),
                      'rmsprop': RMSprop(learning_rate=learning_rate)}

          model.compile(loss='mean_squared_error', optimizer=opt_dict[optimizer])
          return model
        self.model = KerasRegressor(build_fn=build_fn, verbose=1)

      else:
        self.model = self.__class__.models[name]()  # initializing model here
    else:
      raise TypeError(f'Unknown model! The only known models are: {self.__class__.models.keys()}')
    if params:
      self.model.set_params(**params)  # may throw error if keyword not viable
    elif self.__class__.best_params:
      self.model.set_params(**self.__class__.best_params[self.name])

  def set_train_test(self, train_size=0.9, create_balanced=False):
    """Create balanced classes by oversampling."""

    # Creating the train test split.
    X = self.__class__.accessible.drop(columns=['latitude', 'longitude', 'is_accessible',
                                                '.geo', 'mp_score'])
    y = self.__class__.accessible.mp_score
    mask = np.random.rand(len(X)) < train_size
    X_train, X_test, y_train, y_test = X[mask], X[~mask], y[mask], y[~mask]

    if not create_balanced:
      return X_train, X_test, y_train, y_test

    # Discretizing the continuous target variable mp_score to create 10 integer classes.
    y_train_discretized = np.ceil(10 * y_train).astype('int32')

    # Grabbing an equal number of samples from each class
    model = RandomOverSampler()
    X_train, _ = model.fit_resample(X_train, y_train_discretized)

    # Back to the continuous targets which were kept in X.
    indices = model.sample_indices_
    y_train = y.iloc[indices]

    return X_train, X_test, y_train, y_test


  def train(self):
    """Train the model."""
    self.model.fit(self.X_train, self.y_train)

  def print_score(self):
    """Print the r^2 score of the train and test set."""
    # May raise NotFittedError
    print('-' * 80)
    print(f'Scoring {self.name} model.')
    print(f'Train score: {self.model.score(self.X_train, self.y_train)}')
    print(f'Test score: {self.model.score(self.X_test, self.y_test)}')
    print('-' * 80 + '\n')

  def get_predictions(self):
    """Run the model on the entire dataset."""
    X_pred = self.__class__.data.drop(columns=['latitude', 'longitude', 'mp_score',
                                               'is_accessible', '.geo'])
    return self.model.predict(X_pred)

  def plot_feature_importance(self):
    """Plot feature importance of a tree method."""
    if self.name not in ['tree', 'forest', 'xgb']:
      raise NotImplementedError('Only implemented for tree models.')
    n_features = self.X_train.shape[1]
    plt.barh(range(n_features), self.model.feature_importances_, align='center')
    plt.yticks(np.arange(n_features), self.X_train.columns)
    plt.xlabel('Feature importance')
    plt.ylabel('Feature')
    plt.ylim(-1, n_features)
    plt.show()


  def test_random_hyperparameters(self, n_iter, n_folds=5, verbose=1):
    """Use cross validation to run model on various choices of hyperparameters."""

    # Early exit if running linear model; no hyperparameters available.
    if self.name == 'linear':
      return {}

    forest_grid = {'max_features': ['auto', 'sqrt'],
                   'max_depth': [4, 5, 6, 7, 8, 9, 10, None],
                   'min_samples_split': [2, 3, 4, 5],
                   'min_samples_leaf': [1, 2, 3, 4, 5],
                   'bootstrap': [True, False]}

    lasso_grid = {'alpha': [.0001, .0002, .0005, .001, .002, .005, .01, .1, 1, 10],
                  'tol': [2.5],
                  'max_iter': [5000]}  # doesn't converge with default values

    ridge_grid = {'alpha': [0.1, 1, 2, 5, 10, 20, 50, 100]}

    knn_grid = {'n_neighbors': [8, 16, 32, 64, 128],
                'p': [1, 1.5, 2, 2.5]}

    tree_grid = {'ccp_alpha': [0, .005, .01, .02, .05, .1],
                 'max_features': ['auto', 'sqrt'],
                 'max_depth': [3, 4, 5, 6, 7, None],
                 'min_samples_split': [2, 3, 4, 5],
                 'min_samples_leaf': [1, 2, 3, 4]}

    xgb_grid = {'max_depth': [3, 4, 5, 6, 7, 8, 9, None],
                'min_child_weight': [1, 2, 4, 6, 8, 10],
                # learning_rate = eta; should increase n_estimators with low eta
                'learning_rate': [.01, .03, .05, .1, .2],  
                'subsample': [.7, .75, .8, .85, .9],
                'colsample_bytree': [.7, .75, .8, .85, .9]}

    neural_grid = {'epochs': [10, 30, 100, 300, 1000],
                   'batch_size': [8, 16, 32, 64],
                   'learning_rate': [.001, .01, .1, .5],
                   'dropout_rate': [0, 0.05, 0.1, 0.15, 0.2],
                   'neurons': [100, 200, 300, 400],
                   'optimizer': ['sgd', 'rmsprop', 'adam'],
                   'activation': ['relu', 'tanh']}


    random_grids = {'ridge': ridge_grid,
                    'lasso': lasso_grid,
                    'knn': knn_grid,
                    'tree': tree_grid,
                    'forest': forest_grid,
                    'xgb': xgb_grid,
                    'neural': neural_grid}

    random_grid = random_grids[self.name]

    # Random search of hyperparameters chosen uniformly from possibilities above.
    rs = RandomizedSearchCV(estimator=self.model, param_distributions=random_grid,
                            n_iter=n_iter, cv=n_folds, verbose=verbose, n_jobs=2)
    rs.fit(self.X_train, self.y_train)
    return rs.best_params_

  def print_evaluate_hyperparameters(self):
    """Evaluate best hyperparameters from cross validation random search."""

    # Linear model has no hyperparameters to evaluate.
    if self.name != 'linear':
      self.train()
      print('#' * 80)
      print(f'{self.name} with best hyperparameters:')
      print(self.model.get_params())
      self.print_score()
      print('#' * 80)

      # Training with default parameters
      other = self.__class__(self.name)
      other.train()
      print(f'{other.name} with default hyperparameters:')
      print(other.model.get_params())
      other.print_score()
      print('#' * 80)


if __name__ == '__main__':
  #ran = run_all()
  #ran.to_csv('../data/simplified_results.csv', header=True, index=False)
  # results = Model.data[['latitude', 'longitude', 'height', 'mp_score']].copy()
  # results.height *= 1000
  # for model_name in Model.models:
  #   parameters = {}
  #   if model_name in ['forest', 'xgb']:
  #     parameters = {'n_estimators': 200, 'n_jobs': -1}
  #   m = Model(model_name, parameters)
  #   m.train()
  #   m.print_score()
  #   results[model_name + '_score'] = m.get_predictions()
  # results['summary_score'] = results.forest_score + results.xgb_score
  # results.sort_values(by='summary_score', ascending=False, inplace=True)
  # results = results[results.mp_score == 0]  # omitting what is already known!
  # print(results.drop(columns=['ridge_score', 'lasso_score']).head(50))  # dropping bad models
  # for model_name in Model.models:
  #   m = Model(model_name)
  #   m.print_evaluate_hyperparameters()
  bp = Model.tune_all_hyperparameters(n_iter=200)
  print(bp)


# TODO: hyperparameters for NN
# PCA in jupyter
# Look at strongest model, and engineer more features for it
# Run a nearest neighbor for yosemite cliffs.
# Add n_estimators... to forest, xgb
# don't use all accessible cliffs to train; only use those with MP entries

