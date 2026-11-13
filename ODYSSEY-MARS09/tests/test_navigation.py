import unittest
from core.navigation import find_path, compare_routes
from core.terrain import generate_terrain, generate_cost_map


class TestNavigation(unittest.TestCase):
    def test_find_path(self):
        elev = generate_terrain(grid_size=40)
        cost = generate_cost_map(elev)
        path = find_path(cost, start=(0, 0), goal=(39, 39))
        self.assertTrue(len(path) > 0)
        self.assertEqual(path[0], (0, 0))
        self.assertEqual(path[-1], (39, 39))

    def test_compare_routes(self):
        elev = generate_terrain(grid_size=20)
        cost = generate_cost_map(elev)
        r1 = [(i, i) for i in range(10)]
        r2 = [(i, 0) for i in range(10)]
        res = compare_routes(cost, [r1, r2], ["RouteA", "RouteB"])
        self.assertIn("RouteA", res)
        self.assertIn("RouteB", res)


if __name__ == "__main__":
    unittest.main()

