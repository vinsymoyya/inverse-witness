# Inverse Witness

**Check what the measurements leave ambiguous. Choose the next measurement with a verifiable bound.**

Inverse Witness is a small physics–math research toolkit for bounded linear inverse problems. It returns conflicting admissible source fields, a checked interval for the quantity you care about, and a minimax choice among candidate next measurements.

![Two admissible sources explain the current thermometers; candidate next sensors are ranked by remaining ambiguity](assets/ambiguity-demo.png)

**Research status:** synthetic pilot plus a measured-acquisition failure study, external scientific review pending. The theory builds on strict bounds, optimal recovery and worst-case sensor design. Accurate reconstruction across real acquisitions is not established.

## Measured acquisitions and failure cases

The [new study](paper/ACQUISITION_STUDY.md) uses **800 original rows from two public TCLab hardware records**, with pinned source hashes and an Apache 2.0 data license. It evaluates 640 correlated replay cases across calibration errors, missing samples, quantization, saturation, clock errors, channel swaps and stale readings. Injected faults are labeled separately from the original measured data.

The result is a warning about model transfer: the frozen empirical model is inconsistent in **24/25 windows of the separate acquisition**. Metadata-aware handling can preserve admissibility by widening bounds, but many then become uninformative. The software retains these failures and verifies 912 endpoint or inconsistency certificates.

![Measured acquisition failure cases](assets/acquisition-failures.png)

From this checkout:

```bash
python -m inverse_witness.cli acquisition --output results/my-acquisition --data data/tclab_apmonitor
python -S scripts/verify_acquisition.py results/acquisition
```

For custom bounded linear acquisitions, use `compile_acquisition` and `interval_acquisition`. Observations bind by stable row IDs and may contain one-sided intervals, per-row noise, positive gain/offset ranges and operator-error bounds. Source coordinates still belong to `[0,1]`. An inconsistent acquisition raises `InfeasibleProblem` carrying an exactly checkable contradiction. See [data and calibration assumptions](DATA_CARD.md).

## Run the example

From a checkout, with Python 3.10 or later:

```bash
python -m pip install -e .
python -m inverse_witness.cli demo --output results/my-demo
python -m inverse_witness.cli verify results/my-demo/query-upper.json --max-gap 1/1000000
```

The demo solves a continuous steady heat-source inverse problem for a declared 16-cell source class. Four thermometer readings allow different sources. The next thermometer is selected before its reading is known. Files are written to a fresh directory; an existing result directory is never overwritten.

**Verify a published certificate without the optimizer or scientific packages:**

```bash
python -S -m inverse_witness.cli verify results/demo/query-upper.json --max-gap 1/1000000
python -S scripts/verify_results.py results/pilot
```

The checker uses exact rational arithmetic from the standard library. It checks feasibility and a dual-derived objective bound. The full replay also binds certificates to the declared physical instances and compares saved sensor scores.

## What is measured

Read the [actual pilot results](paper/RESULTS.md) and [methods and proofs](paper/METHODS.md). The benchmark includes continuous heat-source inversion, a grounded resistor network, three scalar queries, two bounded-noise levels, and a controlled source-distribution shift. Five sensor policies share the same data and candidate budget. A small random-feature learned baseline illustrates the difference between distribution-dependent intervals and physical admissibility.

![Measured pilot comparisons, with correlated-instance scope stated](assets/pilot-results.png)

All original synthetic data, exact certificate brackets, source vectors, configurations and evaluation rows are retained. Review the [data card](DATA_CARD.md) before extending the claims. The benchmark evaluates minimax on the criterion it explicitly optimizes; it is not evidence of superiority on every objective.

## Bring a linear physics operator

```python
from fractions import Fraction as F
from inverse_witness.solver import interval, choose_sensor

A, y, epsilon = [[F(1), F(1)]], [F(1)], F(1, 10)
c = [F(1), F(0)]  # Ask for the first bounded source.
answer = interval(A, y, epsilon, c)
decision = choose_sensor(A, y, epsilon, c,
                         [[F(1), F(0)], [F(1), F(1)]], F(1, 20))
print(answer["lower"], answer["upper"])
print(decision["selected"], decision["regret_upper"])
```

Here every source coordinate belongs to `[0,1]`. The first candidate resolves the requested coordinate more effectively than repeating the source sum. Inputs are exact integers, fractions or rational strings. To use another source box, explicitly transform its variables and offset the readings and query.

The public optimization API supports bounded linear operators, scalar linear queries and a finite list of single-row candidates. Degenerate instances may fail the numerical certificate search; a failure raises an error. The exact checker can still check a valid certificate obtained by another search procedure.

## Reproduce the research

```bash
python -m unittest discover -s tests -v
python -m inverse_witness.experiment --output results/new-pilot --seeds 4
python -S scripts/verify_results.py results/new-pilot
python -m pip install -e ".[figures]"
python scripts/make_figures.py --pilot results/new-pilot --demo results/my-demo
```

The declared pilot has 96 correlated query instances from 16 distinct test sources. Test sources are separate from training, tuning and calibration sources. See the run's configuration and environment record for exact versions and hashes. Running the full experiment regenerates the scientific result; checking a saved certificate is much cheaper.

## Research and participation

- [Opportunity analysis and adoption strategy](research/MARKET_RESEARCH.md)
- [Original synthetic-pilot technical note, v0.1](output/pdf/inverse-witness-technical-note.pdf)
- [Measured-acquisition study, v0.2](paper/ACQUISITION_STUDY.md)
- [Contribution guide](CONTRIBUTING.md): new operators, counterexamples, independent reproductions and learned sensor policies
- [Publication and ORCID route](PUBLICATION.md)

The useful next research target is a fast learned measurement policy with certified regret on held-out operators. It has not been trained here. New nonlinear or experimental data needs its own validity argument.

**Author:** Vinsy Moyya · [ORCID](https://orcid.org/0009-0003-0042-3556). Code and original synthetic records: [MIT](LICENSE). Imported and derived measured-data records retain [Apache-2.0 attribution](data/tclab_apmonitor/NOTICE.md). Cite via [CITATION.cff](CITATION.cff), and separately credit the datasets and established methods.
