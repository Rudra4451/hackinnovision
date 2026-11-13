"""
Unit and Integration Tests for MARS-09 Odyssey Science Intelligence & Backend API.
"""

import math
import sys
import unittest
import numpy as np

sys.path.insert(0, ".")

from backend.integrations.navigation_adapter import (
    run_multi_waypoint_mission,
    run_route_comparison,
)
from backend.integrations.terrain_adapter import (
    deserialize_cost_map_from_json,
    generate_benchmark_terrain,
    sanitize_cost_map_for_json,
)
from backend.science.identification import calculate_scientific_value
from backend.science.recommendations import generate_mission_recommendation_report
from backend.science.scoring import evaluate_and_rank_targets
from backend.science.uncertainty import calculate_shannon_entropy, compute_target_uncertainty


class TestScienceIntelligenceEngine(unittest.TestCase):
    """Test suite verifying Rule 2, uncertainty, and science scoring."""

    def test_shannon_entropy_and_uncertainty(self):
        """Verify Shannon entropy computation and normalization."""
        # Pure certainty (1.0 for one class)
        e_certain = calculate_shannon_entropy([1.0, 0.0, 0.0])
        self.assertAlmostEqual(e_certain, 0.0, places=4)

        # Maximum ambiguity (equal distribution across 4 classes)
        e_uniform = calculate_shannon_entropy([0.25, 0.25, 0.25, 0.25])
        self.assertAlmostEqual(e_uniform, 2.0, places=4)

        unc = compute_target_uncertainty(
            {"C1": 0.5, "C2": 0.5},
            sensor_variance=0.0,
        )
        self.assertAlmostEqual(unc["normalized_uncertainty"], 1.0, places=3)
        self.assertAlmostEqual(unc["confidence_level"], 0.0, places=3)

    def test_scientific_value_separation_from_operational(self):
        """Rule 2: Scientific Value must reflect inherent merit regardless of hazard."""
        val = calculate_scientific_value(
            target_type="HYDRATED_CLAYS",
            spectral_signature={"signal_to_noise": 9.5, "hydration_index": 0.9, "mineral_diversity": 0.8},
            rarity_factor=1.1,
        )
        self.assertGreater(val, 80.0)
        self.assertLessEqual(val, 100.0)

    def test_rule_2_hard_safety_gate_operational_priority_zero(self):
        """
        Rule 2: Unsafe or unreachable targets (np.inf or blocked paths)
        MUST automatically receive an operational priority score of 0.0.
        """
        cost_map = np.ones((20, 20), dtype=float)
        # Put hazard cell at (5, 5)
        cost_map[5, 5] = np.inf

        raw_targets = [
            {
                "id": "TGT-SAFE",
                "name": "Safe Outcrop",
                "target_type": "BASALTIC_BEDROCK",
                "location": [2, 2],
                "spectral_signature": {"signal_to_noise": 8.0, "hydration_index": 0.3},
            },
            {
                "id": "TGT-HAZARD",
                "name": "Hazardous Clay Ridge",
                "target_type": "HYDRATED_CLAYS",
                "location": [5, 5],  # Located in np.inf
                "spectral_signature": {"signal_to_noise": 10.0, "hydration_index": 0.95},
            },
        ]

        evaluated, ranked_ids = evaluate_and_rank_targets(
            raw_targets=raw_targets,
            cost_map=cost_map,
            rover_pos=(0, 0),
        )

        hazard_tgt = next(t for t in evaluated if t["id"] == "TGT-HAZARD")
        safe_tgt = next(t for t in evaluated if t["id"] == "TGT-SAFE")

        # Inherent scientific value of clay is high
        self.assertGreater(hazard_tgt["scientific_value"], safe_tgt["scientific_value"])

        # BUT Operational Priority MUST BE 0.0 due to hard safety gate!
        self.assertEqual(hazard_tgt["operational_priority"], 0.0)
        self.assertEqual(hazard_tgt["accessibility_status"], "UNREACHABLE_HAZARD")

        # Safe target has operational priority > 0
        self.assertGreater(safe_tgt["operational_priority"], 0.0)
        self.assertEqual(ranked_ids[0], "TGT-SAFE")

    def test_rule_3_non_finite_json_serialization(self):
        """Rule 3: Non-finite values like np.inf must be sanitized safely for JSON."""
        grid = np.array([
            [1.0, 5.0, np.inf],
            [np.nan, 2.5, 1e10],
        ])

        sanitized = sanitize_cost_map_for_json(grid)
        self.assertIsNone(sanitized[0][2])
        self.assertIsNone(sanitized[1][0])
        self.assertIsNone(sanitized[1][2])
        self.assertEqual(sanitized[0][0], 1.0)
        self.assertEqual(sanitized[1][1], 2.5)

        restored = deserialize_cost_map_from_json(sanitized)
        self.assertTrue(np.isinf(restored[0, 2]))
        self.assertTrue(np.isinf(restored[1, 0]))
        self.assertTrue(np.isinf(restored[1, 2]))
        self.assertEqual(restored[0, 0], 1.0)

    def test_navigation_contract_compliance(self):
        """Verify navigation integration contract via compare_routes adapter."""
        cost_map, _ = generate_benchmark_terrain(20, 20)
        res = run_route_comparison(cost_map, (1, 1), (18, 18))

        self.assertIn("safest", res)
        self.assertIn("shortest", res)
        self.assertIn("summary", res)
        self.assertIn("success", res["safest"]["route"])
        self.assertIn("x", res["safest"]["route"])
        self.assertIn("y", res["safest"]["route"])
        self.assertIn("total_distance", res["safest"]["metrics"])
        self.assertIn("recommendation", res["summary"])

    def test_recommendation_report_generation(self):
        """Verify markdown report generation contains required tactical sections."""
        cost_map, _ = generate_benchmark_terrain(20, 20)
        raw_targets = [
            {
                "id": "TGT-1",
                "name": "Test Target",
                "target_type": "HYDRATED_CLAYS",
                "location": [2, 2],
            }
        ]
        evaluated, _ = evaluate_and_rank_targets(raw_targets, cost_map, (0, 0))
        report = generate_mission_recommendation_report(evaluated, (0, 0))

        self.assertIn("MARS-09 ODYSSEY: TACTICAL RECONNAISSANCE REPORT", report)
        self.assertIn("PRIMARY TARGET", report)
        self.assertIn("RECONNAISSANCE TARGET MATRIX", report)

    def test_multi_waypoint_mission_adapter(self):
        """Verify integration of teammate's plan_mission_route."""
        grid = np.ones((10, 10), dtype=float)
        res = run_multi_waypoint_mission(grid, (0, 0), [(2, 2), (5, 5)], mode="safest")
        self.assertTrue(res["success"])
        self.assertEqual(res["path"][0], (0, 0))
        self.assertEqual(res["path"][-1], (5, 5))
        self.assertIn("metrics", res)



if __name__ == "__main__":
    unittest.main()
