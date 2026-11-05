from copy import deepcopy
from fractions import Fraction as F
from pathlib import Path
import tempfile
import unittest

from inverse_witness.acquisition import compile_acquisition
from inverse_witness.exact import feasible
from inverse_witness.thermal import (VARIATIONS, evaluation_windows, fit_model, make_window,
                                    read_thermal, varied_temperatures, verify_data)

DATA = Path(__file__).resolve().parents[1] / "data/tclab_apmonitor"


class ThermalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = read_thermal(DATA / "second_order_data.csv")
        cls.model = fit_model(cls.rows)

    def test_pinned_measured_data_hashes_and_dimensions(self):
        self.assertEqual(verify_data(DATA)["license"], "Apache-2.0")
        self.assertEqual(len(self.rows), 201)
        self.assertEqual(len(read_thermal(DATA / "mimo_data.csv")), 599)
        self.assertNotEqual(self.rows[1]["time"] - self.rows[0]["time"], F(3))

    def test_evaluation_labels_not_used_for_identification(self):
        changed = deepcopy(self.rows)
        for row in changed[140:]:
            row["Q"] = [F(1), F(0)]
        self.assertEqual(fit_model(changed), self.model)

    def test_window_operator_does_not_see_reference_commands(self):
        indices = list(range(140, 148))
        changed = deepcopy(self.rows)
        for k in indices:
            changed[k]["Q"] = [F(1) - v for v in changed[k]["Q"]]
        original, reference = make_window(self.rows, self.model, indices, "nominal", "aware", "second_order_data.csv")
        different, new_reference = make_window(changed, self.model, indices, "nominal", "aware", "second_order_data.csv")
        self.assertEqual(original, different)
        self.assertNotEqual(reference, new_reference)

    def test_calibration_envelope_contains_calibration_commands(self):
        for start in range(100, 140, 8):
            acquisition, reference = make_window(self.rows, self.model, list(range(start, start + 8)),
                                                 "nominal", "aware", "second_order_data.csv")
            B, b, _ = compile_acquisition(acquisition)
            self.assertTrue(feasible(B, b, reference))

    def test_aware_bounded_faults_enclose_original_temperatures(self):
        for variation in ("nominal", "gain", "offset_drift", "quantization", "saturation", "channel_swap"):
            temperatures, _ = varied_temperatures(self.rows, variation, "aware")
            for record, bounds in zip(self.rows, temperatures):
                for value, (lo, hi) in zip(record["T"], bounds):
                    self.assertTrue(lo is None or lo <= value, variation)
                    self.assertTrue(hi is None or hi >= value, variation)

    def test_clock_correction_recovers_actual_elapsed_times(self):
        _, corrected = varied_temperatures(self.rows, "clock_scale", "aware")
        self.assertEqual(corrected, [r["time"] for r in self.rows])

    def test_dropouts_and_stale_samples_are_not_zero_temperatures(self):
        dropped, _ = varied_temperatures(self.rows, "dropout", "aware")
        stale, _ = varied_temperatures(self.rows, "stale_sample", "aware")
        self.assertEqual(dropped[6][0], (None, None))
        self.assertEqual(stale[2][0], (None, None))

    def test_out_of_budget_does_not_get_artificially_repaired(self):
        intervals, _ = varied_temperatures(self.rows, "out_of_budget", "aware")
        self.assertGreater(intervals[0][0][0], self.rows[0]["T"][0])

    def test_nonoverlapping_evaluation_windows_follow_split(self):
        windows = evaluation_windows(self.rows, "second_order_data.csv")
        self.assertEqual(len(windows), 7)
        self.assertTrue(all(min(window) >= 140 for window in windows))
        self.assertEqual(len(set(k for window in windows for k in window)), 8 * len(windows))

    def test_duplicate_timestamps_rejected(self):
        temp_root = Path(__file__).resolve().parents[1] / ".cache/test-data"
        temp_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temp_root) as folder:
            path = Path(folder) / "bad.csv"
            path.write_text("Time (sec),Heater 1,Heater 2,Temperature 1,Temperature 2\n" + "0,0,0,20,20\n" * 4)
            with self.assertRaises(ValueError):
                read_thermal(path)


if __name__ == "__main__":
    unittest.main()
