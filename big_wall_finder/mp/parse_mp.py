"""Parse data collected with mountain-project-scraper.
See https://github.com/alexcrist/mountain-project-scraper.

Notes on the scraped clean-data.json data:
  - Each node in the tree is either an area or a route.
  - Each area node has a list (possibly empty) of children.
  - Each child could be its own area node or a route.
  - Siblings cannot be mixed types: they are either all routes or all sub-areas.
  - Each area has a lat / long. These are inherited from parent in many cases.
  - Each area has a gps2 attribute, which gives a higher precision coordinate.
  - Routes do not have lat / long.
"""

from __future__ import annotations
from typing import Any
from dataclasses import dataclass
import random
import json
import pandas as pd
from big_wall_finder import definitions


@dataclass(eq=True, frozen=True)  # making Coord hashable
class Coord:
  """Wrapper class for geo coordinates."""
  latitude: float
  longitude: float

  def __repr__(self):
    return f'({self.latitude}, {self.longitude})'


@dataclass
class Count:
  """Wrapper class for counts of MP routes."""
  name: str
  n_boulder: int = 0
  n_winter: int = 0
  n_rock: int = 0
  n_views: int = 0

  def count_types(self, types: list[str]):
    """Count number of routes by type. Route types include:
    - tr
    - trad
    - sport
    - boulder
    - mixed
    - ice
    - alpine
    - snow.
    """

    if 'boulder' in types:
      self.n_boulder += 1
    elif 'mixed' in types or 'ice' in types or 'snow' in types:
      self.n_winter += 1
    else:  # tr, trad, sport, alpine
      self.n_rock += 1


def load_data():
  """Load clean-data.json file."""

  print('Loading MP data ...')
  with open(definitions.MP_SCRAPE_JSON_PATH) as f:
    data = json.load(f)
  print('Data loaded.')

  # data is a list; converting it to a dict to match format of children
  return {'name': 'All',
          'children': data,
          # roughly at geographic center of US
          'lat': 39.0,
          'long': -98.0,
          'gps2': '39.0,-98.0',
          'totalViews': 0,
          'url': 'https://mountainproject.com'}


def get_gps(node: dict[str, Any]):
  """Get higher precision gps2 values."""
  lat1, long1 = node['lat'], node['long']
  # gps2 more precise than lat1, long1
  lat2, long2 = [float(coord) for coord in node['gps2'].split(',')]
  if abs(lat1 - lat2) > 1e-3 or abs(long1 - long2) > 1e-3:
    print('Coordinates:', lat1, lat2, long1, long2)
    raise ValueError(f"Something wrong with coordinates! Check {node['url']}")
  return Coord(lat2, long2)


def clean_name(name: str):
  """Clean name by stripping whitespace and newline."""
  return name.splitlines()[0].strip()


def print_random_branch(node: dict[str, Any]):
  """Print a random branch from the passed node for testing purposes."""
  print('-' * 65)
  depth = 0

  # checking if node has children, and that the corresponding list is nonempty
  while 'children' in node and node['children']:
    name = clean_name(node['name'])
    coords = get_gps(node)
    line = ' ' * depth + name + ' ' + str(coords)
    print(line)
    depth += 1
    node = random.choice(node['children'])

  # printing out leaf nodes, ie, climbing routes
  print(' ' * depth + clean_name(node['name']))
  for key in (key for key in node if key not in ['name', 'url']):
    print(' ' * depth, key, node[key])
  print('-' * 65)


def populate(node: dict[str, Any], counts: dict[Coord, Count], key: Coord):
  """Populate counts at a node."""

  # storing name of highest node in tree with unique key
  # any node below this with the same coordinates will share this name
  assert key is not None
  if key not in counts:
    name = clean_name(node['name'])
    counts[key] = Count(name)
  counts[key].n_views += node['totalViews']

  # node is a leaf
  if 'types' in node:
    counts[key].count_types(node['types'])
    counts[key].n_views += node['totalViews']


def dfs(node: dict[str, Any], counts: dict[Coord, Count], key: Coord | None = None):
  """Traverse tree and perform tasks through a DFS."""

  if key is None:
    key = get_gps(node)
  populate(node, counts, key)

  # checking if node has children
  if 'children' in node:
    for child in node['children']:
      if 'lat' in child:  # child has its own geo key, so we pass None
        dfs(child, counts)
      else:  # using parent key
        dfs(child, counts, key)


def save_as_df(counts: dict[Coord, Count]):
  """Save tree data in table form."""
  df = []
  for coord, count in counts.items():
    row = {
        'latitude': coord.latitude,
        'longitude': coord.longitude,
        'name': count.name,
        'n_boulder': count.n_boulder,
        'n_winter': count.n_winter,
        'n_rock': count.n_rock,
        'n_views': count.n_views
    }
    # only keep if area contains some routes
    if row['n_boulder'] + row['n_winter'] + row['n_rock']:
      df.append(row)
  df = pd.DataFrame(df)
  path = definitions.MP_DATA_PATH
  print(f'Writing table data to {path}')
  df.to_csv(path, header=True, index=False)


def main():
  """Convert tree data to table data."""
  root = load_data()
  counts = {}
  print('Searching data tree with DFS ...')
  dfs(root, counts)
  print('Done searching data tree.')
  save_as_df(counts)
