import unittest
from core.science import rank_targets, calculate_confidence


class TestScience(unittest.TestCase):
    def test_rank_targets(self):
        targets = [
            {"id": "A", "pos": (10, 10), "priority": 5},
            {"id": "B", "pos": (90, 90), "priority": 10},
        ]
        ranked = rank_targets(targets, rover_pos=(0, 0))
        self.assertEqual(len(ranked), 2)
        self.assertIn("composite_score", ranked[0])

    def test_confidence(self):
        conf = calculate_confidence({"id": "SAMPLE_1"})
        self.assertTrue(0.0 <= conf <= 1.0)


if __name__ == "__main__":
    unittest.main()

