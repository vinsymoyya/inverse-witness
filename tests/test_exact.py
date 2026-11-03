from copy import deepcopy
from fractions import Fraction as F
import unittest

from inverse_witness.exact import CertificateError, canonical_hash, verify


def known_certificate():
    # max x0-x1 subject x0+x1<=1/2, 0<=x<=1 has optimum 1/2.
    problem = {"B": [["1", "1"]], "b": ["1/2"], "c": ["1", "-1"]}
    return {"schema": "inverse-witness.box-max.v1", "problem": problem,
            "problem_sha256": canonical_hash(problem),
            "proof": {"x": ["1/2", "0"], "multipliers": ["1"], "lower": "1/2", "upper": "1/2"}}


class ExactTests(unittest.TestCase):
    def test_analytic_optimum(self):
        self.assertEqual(verify(known_certificate(), "0")["gap"], "0")

    def test_negative_dual_rejected(self):
        cert = known_certificate()
        cert["proof"]["multipliers"] = ["-1"]
        with self.assertRaises(CertificateError):
            verify(cert)

    def test_rounding_violation_is_not_tolerated(self):
        cert = known_certificate()
        cert["proof"]["x"] = ["500000000000000001/1000000000000000000", "0"]
        with self.assertRaises(CertificateError):
            verify(cert)

    def test_changed_problem_rejected(self):
        cert = known_certificate()
        cert["problem"]["b"] = ["3/4"]
        with self.assertRaises(CertificateError):
            verify(cert)

    def test_incorrect_stated_bound_rejected(self):
        cert = known_certificate()
        cert["proof"]["upper"] = "1/3"
        with self.assertRaises(CertificateError):
            verify(cert)

    def test_float_input_rejected(self):
        cert = known_certificate()
        cert["proof"]["x"][0] = 0.5
        with self.assertRaises(CertificateError):
            verify(cert)

    def test_invalid_dimensions_rejected(self):
        cert = known_certificate()
        cert["proof"]["x"] = ["0"]
        with self.assertRaises(CertificateError):
            verify(cert)

    def test_nonzero_residual_dual_bound(self):
        # lambda=0 gives box support 1, still a valid loose upper bound.
        cert = known_certificate()
        cert["proof"].update(multipliers=["0"], upper="1")
        self.assertEqual(F(verify(cert)["gap"]), F(1, 2))
        with self.assertRaises(CertificateError):
            verify(cert, "1/3")


if __name__ == "__main__":
    unittest.main()
