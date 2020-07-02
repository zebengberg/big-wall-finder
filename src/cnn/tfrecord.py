import tensorflow as tf


# Should import these from gather_cliff_images or from common parameters file
KERNEL_SIZE = 8
naip_keys = ['R', 'G', 'B', 'N']
# TODO: Is it possible to use uint8?
#naip_values = [tf.io.FixedLenFeature(shape=(KERNEL_SIZE, KERNEL_SIZE), dtype=tf.uint8) for _ in naip_keys]
naip_values = [tf.io.FixedLenFeature(shape=(KERNEL_SIZE, KERNEL_SIZE), dtype=tf.float32) for _ in naip_keys]
scalar_keys = ['height', 'pixel_count']
#scalar_values = [tf.io.FixedLenFeature(shape=(1,), dtype=tf.float32) for _ in scalar_keys]
scalar_values = [tf.io.FixedLenFeature(shape=(1,), dtype=tf.float32) for _ in scalar_keys]
features_dict = dict(zip(naip_keys + scalar_keys, naip_values + scalar_values))



# Use glob here once more tfrecord files available
filenames = ['../../data/naip_shard_0.tfrecord']
dataset = tf.data.TFRecordDataset(filenames)
parsed_dataset = dataset.map(lambda example: tf.io.parse_single_example(example, features_dict))

l = list(parsed_dataset.as_numpy_iterator())

for item in l:
  print(item['pixel_count'])
