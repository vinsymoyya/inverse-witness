"""Rational forward operators with explicit physical assumptions."""

from fractions import Fraction as F
from .exact import dot


def poisson_row(position, cells):
    """Exact continuum integral of Dirichlet Green's function on constant cells.

    -u''(s)=f(s), u(0)=u(1)=0; f equals x_j on cell j. Sensor reads u(s).
    No quadrature or finite-difference approximation occurs in this operator.
    """
    s = F(position)
    if not 0 < s < 1 or cells < 1:
        raise ValueError("Need a sensor inside (0,1) and positive cell count")
    row = []
    for j in range(cells):
        left, right = F(j, cells), F(j + 1, cells)
        cut = max(left, min(s, right))
        before = (1 - s) * (cut**2 - left**2) / 2
        after = s * ((right - right**2 / 2) - (cut - cut**2 / 2))
        row.append(before + after)
    return row


def inverse_rational(matrix):
    n = len(matrix)
    work = [[F(v) for v in row] + [F(int(i == j)) for j in range(n)] for i, row in enumerate(matrix)]
    for j in range(n):
        pivot = next((i for i in range(j, n) if work[i][j]), None)
        if pivot is None:
            raise ValueError("Singular physical operator")
        work[j], work[pivot] = work[pivot], work[j]
        scale = work[j][j]
        work[j] = [v / scale for v in work[j]]
        for i in range(n):
            if i != j:
                scale = work[i][j]
                work[i] = [v - scale * w for v, w in zip(work[i], work[j])]
    return [row[n:] for row in work]


def resistor_grid(side):
    """Unit conductance square grid, grounded exterior; current sources in [0,1].

    Each node has four unit conductances, including connections to exterior ground.
    K v = x and A=K^{-1}; row sensors read node voltages. This is a discrete network.
    """
    if side < 2:
        raise ValueError("Grid side must be at least two")
    n = side * side
    K = [[F(0)] * n for _ in range(n)]
    for r in range(side):
        for col in range(side):
            i = r * side + col
            K[i][i] = 4
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                rr, cc = r + dr, col + dc
                if 0 <= rr < side and 0 <= cc < side:
                    K[i][rr * side + cc] = -1
    return inverse_rational(K)


def observe(A, truth, noise):
    if len(A) != len(noise):
        raise ValueError("Noise dimension mismatch")
    return [dot(row, truth) + F(e) for row, e in zip(A, noise)]


def inflate_for_operator_error(A, entrywise_error):
    """Uniform sufficient budget for |(A_true-A)x| when x is in [0,1]^n.

    Bounds each row by the sum of elementwise absolute error bounds. This is
    conservative; the caller must independently justify those error bounds.
    """
    if len(A) != len(entrywise_error) or any(len(a) != len(e) for a, e in zip(A, entrywise_error)):
        raise ValueError("Error-bound dimension mismatch")
    if any(F(v) < 0 for row in entrywise_error for v in row):
        raise ValueError("Error bounds must be nonnegative")
    return [sum((F(v) for v in row), F(0)) for row in entrywise_error]
