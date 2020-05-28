/*
Display Mountain Project data aggregated by coordinate. Show the
FeatureCollection of big-wall formations found through the
gather_ee_data.py script. Explore how well MP geo-tags are aligned
with those found through the elevation data.
*/

var mp = ee.FeatureCollection('users/zebengberg/big_walls/mp_data');
var cliffs = ee.FeatureCollection('users/zebengberg/big_walls/ee_data');

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
Map.addLayer(cliffs.style({styleProperty: 'styleProp'}), null, 'cliffs');
Map.addLayer(mp.style({color: 'lime', styleProperty: 'styleProp'}), null, 'mp');


// When clicking the map, display a disk and calculate MP stats.
Map.onClick(function(event) {
  // Removing any old disk
  var oldDisk = Map.layers().get(2);
  if (oldDisk !== undefined) {
    Map.layers().remove(oldDisk);
  }
  // Calculate within disk at the click location
  var p = ee.Geometry.Point(event.lon, event.lat);
  var disk = p.buffer(500);
  Map.addLayer(disk, {color: 'pink'}, 'clicked_disk');
  var closeMP = mp.filterBounds(disk);
  closeMP = closeMP.sort('num_views', false);
  var closeCliffs = cliffs.filterBounds(disk);
  
  var rock = closeMP.aggregate_sum('num_rock_routes').getInfo();
  var maxHeight = closeCliffs.aggregate_max('height').getInfo();
  if (maxHeight) {
    maxHeight += 'm';
  } else {
    maxHeight = 'No cliffs found!';
  }
  var name = closeMP.aggregate_first('name').getInfo();
  if (name === null) {
    name = 'No MP area found!';
  }

  var rockInfo = ui.Label('Number of MP routes in vicinity: ' + rock);
  var nameInfo = ui.Label('Most viewed MP area: ' + name);
  var heightInfo = ui.Label('Tallest cliff in vicinity: ' + maxHeight);
  resultsPanel.clear().add(rockInfo).add(heightInfo).add(nameInfo).add(button);
});


var resultsPanel = ui.Panel({style: {position: 'bottom-left', width: '500px'}});
var instructionsLabel = ui.Label("Click map to generate a disk and see what's inside.");
var button = ui.Button('Clear results', clearResults);
Map.add(resultsPanel.add(instructionsLabel));

function clearResults() {
  resultsPanel.clear().add(instructionsLabel);
  Map.layers().remove(Map.layers().get(2));
}


// Adding a legend for height.
var bar = ui.Thumbnail({
  image: ee.Image.pixelLonLat().select(1),
  params: {
    bbox: [0, 0, 1, 20],
    dimensions: '20x20',
    format: 'png',
    min: 0,
    max: 30,
    palette: palette,
  },
  style: {stretch: 'vertical', margin: '8px 0px'},
});

var legendLabel = ui.Panel([
  ui.Label('>600m', {margin: '4px 8px', fontWeight: 'bold', height: '50px'}),
  ui.Label(null, {margin: '4px 8px', fontWeight: 'bold', height: '300px'}),
  ui.Label('50m', {margin: '4px 8px', fontWeight: 'bold', height: '50px'})
]);
  
var legend = ui.Panel({style: {position: 'bottom-right'}});
legend.add(ui.Label('Height', {fontWeight: 'bold', margin: '2px'}));
legend.add(ui.Panel([bar, legendLabel], ui.Panel.Layout.flow('horizontal')));
Map.add(legend);
