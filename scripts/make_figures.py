"""Reproducible publication figures and result prose from saved records."""
import argparse
import csv
from fractions import Fraction as F
import json
from pathlib import Path
import statistics
import sys
import os

os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parents[1] / ".cache/matplotlib"))

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from inverse_witness.physics import poisson_row
from inverse_witness.exact import dot


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pilot", type=Path, default=Path("results/pilot"))
    parser.add_argument("--demo", type=Path, default=Path("results/demo"))
    args = parser.parse_args()
    output = Path("assets")
    output.mkdir(exist_ok=True)
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                         "figure.facecolor": "white", "axes.facecolor": "white", "savefig.facecolor": "white"})
    demo = json.loads((args.demo / "summary.json").read_text())
    lo = json.loads((args.demo / "query-negative-upper.json").read_text())
    hi = json.loads((args.demo / "query-upper.json").read_text())
    xlo = [F(v) for v in lo["proof"]["x"]]
    xhi = [F(v) for v in hi["proof"]["x"]]
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.4), layout="constrained")
    edges = np.linspace(0, 1, 17)
    axes[0].stairs([float(v) for v in xlo], edges, color="#007f88", label="Low-query witness", linewidth=2)
    axes[0].stairs([float(v) for v in xhi], edges, color="#b94b26", label="High-query witness", linewidth=2, linestyle="--")
    axes[0].axvspan(6 / 16, 10 / 16, color="#5264a7", alpha=.08, label="Query region")
    axes[0].set(title="A. Two admissible heat sources", xlabel="Position", ylabel="Source amplitude", ylim=(-.05, 1.05))
    axes[0].legend(fontsize=8, loc="upper left")
    points = [F(i, 160) for i in range(1, 160)]
    for x, color, style, label in ((xlo, "#007f88", "-", "Low-query witness"), (xhi, "#b94b26", "--", "High-query witness")):
        values = [float(dot(poisson_row(s, 16), x)) for s in points]
        axes[1].plot([float(s) for s in points], values, color=color, linestyle=style, linewidth=2, label=label)
    positions = [1 / 8, 3 / 8, 5 / 8, 7 / 8]
    axes[1].errorbar(positions, [float(F(v)) for v in demo["measurements"]], yerr=float(F(demo["noise_bound"])),
                     fmt="o", color="#162d40", markersize=5, capsize=4, label="Existing measurements")
    selected = (2 * demo["selected_index"] + 1) / 32
    axes[1].axvline(selected, color="#5264a7", linestyle=":", linewidth=2, label="Next measurement")
    axes[1].set(title="B. Both explain four thermometers", xlabel="Sensor position", ylabel="Temperature (nondimensional)")
    axes[1].legend(fontsize=8)
    scores = [float(F(v["upper"])) for v in demo["candidate_scores"]]
    colors = ["#5264a7" if i == demo["selected_index"] else "#b7c5ce" for i in range(len(scores))]
    axes[2].bar(range(len(scores)), scores, color=colors)
    axes[2].set(title="C. Choose by remaining ambiguity", xlabel="Candidate sensor index", ylabel="Worst-case query width", ylim=(0, max(scores) * 1.15))
    axes[2].annotate("Selected", (demo["selected_index"], scores[demo["selected_index"]]), xytext=(0, 9), textcoords="offset points", ha="center", fontsize=9)
    fig.savefig(output / "ambiguity-demo.png", dpi=170)
    fig.savefig(output / "ambiguity-demo.pdf")
    plt.close(fig)

    rows = list(csv.DictReader((args.pilot / "metrics.csv").open()))
    summary = json.loads((args.pilot / "summary.json").read_text())
    policies = ["minimax", "witness_separation", "d_optimal", "random", "max_row_norm"]
    labels = ["Minimax", "Witness heuristic", "D-optimal", "Random", "Max row norm"]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6), layout="constrained")
    groups = [[float(r["worst_width_ratio"]) for r in rows if r["policy"] == p] for p in policies]
    axes[0].boxplot(groups, tick_labels=labels, showfliers=True, medianprops={"color": "#162d40", "linewidth": 2})
    axes[0].set(title="A. One-step worst-case width", ylabel="Width after / width before (lower is better)", ylim=(0, 1.08))
    axes[0].tick_params(axis="x", labelrotation=20)
    axes[0].grid(axis="y", alpha=.18)
    coverage = summary["baseline_coverage"]
    vals = [100 * coverage[d]["covered"] / coverage[d]["total"] for d in ("smooth", "shifted")]
    axes[1].bar([0, 1], vals, color=["#007f88", "#b94b26"], width=.6)
    axes[1].axhline(95, color="#162d40", linestyle="--", label="Nominal 95% under exchangeability")
    for i, d in enumerate(("smooth", "shifted")):
        inside = vals[i] > 20
        axes[1].text(i, vals[i] - 6 if inside else vals[i] + 2,
                     f'{coverage[d]["covered"]}/{coverage[d]["total"]}', ha="center",
                     color="white" if inside else "black", fontweight="bold" if inside else "normal")
    axes[1].set(xticks=[0, 1], xticklabels=["Smooth test sources", "Shifted test sources"], ylim=(0, 112),
                title="B. Learned baseline interval coverage", ylabel="Covered query instances (%)")
    axes[1].legend(fontsize=8, loc="lower left")
    fig.suptitle("Synthetic pilot: 96 correlated query instances from 16 distinct sources", fontsize=12)
    fig.savefig(output / "pilot-results.png", dpi=170)
    fig.savefig(output / "pilot-results.pdf")
    plt.close(fig)

    minimax = {r["task_id"]: float(r["worst_after_upper"]) for r in rows if r["policy"] == "minimax"}
    table = []
    for p, label in zip(policies, labels):
        selected_rows = [r for r in rows if r["policy"] == p]
        strict = sum(float(r["worst_after_upper"]) - minimax[r["task_id"]] > 1e-6 for r in selected_rows)
        table.append(f'| {label} | {statistics.median(float(r["worst_width_ratio"]) for r in selected_rows):.4f} | {strict}/{len(selected_rows)} |')
    largest_regret = max(float(r["selection_regret_upper"]) for r in rows)
    text = f'''# Measured synthetic pilot

This report is generated from `results/pilot/metrics.csv` and `summary.json`. The run contains **{summary["tasks"]} query instances**, five sensing policies and **{summary["certificates"]} exact rational certificate brackets**. The query instances reuse 16 distinct sources; they are not independent replicates.

![Ambiguity example](../assets/ambiguity-demo.png)

The example starts with width {float(F(demo["before"]["upper"]) - F(demo["before"]["lower"])):.6f} for the local source mean. It selects {demo["selected_sensor"]}. Its worst-case next width is {float(F(demo["candidate_scores"][demo["selected_index"]]["upper"])):.6f}; the realized zero-noise next reading gives width {float(F(demo["after"]["upper"]) - F(demo["after"]["lower"])):.6f}. The realized and worst-case values answer different questions.

![Pilot results](../assets/pilot-results.png)

| Policy | Median worst-case width ratio | Instances worse than minimax by more than 1e-6 |
|---|---:|---:|
{chr(10).join(table)}

These policies are compared on the exact objective that minimax explicitly optimizes. Its advantage on that objective is expected by construction. This experiment does not establish an across-the-board advantage in realized width, average error, runtime or other sensing objectives. Ties and small differences are retained; no significance test treats the correlated rows as independent.

The largest exact candidate-selection regret bound was {largest_regret:.3g}. Every certificate's optimization gap was at most {float(F(summary["maximum_exact_certificate_gap"])):.3g}. All {summary["certificate_truth_coverage"]}/{summary["tasks"]} initial query intervals contained their simulated truth, as they must when all declared assumptions hold. This is an implementation check, not an empirical estimate of a universal coverage probability.

The random-feature learned baseline with nominal 95% split-conformal intervals covered {coverage["smooth"]["covered"]}/{coverage["smooth"]["total"]} smooth and {coverage["shifted"]["covered"]}/{coverage["shifted"]["total"]} shifted query instances. The shifted source law violates exchangeability with calibration. These counts show this baseline's behavior in this small controlled test; they do not characterize frontier AI models or disprove conformal coverage under its assumptions.

The benchmark took {summary["seconds"]:.1f} seconds on the recorded local environment, including certificate checking and output. It is not a controlled speed comparison. Runtime versions: Python {summary["python"]}, NumPy {summary["numpy"]}, SciPy {summary["scipy"]}. Exact configuration and source hashes accompany the run.

Reproduce with `python -m inverse_witness.experiment --output results/new-pilot --seeds 4`. Recheck saved mathematical and physical instances using `python -S scripts/verify_results.py results/pilot`. See [methods](METHODS.md), [data assumptions](../DATA_CARD.md) and [market analysis](../research/MARKET_RESEARCH.md).
'''
    Path("paper/RESULTS.md").write_text(text, encoding="utf-8")
    print("Wrote publication figures and paper/RESULTS.md")


if __name__ == "__main__":
    main()
