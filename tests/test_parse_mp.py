"""Test random branches."""

from big_wall_finder.mp import parse_mp as mp


def test_random_branch():
  """Test random branch."""
  d = mp.load_data()
  for _ in range(100):
    mp.print_random_branch(d)


if __name__ == '__main__':
  test_random_branch()
