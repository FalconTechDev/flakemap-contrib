"""How many repeats does a gate need? A test failing independently with probability p is caught by N runs with
probability 1 - (1-p)^N. A test that never fails (p=0) can never be flagged by the 'mixed results' rule."""
from __future__ import annotations

import math
import random


def detect_prob(p: float, n: int) -> float:
    return 1.0 - (1.0 - p) ** n


def min_runs(p: float, target: float) -> int:
    if not (0 < p < 1 and 0 < target < 1):
        raise ValueError("p and target must be in (0, 1)")
    return math.ceil(math.log(1 - target) / math.log(1 - p))


def simulate(p: float, n: int, trials: int = 20000, seed: int = 0) -> float:
    """Empirical share of trials in which a test with failure prob p shows mixed results in n runs."""
    rng = random.Random(seed)
    hit = 0
    for _ in range(trials):
        fails = sum(rng.random() < p for _ in range(n))
        hit += 0 < fails < n
    return hit / trials
