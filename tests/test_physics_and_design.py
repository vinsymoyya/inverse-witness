from fractions import Fraction as F
import itertools
import unittest

from inverse_witness.exact import dot, verify
from inverse_witness.physics import poisson_row, resistor_grid, inflate_for_operator_error
from inverse_witness.solver import choose_sensor, interval, make_problem, maximize, next_measurement_problem


class PhysicsAndDesignTests(unittest.TestCase):
    def test_uniform_source_continuum_solution(self):
        # For f=1 the exact continuum solution is s(1-s)/2.
        for n, s in itertools.product((1, 3, 8, 16), (F(1, 7), F(1, 2), F(6, 7))):
            self.assertEqual(sum(poisson_row(s, n)), s * (1 - s) / 2)

    def test_sensor_and_cell_reflection(self):
        self.assertEqual(poisson_row(F(1, 5), 7), list(reversed(poisson_row(F(4, 5), 7))))

    def test_resistor_grid_kirchhoff_identity(self):
        A = resistor_grid(3)
        for i in range(9):
            r, c = divmod(i, 3)
            neighbors = [rr * 3 + cc for rr, cc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1))
                         if 0 <= rr < 3 and 0 <= cc < 3]
            for j in range(9):
                self.assertEqual(4 * A[i][j] - sum(A[k][j] for k in neighbors), int(i == j))

    def test_known_ambiguity_and_minimax_sensor(self):
        # x0+x1=1 within 1/10. Reading x0 is useful; reading the same sum is not.
        result = choose_sensor([[F(1), F(1)]], [F(1)], F(1, 10), [F(1), F(0)],
                               [[F(1), F(0)], [F(1), F(1)]], F(1, 20))
        self.assertEqual(result["selected"], 0)
        first, second = result["certificates"]
        self.assertLess(abs(F(first["proof"]["upper"]) - F(1, 10)), F(1, 10**7))
        self.assertLess(abs(F(second["proof"]["upper"]) - 1), F(1, 10**7))

    def test_future_common_reading_exists(self):
        A, y, eps, c, a, eta = [[F(1), F(1)]], [F(1)], F(1, 10), [F(1), F(0)], [F(1), F(0)], F(1, 20)
        cert = maximize(next_measurement_problem(A, y, eps, c, a, eta))
        v = [F(x) for x in cert["proof"]["x"]]
        u, w = v[:2], v[2:]
        common = (dot(a, u) + dot(a, w)) / 2
        self.assertLessEqual(abs(dot(a, u) - common), eta)
        self.assertLessEqual(abs(dot(a, w) - common), eta)

    def test_scalar_interval_has_analytic_answer(self):
        result = interval([[F(2)]], [F(1)], F(1, 5), [F(1)])
        self.assertLess(abs(result["lower"] - F(2, 5)), F(1, 10**7))
        self.assertLess(abs(result["upper"] - F(3, 5)), F(1, 10**7))

    def test_monotonicity_under_added_measurement(self):
        before = interval([[1, 1]], [1], F(1, 10), [1, 0])
        after = interval([[1, 1], [1, 0]], [1, F(1, 2)], F(1, 10), [1, 0])
        self.assertLess(after["upper"] - after["lower"], before["upper"] - before["lower"])

    def test_general_max_against_independent_vertex_enumeration(self):
        # A 2D polygon with independently enumerated intersections of boundary lines.
        B, b, c = [[F(2), F(1)], [F(-1), F(2)]], [F(7, 5), F(1, 2)], [F(3), F(-1)]
        rows = B + [[F(1), F(0)], [F(0), F(1)], [F(-1), F(0)], [F(0), F(-1)]]
        rhs = b + [F(1), F(1), F(0), F(0)]
        values = []
        for i, j in itertools.combinations(range(len(rows)), 2):
            a, d = rows[i], rows[j]
            det = a[0] * d[1] - a[1] * d[0]
            if det:
                x = [(rhs[i] * d[1] - a[1] * rhs[j]) / det,
                     (a[0] * rhs[j] - rhs[i] * d[0]) / det]
                if all(dot(row, x) <= h for row, h in zip(rows, rhs)):
                    values.append(dot(c, x))
        optimum = max(values)
        cert = maximize(make_problem(B, b, c))
        verify(cert, "1/1000000")
        self.assertLessEqual(F(cert["proof"]["lower"]), optimum)
        self.assertGreaterEqual(F(cert["proof"]["upper"]), optimum)

    def test_operator_error_budget_encloses_all_box_vertices(self):
        delta = [[F(1, 10), F(1, 20)]]
        budget = inflate_for_operator_error([[1, 2]], delta)[0]
        for x in itertools.product((F(0), F(1)), repeat=2):
            for signs in itertools.product((-1, 1), repeat=2):
                self.assertLessEqual(abs(dot([s * v for s, v in zip(signs, delta[0])], x)), budget)

    def test_infeasible_problem_fails(self):
        with self.assertRaises(ValueError):
            maximize(make_problem([[1]], [-1], [1]))

    def test_negative_noise_rejected(self):
        with self.assertRaises(ValueError):
            interval([[1]], [0], -1, [1])


if __name__ == "__main__":
    unittest.main()
