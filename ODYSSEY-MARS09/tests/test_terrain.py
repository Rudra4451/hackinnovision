import unittest
from core.terrain import generate_terrain, classify_terrain, generate_cost_map
from core.config import GRID_SIZE, MAX_SLOPE, OBSTACLE_COST


class TestTerrain(unittest.TestCase):
    def test_terrain_dimensions(self):
        elev = generate_terrain(grid_size=50)
        self.assertEqual(len(elev), 50)

    def test_terrain_classification(self):
        elev = generate_terrain(grid_size=30)
        classified = classify_terrain(elev, max_slope=MAX_SLOPE)
        self.assertEqual(len(classified), 30)

    def test_cost_map_bounds(self):
        elev = generate_terrain(grid_size=30)
        cost = generate_cost_map(elev, obstacle_cost=OBSTACLE_COST)
        self.assertEqual(len(cost), 30)

    def test_cost_map_values(self):
        elev = generate_terrain(grid_size=20)
        cost = generate_cost_map(elev, max_slope=MAX_SLOPE)
        # Verify min cost is at least 1.0 (SAFE terrain)
        first_row = cost[0]
        min_val = min(first_row)
        self.assertGreaterEqual(min_val, 1.0)


if __name__ == "__main__":
    unittest.main()
