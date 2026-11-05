# Measured thermal acquisitions

Source: [APMonitor/arduino](https://github.com/APMonitor/arduino), commit `f36e65a70dd7122d1829883899e40e56bf6c4279`. Upstream license: **Apache 2.0**, retained in `LICENSE`. The repository's hardware documentation and acquisition script describe two heaters, two temperature channels, USB acquisition through `TCLab()`, and actual elapsed time. These records are used as upstream-reported experimental data; we did not operate the device, independently verify its calibration, or establish that the two records came from the same physical unit.

The original bytes are preserved. `provenance.json` records the upstream path, immutable Git blob ID, and SHA-256 of every imported file. `README.upstream.md` is the upstream project description. `generate_data.py.txt` and `mimo_fit.py.txt` are documentation copies and are never executed by this project. A source script is provenance context, not proof that its current version generated every supplied record.

| Local file | Upstream source | Shape |
|---|---|---|
| `second_order_data.csv` | `2_Regression/2nd_order_MIMO/GEKKO/data.txt` | 201 rows, 5 columns; approximately 3-second sampling |
| `mimo_data.csv` | `2_Regression/Energy_balance_MIMO/Python_minimize/data.txt` | 599 rows, 7 columns; approximately 1-second sampling |

The first five columns are elapsed seconds, heater-1 command percent, heater-2 command percent, temperature-1 Celsius, and temperature-2 Celsius. The additional columns in the longer record are setpoints. Recorded commands are evaluation references, not independently calibrated heat-input measurements.

Inverse Witness code remains MIT. These imported records, documentation copies, and derived measured-data replay records retain Apache-2.0 attribution. The source license and source notices must accompany redistribution. Counterfactual gain, offset, dropout, quantization, saturation, clock, channel-swap and stale-sample faults are added by this project's replay; they are not labeled faults observed in the original experiment.
