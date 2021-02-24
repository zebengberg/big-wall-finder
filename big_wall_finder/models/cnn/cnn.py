"""Run CNN from NAIP data."""

import tensorflow as tf
import params


# Should import these from gather_cliff_images or from common parameters file


# TODO: (what I was doing)
# inputs are 8 x 8 x 16 tensors along with 16 x 1 tensors -- tf doesn't like this
# can we have a dense feeding into a cnn, or vice versa?


def separate_input_and_output(x):
  """Return tuple with input and output features."""
  inputs = [x.get(key) for key in params.NAIP_KEYS if key not in ['mp_score', 'cliff_id']]
  outputs = [x.get('mp_score')]
  return inputs, outputs



# Use glob here once more tfrecord files available
filenames = ['../../data/naip_shards/naip_shard_0.tfrecord.gz']
dataset = tf.data.TFRecordDataset(filenames, compression_type='GZIP')
dataset = dataset.take(10)

dataset = dataset.map(lambda x: tf.io.parse_single_example(x, params.FEATURES_DICT))
print(iter(dataset.take(1)).next())
dataset = dataset.map(separate_input_and_output)

print('#' * 80)

dataset = dataset.shuffle(params.SHUFFLE_BUFFER_SIZE, reshuffle_each_iteration=True)
dataset = dataset.batch(params.BATCH_SIZE)
dataset = dataset.repeat(params.EPOCHS)

print(iter(dataset.take(1)).next())



# from tensorflow.python.keras import layers
# from tensorflow.python.keras import losses
# from tensorflow.python.keras import models
# from tensorflow.python.keras import metrics
# from tensorflow.python.keras import optimizers

# def conv_block(input_tensor, num_filters):
# 	encoder = layers.Conv2D(num_filters, (3, 3), padding='same')(input_tensor)
# 	encoder = layers.BatchNormalization()(encoder)
# 	encoder = layers.Activation('relu')(encoder)
# 	encoder = layers.Conv2D(num_filters, (3, 3), padding='same')(encoder)
# 	encoder = layers.BatchNormalization()(encoder)
# 	encoder = layers.Activation('relu')(encoder)
# 	return encoder

# def encoder_block(input_tensor, num_filters):
# 	encoder = conv_block(input_tensor, num_filters)
# 	encoder_pool = layers.MaxPooling2D((2, 2), strides=(2, 2))(encoder)
# 	return encoder_pool, encoder

# def decoder_block(input_tensor, concat_tensor, num_filters):
# 	decoder = layers.Conv2DTranspose(num_filters, (2, 2), strides=(2, 2), padding='same')(input_tensor)
# 	decoder = layers.concatenate([concat_tensor, decoder], axis=-1)
# 	decoder = layers.BatchNormalization()(decoder)
# 	decoder = layers.Activation('relu')(decoder)
# 	decoder = layers.Conv2D(num_filters, (3, 3), padding='same')(decoder)
# 	decoder = layers.BatchNormalization()(decoder)
# 	decoder = layers.Activation('relu')(decoder)
# 	decoder = layers.Conv2D(num_filters, (3, 3), padding='same')(decoder)
# 	decoder = layers.BatchNormalization()(decoder)
# 	decoder = layers.Activation('relu')(decoder)
# 	return decoder

# def get_model():
# 	inputs = layers.Input(shape=[None, None, len(BANDS)]) # 256
# 	encoder0_pool, encoder0 = encoder_block(inputs, 32) # 128
# 	encoder1_pool, encoder1 = encoder_block(encoder0_pool, 64) # 64
# 	encoder2_pool, encoder2 = encoder_block(encoder1_pool, 128) # 32
# 	encoder3_pool, encoder3 = encoder_block(encoder2_pool, 256) # 16
# 	encoder4_pool, encoder4 = encoder_block(encoder3_pool, 512) # 8
# 	center = conv_block(encoder4_pool, 1024) # center
# 	decoder4 = decoder_block(center, encoder4, 512) # 16
# 	decoder3 = decoder_block(decoder4, encoder3, 256) # 32
# 	decoder2 = decoder_block(decoder3, encoder2, 128) # 64
# 	decoder1 = decoder_block(decoder2, encoder1, 64) # 128
# 	decoder0 = decoder_block(decoder1, encoder0, 32) # 256
# 	outputs = layers.Conv2D(1, (1, 1), activation='sigmoid')(decoder0)

# 	model = models.Model(inputs=[inputs], outputs=[outputs])

# 	model.compile(
# 		optimizer=optimizers.get(OPTIMIZER), 
# 		loss=losses.get(LOSS),
# 		metrics=[metrics.get(metric) for metric in METRICS])

# 	return model




# l = list(parsed_dataset.as_numpy_iterator())

# print(l[0])
# for i, item in enumerate(l[:50]):
#   print(i, item['cliff_id'], item['height'])

# print(len(l))