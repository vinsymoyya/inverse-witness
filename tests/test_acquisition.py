from copy import deepcopy
from fractions import Fraction as F
import itertools
import unittest

from inverse_witness.acquisition import compile_acquisition
from inverse_witness.exact import CertificateError, dot, verify
from inverse_witness.solver import InfeasibleProblem, interval_acquisition, make_problem, maximize


def record(A, readings, c=None, ids=None, error=None):
    return {"schema": "inverse-witness.acquisition.v1", "A": A,
            "row_ids": ids or [str(i) for i in range(len(A))],
            "c": c or [1] * len(A[0]), "observations": readings,
            "operator_error": error}


class AcquisitionTests(unittest.TestCase):
    def test_reordered_ids_bind_to_correct_rows(self):
        r = record([[1, 0], [0, 1]], [{"row_id": "b", "value": "3/4"},
                                     {"row_id": "a", "value": "1/4"}], [1, 0], ["a", "b"])
        B, b, _ = compile_acquisition(r)
        self.assertTrue(all(dot(a, [F(1, 4), F(3, 4)]) <= h for a, h in zip(B, b)))
        self.assertFalse(all(dot(a, [F(3, 4), F(1, 4)]) <= h for a, h in zip(B, b)))

    def test_dropout_removes_constraints_instead_of_imputing_zero(self):
        r = record([[1]], [{"row_id": "0", "valid": False}])
        B, b, c = compile_acquisition(r)
        self.assertEqual((B, b, c), ([], [], [F(1)]))
        answer = interval_acquisition(r)
        self.assertEqual((answer["lower"], answer["upper"]), (F(0), F(1)))

    def test_known_gain_offset_and_quantization(self):
        # Sensor z=2*x+1 reads [1.9,2.1], yielding x in [.45,.55].
        r = record([[1]], [{"row_id": "0", "lower": "19/10", "upper": "21/10",
                            "gain": [2, 2], "offset": [1, 1]}])
        answer = interval_acquisition(r)
        self.assertLess(abs(answer["lower"] - F(9, 20)), F(1, 10**7))
        self.assertLess(abs(answer["upper"] - F(11, 20)), F(1, 10**7))

    def test_upper_saturation_is_one_sided(self):
        r = record([[1]], [{"row_id": "0", "lower": "4/5", "upper": None}])
        answer = interval_acquisition(r)
        self.assertLess(abs(answer["lower"] - F(4, 5)), F(1, 10**7))
        self.assertEqual(answer["upper"], 1)

    def test_uncertain_gain_offset_and_operator_error_contain_box_vertices(self):
        A, delta = [[F(2), F(-3)]], [[F(1, 5), F(1, 10)]]
        for x, g, o, e, signs in itertools.product(itertools.product((F(0), F(1)), repeat=2),
                                                   (F(4, 5), F(6, 5)), (F(-1, 10), F(1, 10)),
                                                   (F(-1, 20), F(1, 20)), itertools.product((-1, 1), repeat=2)):
            actual = [a + s * d for a, s, d in zip(A[0], signs, delta[0])]
            value = g * dot(actual, x) + o + e
            r = record(A, [{"row_id": "0", "value": str(value), "gain": ["4/5", "6/5"],
                            "offset": ["-1/10", "1/10"], "epsilon": "1/20"}], error=delta)
            B, b, _ = compile_acquisition(r)
            self.assertTrue(all(dot(row, x) <= h for row, h in zip(B, b)))

    def test_duplicate_and_unknown_observations_rejected(self):
        for readings in ([{"row_id": "x", "value": 0}], [{"row_id": "0", "value": 0}] * 2):
            with self.assertRaises(ValueError):
                compile_acquisition(record([[1]], readings))

    def test_invalid_gain_bounds_and_nonfinite_input_rejected(self):
        for changes in ({"gain": [0, 1]}, {"gain": [2, 1]}, {"value": "nan"},
                        {"epsilon": "-1"}, {"lower": 1, "upper": 0}, {"value": True}):
            observation = {"row_id": "0", "value": 0}
            observation.update(changes)
            with self.assertRaises(ValueError):
                compile_acquisition(record([[1]], [observation]))

    def test_missing_and_wrong_dimensions_rejected(self):
        for changes in ({"row_ids": ["a", "a"]}, {"c": [1, 2]}, {"A": [[1], [1, 2]]}):
            r = record([[1], [1]], [])
            r.update(changes)
            with self.assertRaises(ValueError):
                compile_acquisition(r)

    def test_inconsistent_acquisition_has_exact_farkas_proof(self):
        r = record([[1], [1]], [{"row_id": "0", "value": "1/5", "epsilon": "1/100"},
                                {"row_id": "1", "value": "4/5", "epsilon": "1/100"}])
        with self.assertRaises(InfeasibleProblem) as failure:
            interval_acquisition(r)
        certificate = failure.exception.certificate
        self.assertGreater(F(verify(certificate)["margin"]), 0)
        bad = deepcopy(certificate)
        bad["proof"]["multipliers"] = ["0"] * len(bad["proof"]["multipliers"])
        with self.assertRaises(CertificateError):
            verify(bad)

    def test_mathematically_valid_certificate_can_exclude_real_reference(self):
        # True x=.5 but unaccounted gain 1.2 produces y=.6: valid arithmetic, false physical premise.
        naive = record([[1]], [{"row_id": "0", "value": "3/5", "epsilon": "1/100"}])
        bad = interval_acquisition(naive)
        self.assertGreater(bad["lower"], F(1, 2))
        verify(bad["high_certificate"])
        aware = deepcopy(naive)
        aware["observations"][0]["gain"] = ["6/5", "6/5"]
        good = interval_acquisition(aware)
        self.assertLessEqual(good["lower"], F(1, 2))
        self.assertGreaterEqual(good["upper"], F(1, 2))


if __name__ == "__main__":
    unittest.main()
