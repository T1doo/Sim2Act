"""Pure-data mutation/alias regressions, without Sim2Act or archived DB access."""

import hashlib
import os
import subprocess
import sys
import unittest
from pathlib import Path

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
        self.assertIn("no production custom reducers", result["implementation"])
        for count in (0, -1, True):
            with self.assertRaises(ValueError):
                measure(values, count)

    def test_c_primitive_bytes_match_actual_production_in_isolated_process(self):
        # Product imports stay in a separate, bounded interpreter, without any
        # fixture, database, graph producer, model or transport invocation.
        code = r'''
import _pickle, pickle, socket
from unittest.mock import patch
import httpx
from cold_scan_standin import encode
from sim2act import natural_spec_runtime as runtime
from sim2act.db import Store
from sim2act.model import InternModel
from sim2act.worker import Worker
def deny(*args, **kwargs):
    raise AssertionError("C primitive comparison forbids business and network")
assert pickle.Pickler is _pickle.Pickler
assert runtime._ColdGraphPicklerBase is pickle.Pickler
shared = {"deep": ["本地", b"complete\x00", 1, 1.0, True, None]}
vectors = [None, {}, [], (), [shared, shared], [shared, {"deep": list(shared["deep"])}],
           {"source": shared, "again": shared}, {"second": 2, "first": 1},
           b"x" * 200000, [list(range(5000)), tuple(range(5000))]]
with patch.object(pickle, "_Pickler", deny), patch.object(Store, "__init__", deny), \
     patch.object(Store, "tx", deny), patch.object(Worker, "__init__", deny), \
     patch.object(Worker, "once", deny), patch.object(InternModel, "__init__", deny), \
     patch.object(socket, "getaddrinfo", deny), patch.object(socket.socket, "connect", deny), \
     patch.object(httpx.HTTPTransport, "handle_request", deny), \
     patch.object(httpx.AsyncHTTPTransport, "handle_async_request", deny), \
     patch.object(httpx.MockTransport, "handle_request", deny), \
     patch.object(httpx.MockTransport, "handle_async_request", deny):
    for value in vectors:
        assert encode(value) == runtime._cold_graph_bytes(value)
print("C_PICKLER_PRIMITIVE_BYTES_MATCH 10 vectors; no custom-reducer/G0 qualification")
'''
        repo = Path(__file__).resolve().parents[2]
        environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1",
            PYTHONPATH=os.pathsep.join((str(repo / "src"), str(Path(__file__).parent))))
        result = subprocess.run([sys.executable, "-B", "-c", code], cwd=repo,
                                env=environment, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("C_PICKLER_PRIMITIVE_BYTES_MATCH 10 vectors", result.stdout)


if __name__ == "__main__":
    unittest.main()
