/*
Display Mountain Project data aggregated by coordinate. Show the
FeatureCollection of big-wall formations found through the
gather_ee_data.py script. Explore how well MP geo-tags are aligned
with those found through the elevation data.
*/

var mp = ee.FeatureCollection('users/zebengberg/big_walls/mp_data');
var bw = ee.FeatureCollection('users/zebengberg/big_walls/ee_data');


// Display a pin for each MP area. Area of each pin is proportional
// to the score of the area.
mp = mp.map(function(f) {
  var size = ee.Number(f.get('num_rock_routes')).multiply(2000)
  .add(f.get('num_views'));
  size = size.divide(5000).sqrt();
  return f.set({styleProp: {pointSize: size}});
});

Map.setOptions('satellite');
Map.setCenter(-119.55, 37.75, 12);
Map.addLayer(mp.style({color: 'red', styleProperty: 'styleProp'}));


// When clicking the map, display a disk and calculate the number of
// MP routes and views within the disk.
Map.onClick(function(event) {
  // Removing any old disk
  var oldDisk = Map.layers().get(1);
  if (oldDisk !== undefined) {
    Map.layers().remove(oldDisk);
  }
  
  // Adding a new disk at the click location
  var p = ee.Geometry.Point(event.lon, event.lat);
  var disk = p.buffer(1000);
  Map.addLayer(disk);
  var close_mp = mp.filterBounds(disk);
  var rock = close_mp.aggregate_sum('num_rock_routes');
  var views = close_mp.aggregate_sum('num_views');
  print(rock);
});
