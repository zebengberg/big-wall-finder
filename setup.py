"""Install big_wall_finder."""
import setuptools

with open('README.md') as f:
  long_description = f.read()
description = 'Apply ML to GIS to discover big walls.'


install_requires = [
    'earthengine_api',
    'pandas',
    'xgboost',
    'scikit_learn',
    'tqdm',
]

setuptools.setup(
    name='big_wall_finder',
    author='Zeb Engberg',
    author_email='zebengberg@gmail.com',
    description=description,
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/zebengberg/big-wall-finder',
    packages=setuptools.find_namespace_packages(exclude=['tests*']),
    python_requires='>=3.7.0',
    install_requires=install_requires,
    version='0.0.1',
    license='MIT')
