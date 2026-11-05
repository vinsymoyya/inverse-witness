"""Measured TCLab replay. No synthetic temperature replaces an original record.

ARX coefficients are empirical. A calibration residual envelope is not a proved
instrument-error bound; held-out failures are retained, including silent failures.
"""
import csv
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path

from .exact import rational

VARIATIONS = ("nominal", "gain", "offset_drift", "dropout", "quantization",
              "saturation", "clock_scale", "channel_swap", "stale_sample", "out_of_budget")


def read_thermal(path):
    rows = []
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream)
        header = next(reader)
        if len(header) not in (5, 7) or not header[0].strip().startswith("Time"):
            raise ValueError("Expected the pinned TCLab column schema")
        if any(not value.strip().startswith(expected) for value, expected in
               zip(header[1:5], ("Heater 1", "Heater 2", "Temperature 1", "Temperature 2"))):
            raise ValueError("Acquisition channel headers do not match their physical order")
        for index, fields in enumerate(reader):
            if len(fields) != len(header):
                raise ValueError("Wrong acquisition column count")
            values = [rational(v.strip()) for v in fields]
            # Canonical microsecond / microdegree representation; raw bytes are retained.
            t = F(round(values[0] * 10**6), 10**6)
            T = [F(round(v * 10**6), 10**6) for v in values[3:5]]
            Q = [F(round(v * 10**6), 10**8) for v in values[1:3]]
            if any(not 0 <= q <= 1 for q in Q):
                raise ValueError("Heater commands must be percentages in [0,100]")
            if rows and t <= rows[-1]["time"]:
                raise ValueError("Duplicate or nonmonotone acquisition timestamps")
            rows.append({"time": t, "T": T, "Q": Q, "source_row": index})
    if len(rows) < 4:
        raise ValueError("Acquisition is too short")
    return rows


def verify_data(directory):
    directory = Path(directory)
    manifest = json.loads((directory / "provenance.json").read_text(encoding="utf-8-sig"))
    for entry in manifest["files"]:
        if Path(entry["file"]).name != entry["file"]:
            raise ValueError("Unexpected provenance filename")
        payload = (directory / entry["file"]).read_bytes()
        if hashlib.sha256(payload).hexdigest() != entry["sha256"]:
            raise ValueError("Data SHA-256 mismatch: " + entry["file"])
        blob = b"blob " + str(len(payload)).encode() + b"\0" + payload
        if hashlib.sha1(blob).hexdigest() != entry["git_blob_sha"]:
            raise ValueError("Upstream Git blob mismatch: " + entry["file"])
    return manifest


def features(rows, k):
    previous_dt = rows[k]["time"] - rows[k - 1]["time"]
    return ([F(1)] + [v - 20 for v in rows[k]["T"]]
            + [(v - u) / previous_dt for v, u in zip(rows[k]["T"], rows[k - 1]["T"])]
            + rows[k]["Q"])


def fit_model(rows):
    import numpy as np
    from scipy.optimize import lsq_linear
    # Fixed chronological split declared before evaluating the record.
    train = list(range(1, 100))
    calibration = list(range(100, 140))
    if len(rows) < 201:
        raise ValueError("The declared calibration record requires 201 samples")
    X = np.array([features(rows, k) for k in train], dtype=float)
    Y = np.array([[(rows[k + 1]["T"][j] - rows[k]["T"][j]) /
                   (rows[k + 1]["time"] - rows[k]["time"]) for j in range(2)] for k in train], dtype=float)
    coefficients = []
    for output in range(2):
        # Nonnegative input coefficients; this is still an empirical ARX model.
        lower = [-np.inf] * 5 + [0., 0.]
        lower[5 + output] = 1e-4
        fit = lsq_linear(X, Y[:, output], bounds=(lower, [np.inf] * 7), tol=1e-12)
        if not fit.success:
            raise ValueError("Thermal identification did not converge")
        coefficients.append([F(round(float(v) * 10**8), 10**8) for v in fit.x])
    budgets = [F(0), F(0)]
    for k in calibration:
        dt = rows[k + 1]["time"] - rows[k]["time"]
        f = features(rows, k)
        for output, beta in enumerate(coefficients):
            measured_rate = (rows[k + 1]["T"][output] - rows[k]["T"][output]) / dt
            residual = measured_rate - sum((a * v for a, v in zip(beta, f)), F(0))
            budgets[output] = max(budgets[output], abs(residual))
    return {"schema": "inverse-witness.thermal-arx.v1", "train_transition_indices": train,
            "calibration_transition_indices": calibration,
            "coefficient_rows": [[str(v) for v in row] for row in coefficients],
            "residual_rate_bounds": [str(v) for v in budgets],
            "training_design_condition_number": float(np.linalg.cond(X)),
            "reference_temperature_degC": 20,
            "interpretation": "Empirical maximum calibration residual; no universal noise guarantee"}


def varied_temperatures(rows, variation, handling):
    if variation not in VARIATIONS or handling not in ("naive", "aware"):
        raise ValueError("Unknown acquisition variation or handling mode")
    aware = handling == "aware"
    temperatures, times = [], []
    for i, row in enumerate(rows):
        points = list(row["T"])
        bounds = [(v, v) for v in points]
        t = row["time"]
        if variation == "gain":
            gains = (F(103, 100), F(97, 100))
            declared = ((F(102, 100), F(104, 100)), (F(96, 100), F(98, 100)))
            points = [v * g for v, g in zip(points, gains)]
            bounds = [(v / hi, v / lo) for v, (lo, hi) in zip(points, declared)] if aware else [(v, v) for v in points]
        elif variation in ("offset_drift", "out_of_budget"):
            drift = F(i, len(rows) - 1)
            offsets = (F(4, 5) * drift, -F(3, 5) * drift) if variation == "offset_drift" else (F(3), F(-3))
            points = [v + o for v, o in zip(points, offsets)]
            allowance = F(1) if variation == "offset_drift" else F(1, 5)
            bounds = [(v - allowance, v + allowance) if aware else (v, v) for v in points]
        elif variation == "quantization":
            points = [F(round(v * 2), 2) for v in points]
            bounds = [(v - F(1, 4), v + F(1, 4)) if aware else (v, v) for v in points]
        elif variation == "saturation":
            bounds = [(F(40), None) if aware and v >= 40 else (min(v, F(40)), min(v, F(40))) for v in points]
        elif variation == "dropout":
            if i % 24 in (6, 7, 8, 9):
                bounds[0] = (None, None) if aware else (F(0), F(0))
        elif variation == "clock_scale":
            t *= F(11, 10)
            if aware:
                t /= F(11, 10)
        elif variation == "channel_swap":
            bounds.reverse()
            if aware:  # Stable sensor labels restore the physical channel order.
                bounds.reverse()
        elif variation == "stale_sample" and i >= 2:
            value = rows[i - 2]["T"][0]
            bounds[0] = (None, None) if aware else (value, value)
        temperatures.append(bounds)
        times.append(t)
    return temperatures, times


def _linear_interval(constant, terms, temperatures):
    lower = upper = constant
    for (index, channel), coefficient in terms.items():
        if not coefficient:
            continue
        lo, hi = temperatures[index][channel]
        low_value, high_value = (lo, hi) if coefficient > 0 else (hi, lo)
        lower = None if lower is None or low_value is None else lower + coefficient * low_value
        upper = None if upper is None or high_value is None else upper + coefficient * high_value
    return lower, upper


def make_window(rows, model, indices, variation, handling, dataset):
    if not indices or any(k < 1 or k + 1 >= len(rows) for k in indices):
        raise ValueError("Window transition index is out of range")
    temperatures, times = varied_temperatures(rows, variation, handling)
    betas = [[F(v) for v in row] for row in model["coefficient_rows"]]
    budgets = [F(v) for v in model["residual_rate_bounds"]]
    n = 2 * len(indices)
    A, observations, row_ids = [], [], []
    for position, k in enumerate(indices):
        dt, previous_dt = times[k + 1] - times[k], times[k] - times[k - 1]
        if dt <= 0 or previous_dt <= 0:
            raise ValueError("Acquisition timing is not monotone")
        for output, beta in enumerate(betas):
            row = [F(0)] * n
            row[2 * position:2 * position + 2] = [dt * beta[5], dt * beta[6]]
            terms = {(k + 1, output): F(1), (k, output): F(-1)}
            for channel in range(2):
                terms[(k, channel)] = terms.get((k, channel), F(0)) - dt * beta[1 + channel] - dt / previous_dt * beta[3 + channel]
                terms[(k - 1, channel)] = terms.get((k - 1, channel), F(0)) + dt / previous_dt * beta[3 + channel]
            constant = -dt * beta[0] + dt * 20 * (beta[1] + beta[2])
            lo, hi = _linear_interval(constant, terms, temperatures)
            key = f"transition:{k}:temperature:{output + 1}"
            A.append([str(v) for v in row])
            row_ids.append(key)
            observations.append({"row_id": key, "lower": None if lo is None else str(lo),
                                 "upper": None if hi is None else str(hi), "epsilon": str(dt * budgets[output])})
    reference = [v for k in indices for v in rows[k]["Q"]]
    c = [F(1, len(indices)) if i % 2 == 0 else F(0) for i in range(n)]
    document = {"schema": "inverse-witness.acquisition.v1", "A": A, "row_ids": row_ids,
                "c": [str(v) for v in c], "observations": observations,
                "metadata": {"dataset": dataset, "transition_indices": indices,
                             "variation": variation, "handling": handling,
                             "quantity": "mean logged heater-1 command fraction"}}
    return document, reference


def evaluation_windows(rows, dataset):
    start, stride = (140, 8) if dataset == "second_order_data.csv" else (1, 24)
    return [list(range(k, k + 8)) for k in range(start, len(rows) - 8, stride)]


def input_assumptions_hold(rows, indices, variation, handling):
    """Offline audit using the unmodified record, unavailable on a new live fault."""
    temperatures, times = varied_temperatures(rows, variation, handling)
    for i in set(j for k in indices for j in (k - 1, k, k + 1)):
        if times[i] != rows[i]["time"]:
            return False
        for value, (lo, hi) in zip(rows[i]["T"], temperatures[i]):
            if (lo is not None and value < lo) or (hi is not None and value > hi):
                return False
    return True
