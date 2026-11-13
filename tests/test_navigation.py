"""
Unit and integration tests for ODYSSEY MARS-09 autonomous navigation engine.

Validates:
- Scenario A: Nominal flat terrain
- Scenario B: Impassable obstacle avoidance
- Scenario C: Diagonal corner-cutting and pinch-point prevention
- Scenario D: Risk vs. distance trade-offs (safe detour vs. direct caution)
- Scenario E: Unreachable goals and obstacle start/goal handling
- Scenario F: Boundary constraints and start == goal handling
"""

import math
import sys
import unittest
import numpy as np

# Ensure root directory is on Python path
sys.path.insert(0, ".")

from core.navigation import (
    find_path,
    calculate_path_metrics,
    compare_routes,
)


class TestNavigationScenarios(unittest.TestCase):
    """Test suite verifying all operational navigation scenarios and contracts."""

    def test_scenario_a_open_terrain(self):
        """Scenario A: Open flat terrain where shortest and safest routes are identical."""
        grid = np.ones((10, 10), dtype=float)
        start = (0, 0)
        goal = (8, 8)

        shortest = find_path(grid, start, goal, mode="shortest")
        safest = find_path(grid, start, goal, mode="safest")

        self.assertTrue(shortest["success"], "Shortest path should succeed")
        self.assertTrue(safest["success"], "Safest path should succeed")
        self.assertEqual(shortest["path"][0], start)
        self.assertEqual(shortest["path"][-1], goal)
        self.assertEqual(safest["path"][0], start)
        self.assertEqual(safest["path"][-1], goal)

        # Plotly coordinate alignment
        self.assertEqual(shortest["x"], [c for _, c in shortest["path"]])
        self.assertEqual(shortest["y"], [r for r, _ in shortest["path"]])

        m_short = calculate_path_metrics(shortest["path"], grid)
        m_safe = calculate_path_metrics(safest["path"], grid)

        self.assertAlmostEqual(m_short["total_distance"], m_safe["total_distance"], places=3)
        self.assertAlmostEqual(m_short["total_cost"], m_safe["total_cost"], places=3)
        self.assertEqual(m_short["caution_steps"], 0)
        self.assertEqual(m_safe["caution_steps"], 0)

        comparison = compare_routes(grid, start, goal)
        self.assertTrue(comparison["summary"]["both_reachable"])
        self.assertAlmostEqual(comparison["summary"]["distance_delta"], 0.0, places=3)
        self.assertAlmostEqual(comparison["summary"]["cost_reduction_pct"], 0.0, places=3)

    def test_scenario_b_impassable_obstacle_wall(self):
        """Scenario B: Impassable np.inf wall blocking line of sight."""
        grid = np.ones((12, 12), dtype=float)
        # Create an impassable wall across row 5, with a passage at column 10..11
        grid[5, 0:10] = np.inf
        start = (2, 4)
        goal = (8, 4)

        for mode in ("shortest", "safest"):
            res = find_path(grid, start, goal, mode=mode)
            self.assertTrue(res["success"], f"Mode {mode} should navigate around wall")
            self.assertEqual(res["path"][0], start)
            self.assertEqual(res["path"][-1], goal)

            # Ensure no step ever touches np.inf
            for r, c in res["path"]:
                self.assertFalse(
                    np.isinf(grid[r, c]),
                    f"Path in mode {mode} touched impassable cell at ({r}, {c})",
                )

    def test_scenario_c_diagonal_corner_cutting_prevention(self):
        """
        Scenario C: Diagonal Corner-Cutting & Squeeze Prevention.
        Two obstacles touching diagonally at (1, 2) and (2, 1).
        A rover at (1, 1) cannot squeeze diagonally through to (2, 2).
        Single obstacle at (1, 2) also prevents cutting the corner from (1, 1) to (2, 2).
        """
        # Test 1: Squeeze prevention between diagonally touching obstacles
        grid = np.ones((5, 5), dtype=float)
        grid[1, 2] = np.inf
        grid[2, 1] = np.inf

        res = find_path(grid, (1, 1), (2, 2), mode="shortest")
        self.assertTrue(res["success"])

        # Check that no two consecutive steps are (1, 1) -> (2, 2) or (2, 2) -> (1, 1)
        path = res["path"]
        for i in range(len(path) - 1):
            pair = (path[i], path[i + 1])
            self.assertNotEqual(
                pair,
                ((1, 1), (2, 2)),
                "Rover squeezed diagonally between two touching obstacles!",
            )
            self.assertNotEqual(
                pair,
                ((2, 2), (1, 1)),
                "Rover squeezed diagonally between two touching obstacles in reverse!",
            )

        # Test 2: Single obstacle corner cut prevention
        grid2 = np.ones((5, 5), dtype=float)
        grid2[1, 2] = np.inf  # Single obstacle
        res2 = find_path(grid2, (1, 1), (2, 2), mode="shortest")
        self.assertTrue(res2["success"])
        path2 = res2["path"]
        for i in range(len(path2) - 1):
            self.assertNotEqual(
                (path2[i], path2[i + 1]),
                ((1, 1), (2, 2)),
                "Rover cut corner across orthogonal obstacle at (1, 2)!",
            )

    def test_scenario_d_risk_vs_distance_hero_demo(self):
        """
        Scenario D (Hero Demo): High-cost hazard zone (15.0) vs safe detour (1.0).
        Shortest route cuts through (minimizing distance).
        Safest route detours around (minimizing total risk cost).
        """
        grid = np.ones((15, 15), dtype=float)
        # Moderate-to-high caution hazard zone blocking direct corridor
        grid[5:10, 4:11] = 15.0

        start = (7, 1)
        goal = (7, 13)

        comparison = compare_routes(grid, start, goal)
        summary = comparison["summary"]
        shortest_m = comparison["shortest"]["metrics"]
        safest_m = comparison["safest"]["metrics"]

        self.assertTrue(summary["both_reachable"])
        # Shortest distance must be strictly shorter than safest detour distance
        self.assertLess(
            shortest_m["total_distance"],
            safest_m["total_distance"],
            "Shortest route should have shorter physical distance",
        )
        # Safest total cost must be strictly lower than shortest route's cost
        self.assertLess(
            safest_m["total_cost"],
            shortest_m["total_cost"],
            "Safest route should have significantly lower total cost",
        )
        # Shortest should enter caution cells; Safest should avoid them
        self.assertGreater(shortest_m["caution_steps"], 0)
        self.assertEqual(safest_m["caution_steps"], 0)
        self.assertGreater(summary["caution_steps_avoided"], 0)
        self.assertGreater(summary["cost_reduction_pct"], 0.0)
        self.assertIn("SAFEST", summary["recommendation"])

    def test_scenario_e_unreachable_and_hazard_positions(self):
        """Scenario E: Unreachable goals and start/goal on hazard cells."""
        grid = np.ones((8, 8), dtype=float)

        # 1. Goal completely enclosed by np.inf
        grid[2:5, 2:5] = np.inf
        grid[3, 3] = 1.0  # Safe cell inside a sealed crater
        res_enclosed = find_path(grid, (0, 0), (3, 3), mode="safest")
        self.assertFalse(res_enclosed["success"])
        self.assertEqual(res_enclosed["path"], [])
        self.assertEqual(res_enclosed["x"], [])
        self.assertEqual(res_enclosed["y"], [])
        self.assertIn("No traversable path", res_enclosed["reason"])

        # 2. Start is on np.inf
        grid[0, 0] = np.inf
        res_start_inf = find_path(grid, (0, 0), (7, 7), mode="shortest")
        self.assertFalse(res_start_inf["success"])
        self.assertIn("Start position", res_start_inf["reason"])
        self.assertIn("hazard zone", res_start_inf["reason"])

        # 3. Goal is on np.inf
        grid[0, 0] = 1.0
        grid[7, 7] = np.inf
        res_goal_inf = find_path(grid, (0, 0), (7, 7), mode="safest")
        self.assertFalse(res_goal_inf["success"])
        self.assertIn("Goal position", res_goal_inf["reason"])
        self.assertIn("hazard zone", res_goal_inf["reason"])

        # 4. compare_routes with unreachable goal
        comp_unreachable = compare_routes(grid, (0, 0), (7, 7))
        self.assertFalse(comp_unreachable["summary"]["both_reachable"])
        self.assertEqual(comp_unreachable["summary"]["distance_delta"], 0.0)

    def test_scenario_f_boundary_and_start_equals_goal(self):
        """Scenario F: Boundary checks and start == goal."""
        grid = np.ones((6, 6), dtype=float)

        # 1. Out-of-bounds start
        res_oob_start = find_path(grid, (-1, 2), (4, 4))
        self.assertFalse(res_oob_start["success"])
        self.assertIn("out of grid bounds", res_oob_start["reason"])

        # 2. Out-of-bounds goal
        res_oob_goal = find_path(grid, (2, 2), (6, 0))
        self.assertFalse(res_oob_goal["success"])
        self.assertIn("out of grid bounds", res_oob_goal["reason"])

        # 3. Start == Goal
        res_same = find_path(grid, (3, 3), (3, 3))
        self.assertTrue(res_same["success"])
        self.assertEqual(res_same["path"], [(3, 3)])
        self.assertEqual(res_same["x"], [3])
        self.assertEqual(res_same["y"], [3])

        metrics_same = calculate_path_metrics(res_same["path"], grid)
        self.assertEqual(metrics_same["total_distance"], 0.0)
        self.assertEqual(metrics_same["total_cost"], 0.0)
        self.assertEqual(metrics_same["step_count"], 0)
        self.assertEqual(metrics_same["caution_steps"], 0)

        # 4. Invalid mode raises ValueError
        with self.assertRaises(ValueError):
            find_path(grid, (0, 0), (1, 1), mode="fastest")

    def test_metrics_empty_path(self):
        """Test telemetry calculation on empty path."""
        grid = np.ones((5, 5), dtype=float)
        metrics = calculate_path_metrics([], grid)
        self.assertEqual(metrics["total_distance"], 0.0)
        self.assertEqual(metrics["total_cost"], 0.0)
        self.assertEqual(metrics["avg_terrain_cost"], 0.0)
        self.assertEqual(metrics["max_cell_cost"], 0.0)
        self.assertEqual(metrics["caution_steps"], 0)
        self.assertEqual(metrics["step_count"], 0)


if __name__ == "__main__":
    unittest.main()

