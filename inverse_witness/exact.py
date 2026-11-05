"""Small independent checker: standard-library rational arithmetic only.

The checker trusts the supplied mathematical problem, not its physical provenance.
All variables lie in [0,1]. See paper/METHODS.md for the bound derivation.
"""

from fractions import Fraction
import hashlib
import json


class CertificateError(ValueError):
    """A certificate does not establish its stated claim."""


def rational(value):
    if isinstance(value, bool) or isinstance(value, float):
        raise CertificateError("Use exact integer or rational-string inputs, not floats")
    try:
        return Fraction(value)
    except (TypeError, ValueError, ZeroDivisionError) as exc:
        raise CertificateError("Invalid rational") from exc


def dot(a, b):
    if len(a) != len(b):
        raise CertificateError("Dot-product dimension mismatch")
    return sum((rational(x) * rational(y) for x, y in zip(a, b)), Fraction(0))


def canonical_hash(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def parse_problem(problem):
    try:
        B = [[rational(v) for v in row] for row in problem["B"]]
        b = [rational(v) for v in problem["b"]]
        c = [rational(v) for v in problem["c"]]
    except (KeyError, TypeError) as exc:
        raise CertificateError("Malformed problem") from exc
    if not c or len(B) != len(b) or any(len(row) != len(c) for row in B):
        raise CertificateError("Invalid problem dimensions")
    return B, b, c


def feasible(B, b, x):
    return all(0 <= v <= 1 for v in x) and all(dot(row, x) <= rhs for row, rhs in zip(B, b))


def dual_ceiling(B, b, c, multipliers):
    """For ANY nonnegative multipliers, compute an exact valid upper bound."""
    if len(multipliers) != len(B) or any(v < 0 for v in multipliers):
        raise CertificateError("Invalid dual multipliers")
    residual = [c[j] - sum((multipliers[i] * B[i][j] for i in range(len(B))), Fraction(0))
                for j in range(len(c))]
    return dot(b, multipliers) + sum((max(Fraction(0), v) for v in residual), Fraction(0))


def verify(certificate, max_gap=None):
    """Verify a maximization bracket; never use a floating-point tolerance."""
    if certificate.get("schema") == "inverse-witness.box-infeasible.v1":
        return verify_infeasibility(certificate)
    if certificate.get("schema") != "inverse-witness.box-max.v1":
        raise CertificateError("Unknown schema")
    problem = certificate.get("problem", {})
    if canonical_hash(problem) != certificate.get("problem_sha256"):
        raise CertificateError("Problem hash mismatch")
    B, b, c = parse_problem(problem)
    try:
        proof = certificate["proof"]
        x = [rational(v) for v in proof["x"]]
        lam = [rational(v) for v in proof["multipliers"]]
        stated_lower = rational(proof["lower"])
        stated_upper = rational(proof["upper"])
    except (KeyError, TypeError) as exc:
        raise CertificateError("Malformed proof") from exc
    if len(x) != len(c) or not feasible(B, b, x):
        raise CertificateError("Primal witness is infeasible")
    lower = dot(c, x)
    upper = dual_ceiling(B, b, c, lam)
    if lower != stated_lower or upper != stated_upper or lower > upper:
        raise CertificateError("Incorrect objective bracket")
    gap = upper - lower
    if max_gap is not None and gap > rational(max_gap):
        raise CertificateError("Certificate gap exceeds requested bound")
    return {"lower": str(lower), "upper": str(upper), "gap": str(gap),
            "problem_sha256": canonical_hash(problem)}


def verify_infeasibility(certificate):
    """Check a boxed Farkas contradiction: min_box lambda.Bx > lambda.b."""
    problem = certificate.get("problem", {})
    if canonical_hash(problem) != certificate.get("problem_sha256"):
        raise CertificateError("Problem hash mismatch")
    B, b, c = parse_problem(problem)
    proof = certificate.get("proof", {})
    lam = [rational(v) for v in proof.get("multipliers", [])]
    if len(lam) != len(B) or any(v < 0 for v in lam):
        raise CertificateError("Invalid infeasibility multipliers")
    support = sum((min(Fraction(0), sum((lam[i] * B[i][j] for i in range(len(B))), Fraction(0)))
                   for j in range(len(c))), Fraction(0))
    margin = support - dot(b, lam)
    if margin <= 0 or margin != rational(proof.get("margin")):
        raise CertificateError("No exact infeasibility contradiction")
    return {"status": "infeasible", "margin": str(margin), "problem_sha256": canonical_hash(problem)}
