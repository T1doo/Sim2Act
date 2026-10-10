"""Offline status-only checks; run with unittest, never load business conftest/fixtures."""

import contextlib
import importlib.abc
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx
import psutil

from sim2act.config import Settings
from sim2act.status_report import collect_status

SECRET = "SYNTHETIC_PRIVATE_SENTINEL"
HEALTH = {
    "api": "UP", "database": "UP", "worker": "UP",
    "mode": "MOCK", "live_acceptance": "BLOCKED",
}
RECORDS = [
    {"kind": "api", "pid": 101, "created_at": 100.0, "port": 8000},
    {"kind": "worker", "pid": 102, "created_at": 100.0,
     "command": ["synthetic-python", "-m", "sim2act.worker"]},
]
ROOT = Path(__file__).resolve().parents[1]


class StatusReportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="状态 diagnostics ")
        self.addCleanup(self.temp.cleanup)
        self.state = Path(self.temp.name) / "processes.json"
        self.write_state(RECORDS)

    def write_state(self, records):
        self.state.write_text(json.dumps(records), encoding="utf-8")

    def collect(self, response=None, observations=None, error=None):
        response = response if response is not None else httpx.Response(200, json=HEALTH)
        seen = []
        calls = []

        def handler(request):
            calls.append((request.method, str(request.url)))
            if error is not None:
                raise error
            return response

        def observe(record):
            seen.append(record["kind"])
            result = observations[record["kind"]] if observations else object()
            if isinstance(result, Exception):
                raise result
            return result

        with httpx.Client(transport=httpx.MockTransport(handler), trust_env=False) as client:
            report = collect_status(
                self.state, observe, lambda: client.get("http://127.0.0.1:8000/health")
            )
        self.assertEqual(calls, [("GET", "http://127.0.0.1:8000/health")])
        self.assertNotIn(SECRET, json.dumps(report))
        return report, seen

    def test_healthy_response_reports_each_component_and_local_identity(self):
        for mode in ("MOCK", "LIVE"):
            with self.subTest(mode=mode):
                report, seen = self.collect(httpx.Response(200, json={**HEALTH, "mode": mode}))
                self.assertEqual(report["health_check"], {
                    "status": "HEALTHY", "api": "UP", "database": "UP",
                    "worker": "UP", "http_status": 200,
                })
                self.assertEqual(report["health"]["live_acceptance"], "BLOCKED")
                self.assertEqual(seen, ["api", "worker"])
                for kind in ("api", "worker"):
                    self.assertTrue(report[kind]["alive"])
                    self.assertEqual(report[kind]["identity"], "VERIFIED")

    def test_connection_and_timeout_failures_are_sanitized_and_unknown(self):
        for error in (httpx.ConnectError(SECRET), httpx.ReadTimeout(SECRET),
                      httpx.RemoteProtocolError(SECRET)):
            with self.subTest(error=type(error).__name__):
                report, _ = self.collect(error=error)
                self.assertEqual(report["health"], "OFFLINE")
                self.assertEqual(report["health_check"]["status"], "CONNECTION_FAILED")
                self.assertEqual(report["health_check"]["api"], "OFFLINE")
                self.assertEqual(report["health_check"]["database"], "UNKNOWN")
                self.assertEqual(report["health_check"]["worker"], "UNKNOWN")
                self.assertTrue(report["api"]["alive"])

    def test_non_success_http_is_classified_before_json_parsing(self):
        for code in (301, 401, 404, 500, 503):
            with self.subTest(code=code):
                response = httpx.Response(code, text=SECRET)
                with patch.object(response, "json", side_effect=AssertionError("do not parse")):
                    report, _ = self.collect(response)
                self.assertEqual(report["health_check"]["status"], "HTTP_ERROR")
                self.assertEqual(report["health_check"]["http_status"], code)
                self.assertEqual(report["health_check"]["database"], "UNKNOWN")
                self.assertEqual(report["health_check"]["worker"], "UNKNOWN")
        report, _ = self.collect(httpx.Response(503, json=HEALTH))
        self.assertEqual(report["health"], "OFFLINE")

    def test_invalid_json_and_encoding_do_not_exit_or_echo_content(self):
        for body in (b"", SECRET.encode(), b"\xff", b'{"api":"UP"', b"[" * 2000):
            with self.subTest(body_size=len(body)):
                report, _ = self.collect(httpx.Response(200, content=body))
                self.assertEqual(report["health_check"]["status"], "INVALID_JSON")
                self.assertEqual(report["health"], "OFFLINE")

    def test_invalid_response_structures_and_enums_never_report_up(self):
        payloads = [None, [], True, SECRET, {}, {"api": "UP"}]
        for key in HEALTH:
            payloads.append({k: value for k, value in HEALTH.items() if k != key})
            for value in (None, True, [], {}, SECRET):
                payloads.append({**HEALTH, key: value})
        payloads.extend([{**HEALTH, "api": "OFFLINE"}, {**HEALTH, "database": "OFFLINE"},
                         {**HEALTH, "worker": "STALE"}, {**HEALTH, "live_acceptance": "PASS"}])
        for payload in payloads:
            with self.subTest(payload_type=type(payload).__name__):
                # json=None means no body in httpx; encode JSON null explicitly.
                report, _ = self.collect(httpx.Response(200, content=json.dumps(payload)))
                self.assertEqual(report["health_check"]["status"], "INVALID_STRUCTURE")
                self.assertEqual(report["health_check"]["api"], "UNKNOWN")
                self.assertEqual(report["health_check"]["database"], "UNKNOWN")
                self.assertEqual(report["health_check"]["worker"], "UNKNOWN")

    def test_worker_offline_is_separate_from_verified_local_process(self):
        report, _ = self.collect(httpx.Response(200, json={**HEALTH, "worker": "OFFLINE"}))
        self.assertEqual(report["health_check"]["status"], "WORKER_OFFLINE")
        self.assertEqual(report["health"]["worker"], "OFFLINE")
        self.assertEqual(report["health_check"]["database"], "UP")
        self.assertEqual(report["worker"]["identity"], "VERIFIED")

    def test_api_health_never_overrides_failed_or_unknown_local_identity(self):
        observations = {"api": None, "worker": RuntimeError(SECRET)}
        before = self.state.read_bytes()
        report, _ = self.collect(observations=observations)
        self.assertEqual(report["health_check"]["status"], "HEALTHY")
        self.assertEqual(report["api"]["alive"], False)
        self.assertEqual(report["api"]["identity"], "NOT_VERIFIED")
        self.assertIsNone(report["worker"]["alive"])
        self.assertEqual(report["worker"]["identity"], "UNVERIFIABLE")
        self.assertEqual(self.state.read_bytes(), before)

    def test_extra_response_fields_and_process_details_are_discarded(self):
        self.write_state([{**record, "token": SECRET, "connection": SECRET} for record in RECORDS])
        report, _ = self.collect(httpx.Response(200, json={**HEALTH, "token": SECRET, "detail": SECRET}))
        self.assertEqual(report["health"], HEALTH)
        self.assertEqual(set(report["worker"]), {"pid", "alive", "identity"})

    def test_missing_empty_and_partial_state_do_not_invent_local_processes(self):
        for records in (None, [], RECORDS[:1]):
            with self.subTest(records=records):
                if records is None:
                    self.state.unlink(missing_ok=True)
                else:
                    self.write_state(records)
                report, seen = self.collect()
                self.assertEqual(seen, [] if not records else ["api"])
                self.assertEqual(report["worker"], {
                    "pid": None, "alive": None, "identity": "NOT_RECORDED",
                })
                self.assertEqual(report["process_state"], "MISSING" if records is None else "VALID")
                self.assertEqual(report["health_check"]["status"], "HEALTHY")

    def test_invalid_state_is_preserved_and_never_passed_to_process_verifier(self):
        records = [None, {}, SECRET, [None], RECORDS * 2,
                   [RECORDS[0], RECORDS[0]], [{**RECORDS[0], "kind": SECRET}]]
        for key, value in (("pid", True), ("pid", -1), ("pid", 10 ** 400), ("created_at", SECRET),
                           ("created_at", float("nan")), ("created_at", 10 ** 400),
                           ("command", SECRET), ("command", [True]), ("port", True)):
            records.append([{**RECORDS[0], key: value}])
        for item in records:
            with self.subTest(item_type=type(item).__name__):
                self.write_state(item)
                before = self.state.read_bytes()
                report, seen = self.collect()
                self.assertEqual(seen, [])
                self.assertEqual(report["process_state"], "INVALID_STRUCTURE")
                self.assertEqual(report["worker"]["identity"], "UNVERIFIABLE")
                self.assertEqual(self.state.read_bytes(), before)
        for content in (SECRET.encode(), b"\xff", b"[" * 2000):
            self.state.write_bytes(content)
            report, seen = self.collect()
            self.assertEqual(seen, [])
            self.assertEqual(report["process_state"], "INVALID_JSON")
            self.assertEqual(self.state.read_bytes(), content)

    def test_unreadable_state_does_not_suppress_health_or_leak_path(self):
        with patch.object(Path, "read_text", side_effect=PermissionError(SECRET)):
            report, seen = self.collect()
        self.assertEqual(seen, [])
        self.assertEqual(report["process_state"], "UNREADABLE")
        self.assertEqual(report["health_check"]["status"], "HEALTHY")

    def test_manager_status_uses_existing_identity_checks_without_business_imports(self):
        spec = importlib.util.spec_from_file_location("status_manager", ROOT / "scripts/manage.py")
        manager = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(manager)

        class SyntheticProcess:
            def __init__(self, pid):
                self.pid = pid

            def is_running(self):
                return True

            def status(self):
                return psutil.STATUS_RUNNING

            def create_time(self):
                return 100.0

            def cmdline(self):
                # API matches legacy argv; worker is a reused/mismatched PID.
                if self.pid == 101:
                    return [sys.executable, "-m", "uvicorn", "sim2act.api:create_app",
                            "--factory", "--host", "127.0.0.1", "--port", "8000", "--no-access-log"]
                return ["unrelated", SECRET]

        class NoBusinessImports(importlib.abc.MetaPathFinder):
            def find_spec(self, fullname, path=None, target=None):
                if fullname in {"sim2act.api", "sim2act.worker", "sim2act.db", "sim2act.process_env"}:
                    raise AssertionError("Status must not load " + fullname)

        calls = []

        def handler(request):
            calls.append(request.url.path)
            return httpx.Response(200, json=HEALTH)

        before = self.state.read_bytes()
        with httpx.Client(transport=httpx.MockTransport(handler), trust_env=False) as client:
            with (patch.object(Settings, "from_env", return_value=Settings("synthetic", self.state.parent)),
                  patch.object(manager.psutil, "Process", SyntheticProcess),
                  patch.object(manager.httpx, "get", side_effect=client.get),
                  patch.object(sys, "argv", ["manage.py", "status"]),
                  patch.object(sys, "meta_path", [NoBusinessImports(), *sys.meta_path]),
                  contextlib.redirect_stdout(io.StringIO()) as output):
                manager.main()
        report = json.loads(output.getvalue())
        self.assertTrue(report["api"]["alive"])
        self.assertFalse(report["worker"]["alive"])
        self.assertEqual(report["worker"]["identity"], "NOT_VERIFIED")
        self.assertEqual(report["health_check"]["worker"], "UP")
        self.assertEqual(calls, ["/health"])
        self.assertEqual(self.state.read_bytes(), before)
        self.assertNotIn(SECRET, output.getvalue())
        self.assertTrue(all(name not in sys.modules for name in (
            "sim2act.api", "sim2act.worker", "sim2act.db", "sim2act.process_env",
        )))


if __name__ == "__main__":
    unittest.main()
