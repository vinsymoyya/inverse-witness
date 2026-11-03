# Validation evidence — version 0.1.0

Local results recorded on 3 November 2026. Scientific conclusions remain limited to the declared synthetic experiment.

| Requirement | Fresh evidence | Result |
|---|---|---|
| Rational checker rejects invalid claims | `python -S -m unittest discover -s tests -p test_exact.py -v` | 8 tests passed, including a violation of size 1e-18, negative multipliers, wrong dimensions and modified claims. |
| Physical operator and next-measurement contracts | `python -m unittest discover -s tests -v` | 19 tests passed. Includes analytic continuum temperatures, Kirchhoff identities, an independently enumerated polygon optimum, scalar intervals, and common future readings. |
| End-to-end ambiguity example | `python -m inverse_witness.cli demo --output results/demo` | Selected s=19/32. Initial query width 0.377848; worst-case next width 0.108417; realized width 0.076623. |
| Complete declared experiment | `python -m inverse_witness.experiment --output results/pilot --seeds 4` | 96 query instances; 480 policy rows; 2,146 certificate brackets; full output retained. |
| Solver-independent replay and physical binding | `python -S scripts/verify_results.py results/pilot` | All 2,146 brackets verified with zero third-party dependencies. Reconstructed physical instances and CSV sensor scores matched. Maximum exact optimization gap was less than 1e-6. |
| Figure and PDF output | `python scripts/make_figures.py`; `python scripts/build_paper.py`; `python scripts/inspect_pdf.py` | Figures inspected. Six-page PDF rendered and visually inspected; automated text-boundary check found no margin violations. |

The expected-value tests use analytic solutions or independent finite enumeration, rather than only checking agreement between the optimizer and itself. Rational primal feasibility and the box-support inequality establish objective brackets even when the floating-point optimizer is inexact.

The pilot uses only 16 distinct test sources, reused across noise levels and queries. The 96 query instances are correlated. No statistical significance or frontier-model comparison is claimed. All 96 initial physical intervals contain their simulated truth by construction under the declared assumptions; this is an implementation check, not universal real-world coverage evidence.

Package and hosted-CI results are reported with the tagged GitHub release. A local check alone does not establish that a hosted job passed. There is no external scientific review, real-instrument validation, journal acceptance, DOI, or ORCID work update implied by this file.
