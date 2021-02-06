"""Build CNN that predicts slope and aspect of region from NAIP pixels."""

import os
import glob
import tensorflow as tf
from tensorflow.keras import layers


DATA_PATH = os.path.join(os.path.dirname(__file__), 'yosemite_shards')
TRAIN_RECORDS = glob.glob(DATA_PATH + '/*train*')
EVAL_RECORDS = glob.glob(DATA_PATH + '/*eval*')
FEATURES = ['R', 'G', 'B', 'N', 'slope', 'aspect']
KERNEL_SIZE = 32
COLUMNS = [
    tf.io.FixedLenFeature(shape=(KERNEL_SIZE, KERNEL_SIZE), dtype=tf.float32),
    tf.io.FixedLenFeature(shape=(KERNEL_SIZE, KERNEL_SIZE), dtype=tf.float32),
    tf.io.FixedLenFeature(shape=(KERNEL_SIZE, KERNEL_SIZE), dtype=tf.float32),
    tf.io.FixedLenFeature(shape=(KERNEL_SIZE, KERNEL_SIZE), dtype=tf.float32),
    tf.io.FixedLenFeature([], dtype=tf.float32),
    tf.io.FixedLenFeature([], dtype=tf.float32),
]
FEATURES_DICT = dict(zip(FEATURES, COLUMNS))


@tf.function
def convert_to_tuple(inputs):
  """Helper function to convert features into an input, output tuple."""
  feature_list = [inputs.get(key) for key in FEATURES[:4]]
  stacked = tf.stack(feature_list, axis=0)
  # Convert from CHW to HWC
  stacked = tf.transpose(stacked, [1, 2, 0])
  slope = inputs.get('slope') / 90
  sin_aspect = tf.math.sin(inputs.get('aspect') / 360 * 2 * 3.14159)
  cos_aspect = tf.math.cos(inputs.get('aspect') / 360 * 2 * 3.14159)
  #target_list = [inputs.get(key) for key in FEATURES[4:]]
  return stacked, [slope, sin_aspect, cos_aspect]


def build_dataset(arg: str):
  """Load, parse, and return tf dataset for train and eval TFRecords."""
  if arg == 'train':
    records = TRAIN_RECORDS
  elif arg == 'eval':
    records = EVAL_RECORDS
  else:
    raise ValueError

  dataset = tf.data.TFRecordDataset(records, compression_type='GZIP')
  dataset = dataset.map(
      lambda inputs: tf.io.parse_single_example(inputs, FEATURES_DICT))

  dataset = dataset.map(convert_to_tuple)
  if arg == 'train':
    return dataset.shuffle(10000).batch(16)
  return dataset.batch(1)


@tf.function
def slope_loss(y_true, y_pred):
  """Return absolute difference in slope angle coordinate."""
  return tf.math.abs(y_true[:, 0] - y_pred[:, 0])


@tf.function
def aspect_loss(y_true, y_pred):
  """Return angle between aspect vectors."""
  dot = y_true[:, 1] * y_pred[:, 1] + y_true[:, 2] * y_pred[:, 2]
  dot = tf.math.minimum(dot, 1.0)
  dot = tf.math.maximum(dot, -1.0)
  return tf.math.acos(dot)


def build_model():
  """Build CNN as tf Sequential."""
  model = tf.keras.models.Sequential()
  model.add(layers.Conv2D(32, (3, 3), activation='relu', input_shape=(32, 32, 4)))
  model.add(layers.MaxPooling2D((2, 2)))
  model.add(layers.Conv2D(64, (3, 3), activation='relu'))
  model.add(layers.MaxPooling2D((2, 2)))
  model.add(layers.Conv2D(64, (3, 3), activation='relu'))
  model.add(layers.Flatten())
  model.add(layers.Dense(64, activation='relu'))
  model.add(layers.Dense(3))
  model.compile(
      optimizer='adam',
      loss='mse',
      metrics=['mae', slope_loss, aspect_loss]
  )
  return model


if __name__ == '__main__':
  train_dataset = build_dataset('train')
  eval_dataset = build_dataset('eval')
  model = build_model()
  print(model.summary())
  train_history = model.fit(train_dataset, epochs=10)
  eval_history = model.evaluate(eval_dataset)
