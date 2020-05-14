# big-wall-finder

>Apply machine learning to geographic data to discover big walls.

[View the results here.]()


## Motivation and Summary

As a rock climber, it is a great thrill to stumble across an unseen boulder field or to discover an uncharted cliff. Some climbers consider this act of "rock-pioneering" as a pinnacle of their craft. Climbers who explore, prepare, and establish new climbing routes are known within the climbing community as *route developers*. These developers spend months or years of their lives combing through under-explored terrain that might lend itself to rock climbing.

This project attempts to leverages data to identity terrain in the continental United States which may be of interest to route developers. At a high-level, this project:

1. Analyzes elevation data to identity cliff-like formations.
1. Extracts geographic *features* for each discovered cliff, including geologic and satellite data.
1. Extracts human-generated rock climbing data found within the collaborative online guidebook [Mountain Project](https://www.mountainproject.com/).
1. Models the rock climbing potential of a cliff based on the geographic features.
1. Predicts which unexplored cliffs have the best potential for rock climbing.

See [Methodolgy](#methodology) for details.



## Screenshots

## Technologies
Languages, APIs, and libraries include
- Python (pandas, scikit-learn, XGBoost, TensorFlow)
- [Google Earth Engine](https://developers.google.com/earth-engine) (JavaScript and Python APIs)
- [mountain-project-scraper](https://github.com/alexcrist/mountain-project-scraper) (node.js)

Datasets include
- [USGS National Elevation Dataset 1/3 arc-second](https://developers.google.com/earth-engine/datasets/catalog/USGS_NED)
- [US Lithology](https://developers.google.com/earth-engine/datasets/catalog/CSP_ERGo_1_0_US_lithology
)
- [Landsat 8](https://developers.google.com/earth-engine/datasets/catalog/landsat-8)
- [Mountain Project Route Database](https://www.mountainproject.com/route-guide)






## How to use?


The results of project can be [viewed through an interactive map](). The data is available within the `data/` directory of this repo. Several files are of interest:
- The file [ee_data.csv](data/ee_data.csv) contains the raw data generated with [gather_big_wall_data.py](src/gather_big_wall_data.py). This script uses elevation data to find cliff-like formations in the western continental United States (west of longitude line defining the Colorado Kansas border). The data contains geologic and satellite data for each cliff as well as a polygon defining its coordinates. This script ran for over 8 hours on the Google Cloud servers.
- The file [mp_data.csv](data/mp_data.csv) was generated with [parse_mp_data.py](src/parse_mp_data.py) and holds Mountain Project route data organized by geographic coordinates. The Mountain Project data was scraped with [mountain-project-scraper](https://github.com/alexcrist/mountain-project-scraper), and [mp_data.csv](data/mp_data.csv) aggregates routes according to geographic coordinate.
- Various machine learning models were used to make predictions. Results can be seen in [simplified_results.csv](data/simplified_results.csv). The file [results.csv](data/results.csv) contains GeoJSON Polygons defining the footprint of each cliff. This file is rendered in the [interactive map]().

The script [big_wall_prediction.py](src/big_wall_prediction.py) implements several of the standard machine learning algorithms such as k-nearest neighbors, gradient tree boosting, and random forest. Because the dataset we use for training is not particularly large (~10k data points), deep learning techniques are limited. All of the models used train quickly and can readily be modified.


## Methodology

### Cliff-like formations
We start by using raster elevation data to identify connected regions of steep terrain. To this end, we set two thresholds: a height threshold and a slope threshold. A *cliff-like formation* is defined by an 8-connected region in which
- all pixels within the region have slope at least as large as the slope threshold, and
- the total elevation change of the region is at least as large as the height threshold.
These cliff-like formations (CLFs) are the central objects of study in this project. Each CLF can be extracted as a GeoJSON Polygon object.

The collection of CLFs will include any sufficiently tall and sufficiently steep cliff of interest to rock climbers. That said, the overwhelming majority of CLFs found will be *false positives*: climbers will not find terrain amenable to climbing in these regions. Exploring the data, in addition to the best big-walls of Yosemite Valley, CLFs also include steep alpine scree fields, loose chossy sandstone layers similar to those in the Grand Canyon, jagged exfoliating alpine spires, and other weird anomalies arising from noise in the data.


### Extracting data

To distinguish between CLFs which have rock climbing potential from those which don't, we incorporate additional data. On the geographic side, we collect geologic data from the US Lithology database as well as satellite data from the Landsat 8 database.
- US Lithology: For each CLF, we record the proportion of pixels in a disk surrounding the cliff that are categorized as:
  - non carbonate material
  - silicic residual material
  - colluvial sediment material
  - glacial till coarse material
  - alluvium material.
- Landsat 8: For each cliff-like formation, we record the median-value of the pixels contained within the CLF footprint in each of the following bands:
  - B2
  - B4
  - B5
  - B6
  - B7
  - the ratio B4 / B2
  - the ratio B6 / B5
  - the ratio B6 / B7.

The selection of this particular collection of features was informed by exploring the lithology-values of CLFs and by emulating the process by which geologists [classify geologic formations](https://www.arcgis.com/home/item.html?id=9f9d2f7b6460497c9cbb9548d4ec0bc8) with Landsat 8 data.

In addition, for each CLF, we calculate a *score* based on data scraped from Mountain Project. This score is computed by taking a weighted sum of the number of routes and the number of page-views of those routes within a disk containing the CLF. The score gives a measure of the rock-climbing quality: we expect CLFs with a high score to have quality climbing. CLFs without any existing Mountain Project entry receives a score of zero.

There are two reasons a CLF has no Mountain Project entry:
- The CLF has already been explored and no quality climbing exists.
- The CLF has not yet been explored.

### A function to learn

Call a CLF *accessible* if it is sufficiently close to a road and sufficiently close to a large population center. The precise threshold for closeness is unimportant at the moment, and can be fine-tuned later on. We make the assumption that any accessible CLF has already been explored for climbing. Therefore, an accessible CLF not present on Mountain Project has no potential for climbing. We call this assumption *ACCESSIBLE = COMPLETE*.

With this assumption in place, we have full knowledge of the quality of accessible CLFs. For each accessible CLF, let X be the aforementioned geographic data pertaining to the CLF, and let y be the score of the CLF. We now have a machine learning problem: We seek to approximate the function which associates X to y.

This function is likely highly nonlinear. Most cliff bands contain loose rock not suited to climbing. The conditions that make a cliff well suited for climbing vary depending on the rock type and terrain properties. Indeed, imagine two of the most iconic big-wall rock climbs in the country: Moonlight Buttress in Zion National Park and El Capitan in Yosemite. Now, imagine a cliff with geographic data corresponding to the average of Moonlight Buttress and El Capitan. My intuition tells me that nothing good will come out of averaging water-eroded sandstone with glacially polished granite.

Once this function is learned, we then apply it to the collection of inaccessible CLFs to predict their scores. The CLFs with a high predicted score and without a Mountain Project entry may have undiscovered or little-known rock climbing potential.

### Constraints and Limitations

- The USGS Elevation dataset is coarse. The pixel size of this raster data is roughly 10m x 10m. Said differently, elevation is sampled only one in each 10m x 10m square. As a consequence, it is not possible to identify steep but short cliffs using this dataset. For example, a vertical cliff that is only 10m tall will appear to be a 45 degree slab from the perspective of this dataset. Once lidar data becomes widely available, this could be used in place of the USGS Elevation dataset.
- The USGS Elevation dataset is noisy. As an extreme example, the dataset (used for Google Map terrain) shows a [4000 foot deep X-shaped hole](https://goo.gl/maps/HTCByKHDRR2GjdheA) in the ground in the middle of the desert. [Here](https://goo.gl/maps/KDranmgbPAi18pzh9) we have a nearly 5000 foot deep well. More commonly, spikey non-smooth terrain often gives rise to absurd elevation readings. These sorts of mistakes need to be manually removed from the dataset when possible.
- Mountain Project data is incomplete. In some sense, this project would not exist if Mountain Project was a complete data set. Nevertheless, having complete Mountain Project data for some regions would allow us to weaken our ACCESSIBLE = COMPLETE assumption.
- Within the training data, there is a significant imbalance: most CLFs have no entry on Mountain Project. There are several ways to account for this (oversampling the under-represented class, using additional CLFs from the inaccessible data with Mountain Project entries), but it may not be possible to completely remove bias from the model.
- The extracted dataset (the set of CLFs) is small. The dataset of Mountain Project routes is small. The accuracy is limited by the size of the datasets used in training.
- In searching for CLFs with specific properties, handcrafting features may give stronger results than machine learning. If a route developer only sought Yosemite-style granite, they could first examine the geological spectrum of Yosemite granite, then filter CLFs by the targeted spectrum.


### Results
Write this!



## Earth Engine

Google Earth Engine provides a Python and JavaScript [API](https://github.com/google/earthengine-api) for accessing and manipulating geographic data. The API uses a functional programming paradigm and includes custom highly optimized containers for performing calculations with raster and vector geographic data. Functions within the `ee` namespace run server-side on Google Cloud.

As a small example of this, the following snippet imports the US elevation dataset and masks it to contain only pixels in which the slope is at least 80 degrees.
```python
dem = ee.Image('USGS/NED')
steep = ee.Terrain.slope(dem).gt(80)
dem = dem.updateMask(steep)
```



## License

This project is released under the [MIT license](https://opensource.org/licenses/MIT).