"""
Distance computation utilities using Euclidean metric.
"""

import math
from .models import Location


def calculate_distance(loc1: Location, loc2: Location) -> float:
    """
    Computes the exact standard Euclidean distance between two 2D locations.
    Formula: sqrt((x2 - x1)^2 + (y2 - y1)^2)
    Intermediate calculations preserve full IEEE 754 floating point precision.
    """
    dx = loc2.x - loc1.x
    dy = loc2.y - loc1.y
    return math.hypot(dx, dy)
