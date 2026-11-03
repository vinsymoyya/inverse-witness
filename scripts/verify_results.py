"""Recheck every saved certificate using only the Python standard library.

Run from the repository root: python scripts/verify_results.py results/pilot
"""
import argparse
import csv
from fractions import Fraction as F
import gzip
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from inverse_witness.exact import verify, parse_problem, dot
from inverse_witness.physics import poisson_row, resistor_grid


def expected_problem(A, y, epsilon, c, sensor=None):
    # Construct independently of the optimization/search module.
    B = A + [[-v for v in row] for row in A]
    b = [v + epsilon for v in y] + [-v + epsilon for v in y]
    if sensor is None:
        return B, b, c
    zero = [F(0)] * len(c)
    return ([row + zero for row in B] + [zero + row for row in B]
            + [sensor + [-v for v in sensor], [-v for v in sensor] + sensor],
            b + b + [2 * epsilon] * 2, c + [-v for v in c])


def check_binding(cert, expected):
    if parse_problem(cert["problem"]) != expected:
        raise AssertionError("Certificate does not describe its declared physical instance")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    files = sorted((args.directory / "certificates").glob("*.json.gz"))
    if not files:
        raise SystemExit("No certificate bundles found")
    sources = json.loads((args.directory / "sources.json").read_text())
    rows = list(csv.DictReader((args.directory / "metrics.csv").open()))
    families = {}
    initial = [poisson_row(F(i, 8), 16) for i in (1, 3, 5, 7)]
    candidates = [poisson_row(F(i, 32), 16) for i in range(1, 32, 2)]
    families["poisson"] = initial, candidates, [f"s={i}/32" for i in range(1, 32, 2)]
    grid = resistor_grid(4)
    indices = [i for i in range(16) if i not in (0, 3, 12, 15)]
    families["resistor"] = [grid[i] for i in (0, 3, 12, 15)], [grid[i] for i in indices], [f"node={i}" for i in indices]
    count, max_gap = 0, F(0)
    for path in files:
        data = gzip.decompress(path.read_bytes())
        if hashlib.sha256(data).hexdigest() != sources[path.name.removesuffix(".json.gz")]["certificate_payload_sha256"]:
            raise AssertionError("Bundle hash mismatch")
        task_id = path.name.removesuffix(".json.gz")
        record = sources[task_id]
        family = task_id.split("-")[0]
        A, candidates, labels = families[family]
        truth = [F(v) for v in record["truth"]]
        y, c, epsilon = [F(v) for v in record["y"]], [F(v) for v in record["c"]], F(record["epsilon"])
        if not all(0 <= v <= 1 for v in truth) or any(abs(dot(a, truth) - v) > epsilon for a, v in zip(A, y)):
            raise AssertionError("Synthetic truth violates declared physical instance")
        qname = task_id.split("-")[-1]
        center = (6, 7, 8, 9) if family == "poisson" else (5, 6, 9, 10)
        edge = (0, 1, 14, 15) if family == "poisson" else (0, 3, 12, 15)
        expected_c = ([F(1, 16)] * 16 if qname == "total" else
                      [F(int(i in center) - (int(i in edge) if qname == "contrast" else 0), 4) for i in range(16)])
        if c != expected_c:
            raise AssertionError("Query does not match its declaration")
        bundle = json.loads(data)
        expected = [expected_problem(A, y, epsilon, [-v for v in c]), expected_problem(A, y, epsilon, c)]
        expected += [expected_problem(A, y, epsilon, c, a) for a in candidates]
        for i in record["post_indices"]:
            future_A, future_y = A + [candidates[i]], y + [dot(candidates[i], truth)]
            expected += [expected_problem(future_A, future_y, epsilon, [-v for v in c]), expected_problem(future_A, future_y, epsilon, c)]
        if len(expected) != len(bundle):
            raise AssertionError("Unexpected bundle layout")
        for cert, intended in zip(bundle, expected):
            check_binding(cert, intended)
            result = verify(cert, "1/1000000")
            count += 1
            max_gap = max(max_gap, F(result["gap"]))
        scores = bundle[2:2 + len(candidates)]
        selected = record["policies"]["minimax"]
        regret = F(scores[selected]["proof"]["upper"]) - min(F(cert["proof"]["lower"]) for cert in scores)
        for row in (r for r in rows if r["task_id"] == task_id):
            i = record["policies"][row["policy"]]
            score = scores[i]["proof"]
            if row["sensor"] != labels[i] or abs(float(row["worst_after_upper"]) - float(F(score["upper"]))) > 1e-12:
                raise AssertionError("CSV metric does not match certificate")
            if abs(float(row["selection_regret_upper"]) - float(regret)) > 1e-12:
                raise AssertionError("Selection-regret metric does not match certificates")
    summary = json.loads((args.directory / "summary.json").read_text())
    if count != summary["certificates"] or len(files) != summary["tasks"]:
        raise AssertionError("Result count mismatch")
    print(json.dumps({"tasks": len(files), "verified_certificates": count,
                      "maximum_exact_gap": str(max_gap), "physical_binding_checked": True,
                      "csv_sensor_scores_checked": True, "third_party_dependencies": 0}, indent=2))


if __name__ == "__main__":
    main()
