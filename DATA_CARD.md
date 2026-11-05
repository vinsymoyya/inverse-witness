# Data and certificate card

The original `results/pilot` study is synthetic, with code and generated synthetic records under MIT. The measured-acquisition extension additionally redistributes two pinned upstream-reported TCLab hardware records from APMonitor/arduino, under Apache 2.0. Their original bytes, upstream license, attribution, Git blob IDs and SHA-256 hashes are retained in `data/tclab_apmonitor`. Derived measured-data replay records retain the upstream attribution. No personal data or pretrained weights are included. Cited literature retains its own copyright.

## Measured replay

The files contain 201 and 599 rows of elapsed time, heater commands and two measured temperatures. One also contains setpoints. Acquisition documentation uses hardware `TCLab()` reads. We did not operate the device or independently verify calibration, common device identity or a traceable heat-input reference. Logged heater commands are the evaluation reference; they are not independently measured heat flux.

Only the 201-row record fits the empirical model: transitions 1..99 train coefficients, 100..139 set maximum calibration residual budgets, and windows starting at 140 or later evaluate a chronological holdout. The 599-row record is an additional acquisition used only for evaluation. Boundary temperature states are shared across adjacent time blocks, and all replay variations of a window are correlated. Two files are not a population of independent devices.

Original measurements are never replaced by generated temperatures. Added gain, drift, dropout, quantization, saturation, timing, channel-order, stale-reading and exceeded-specification faults are explicit counterfactual replay. The aware arm receives declared metadata; it is not an autonomous fault-diagnosis system. The offline audit can compare declarations with the unmodified record; a deployed system would not have that reference.

The empirical ARX residual envelope is not a verified instrument or model-discrepancy bound. The negative-results study retains inconsistent acquisitions, broad uninformative bounds, and bounded intervals excluding the logged mean. A feasible interval or mean coverage does not establish correct calibration or a valid full-state model. No new measurement selected by the minimax policy was acquired on hardware.

## Original synthetic pilot

The 16-dimensional source box is a physical assumption in nondimensional units. The heat example assumes piecewise-constant sources, exact boundary conditions, unit coefficients and specified sensor locations. The resistor example assumes exact unit conductances and known grounding. Noise is bounded and generated independently within its budget. Data do not validate any real instrument, diagnostic task or material.

Smooth sources define the learned baseline's training, tuning and calibration distribution. Shifted sources are nearly binary and sparse, while remaining inside the same box. They are intentionally a distribution shift. The certificate uses physical bounds, not the training distribution. Its validity remains conditional on those physical bounds and the forward operator.

Training/tuning/calibration source seeds are separate from test seeds. The 96 query instances reuse 16 test sources across noise levels and queries; treat them as correlated. Source vectors, readings, query coefficients and compressed certificate hashes are in `results/pilot/sources.json`; the full run declaration is `results/pilot/config.json`.

The exact checker verifies rational claims for encoded finite problems. End-to-end replay must also bind certificates to the declared physical operator, readings, noise and query. A checked JSON file alone does not validate the physical modeling assumptions.
