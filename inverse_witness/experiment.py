"""Declared synthetic experiments. Ground truth is used only by the evaluator."""

import argparse
import csv
from fractions import Fraction as F
import gzip
import hashlib
import json
from pathlib import Path
import platform
import random
import time

import numpy as np
import scipy

from .exact import canonical_hash, dot, rational, verify
from .physics import observe, poisson_row, resistor_grid
from .solver import choose_sensor, interval


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, default=str) + "\n", encoding="utf-8")


def setup(family):
    n = 16
    if family == "poisson":
        initial = [poisson_row(F(j, 8), n) for j in (1, 3, 5, 7)]
        candidates = [poisson_row(F(j, 32), n) for j in range(1, 32, 2)]
        labels = [f"s={j}/32" for j in range(1, 32, 2)]
    elif family == "resistor":
        full = resistor_grid(4)
        initial = [full[i] for i in (0, 3, 12, 15)]
        indices = [i for i in range(n) if i not in (0, 3, 12, 15)]
        candidates = [full[i] for i in indices]
        labels = [f"node={i}" for i in indices]
    else:
        raise ValueError("Unknown physics family")
    return initial, candidates, labels


def query(family, name):
    center = (6, 7, 8, 9) if family == "poisson" else (5, 6, 9, 10)
    edge = (0, 1, 14, 15) if family == "poisson" else (0, 3, 12, 15)
    if name == "local":
        return [F(int(i in center), 4) for i in range(16)]
    if name == "contrast":
        return [F(int(i in center) - int(i in edge), 4) for i in range(16)]
    if name == "total":
        return [F(1, 16)] * 16
    raise ValueError("Unknown query")


def source(rng, family, distribution):
    if distribution == "smooth":
        if family == "poisson":
            coordinate = (np.arange(16) + .5) / 16
            values = .45 + rng.uniform(-.12, .12)
            values = values + rng.normal(0, .07) * np.sin(2 * np.pi * coordinate)
            values = values + rng.normal(0, .05) * np.cos(2 * np.pi * coordinate)
        else:
            rr, cc = np.indices((4, 4)) / 3
            values = .45 + rng.uniform(-.12, .12)
            values = values + rng.normal(0, .08) * (rr - .5) + rng.normal(0, .08) * (cc - .5)
            values = values + rng.normal(0, .04) * np.cos(np.pi * rr) * np.cos(np.pi * cc)
            values = values.ravel()
    elif distribution == "shifted":
        values = np.where(rng.random(16) < rng.uniform(.15, .5), .96, .04)
    else:
        raise ValueError("Unknown source distribution")
    values = np.clip(values, .01, .99)
    return [F(int(round(v * 10000)), 10000) for v in values]


def _noise(rng, m, epsilon):
    return [F(int(v), 10000) * epsilon for v in rng.integers(-10000, 10001, size=m)]


def _training_data(family, A, epsilon, count, seed):
    rng = np.random.default_rng(seed)
    sources = [source(rng, family, "smooth") for _ in range(count)]
    measurements = [observe(A, x, _noise(rng, len(A), epsilon)) for x in sources]
    return np.asarray(measurements, dtype=float), np.asarray(sources, dtype=float)


def fit_baseline(family, A, epsilon):
    # Disjoint deterministic source streams: train, tune, calibration, evaluation.
    Y, X = _training_data(family, A, epsilon, 1024, 30101)
    Yt, Xt = _training_data(family, A, epsilon, 128, 30202)
    Yc, Xc = _training_data(family, A, epsilon, 256, 30303)
    mean, scale = Y.mean(0), Y.std(0)
    scale = np.maximum(scale, 1e-12)
    rng = np.random.default_rng(30404)
    W, bias = rng.normal(size=(4, 64)), rng.normal(size=64)

    def features(y):
        y = np.atleast_2d(y)
        z = (y - mean) / scale
        return np.c_[np.ones(len(z)), z, np.tanh(z @ W + bias)]

    H, Ht = features(Y), features(Yt)
    candidates = []
    for regularization in (1e-4, 1e-2, 1.):
        coefficient = np.linalg.solve(H.T @ H + regularization * np.eye(H.shape[1]), H.T @ X)
        candidates.append((float(np.mean((Ht @ coefficient - Xt)**2)), regularization, coefficient))
    _, regularization, coefficient = min(candidates, key=lambda v: v[0])
    calibration_prediction = features(Yc) @ coefficient

    def predict(y):
        return (features(np.asarray(y, dtype=float)) @ coefficient)[0]

    return {"predict": predict, "calibration_prediction": calibration_prediction,
            "calibration_truth": Xc, "regularization": regularization}


def baseline_query(model, c, y):
    c = np.asarray(c, dtype=float)
    scores = np.abs((model["calibration_prediction"] - model["calibration_truth"]) @ c)
    # Split conformal order statistic ceil((n+1)*(1-alpha)); only ID exchangeability applies.
    rank = min(len(scores), int(np.ceil((len(scores) + 1) * .95)))
    radius = float(np.sort(scores)[rank - 1])
    prediction = float(model["predict"](y) @ c)
    return prediction, radius


def policies(A, c, candidates, before, selection, seed):
    Af = np.asarray(A, dtype=float)
    pool = np.asarray(candidates, dtype=float)
    ridge = max(float(np.trace(Af.T @ Af)) / 16 * 1e-3, 1e-12)
    covariance = np.linalg.inv(Af.T @ Af + ridge * np.eye(16))
    d_opt = np.einsum("ij,jk,ik->i", pool, covariance, pool)
    hi = np.array([float(F(v)) for v in before["high_certificate"]["proof"]["x"]])
    lo = np.array([float(F(v)) for v in before["low_certificate"]["proof"]["x"]])
    return {"minimax": selection["selected"], "random": random.Random(seed).randrange(len(pool)),
            "d_optimal": int(np.argmax(d_opt)), "witness_separation": int(np.argmax(np.abs(pool @ (hi - lo)))),
            "max_row_norm": int(np.argmax(np.linalg.norm(pool, axis=1)))}


def _serialized_interval(result):
    return {key: str(result[key]) for key in ("lower", "upper", "witness_lower", "witness_upper")}


def run_demo(output):
    output = Path(output)
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite {output}")
    A, candidates, labels = setup("poisson")
    c, epsilon = query("poisson", "local"), F(1, 20000)
    truth = source(np.random.default_rng(50101), "poisson", "shifted")
    y = observe(A, truth, [F(0)] * len(A))
    before = interval(A, y, epsilon, c)
    selection = choose_sensor(A, y, epsilon, c, candidates, epsilon)
    index = selection["selected"]
    new_value = dot(candidates[index], truth)
    after = interval(A + [candidates[index]], y + [new_value], epsilon, c)
    write_json(output / "query-upper.json", before["high_certificate"])
    write_json(output / "query-negative-upper.json", before["low_certificate"])
    for i, cert in enumerate(selection["certificates"]):
        write_json(output / "candidates" / f"{i:02d}.json", cert)
    write_json(output / "after-upper.json", after["high_certificate"])
    write_json(output / "after-negative-upper.json", after["low_certificate"])
    result = {"family": "poisson", "noise_bound": str(epsilon), "truth": [str(v) for v in truth],
              "measurements": [str(v) for v in y], "query": [str(v) for v in c],
              "true_query": str(dot(c, truth)), "before": _serialized_interval(before),
              "after": _serialized_interval(after), "selected_sensor": labels[index],
              "selected_index": index, "selection_regret_upper": selection["regret_upper"],
              "candidate_scores": [{"sensor": label, "lower": cert["proof"]["lower"],
                                    "upper": cert["proof"]["upper"]} for label, cert in zip(labels, selection["certificates"])]}
    write_json(output / "summary.json", result)
    return {"selected_sensor": result["selected_sensor"],
            "before_width": float(before["upper"] - before["lower"]),
            "worst_case_after_width": float(F(selection["certificates"][index]["proof"]["upper"])),
            "realized_after_width": float(after["upper"] - after["lower"]),
            "selection_regret_upper": float(F(selection["regret_upper"])), "output": str(output)}


def run_benchmark(output, seeds=4):
    output = Path(output)
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite {output}")
    output.mkdir(parents=True)
    config = {"schema": "inverse-witness.synthetic.v1", "state_dimension": 16,
              "families": ["poisson", "resistor"], "queries": ["local", "contrast", "total"],
              "distributions": ["smooth", "shifted"], "seeds_per_cell": seeds,
              "training": 1024, "tuning": 128, "calibration": 256,
              "noise": {"poisson": ["1/20000", "1/4000"], "resistor": ["1/2000", "1/400"]},
              "seed_streams": {"train": 30101, "tune": 30202, "calibration": 30303, "features": 30404, "test_start": 60101},
              "claim": "Synthetic pilot; no new general theorem, SOTA advantage, or real-data claim"}
    write_json(output / "config.json", config)
    start = time.perf_counter()
    rows, sources, certificate_count, max_gap = [], {}, 0, F(0)
    for family in config["families"]:
        A, candidates, labels = setup(family)
        for epsilon_string in config["noise"][family]:
            epsilon = F(epsilon_string)
            model = fit_baseline(family, A, epsilon)
            for distribution in config["distributions"]:
                for seed in range(seeds):
                    # Shared source across noise levels and queries supports paired comparisons.
                    rng = np.random.default_rng(60101 + seed + 100 * (distribution == "shifted") + 1000 * (family == "resistor"))
                    truth = source(rng, family, distribution)
                    y = observe(A, truth, _noise(rng, len(A), epsilon))
                    for qname in config["queries"]:
                        task_id = f"{family}-{epsilon.denominator}-{distribution}-{seed}-{qname}"
                        c = query(family, qname)
                        true_q = dot(c, truth)
                        before = interval(A, y, epsilon, c)
                        selection = choose_sensor(A, y, epsilon, c, candidates, epsilon)
                        selected = policies(A, c, candidates, before, selection, 70101 + seed)
                        bundle = [before["low_certificate"], before["high_certificate"]] + selection["certificates"]
                        pred, radius = baseline_query(model, c, y)
                        values = {i: dot(candidates[i], truth) for i in set(selected.values())}
                        post = {}
                        for i in values:
                            post[i] = interval(A + [candidates[i]], y + [values[i]], epsilon, c)
                            bundle += [post[i]["low_certificate"], post[i]["high_certificate"]]
                        for cert in bundle:
                            checked = verify(cert, "1/1000000")
                            max_gap = max(max_gap, F(checked["gap"]))
                        certificate_count += len(bundle)
                        cert_path = output / "certificates" / f"{task_id}.json.gz"
                        cert_path.parent.mkdir(exist_ok=True)
                        payload = json.dumps(bundle, sort_keys=True, separators=(",", ":")).encode()
                        with gzip.GzipFile(filename=str(cert_path), mode="wb", mtime=0) as f:
                            f.write(payload)
                        sources[task_id] = {"truth": [str(v) for v in truth], "y": [str(v) for v in y],
                                            "c": [str(v) for v in c], "epsilon": str(epsilon),
                                            "post_indices": list(values), "policies": selected,
                                            "baseline_regularization": model["regularization"],
                                            "certificate_payload_sha256": hashlib.sha256(payload).hexdigest()}
                        old_width = before["upper"] - before["lower"]
                        coverage = before["lower"] <= true_q <= before["upper"]
                        for policy, index in selected.items():
                            score = selection["certificates"][index]["proof"]
                            after = post[index]
                            if not after["lower"] <= true_q <= after["upper"]:
                                raise AssertionError("Certificate interval lost an admissible truth")
                            rows.append({"task_id": task_id, "family": family, "noise": str(epsilon),
                                         "distribution": distribution, "seed": seed, "query": qname,
                                         "policy": policy, "sensor": labels[index],
                                         "before_width": float(old_width), "worst_after_lower": float(F(score["lower"])),
                                         "worst_after_upper": float(F(score["upper"])),
                                         "worst_width_ratio": float(F(score["upper"]) / old_width),
                                         "realized_after_width": float(after["upper"] - after["lower"]),
                                         "selection_regret_upper": float(F(selection["regret_upper"])),
                                         "true_query": float(true_q), "baseline_prediction": pred,
                                         "baseline_radius_95": radius, "baseline_covered": abs(pred - float(true_q)) <= radius,
                                         "certificate_covered": bool(coverage)})
                        print(f"completed {task_id}", flush=True)
    with (output / "metrics.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    write_json(output / "sources.json", sources)
    unique = [r for r in rows if r["policy"] == "minimax"]
    summary = {"tasks": len(unique), "policy_rows": len(rows), "certificates": certificate_count,
               "maximum_exact_certificate_gap": str(max_gap), "seconds": time.perf_counter() - start,
               "python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__,
               "config_sha256": canonical_hash(config), "certificate_truth_coverage": sum(r["certificate_covered"] for r in unique),
               "baseline_coverage": {d: {"covered": sum(r["baseline_covered"] for r in unique if r["distribution"] == d),
                                          "total": sum(r["distribution"] == d for r in unique)} for d in config["distributions"]},
               "policies": {policy: {"median_worst_width_ratio": float(np.median([r["worst_width_ratio"] for r in rows if r["policy"] == policy])),
                                     "median_realized_width": float(np.median([r["realized_after_width"] for r in rows if r["policy"] == policy]))}
                            for policy in ("minimax", "random", "d_optimal", "witness_separation", "max_row_norm")}}
    write_json(output / "summary.json", summary)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seeds", type=int, default=4)
    args = parser.parse_args()
    if args.seeds < 1:
        parser.error("--seeds must be positive")
    print(json.dumps(run_benchmark(args.output, args.seeds), indent=2))
