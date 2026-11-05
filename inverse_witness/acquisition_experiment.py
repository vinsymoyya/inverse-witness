"""Replay real thermal records and separately labeled injected acquisition faults."""
import argparse
import csv
from fractions import Fraction as F
import gzip
import hashlib
import json
from pathlib import Path
import platform
import time

from .acquisition import acquisition_hash, compile_acquisition
from .exact import CertificateError, dot, feasible, verify
from .solver import InfeasibleProblem, interval_acquisition
from .thermal import VARIATIONS, evaluation_windows, fit_model, input_assumptions_hold, make_window, read_thermal, verify_data


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8", newline="\n")


def run_acquisition(output, data_directory):
    output, data_directory = Path(output), Path(data_directory)
    if output.exists():
        raise FileExistsError("Refusing to overwrite an existing acquisition run")
    provenance = verify_data(data_directory)
    datasets = {name: read_thermal(data_directory / name) for name in ("second_order_data.csv", "mimo_data.csv")}
    model = fit_model(datasets["second_order_data.csv"])
    config = {"schema": "inverse-witness.acquisition-replay.v1", "source_repository": provenance["repository"],
              "source_commit": provenance["commit"], "source_license": provenance["license"],
              "variations": list(VARIATIONS), "handling_modes": ["naive", "aware"],
              "window_transitions": 8, "within_record_stride": 8, "cross_record_stride": 24,
              "uninformative_width_threshold": "99/100", "maximum_certificate_gap": "1/1000000",
              "claim": "Real recorded temperatures and commands; injected faults are counterfactual replay. Empirical calibration is not a physical guarantee."}
    output.mkdir(parents=True)
    write_json(output / "config.json", config)
    write_json(output / "model.json", model)
    write_json(output / "data_provenance.json", provenance)
    (output / "LICENSE").write_bytes((data_directory / "LICENSE").read_bytes())
    (output / "NOTICE.txt").write_text("Measured TCLab data and derived replay records: Apache-2.0.\n"
        "Source: APMonitor/arduino, commit " + provenance["commit"] + ".\n"
        "Counterfactual faults and empirical replay code: Inverse Witness / Vinsy Moyya.\n"
        "See data/tclab_apmonitor/NOTICE.md for source paths and scope.\n", encoding="utf-8", newline="\n")
    start, metrics, certificates, numerical_failures = time.perf_counter(), [], 0, 0
    for dataset, samples in datasets.items():
        for indices in evaluation_windows(samples, dataset):
            nominal, nominal_reference = make_window(samples, model, indices, "nominal", "aware", dataset)
            nominal_B, nominal_b, _ = compile_acquisition(nominal)
            model_budget_holds = feasible(nominal_B, nominal_b, nominal_reference)
            for variation in VARIATIONS:
                for handling in config["handling_modes"]:
                    case_id = f"{Path(dataset).stem}-{indices[0]:04d}-{variation}-{handling}"
                    acquisition, reference = make_window(samples, model, indices, variation, handling, dataset)
                    B, b, c = compile_acquisition(acquisition)
                    reference_query = dot(c, reference)
                    reference_feasible = feasible(B, b, reference)
                    record = {"case_id": case_id, "dataset": dataset,
                              "split": "held_out_time" if dataset == "second_order_data.csv" else "other_acquisition",
                              "start_transition": indices[0], "variation": variation, "handling": handling,
                              "constraint_count": len(B), "reference_query": float(reference_query),
                              "reference_feasible": reference_feasible, "status": "", "query_covered": "",
                              "input_assumptions_hold": input_assumptions_hold(samples, indices, variation, handling),
                              "baseline_model_budget_holds": model_budget_holds,
                              "width": "", "uninformative": "", "silent_failure": False}
                    payload = {"schema": "inverse-witness.acquisition-case.v1", "acquisition": acquisition,
                               "acquisition_sha256": acquisition_hash(acquisition),
                               "reference_commands": [str(v) for v in reference], "certificates": []}
                    try:
                        answer = interval_acquisition(acquisition)
                        for cert in (answer["low_certificate"], answer["high_certificate"]):
                            verify(cert, config["maximum_certificate_gap"])
                            payload["certificates"].append(cert)
                        covered = answer["lower"] <= reference_query <= answer["upper"]
                        width = answer["upper"] - answer["lower"]
                        record.update(status="bounded", query_covered=covered, width=float(width),
                                      uninformative=width >= F(99, 100), silent_failure=not covered)
                        payload["interval"] = {"lower": str(answer["lower"]), "upper": str(answer["upper"])}
                    except InfeasibleProblem as exc:
                        verify(exc.certificate)
                        payload["certificates"] = [exc.certificate]
                        record["status"] = "inconsistent"
                    except CertificateError as exc:
                        # Failure to produce a proof is not an inconsistency certificate.
                        record["status"] = "search_failure"
                        payload["search_error"] = str(exc)
                        numerical_failures += 1
                    certificates += len(payload["certificates"])
                    payload["metrics"] = record
                    content = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
                    path = output / "cases" / (case_id + ".json.gz")
                    path.parent.mkdir(exist_ok=True)
                    with gzip.GzipFile(filename=str(path), mode="wb", mtime=0) as stream:
                        stream.write(content)
                    metrics.append(record)
            print(f"completed {dataset} transitions {indices[0]}..{indices[-1]}", flush=True)
    with (output / "metrics.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(metrics[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(metrics)
    groups = []
    for dataset in datasets:
        for variation in VARIATIONS:
            for handling in config["handling_modes"]:
                rows = [r for r in metrics if (r["dataset"], r["variation"], r["handling"]) == (dataset, variation, handling)]
                widths = sorted(r["width"] for r in rows if r["status"] == "bounded")
                from statistics import median
                groups.append({"dataset": dataset, "variation": variation, "handling": handling, "cases": len(rows),
                               "bounded": len(widths), "inconsistent": sum(r["status"] == "inconsistent" for r in rows),
                               "search_failure": sum(r["status"] == "search_failure" for r in rows),
                               "silent_failure": sum(r["silent_failure"] for r in rows),
                               "reference_feasible": sum(r["reference_feasible"] for r in rows),
                               "input_assumptions_hold": sum(r["input_assumptions_hold"] for r in rows),
                               "baseline_model_budget_holds": sum(r["baseline_model_budget_holds"] for r in rows),
                               "query_covered": sum(r["query_covered"] is True for r in rows),
                               "uninformative": sum(r["uninformative"] is True for r in rows),
                               "median_width_if_bounded": median(widths) if widths else None})
    summary = {"cases": len(metrics), "acquisition_files": 2, "certificates": certificates,
               "search_failures": numerical_failures, "seconds": time.perf_counter() - start,
               "python": platform.python_version(), "groups": groups}
    write_json(output / "summary.json", summary)
    return {key: value for key, value in summary.items() if key != "groups"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--data", type=Path, default=Path("data/tclab_apmonitor"))
    args = parser.parse_args()
    print(json.dumps(run_acquisition(args.output, args.data), indent=2))
