/*
Display Mountain Project data aggregated by coordinate. Show the
FeatureCollection of big-wall formations found through the
gather_ee_data.py script. Explore how well MP geo-tags are aligned
with those found through the elevation data.
*/

var mp = ee.FeatureCollection('users/zebengberg/big_walls/mp_data');
var cliffs = ee.FeatureCollection('users/zebengberg/big_walls/ee_data');

// In order to see vectorized data upon inspection.
Map.addLayer(mp, null, 'mp_vector', false);
Map.addLayer(cliffs, null, 'cliff_vector', false);

// Display a pin for each MP area. Area of each pin is proportional
// to the score of the area.
mp = mp.map(function(f) {
  var size = ee.Number(f.get('num_rock_routes')).multiply(2000)
  .add(f.get('num_views'));
  size = size.divide(2000).sqrt();
  return f.set({styleProp: {pointSize: size}});
});


// Give each cliff a color from custom color palette.
// Need to include so many colors due to some mistakes in elevation data.
var palette = ee.List(['FFFF00', 'FFF000', 'FFE000', 'FFD000',
  'FFC000', 'FFB000', 'FFA000', 'FF9000', 'FF8000', 'FF7000',
  'FF6000', 'FF5000', 'FF4000', 'FF3000', 'FF2000', 'FF1000',
  'FF0000', 'FF0010', 'FF0020', 'FF0030', 'FF0040', 'FF0050',
  'FF0060', 'FF0070', 'FF0080', 'FF0090', 'FF00A0', 'FF00B0',
  'FF00C0', 'FF00D0', 'FF00D0', 'FF00F0', 'FF00FF', 'FF00FF',
  'FF00FF', 'FF00FF', 'FF00FF', 'FF00FF', 'FF00FF', 'FF00FF']);
cliffs = cliffs.map(function(f) {
  // Getting the index within the palette list to color the feature.
  var index = ee.Number(f.get('height')).divide(40).floor();
  return f.set({styleProp: {color: palette.get(index)}});
});


Map.setOptions('satellite');
Map.setCenter(-119.55, 37.75, 11);
Map.addLayer(cliffs.style({styleProperty: 'styleProp'}), null, 'cliffs');
Map.addLayer(mp.style({color: 'lime', styleProperty: 'styleProp'}), null, 'mp');


// When clicking the map, display a disk and calculate MP stats.
Map.onClick(function(event) {
  // Removing any old disk
  var oldDisk = Map.layers().get(4);
  if (oldDisk !== undefined) {
    Map.layers().remove(oldDisk);
  }
  // Calculate within disk at the click location
  var p = ee.Geometry.Point(event.lon, event.lat);
  var disk = p.buffer(500);
  Map.addLayer(disk, {color: 'pink'}, 'clicked_disk');
  var close_mp = mp.filterBounds(disk);
  var rock = close_mp.aggregate_sum('num_rock_routes');
  var views = close_mp.aggregate_sum('num_views');
  print('Number of MP routes in vicinity: ' + rock.getInfo());
});
