"""Read-only verification of exact source, original assertions and saved receipts."""

import collections
import gzip
import hashlib
import json
import re
import statistics
import subprocess
from pathlib import Path

from sim2act.db import fingerprint

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
BASE = "48accbbea0fd90fc022abd049a92b2d6c16eeb52"
PRODUCT = "src/sim2act/protocol_jobs.py"


def read(path):
    data = path.read_bytes()
    return gzip.decompress(data) if path.suffix == ".gz" else data


def load(path):
    return json.loads(read(path))


def normalized(request):
    if request is None:
        return "outside_http"
    return re.sub(r"_[0-9a-f]{32}", "_ID", request.split(":", 1)[1])


def main():
    report = {"base": BASE, "runs": {}, "scope": "local pure-hash gain; no end-to-end claim"}
    for variant in ["baseline", "candidate", "regression"]:
        root = ROOT / variant
        manifest = load(root / "export-manifest.json")
        for row in manifest["files"]:
            path = root / row["artifact"]
            assert hashlib.sha256(path.read_bytes()).hexdigest() == row["artifact_sha256"]
            assert hashlib.sha256(read(path)).hexdigest() == row["raw_sha256"]
        result = load(root / "result.json")
        cleanup = load(root / "cleanup.json")
        assert result["complete"] and result["pytest_exit_code"] == 0
        assert cleanup["owner_label_verified"] and cleanup["owned_container_absent"]
        assert all(row["absent"] for row in cleanup["owned_volume_absence"])
        state = load(root / "state-before-cleanup.json")["state"]
        assert state["Running"] and not state["OOMKilled"]
        for name in ["census-before.json", "census-after.json"]:
            assert set(load(root / name).values()) == {0}
        before, after = [load(root / name) for name in ["source-before.json", "source-after.json"]]
        assert before == after and len(before) == 284
        mismatches = [row["path"] for row in before if not row["matches_baseline"]]
        assert mismatches == ([] if variant == "baseline" else [PRODUCT])
        for row in before:
            if variant != "baseline" or row["path"] != PRODUCT:
                assert hashlib.sha256((REPO / row["path"]).read_bytes()).hexdigest() == row["sha256"]
        phases = load(root / "phase-audit.json")
        outcomes = collections.Counter(r["outcome"] for r in phases["reports"] if r["phase"] == "call")
        assert outcomes == {"passed": 191 if variant == "regression" else 1}
        assert all(r["outcome"] == "passed" for r in phases["reports"])
        if variant == "regression":
            modules = collections.Counter(n.split("::", 1)[0] for n in phases["nodes"])
            assert modules == {
                "tests/test_protocol_jobs.py": 40,
                "tests/test_protocol_reviews.py": 43,
                "tests/test_conditional_run_bindings.py": 48,
                "tests/test_report_validated_origin.py": 23,
                "tests/test_report_manifest_apps.py": 23,
                "tests/test_protocol_recovery.py": 14,
            }
        else:
            assert phases["nodes"] == ["tests/test_report_manifest_apps_ui.py::test_report_manifest_real_http_dom"]
            driver = list((root / "fixtures").rglob("results.json"))
            assert len(driver) == 1
            receipt = load(driver[0])
            assert receipt["status"] == "PASS" and len(receipt["checks"]) == 49
            assert receipt["actual_mock_requests"] == 7
            assert receipt["live_requests"] == receipt["requests_outside_origin"] == 0
        text = read(root / "python-timeline.jsonl.gz").decode()
        events = [json.loads(line) for line in text.splitlines()]
        assert not any(e.get("sqlstate") == "40P01" for e in events)
        assert not any(e.get("status", 0) == 500 for e in events)
        hashes = load(root / "snapshot-hashes.json.gz")
        assert hashes["exitstatus"] == 0
        history = [
            row for row in hashes["rows"]
            if normalized(row["request"]) == "GET:/api/projects/proj_ID/apps/app_ID/history"
        ]
        if variant != "regression":
            assert len({row["request"] for row in history}) == 27
            assert sum(row["count"] for row in history) == (1512 if variant == "baseline" else 756)
        report["runs"][variant] = {
            "pass": sum(outcomes.values()),
            "process_wall_seconds": result["stages"][0]["wall_seconds"],
            "phases": {
                phase: sum(r["seconds"] for r in phases["reports"] if r["phase"] == phase)
                for phase in ["setup", "call", "teardown"]
            },
            "snapshot_hash_count": sum(row["count"] for row in hashes["rows"]),
            "snapshot_hash_seconds": sum(row["nanoseconds"] for row in hashes["rows"]) / 1e9,
            "fixed_27_history_hashes": sum(row["count"] for row in history),
            "export_hashes_verified": len(manifest["files"]),
            "source_hashes_verified": len(before),
        }
    frozen = subprocess.check_output(["git", "show", BASE + ":" + PRODUCT], cwd=REPO)
    expected = frozen.replace(
        b'"fingerprint": fingerprint(snapshot),',
        b'"fingerprint": (snapshot_fp := fingerprint(snapshot)),',
        1,
    ).replace(b'fingerprint(snapshot) != job["fingerprint"]', b'snapshot_fp != job["fingerprint"]', 1)
    assert (REPO / PRODUCT).read_bytes() == expected
    bench = load(ROOT / "baseline/hash-stage-benchmark.json")
    baseline_inputs = read(ROOT / "baseline/snapshot-hashes.json.gz")
    assert hashlib.sha256(baseline_inputs).hexdigest() == bench["input_file_sha256"]
    for expected_fp, snapshot in json.loads(baseline_inputs)["inputs"].items():
        assert fingerprint(snapshot) == expected_fp
    assert len(bench["samples"]) == 7 and bench["rounds"] == 9
    for row in bench["samples"]:
        timings = row["pairs_nanoseconds"]
        old = statistics.median(t["baseline"] for t in timings) / 300
        new = statistics.median(t["optimized"] for t in timings) / 300
        assert old == row["median_baseline_nanoseconds"]
        assert new == row["median_optimized_nanoseconds"]
        assert (old - new) / old * 100 == row["stage_reduction_percent"]
    environment = load(ROOT / "environment.json")
    for observer in environment["observers"]:
        assert hashlib.sha256((ROOT / observer["path"]).read_bytes()).hexdigest() == observer["sha256"]
        assert observer["created_before_each_run"]
    assert all(check["exit_code"] == 0 for check in load(ROOT / "quality.json")["checks"])
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
