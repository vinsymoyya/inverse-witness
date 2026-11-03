"""Floating-point search followed by exact, independently checked bounds."""

from fractions import Fraction as F
import numpy as np
from scipy.optimize import linprog

from .exact import CertificateError, canonical_hash, dot, dual_ceiling, feasible, parse_problem, verify


def quantize(value):
    return F(float(value)).limit_denominator(10**12)


def make_problem(B, b, c, metadata=None):
    return {"B": [[str(F(v)) for v in row] for row in B],
            "b": [str(F(v)) for v in b], "c": [str(F(v)) for v in c],
            "metadata": metadata or {}}


def _repair(B, b, x, Bf, bf):
    if feasible(B, b, x):
        return x
    n = len(x)
    # A strict interior point permits exact convex repair of rounded endpoints.
    G = B + [[F(int(i == j)) for j in range(n)] for i in range(n)]
    G += [[F(-int(i == j)) for j in range(n)] for i in range(n)]
    h = b + [F(1)] * n + [F(0)] * n
    Gf = np.asarray(G, dtype=float)
    hf = np.asarray(h, dtype=float)
    interior = linprog(np.r_[np.zeros(n), -1.], A_ub=np.c_[Gf, np.ones(len(G))],
                       b_ub=hf, bounds=[(None, None)] * n + [(0, None)], method="highs")
    if not interior.success:
        raise CertificateError("Could not find a repair anchor: " + interior.message)
    anchor = [quantize(v) for v in interior.x[:n]]
    if any(dot(row, anchor) >= rhs for row, rhs in zip(G, h)):
        raise CertificateError("No exact strict interior anchor; degenerate instances need another solver")
    blend = F(0)
    for row, rhs in zip(G, h):
        violation = dot(row, x) - rhs
        if violation > 0:
            blend = max(blend, violation / (dot(row, x) - dot(row, anchor)))
    blend = min(F(1), blend + F(1, 10**12))
    repaired = [(1 - blend) * u + blend * v for u, v in zip(x, anchor)]
    if not feasible(B, b, repaired):
        raise CertificateError("Exact endpoint repair failed")
    return repaired


def maximize(problem):
    B, b, c = parse_problem(problem)
    n = len(c)
    Bf = np.asarray(B, dtype=float).reshape((-1, n))
    bf = np.asarray(b, dtype=float)
    result = linprog(-np.asarray(c, dtype=float), A_ub=Bf if len(B) else None,
                     b_ub=bf if len(B) else None, bounds=[(0, 1)] * n,
                     method="highs", options={"dual_feasibility_tolerance": 1e-9,
                                               "primal_feasibility_tolerance": 1e-9})
    if not result.success:
        raise CertificateError("LP search did not succeed: " + result.message)
    x = _repair(B, b, [quantize(v) for v in result.x], Bf, bf)
    lam = [max(F(0), quantize(-v)) for v in result.ineqlin.marginals]
    certificate = {"schema": "inverse-witness.box-max.v1", "problem": problem,
                   "problem_sha256": canonical_hash(problem),
                   "proof": {"x": [str(v) for v in x], "multipliers": [str(v) for v in lam],
                             "lower": str(dot(c, x)), "upper": str(dual_ceiling(B, b, c, lam))}}
    verify(certificate)
    return certificate


def measurement_constraints(A, y, epsilon):
    A = [[F(v) for v in row] for row in A]
    y = [F(v) for v in y]
    epsilon = [F(epsilon)] * len(A) if isinstance(epsilon, (str, int, F)) else [F(v) for v in epsilon]
    if len(A) != len(y) or len(A) != len(epsilon) or any(e < 0 for e in epsilon):
        raise ValueError("Invalid measurement lengths or noise bounds")
    return A + [[-v for v in row] for row in A], [v + e for v, e in zip(y, epsilon)] + [-v + e for v, e in zip(y, epsilon)]


def interval(A, y, epsilon, c):
    B, b = measurement_constraints(A, y, epsilon)
    hi = maximize(make_problem(B, b, c, {"role": "query-upper"}))
    lo = maximize(make_problem(B, b, [-F(v) for v in c], {"role": "negative-query-upper"}))
    return {"lower": -F(lo["proof"]["upper"]), "upper": F(hi["proof"]["upper"]),
            "witness_lower": -F(lo["proof"]["lower"]), "witness_upper": F(hi["proof"]["lower"]),
            "low_certificate": lo, "high_certificate": hi}


def next_measurement_problem(A, y, epsilon, c, sensor, sensor_epsilon):
    """Exact worst-case posterior query width for ONE candidate measurement.

    Two states can share a future reading iff |a.(u-v)| <= 2*sensor_epsilon.
    This eliminates the future reading and the bilevel maximization.
    """
    if F(sensor_epsilon) < 0:
        raise ValueError("Noise bound must be nonnegative")
    B, b = measurement_constraints(A, y, epsilon)
    n = len(c)
    if len(sensor) != n:
        raise ValueError("Candidate sensor dimension mismatch")
    zeros = [F(0)] * n
    pair_B = [row + zeros for row in B] + [zeros + row for row in B]
    sensor = [F(v) for v in sensor]
    pair_B += [sensor + [-v for v in sensor], [-v for v in sensor] + sensor]
    pair_b = b + b + [2 * F(sensor_epsilon)] * 2
    return make_problem(pair_B, pair_b, [F(v) for v in c] + [-F(v) for v in c],
                        {"role": "worst-case-next-measurement-width", "state_dimension": n,
                         "sensor": [str(v) for v in sensor], "sensor_epsilon": str(F(sensor_epsilon))})


def choose_sensor(A, y, epsilon, c, candidates, sensor_epsilon):
    if not candidates:
        raise ValueError("At least one candidate is required")
    proofs = [maximize(next_measurement_problem(A, y, epsilon, c, a, sensor_epsilon)) for a in candidates]
    selected = min(range(len(proofs)), key=lambda i: F(proofs[i]["proof"]["upper"]))
    regret = F(proofs[selected]["proof"]["upper"]) - min(F(p["proof"]["lower"]) for p in proofs)
    return {"selected": selected, "regret_upper": str(max(F(0), regret)), "certificates": proofs}
