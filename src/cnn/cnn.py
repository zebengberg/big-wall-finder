"""Run CNN from NAIP data."""

import tensorflow as tf
import params


# Should import these from gather_cliff_images or from common parameters file


# Use glob here once more tfrecord files available
filenames = ['../../data/naip_shards/naip_shard_0.tfrecord.gz']
dataset = tf.data.TFRecordDataset(filenames, compression_type='GZIP')

parsed_dataset = dataset.map(lambda example: tf.io.parse_single_example(example, params.FEATURES_DICT))

l = list(parsed_dataset.as_numpy_iterator())

for item in l[:100]:
  print(item['pixel_count'])
