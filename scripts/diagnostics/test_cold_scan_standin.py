"""Pure-data mutation/alias regressions, without Sim2Act or archived DB access."""

import hashlib
import sys
import unittest

from cold_scan_standin import encode, measure


class StandinUnits(unittest.TestCase):
    def tearDown(self):
        self.assertFalse(any(k == "sim2act" or k.startswith("sim2act.") for k in sys.modules))

    def test_deep_field_mutation_is_seen_on_each_full_scan(self):
        shared = {"payload": ["original", b"wire\x00"]}
        graph = {"source": shared, "again": shared}
        original = hashlib.sha256(encode(graph)).digest()
        shared["payload"][0] = "changed"
        self.assertNotEqual(hashlib.sha256(encode(graph)).digest(), original)
        shared["payload"][0] = "original"
        self.assertEqual(hashlib.sha256(encode(graph)).digest(), original)
        shared["extra-field"] = None
        self.assertNotEqual(hashlib.sha256(encode(graph)).digest(), original)

    def test_equal_fields_with_different_alias_structure_are_not_collapsed(self):
        shared = {"x": [1, 2]}
        aliased = [shared, shared]
        duplicated = [{"x": [1, 2]}, {"x": [1, 2]}]
        self.assertEqual(aliased, duplicated)
        self.assertNotEqual(encode(aliased), encode(duplicated))

    def test_measured_pipeline_remains_a_calibration_without_speedup_claim(self):
        values = {"complete": [b"wire", "本地", {"nested": None}]}
        result = measure(values, 3)
        self.assertEqual(result["sha256"], hashlib.sha256(encode(values)).hexdigest())
        self.assertEqual(result["serialized_bytes"], len(encode(values)))
        self.assertEqual(result["iterations"], 3)
        self.assertGreaterEqual(result["serialization_seconds"], 0)
        self.assertGreaterEqual(result["digest_seconds"], 0)
        self.assertFalse(result["predicts_G0_speedup"])
        for count in (0, -1, True):
            with self.assertRaises(ValueError):
                measure(values, count)


if __name__ == "__main__":
    unittest.main()
