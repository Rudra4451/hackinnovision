"""Metrics computation for energy, roughness, and path efficiency."""
import math
from typing import List, Tuple


def calculate_path_length(path: List[Tuple[int, int]]) -> float:
    if len(path) < 2:
        return 0.0
    total = 0.0
    for i in range(len(path) - 1):
        dr = path[i+1][0] - path[i][0]
        dc = path[i+1][1] - path[i][1]
        total += math.hypot(dr, dc)
    return float(total)
