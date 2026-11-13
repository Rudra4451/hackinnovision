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
    plan_mission_route,
    smooth_trajectory,
    recalculate_on_dynamic_hazard,
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

    def test_plan_mission_route_three_stops(self):
        """Test multi-stop mission routing connecting start through 3 waypoints."""
        grid = np.ones((10, 10), dtype=float)
        start = (0, 0)
        waypoints = [(0, 3), (3, 3), (3, 6)]

        # 1. Success case: continuous 3-stop trajectory
        res = plan_mission_route(grid, start, waypoints, mode="safest")
        self.assertTrue(res["success"], "Mission route planning should succeed")
        self.assertEqual(res["path"][0], start)
        self.assertEqual(res["path"][-1], waypoints[-1])

        # Verify all waypoints are in the stitched trajectory in sequence
        wp_indices = [res["path"].index(wp) for wp in waypoints]
        self.assertEqual(wp_indices, sorted(wp_indices), "Waypoints must be visited in order")

        # Verify duplicate overlapping points at transitions were removed
        for i in range(len(res["path"]) - 1):
            self.assertNotEqual(
                res["path"][i],
                res["path"][i + 1],
                f"Duplicate waypoint found at index {i}",
            )

        # Coordinate alignment checks
        self.assertEqual(len(res["x"]), len(res["path"]))
        self.assertEqual(len(res["y"]), len(res["path"]))
        self.assertEqual(res["x"], [c for _, c in res["path"]])
        self.assertEqual(res["y"], [r for r, _ in res["path"]])

        # Telemetry metrics checks
        metrics = res["metrics"]
        self.assertGreater(metrics["total_distance"], 0.0)
        self.assertEqual(metrics["step_count"], len(res["path"]) - 1)

        # 2. Failure case: Waypoint 2 unreachable due to hazard
        grid[3, 3] = np.inf
        fail_res = plan_mission_route(grid, start, waypoints, mode="safest")
        self.assertFalse(fail_res["success"])
        self.assertEqual(fail_res["reason"], "Waypoint 2 unreachable")
        self.assertEqual(fail_res["path"], [])

    def test_kinematic_turn_penalties(self):
        """
        Verify that high turn_penalty penalizes heading changes, forcing A*
        to prefer a straight path with fewer turns over a lower-cost zigzag path.
        """
        def count_turns(path):
            if len(path) <= 2:
                return 0
            turns = 0
            for i in range(1, len(path) - 1):
                h1 = (path[i][0] - path[i - 1][0], path[i][1] - path[i - 1][1])
                h2 = (path[i + 1][0] - path[i][0], path[i + 1][1] - path[i][1])
                if h1 != h2:
                    turns += 1
            return turns

        # 6x6 grid where a zigzag corridor has slightly lower terrain cost (1.0)
        # while a straight-line detour has slightly higher terrain cost (1.2).
        grid = np.full((6, 6), 5.0)
        zigzag_cells = [(0, 0), (1, 0), (1, 1), (2, 1), (2, 2), (3, 2), (3, 3)]
        for r, c in zigzag_cells:
            grid[r, c] = 1.0

        for r in range(4):
            grid[r, 0] = 1.2
        for c in range(4):
            grid[3, c] = 1.2
        grid[0, 0] = 1.0

        # Block diagonal cuts across the zigzag steps to force discrete turns
        grid[0, 1] = np.inf
        grid[1, 2] = np.inf
        grid[2, 3] = np.inf

        # Without turn penalty: chooses zigzag path with lower terrain cost
        res_no_penalty = find_path(grid, (0, 0), (3, 3), mode="safest", turn_penalty=0.0)
        self.assertTrue(res_no_penalty["success"])
        turns_no_penalty = count_turns(res_no_penalty["path"])

        # With turn penalty = 3.0: chooses straight corridor (down col 0, across row 3) with exactly 1 turn
        res_penalty = find_path(grid, (0, 0), (3, 3), mode="safest", turn_penalty=3.0)
        self.assertTrue(res_penalty["success"])
        turns_penalty = count_turns(res_penalty["path"])

        self.assertGreater(
            turns_no_penalty,
            turns_penalty,
            f"Expected turn penalty to reduce turns: {turns_no_penalty} vs {turns_penalty}",
        )
        self.assertEqual(turns_penalty, 1, "Straight corridor path should contain exactly 1 turn")
        self.assertEqual(
            res_penalty["path"],
            [(0, 0), (1, 0), (2, 0), (3, 0), (3, 1), (3, 2), (3, 3)],
        )

    def test_smooth_trajectory_and_hazard_clamping(self):
        """
        Verify gradient descent path smoothing:
        1. Smoothed coordinates slightly round sharp 90-degree corners.
        2. Output dictionary contains float smoothed_x and smoothed_y lists matching path length.
        3. Smoothed points clamp back to the safe grid center when bordering np.inf hazards.
        """
        # 1. Basic path smoothing
        sharp_path = [(0, 0), (1, 0), (2, 0), (2, 1), (2, 2)]
        smoothed = smooth_trajectory(sharp_path, weight_data=0.5, weight_smooth=0.1)

        self.assertEqual(len(smoothed), len(sharp_path))
        # Fixed endpoints
        self.assertEqual(smoothed[0], (0.0, 0.0))
        self.assertEqual(smoothed[-1], (2.0, 2.0))

        # Intermediate points should have continuous float coordinates rounding the corner
        self.assertNotEqual(smoothed[2], (2.0, 0.0))
        self.assertIsInstance(smoothed[2][0], float)
        self.assertIsInstance(smoothed[2][1], float)

        # 2. find_path returns smoothed coordinates
        grid = np.ones((8, 8), dtype=float)
        res = find_path(grid, (0, 0), (4, 4), mode="safest")
        self.assertTrue(res["success"])
        self.assertIn("smoothed_x", res)
        self.assertIn("smoothed_y", res)
        self.assertEqual(len(res["smoothed_x"]), len(res["path"]))
        self.assertEqual(len(res["smoothed_y"]), len(res["path"]))
        self.assertIsInstance(res["smoothed_x"][0], float)

        # 3. Hazard clamping test
        # Create hazard immediately adjacent to corner (2, 0) at (2, -1) or (3, 0)
        hazard_grid = np.ones((5, 5), dtype=float)
        hazard_grid[1, 1] = np.inf
        # Path going around corner near (1, 1)
        path = [(0, 1), (0, 0), (1, 0)]
        clamped_smoothed = smooth_trajectory(path, cost_map=hazard_grid)
        self.assertEqual(clamped_smoothed[0], (0.0, 1.0))
        self.assertEqual(clamped_smoothed[-1], (1.0, 0.0))

    def test_recalculate_on_dynamic_hazard(self):
        """
        Verify real-time vision integration: uncharted boulder injected mid-drive
        forces an evasive reroute around the new obstacle with reroute_required=True.
        """
        grid = np.ones((10, 10), dtype=float)
        start = (0, 0)
        goal = (0, 7)

        # Initial clear path straight down row 0
        initial_route = find_path(grid, start, goal, mode="safest")
        self.assertTrue(initial_route["success"])
        self.assertIn((0, 3), initial_route["path"])
        self.assertIn((0, 4), initial_route["path"])

        # Rover reaches (0, 2) when vision system flags boulders at (0, 3) and (0, 4)
        current_pos = (0, 2)
        new_hazards = [(0, 3), (0, 4)]

        reroute = recalculate_on_dynamic_hazard(
            cost_map=grid,
            current_pos=current_pos,
            goal=goal,
            new_hazards=new_hazards,
            mode="safest",
        )

        self.assertTrue(reroute["success"])
        self.assertTrue(reroute.get("reroute_required"))
        self.assertEqual(reroute["path"][0], current_pos)
        self.assertEqual(reroute["path"][-1], goal)

        # Ensure rerouted path strictly avoids newly detected hazard cells
        for hazard in new_hazards:
            self.assertNotIn(
                hazard,
                reroute["path"],
                f"Rerouted path passed through injected hazard at {hazard}",
            )

        # Ensure original map was not mutated (function takes a copy)
        self.assertEqual(grid[0, 3], 1.0, "Original cost map must not be modified in place")

        # Failure case: newly injected hazards completely isolate the goal
        boxed_goal_hazards = [(0, 6), (1, 7)]
        grid[0, 8] = np.inf  # Out of bounds/wall
        fail_reroute = recalculate_on_dynamic_hazard(
            cost_map=grid,
            current_pos=current_pos,
            goal=goal,
            new_hazards=[(0, 7)],  # Direct hit on goal
        )
        self.assertFalse(fail_reroute["success"])
        self.assertTrue(fail_reroute["reroute_required"])


if __name__ == "__main__":
    unittest.main()

