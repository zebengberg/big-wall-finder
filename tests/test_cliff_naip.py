"""Test cliff_naip. Assumes existence of a naip_test.tfrecord file in directory."""

import os
import tensorflow as tf
from big_wall_finder import definitions


def build_dataset():
  """Load, parse, and return tf dataset."""
  data_path = os.path.join(os.path.dirname(__file__), 'naip_test.tfrecord.gz')
  size = definitions.NAIP_KERNEL_SIZE

  features = {
      'B': tf.io.FixedLenFeature(shape=(size, size), dtype=tf.float32),
      'G': tf.io.FixedLenFeature(shape=(size, size), dtype=tf.float32),
      'N': tf.io.FixedLenFeature(shape=(size, size), dtype=tf.float32),
      'R': tf.io.FixedLenFeature(shape=(size, size), dtype=tf.float32),
      'S': tf.io.FixedLenFeature(shape=(size, size), dtype=tf.float32),
      'cliff_id': tf.io.FixedLenFeature([], dtype=tf.string),
  }

  dataset = tf.data.TFRecordDataset(data_path, compression_type='GZIP')
  dataset = dataset.map(lambda x: tf.io.parse_single_example(x, features))

  def pixels_to_float(x):
    as_float = [x.get(k) / 256 for k in ['B', 'G', 'N', 'R']]
    return as_float + [x.get('S')], x.get('cliff_id')

  dataset = dataset.map(pixels_to_float)
  return dataset


def test_dataset():
  """Test build dataset."""
  dataset = build_dataset()
  for x, y in dataset.take(5):
    print(x)
    print(y)


if __name__ == '__main__':
  test_dataset()
