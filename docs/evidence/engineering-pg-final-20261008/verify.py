"""Verify final full PG receipts without creating a DB or changing source."""

import collections
import gzip
import hashlib
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from analyze import main as analyze

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "run"
FROZEN = "d85f6f5ceb05972171a84f5aa72f821b39fcb226"


def read(path):
    if path.exists():
        return json.loads(path.read_text())
    return json.loads(gzip.decompress(Path(str(path) + ".gz").read_bytes()))


findings = analyze(ROOT)
assert findings["source_sha"] == FROZEN
assert findings["execution_collection_matches"] and findings["junit_multiset_matches_collection"]
assert not findings["failures"] and findings["outcomes"].get("errors", 0) == 0
collected = read(ROOT / "collection.json")["nodes"]
baseline = read(REPO / "docs/evidence/engineering-pg-phase-20261008/first/collection.json")["nodes"]
extra = [n for n in collected if n not in set(baseline)]
assert len(collected) == 1591 and len(extra) == 5
assert collections.Counter(collected) - collections.Counter(extra) == collections.Counter(baseline)
old = read(REPO / "docs/evidence/engineering-pg-phase-20261008/full-verification/analysis.json")
assert findings["skips"] == old["skips"]
assert findings["before_after_and_baseline_bytes_match"]
after = read(ROOT / "source-after.json")
assert len(after) == 284
for row in after:
    current = (REPO / row["path"]).read_bytes()
    frozen = subprocess.check_output(["git", "show", FROZEN + ":" + row["path"]], cwd=REPO)
    assert current == frozen and hashlib.sha256(current).hexdigest() == row["sha256"]
for row in read(ROOT / "instrumentation-sha256.json"):
    assert hashlib.sha256((REPO / row["path"]).read_bytes()).hexdigest() == row["sha256"]
exceptions = read(ROOT / "exception-audit.json")
deadlocks = [r for r in exceptions["sql_errors"] if r["sqlstate"] == "40P01"]
http500 = [r for r in exceptions["http_exceptions"] if r["status"] == 500]
expected503 = [
    r
    for r in exceptions["http_exceptions"]
    if r["status"] == 503
    and r["node"]
    == "tests/test_conditional_run_product.py::test_source_bound_product_actual_http_dom"
    and r["request"].startswith("GET:/api/projects/")
    and r["request"].endswith("/resources")
    and r["exception_type"] is None
]
assert len(expected503) == 1
unexpected5xx = [
    r
    for r in exceptions["http_exceptions"]
    if r["status"] is not None and r["status"] >= 500 and r not in expected503
]
server = (ROOT / "server-attached.stderr.log").read_text()
assert not deadlocks and "deadlock detected" not in server and not unexpected5xx
cases = {
    (c.attrib["classname"], c.attrib["name"]): c
    for c in ET.parse(ROOT / "engineering.xml").getroot().iter("testcase")
}


def status(node):
    path, _, qualified = node.partition("::")
    prefix, bracket, parameter = qualified.partition("[")
    parts = prefix.split("::")
    module = path[:-3].replace("/", ".")
    if len(parts) > 1:
        module += "." + ".".join(parts[:-1])
    name = parts[-1] + bracket + parameter
    case = cases[(module, name)]
    return (
        "PASS" if all(case.find(k) is None for k in ["failure", "error", "skipped"]) else "NOT_PASS"
    )


assert all(status(n) == "PASS" for n in extra)
audit = read(ROOT / "phase-audit.json")
roles = sorted(
    {
        r["nodeid"]
        for r in audit["fixture_setup_reports"]
        if r["name"] == "runtime_role" and not r["failed"]
    }
)
assert roles and all(status(n) == "PASS" for n in roles)
role_receipts = [read(p) for p in (ROOT / "fixtures").rglob("pg-runtime-role.json")]
assert len(role_receipts) == 1
locks = [
    read(p)
    for p in (ROOT / "fixtures").rglob("resources-graph-pg-lock.json")
    if "current" not in p.relative_to(ROOT / "fixtures").parts
]
assert len(locks) == 4 and all(r["project_first_observed"] and not r["sql_errors"] for r in locks)
assert all(len(set(r["pids"].values())) == 2 for r in locks)
cleanup = read(ROOT / "cleanup.json")
assert cleanup["owner_label_verified"] and cleanup["owned_container_absent"]
assert all(row["absent"] for row in cleanup["owned_volume_absence"])
assert (
    findings["census_before"]
    == findings["census_after"]
    == {"test_schemas": 0, "test_roles": 0, "public_tables": 0}
)
assert (
    findings["metrics"]["measurement_status"] == "COMPLETE"
    and findings["metrics"]["pending_sql"] == 0
)
controller = read(ROOT / "controller.json")
assert controller["complete"] and controller["pytest_exit_code"] == 0
assert all(s["exit_code"] == 0 for s in controller["stages"])
if (ROOT / "export-manifest.json").exists():
    for row in read(ROOT / "export-manifest.json")["files"]:
        data = (ROOT / row["artifact"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == row["artifact_sha256"]
        raw = gzip.decompress(data) if row["artifact"].endswith(".gz") else data
        assert hashlib.sha256(raw).hexdigest() == row["raw_sha256"]
proof = {
    "source_sha": FROZEN,
    "collection_execution_junit_multisets_equal": True,
    "actual_collection": len(collected),
    "original1586_preserved": True,
    "added5_pass": extra,
    "outcomes": findings["outcomes"],
    "same27_skips_and_reasons": True,
    "source284_before_after_current_equal": True,
    "instrumentation_hashes_equal": True,
    "sql40P01": deadlocks,
    "server_deadlock_count": server.count("deadlock detected"),
    "observed_HTTP500": http500,
    "unexpected_HTTP5xx": unexpected5xx,
    "expected_injected_HTTP503": expected503,
    "HTTP503_source": {
        "python": "tests/test_conditional_run_product.py:66-78",
        "driver": "tests/conditional_run_product.cjs:50-52",
        "meaning": "Original test-only metadata middleware and original assert.rejects / HTTP503 clearing assertion; no product or assertion change.",
    },
    "other_http_exceptions": [
        r for r in exceptions["http_exceptions"] if r not in expected503 and r not in http500
    ],
    "sql_error_counts": dict(collections.Counter(r["sqlstate"] for r in exceptions["sql_errors"])),
    "runtime_role_fixture_junit_pass_nodes": roles,
    "runtime_role_receipt": role_receipts,
    "lock_receipt_count": len(locks),
    "census_zero": True,
    "owned_container_volume_absent": True,
    "stages": controller["stages"],
    "limits": [
        exceptions["limits"],
        "Subprocess exception signatures are scanned separately; absence of signatures is not exhaustive response-status capture.",
        "Linux current complete cost only, warm caches and observers; no causal speedup, Windows/native/CI/provider acceptance.",
        "Windows900/Edge240/Node150 unchanged; NO_GO retained; original instance untouched.",
    ],
}
(ROOT / "verification.json").write_text(json.dumps(proof, indent=2) + "\n")
print(
    json.dumps(
        {
            "verified": True,
            "outcomes": proof["outcomes"],
            "runtime_role_fixture_cases": len(roles),
            "SQL40P01": len(deadlocks),
            "observed_HTTP500": len(http500),
        }
    )
)
