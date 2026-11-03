# Contribute a checkable result

Useful contributions include a physically justified bounded linear operator, a counterexample to a sensing heuristic, a better certificate search, a scalability measurement, or a reproduction of the released results.

1. State the source domain, units, boundary conditions, sensor budget, noise assumptions and requested quantity.
2. Keep training and evaluation sources disjoint. If sources repeat across queries or noise levels, report the dependence.
3. Save admissible conflicting states and a verified certificate. Separate numerical search from exact checking.
4. Compare on identical sensor candidates and noise budgets. Report ties, solver failures, runtime, and unfavorable cases.
5. Run `python -m unittest discover -s tests -v` and the relevant result-replay command.

Small cases that falsify a claim are valuable. A real instrument requires justified model-error bounds. Do not describe a discrete or restricted-source certificate as a universal continuum theorem.

The project welcomes adapters to existing inverse libraries. Please discuss the physical contract before adding large dependencies or pretrained weights.
