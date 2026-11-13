import unittest
from core.navigation import find_path, compare_routes
from core.terrain import generate_terrain, generate_cost_map


class TestNavigation(unittest.TestCase):
    def test_find_path_basic(self):
        elev = generate_terrain(grid_size=40)
        cost = generate_cost_map(elev)
        path = find_path(cost, start=(0, 0), goal=(39, 39))
        self.assertTrue(len(path) > 0)
        self.assertEqual(path[0], (0, 0))
        self.assertEqual(path[-1], (39, 39))

    def test_find_path_dual_mode(self):
        elev = generate_terrain(grid_size=30)
        cost = generate_cost_map(elev)
        path_shortest = find_path(cost, start=(0, 0), goal=(29, 29), mode="shortest")
        path_safest = find_path(cost, start=(0, 0), goal=(29, 29), mode="safest")
        self.assertTrue(len(path_shortest) > 0)
        self.assertTrue(len(path_safest) > 0)

    def test_compare_routes(self):
        elev = generate_terrain(grid_size=20)
        cost = generate_cost_map(elev)
        res = compare_routes(cost, (0, 0), (19, 19))
        self.assertIn("Shortest Route", res)
        self.assertIn("Safest Route", res)


if __name__ == "__main__":
    unittest.main()
