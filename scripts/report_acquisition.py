"""Figures and failure analysis generated from verified acquisition-case metrics."""
import csv
from fractions import Fraction as F
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".cache/matplotlib"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from inverse_witness.thermal import VARIATIONS, read_thermal


def main():
    directory = ROOT / "results/acquisition"
    summary = json.loads((directory / "summary.json").read_text())
    model = json.loads((directory / "model.json").read_text())
    records = list(csv.DictReader((directory / "metrics.csv").open()))
    assets = ROOT / "assets"
    datasets = ("second_order_data.csv", "mimo_data.csv")
    labels = ("No injected fault", "Gain mismatch", "Offset drift", "Missing samples", "0.5 C quantization",
              "40 C saturation", "Clock scale", "Swapped channels", "Stale samples", "Exceeded offset spec")
    colors = ("#bd572c", "#852f58", "#bac5cb", "#007f88", "#555d67")
    categories = ("Proved inconsistent", "Bounded, reference mean excluded", "Bounded, width >= 0.99",
                  "Bounded, narrower interval", "Search failure")
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                         "figure.facecolor": "white", "axes.facecolor": "white", "savefig.facecolor": "white"})
    fig, axes = plt.subplots(2, 2, figsize=(14, 9), layout="constrained")
    for row, dataset in enumerate(datasets):
        for col, handling in enumerate(("naive", "aware")):
            ax = axes[row, col]
            groups = [[r for r in records if (r["dataset"], r["handling"], r["variation"]) == (dataset, handling, variation)]
                      for variation in VARIATIONS]
            counts = []
            for group in groups:
                counts.append([sum(r["status"] == "inconsistent" for r in group),
                               sum(r["silent_failure"] == "True" for r in group),
                               sum(r["status"] == "bounded" and r["silent_failure"] == "False" and r["uninformative"] == "True" for r in group),
                               sum(r["status"] == "bounded" and r["silent_failure"] == "False" and r["uninformative"] == "False" for r in group),
                               sum(r["status"] == "search_failure" for r in group)])
            counts = np.array(counts)
            left = np.zeros(len(VARIATIONS))
            for i, (color, label) in enumerate(zip(colors, categories)):
                ax.barh(np.arange(len(VARIATIONS)), counts[:, i], left=left, color=color, label=label, height=.7)
                left += counts[:, i]
            n = len(groups[0])
            ax.set(yticks=np.arange(len(VARIATIONS)), yticklabels=labels, xlim=(0, n),
                   title=f'{"Same-record holdout" if row == 0 else "Other acquisition"} / {handling} ({n} windows)',
                   xlabel="Number of replay windows")
            ax.invert_yaxis()
            ax.set_xticks([0, n // 2, n])
    handles, legend_labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, legend_labels, loc="outside upper center", ncol=3, fontsize=9)
    fig.savefig(assets / "acquisition-failures.png", dpi=160)
    fig.savefig(assets / "acquisition-failures.pdf")
    plt.close(fig)

    fig, axes = plt.subplots(2, 2, figsize=(13, 6.5), layout="constrained")
    for i, dataset in enumerate(datasets):
        samples = read_thermal(ROOT / "data/tclab_apmonitor" / dataset)
        times = [float(r["time"]) for r in samples]
        for channel, color, style in ((0, "#007f88", "-"), (1, "#bd572c", "--")):
            axes[i, 0].plot(times, [float(r["T"][channel]) for r in samples], color=color, linestyle=style, label=f"Temperature {channel + 1}")
            axes[i, 1].step(times, [100 * float(r["Q"][channel]) for r in samples], where="post", color=color, linestyle=style, label=f"Heater {channel + 1}")
        if i == 0:
            for ax in axes[i]:
                ax.axvline(times[100], color="#4c5860", linestyle=":")
                ax.axvline(times[140], color="#4c5860", linestyle=":")
                ax.axvspan(times[0], times[100], color="#bac5cb", alpha=.15)
            axes[i, 0].set_title("Measured 3-second record / training, calibration, holdout")
        else:
            axes[i, 0].set_title("Measured 1-second record / separate acquisition replay")
        axes[i, 0].set(xlabel="Actual elapsed time (s)", ylabel="Temperature (C)")
        axes[i, 1].set(xlabel="Actual elapsed time (s)", ylabel="Logged heater command (%)", ylim=(-3, 103))
        axes[i, 0].legend(fontsize=8)
        axes[i, 1].legend(fontsize=8)
    fig.savefig(assets / "measured-thermal-records.png", dpi=160)
    fig.savefig(assets / "measured-thermal-records.pdf")
    plt.close(fig)

    def group(dataset, variation="nominal", handling="aware"):
        return next(g for g in summary["groups"] if (g["dataset"], g["variation"], g["handling"]) == (dataset, variation, handling))
    table = []
    for dataset, label in zip(datasets, ("Same-record holdout", "Other acquisition")):
        for variation in VARIATIONS:
            for handling in ("naive", "aware"):
                g = group(dataset, variation, handling)
                table.append(f'| {label} | {variation} | {handling} | {g["cases"]} | {g["inconsistent"]} | {g["silent_failure"]} | {g["uninformative"]} | {g["input_assumptions_hold"]} |')
    same, other = group(datasets[0]), group(datasets[1])
    naive = sum(r["silent_failure"] == "True" for r in records if r["handling"] == "naive")
    aware = sum(r["silent_failure"] == "True" for r in records if r["handling"] == "aware")
    text = f'''# Measured acquisitions and failure cases

Research date: 5 November 2026. **The empirical model does not transfer reliably to the second acquisition.** Correct sensor handling prevents specific acquisition mistakes, but can also produce intervals too wide to support a useful answer. This is a negative-results study, not real-world validation of accurate source reconstruction.

## Data actually used

We downloaded and pinned two upstream-reported hardware TCLab records from [APMonitor/arduino](https://github.com/APMonitor/arduino/tree/f36e65a70dd7122d1829883899e40e56bf6c4279), under Apache 2.0. There are 201 and 599 original rows (800 total), with two temperatures and two logged heater commands. The files retain original bytes, Git blob IDs and SHA-256 hashes; see [source notice](../data/tclab_apmonitor/NOTICE.md) and [provenance](../data/tclab_apmonitor/provenance.json). Acquisition documentation uses the hardware `TCLab()` class. We did not operate a device or independently establish the instrument's calibration or whether both records came from the same unit.

![Original recorded temperatures and commands](../assets/measured-thermal-records.png)

The original measured temperatures are used directly. Faults below are counterfactual modifications of those records, not claims that the upstream experiment had those labeled faults. Heater-command percentages are evaluation references; they are not independently measured heat flux or temperature-field ground truth.

## Frozen identification and evaluation contract

Fit a two-output empirical ARX model to temperature **rates**, using current temperature, previous measured rate, a constant, and both heater commands. Coefficients are fitted on transitions 1..99 of the 201-row record, then rounded to rational values. The residual-rate budget for each temperature is the **maximum absolute residual on transitions 100..139**, not a proved hardware noise bound. Frozen budgets are {float(F(model["residual_rate_bounds"][0])):.6f} and {float(F(model["residual_rate_bounds"][1])):.6f} C/s. The training design condition number is {model["training_design_condition_number"]:.1f}.

Evaluate seven nonoverlapping 8-transition windows beginning at indices 140,148,...,188 of that record, plus 25 windows beginning at 1,25,...,577 of the separate 599-row acquisition. No held-out command labels fit the coefficients or budgets. Adjacent splits share boundary temperature states, and windows/fault replays are correlated. The data comprise two acquisition files, not a population of independently calibrated instruments.

For each window, the unknowns are 16 command fractions in [0,1], two heaters per transition. The query is the mean heater-1 command. Logged elapsed time is used without resampling. Recorded temperatures form the measured right-hand side; heater commands enter that reconstruction only as hidden evaluation references. The empirical model and every case are retained in `results/acquisition`.

## Acquisition handling

The adapter supports stable row IDs, individual noise budgets, positive gain intervals, offset intervals, elementwise operator-error bounds, missing rows, and one-sided saturation. It never replaces a missing measurement with zero. Independent calibration intervals relax correlations between repeated temperatures and can be conservative.

For each window we compare naive handling with metadata-aware handling under ten declared conditions:

| Replay | Injected change | Aware handling |
|---|---|---|
| nominal | No injected fault; actual irregular sampling remains | Use logged times and channels |
| gain | T1 gain 1.03; T2 gain 0.97 | Declared gain ranges [1.02,1.04], [0.96,0.98] |
| offset_drift | Linear drift up to +0.8/-0.6 C | +/-1 C offset intervals |
| dropout | Four T1 samples per 24-sample burst | Missing/censored intervals; no zero fill |
| quantization | Nearest 0.5 C | +/-0.25 C quantization cells |
| saturation | Upper rail 40 C | One-sided temperature bounds |
| clock_scale | Recorded clock stretched by 10% | Known clock-scale correction |
| channel_swap | Temperature array order swapped | Stable channel labels restore order |
| stale_sample | T1 repeats a two-sample-old reading | Age flag marks T1 unavailable |
| out_of_budget | +/-3 C offsets | Only +/-0.2 C declared: specification intentionally false |

The “aware” arm receives declared calibration/quality metadata, not a learned fault diagnosis. It does not know source commands. Offline `input_assumptions_hold` audits use the unmodified record to check the injected sensor assumptions; they would not be available for an unknown live fault. `baseline_model_budget_holds` separately checks the original empirical model envelope before faults are added. Neither audit should be confused with an online detector.

## Measured outcomes

The completed run has **{summary["cases"]} replay cases and {summary["certificates"]} exact certificates**, with {summary["search_failures"]} unclassified numerical search failures. An inconsistency is reported only with an exactly checked boxed Farkas contradiction. A bounded case retains both endpoint certificates, even when it excludes the reference mean. A width >=0.99 is explicitly reported as practically uninformative relative to the unit prior range.

![Failure outcomes by record and handling](../assets/acquisition-failures.png)

Without injected faults, the same-record holdout has **{same["inconsistent"]}/{same["cases"]} inconsistent windows**. Of {same["bounded"]} bounded windows, {same["uninformative"]} have width >=0.99. On the separate acquisition, **{other["inconsistent"]}/{other["cases"]} windows are inconsistent**, and the full logged command vector is admissible in only {other["reference_feasible"]}/{other["cases"]}. A query mean can fall inside a wide interval even when the full reference vector violates the model; query coverage alone does not validate the physics.

Across counterfactual replays, naive handling has {naive} bounded intervals excluding the reference mean, and aware handling has {aware}. These are descriptive counts for matched, correlated cases, not general failure probabilities. Aware handling need not reduce every failure count: dropping contradictory information can reveal a feasible but wrong model that was previously rejected. Wider intervals can hide a misspecified sensor budget. In particular, the deliberately exceeded offset specification must not be called valid merely because its interval is nonempty.

| Record | Variation | Handling | Cases | Proved inconsistent | Bounded mean excluded | Width >=0.99 | Input assumptions hold |
|---|---|---|---:|---:|---:|---:|---:|
{chr(10).join(table)}

## What is fixed and what remains open

The implementation now preserves channel identity, propagates known calibration/censoring information, rejects malformed acquisitions, distinguishes exact inconsistency from solver failure, and retains silent exclusions instead of hiding them. Exact checking verifies statements about the **encoded** inverse problem. It does not establish that the ARX model, instrument calibration, or empirical residual envelope is correct.

Transfer changes sampling cadence, operating temperatures and input schedules together; this study cannot attribute failure to a single cause. The model uses lagged rates without a continuous latent heater-state model. No actual acquisition of a new minimax-selected thermometer was performed. Better transfer needs a cadence-consistent dynamical model, additional independent hardware runs, explicit latent/state uncertainty, and justified instrument/model discrepancy bounds. Budgets must be chosen without using the target test labels.

## Reproduce and inspect

```bash
python -m inverse_witness.cli acquisition --output results/new-acquisition --data data/tclab_apmonitor
python -S scripts/verify_acquisition.py results/new-acquisition
python -m unittest discover -s tests -v
```

The standard-library verifier checks pinned raw-data hashes, frozen model and acquisition binding, rational endpoint/inconsistency proofs, source-reference audits, case completeness, CSV metrics and group summaries. It shares the declared forward-model construction with the producer; it is an independent arithmetic replay, not external validation of the model or source provenance. The completed local run took {summary["seconds"]:.1f} seconds; this is not a controlled performance comparison. Code is MIT; imported and derived measured-data records retain Apache-2.0 attribution.
'''
    (ROOT / "paper/ACQUISITION_STUDY.md").write_text(text, encoding="utf-8", newline="\n")
    print("Wrote acquisition figures and paper/ACQUISITION_STUDY.md")


if __name__ == "__main__":
    main()
