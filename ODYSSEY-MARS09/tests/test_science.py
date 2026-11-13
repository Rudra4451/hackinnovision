import unittest
from core.science import rank_targets, calculate_confidence, calculate_shannon_entropy


class TestScience(unittest.TestCase):
    def test_rank_targets(self):
        targets = [
            {"id": "A", "pos": (10, 10), "type": "PHYLLOSILICATES", "priority": 10},
            {"id": "B", "pos": (90, 90), "type": "BASALTIC_BEDROCK", "priority": 4},
        ]
        ranked = rank_targets(targets, rover_pos=(0, 0))
        self.assertEqual(len(ranked), 2)
        self.assertIn("composite_score", ranked[0])
        self.assertIn("confidence", ranked[0])

    def test_accessibility_safety_gating(self):
        # Target placed in impassable obstacle cost
        cost_map = [[float("inf") for _ in range(20)] for _ in range(20)]
        targets = [{"id": "HAZARD_TGT", "pos": (5, 5), "type": "HEMATITE_RIDGE", "priority": 8}]
        ranked = rank_targets(targets, rover_pos=(0, 0), cost_map=cost_map)
        self.assertEqual(ranked[0]["status"], "IMPASSABLE_HAZARD")
        self.assertEqual(ranked[0]["composite_score"], 0.0)

    def test_shannon_entropy(self):
        # Uniform distribution across 2 classes has entropy 1.0 bit
        entropy = calculate_shannon_entropy([0.5, 0.5])
        self.assertAlmostEqual(entropy, 1.0, places=4)

    def test_confidence(self):
        conf = calculate_confidence({"id": "SAMPLE_1", "class_probabilities": [0.90, 0.08, 0.02]})
        self.assertTrue(0.0 <= conf <= 1.0)


if __name__ == "__main__":
    unittest.main()
