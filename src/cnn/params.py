"""Constants and feature labels used within CNN."""

import tensorflow as tf
from tensorflow.io import FixedLenFeature as flf

KERNEL_SIZE = 8

NAIP_KEYS = ['R', 'G', 'B', 'N']
NAIP_VALUES = [flf(shape=(KERNEL_SIZE, KERNEL_SIZE), dtype=tf.float32) for _ in NAIP_KEYS]
# TODO: Is it possible to use uint8 rather than tf.float?

SCALAR_KEYS = ['height', 'pixel_count', 'mp_score']
SCALAR_VALUES = [flf(shape=(1,), dtype=tf.float32) for _ in SCALAR_KEYS]

FEATURES_DICT = dict(zip(NAIP_KEYS + SCALAR_KEYS, NAIP_VALUES + SCALAR_VALUES))
