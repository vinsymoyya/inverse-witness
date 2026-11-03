# Synthetic data and certificate card

All experiment data are generated locally by the original code in this repository. No third-party measurements, licensed image collections, personal data or pretrained weights are redistributed. Code and generated synthetic numerical records are released under MIT. Cited literature retains its own copyright.

The 16-dimensional source box is a physical assumption in nondimensional units. The heat example assumes piecewise-constant sources, exact boundary conditions, unit coefficients and specified sensor locations. The resistor example assumes exact unit conductances and known grounding. Noise is bounded and generated independently within its budget. Data do not validate any real instrument, diagnostic task or material.

Smooth sources define the learned baseline's training, tuning and calibration distribution. Shifted sources are nearly binary and sparse, while remaining inside the same box. They are intentionally a distribution shift. The certificate uses physical bounds, not the training distribution. Its validity remains conditional on those physical bounds and the forward operator.

Training/tuning/calibration source seeds are separate from test seeds. The 96 query instances reuse 16 test sources across noise levels and queries; treat them as correlated. Source vectors, readings, query coefficients and compressed certificate hashes are in `results/pilot/sources.json`; the full run declaration is `results/pilot/config.json`.

The exact checker verifies rational claims for encoded finite problems. End-to-end replay must also bind certificates to the declared physical operator, readings, noise and query. A checked JSON file alone does not validate the physical modeling assumptions.
