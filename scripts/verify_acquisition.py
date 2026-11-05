"""Standard-library replay of real-data binding, certificate proofs, and metrics."""
import argparse
import csv
from fractions import Fraction as F
import gzip
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from inverse_witness.acquisition import acquisition_hash, compile_acquisition
from inverse_witness.exact import dot, feasible, parse_problem, verify
from inverse_witness.thermal import VARIATIONS, evaluation_windows, input_assumptions_hold, make_window, read_thermal, verify_data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--data", type=Path, default=Path("data/tclab_apmonitor"))
    args = parser.parse_args()
    provenance = verify_data(args.data)
    saved = json.loads((args.directory / "data_provenance.json").read_text())
    if saved != provenance:
        raise AssertionError("Replay provenance does not match pinned raw data")
    model = json.loads((args.directory / "model.json").read_text())
    if model["train_transition_indices"] != list(range(1, 100)) or model["calibration_transition_indices"] != list(range(100, 140)):
        raise AssertionError("Declared identification split changed")
    rows = list(csv.DictReader((args.directory / "metrics.csv").open()))
    metrics = {r["case_id"]: r for r in rows}
    if len(metrics) != len(rows):
        raise AssertionError("Duplicate metric case")
    expected_cases, count, certificate_count, failed_searches = set(), 0, 0, 0
    for dataset in ("second_order_data.csv", "mimo_data.csv"):
        samples = read_thermal(args.data / dataset)
        for indices in evaluation_windows(samples, dataset):
            nominal, nominal_reference = make_window(samples, model, indices, "nominal", "aware", dataset)
            nominal_B, nominal_b, _ = compile_acquisition(nominal)
            for variation in VARIATIONS:
                for handling in ("naive", "aware"):
                    case_id = f"{Path(dataset).stem}-{indices[0]:04d}-{variation}-{handling}"
                    expected_cases.add(case_id)
                    path = args.directory / "cases" / (case_id + ".json.gz")
                    item = json.loads(gzip.decompress(path.read_bytes()))
                    acquisition, reference = make_window(samples, model, indices, variation, handling, dataset)
                    if item["acquisition"] != acquisition or item["reference_commands"] != [str(v) for v in reference]:
                        raise AssertionError("Raw acquisition / model binding changed: " + case_id)
                    if item["acquisition_sha256"] != acquisition_hash(acquisition):
                        raise AssertionError("Acquisition hash mismatch")
                    B, b, c = compile_acquisition(acquisition)
                    q = dot(c, reference)
                    recorded = item["metrics"]
                    if recorded["reference_feasible"] != feasible(B, b, reference):
                        raise AssertionError("Reference-feasibility metric changed")
                    if recorded["input_assumptions_hold"] != input_assumptions_hold(samples, indices, variation, handling):
                        raise AssertionError("Input-assumptions audit changed")
                    if recorded["baseline_model_budget_holds"] != feasible(nominal_B, nominal_b, nominal_reference):
                        raise AssertionError("Original model-budget audit changed")
                    checked = []
                    for cert in item["certificates"]:
                        BB, bb, cc = parse_problem(cert["problem"])
                        if BB != B or bb != b or cc not in (c, [-v for v in c]):
                            raise AssertionError("Certificate does not describe the acquisition")
                        if cert["problem"]["metadata"]["acquisition_sha256"] != acquisition_hash(acquisition):
                            raise AssertionError("Certificate acquisition hash changed")
                        checked.append(verify(cert, "1/1000000"))
                        certificate_count += 1
                    if recorded["status"] == "bounded":
                        if len(checked) != 2 or any("gap" not in v for v in checked):
                            raise AssertionError("Missing query certificates")
                        low_cert, high_cert = item["certificates"]
                        if parse_problem(low_cert["problem"])[2] != [-v for v in c] or parse_problem(high_cert["problem"])[2] != c:
                            raise AssertionError("Wrong interval objective signs")
                        lower, upper = -F(checked[0]["upper"]), F(checked[1]["upper"])
                        if item["interval"] != {"lower": str(lower), "upper": str(upper)}:
                            raise AssertionError("Interval endpoints changed")
                        if recorded["query_covered"] != (lower <= q <= upper) or recorded["silent_failure"] != (not lower <= q <= upper):
                            raise AssertionError("False interval-coverage metric")
                        if abs(recorded["width"] - float(upper - lower)) > 1e-12 or recorded["uninformative"] != (upper - lower >= F(99, 100)):
                            raise AssertionError("Width metric changed")
                    elif recorded["status"] == "inconsistent":
                        if len(checked) != 1 or checked[0].get("status") != "infeasible":
                            raise AssertionError("Inconsistency has no exact proof")
                    elif recorded["status"] == "search_failure":
                        if checked or not item.get("search_error"):
                            raise AssertionError("Invalid search-failure record")
                        failed_searches += 1
                    else:
                        raise AssertionError("Unknown case outcome")
                    if any(str(value) != metrics[case_id][key] for key, value in recorded.items()):
                        raise AssertionError("CSV and verified case metrics differ")
                    count += 1
    actual_cases = {p.name.removesuffix(".json.gz") for p in (args.directory / "cases").glob("*.json.gz")}
    summary = json.loads((args.directory / "summary.json").read_text())
    if expected_cases != actual_cases or expected_cases != set(metrics):
        raise AssertionError("Missing or unexpected acquisition cases")
    if (summary["cases"], summary["certificates"], summary["search_failures"]) != (count, certificate_count, failed_searches):
        raise AssertionError("Summary counts differ from replay")
    for group in summary["groups"]:
        selected = [r for r in rows if all(r[k] == group[k] for k in ("dataset", "variation", "handling"))]
        from statistics import median
        widths = [float(r["width"]) for r in selected if r["status"] == "bounded"]
        expected = {"cases": len(selected), "bounded": len(widths),
                    "inconsistent": sum(r["status"] == "inconsistent" for r in selected),
                    "search_failure": sum(r["status"] == "search_failure" for r in selected),
                    **{k: sum(r[k] == "True" for r in selected) for k in ("silent_failure", "reference_feasible", "query_covered", "uninformative", "input_assumptions_hold", "baseline_model_budget_holds")},
                    "median_width_if_bounded": median(widths) if widths else None}
        if any(group[k] != v for k, v in expected.items()):
            raise AssertionError("Group summary changed")
    print(json.dumps({"verified_cases": count, "verified_certificates": certificate_count,
                      "explicit_search_failures": failed_searches, "raw_data_binding": True,
                      "third_party_dependencies": 0}, indent=2))


if __name__ == "__main__":
    main()
