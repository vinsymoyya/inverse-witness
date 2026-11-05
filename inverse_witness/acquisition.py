"""Compile acquisition intervals and calibration bounds without scientific libraries.

Bounds are supplied assumptions. This module does not infer a calibration from a
measurement or prove that a real instrument obeys its declared error budget.
"""
from fractions import Fraction as F

from .exact import canonical_hash, rational


def acquisition_hash(document):
    def safe(value):
        if isinstance(value, F):
            return str(value)
        if isinstance(value, dict):
            return {k: safe(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [safe(v) for v in value]
        return value
    return canonical_hash(safe(document))


def _bounds(value, default, positive=False):
    if value is None:
        value = default
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError("Calibration bounds must have two endpoints")
    lo, hi = map(rational, value)
    if lo > hi or (positive and lo <= 0):
        raise ValueError("Invalid calibration bounds")
    return lo, hi


def compile_acquisition(document):
    """Return B,b,c for a conservative outer set of admissible source states.

    Observation z=g*(a+da).x+offset+noise. Gain must be strictly positive;
    x is in [0,1]^n, |da_j|<=operator_error_j. Unknown offsets and gains
    are projected row by row, so shared calibration correlations are relaxed.
    None endpoints denote censoring, not a missing value to impute.
    """
    if document.get("schema") != "inverse-witness.acquisition.v1":
        raise ValueError("Unknown acquisition schema")
    A = [[rational(v) for v in row] for row in document["A"]]
    c = [rational(v) for v in document["c"]]
    row_ids = document["row_ids"]
    if not c or any(len(row) != len(c) for row in A) or len(row_ids) != len(A):
        raise ValueError("Acquisition dimensions do not match")
    if any(not isinstance(v, str) or not v for v in row_ids) or len(set(row_ids)) != len(row_ids):
        raise ValueError("Row identifiers must be unique nonempty strings")
    error = document.get("operator_error")
    error = [[F(0)] * len(c) for _ in A] if error is None else [[rational(v) for v in row] for row in error]
    if len(error) != len(A) or any(len(row) != len(c) or any(v < 0 for v in row) for row in error):
        raise ValueError("Invalid operator-error dimensions or sign")
    lookup = {key: i for i, key in enumerate(row_ids)}
    seen, B, b = set(), [], []
    for observation in document["observations"]:
        key = observation["row_id"]
        if key not in lookup or key in seen:
            raise ValueError("Unknown or duplicate observation row identifier")
        seen.add(key)
        valid = observation.get("valid", True)
        if not isinstance(valid, bool):
            raise ValueError("valid must be a boolean")
        if not valid:
            continue
        if "value" in observation:
            if "lower" in observation or "upper" in observation:
                raise ValueError("Use value OR interval endpoints")
            lo = hi = rational(observation["value"])
        else:
            lo = observation.get("lower")
            hi = observation.get("upper")
            lo = None if lo is None else rational(lo)
            hi = None if hi is None else rational(hi)
        if lo is not None and hi is not None and lo > hi:
            raise ValueError("Observation interval is reversed")
        gain_lo, gain_hi = _bounds(observation.get("gain"), [1, 1], positive=True)
        offset_lo, offset_hi = _bounds(observation.get("offset"), [0, 0])
        epsilon = rational(observation.get("epsilon", 0))
        if epsilon < 0:
            raise ValueError("Noise budget must be nonnegative")
        i = lookup[key]
        delta = sum(error[i], F(0))
        if hi is not None:
            value = hi - offset_lo + epsilon
            bound = max(value / gain_lo, value / gain_hi) + delta
            B.append(A[i])
            b.append(bound)
        if lo is not None:
            value = lo - offset_hi - epsilon
            bound = min(value / gain_lo, value / gain_hi) - delta
            B.append([-v for v in A[i]])
            b.append(-bound)
    return B, b, c
