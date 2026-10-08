"""Verify saved results, original collection/source and controlled lock evidence."""

import collections
import datetime
import gzip
import hashlib
import json
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
FROZEN = "0f11dcd6e4fcb6bbc004ea30e0e8cc154727c440"


def read(path):
    return json.loads(path.read_text())


def raw(path):
    return gzip.decompress(path.read_bytes()) if path.suffix == ".gz" else path.read_bytes()


def case(node):
    file, name = node.split("::", 1)
    return file.removesuffix(".py").replace("/", "."), name


proof = {"source_sha": FROZEN, "runs": {}}
new_test = read(ROOT / "new-regression-source.json")
assert hashlib.sha256((REPO / new_test["path"]).read_bytes()).hexdigest() == new_test["sha256"]
proof["new_regression_current_source_sha256"] = new_test["sha256"]
old_api = subprocess.check_output(["git", "show", FROZEN + ":src/sim2act/api.py"], cwd=REPO)
expected_api = old_api.replace(
    b"    def list_resources(pid: str, user=user_dependency):\n        with db.tx() as c:\n            p = db.own_project(c, user, pid)",
    b"    def list_resources(pid: str, user=user_dependency):\n        with db.tx() as c:\n            # Graph reads also authorize multiple resources. Serialize at the\n            # project before grants so their traversal order cannot deadlock.\n            p = db.lock_project(c, user, pid)",
)
assert expected_api != old_api and (REPO / "src/sim2act/api.py").read_bytes() == expected_api
baseline = read(ROOT / "baseline/source-before.json")
for row in baseline:
    path = row["path"]
    frozen = subprocess.check_output(["git", "show", FROZEN + ":" + path], cwd=REPO)
    assert hashlib.sha256(frozen).hexdigest() == row["sha256"]
    assert (REPO / path).read_bytes() == (expected_api if path == "src/sim2act/api.py" else frozen)
proof["original_source_files"] = len(baseline)
proof["changed_original_source"] = ["src/sim2act/api.py"]
proof["all_original_test_script_web_workflow_bytes_preserved"] = True
for name, expected_count, expected_fail in [
    ("baseline", 2, 0),
    ("candidate", 2, 0),
    ("old-regression", 4, 4),
    ("validation", 91, 0),
]:
    directory = ROOT / name
    before, after = read(directory / "source-before.json"), read(directory / "source-after.json")
    assert before == after
    assert len(before) == len(baseline)
    changed = [r["path"] for r in before if not r["matches_baseline"]]
    assert changed == (["src/sim2act/api.py"] if name in {"candidate", "validation"} else [])
    audit = read(directory / "phase-audit.json")
    cases = list(ET.parse(directory / "engineering.xml").getroot().iter("testcase"))
    assert len(cases) == expected_count == len(audit["nodes"])
    assert collections.Counter(case(n) for n in audit["nodes"]) == collections.Counter(
        (c.attrib["classname"], c.attrib["name"]) for c in cases
    )
    failures = sum(c.find("failure") is not None for c in cases)
    errors = sum(c.find("error") is not None for c in cases)
    skips = sum(c.find("skipped") is not None for c in cases)
    assert failures == expected_fail and errors == 0 and skips == 0
    census = {"test_schemas": 0, "test_roles": 0, "public_tables": 0}
    assert read(directory / "census-before.json") == census == read(directory / "census-after.json")
    cleanup = read(directory / "cleanup.json")
    assert cleanup["owner_label_verified"] and cleanup["owned_container_absent"]
    assert all(row["absent"] for row in cleanup["owned_volume_absence"])
    exports = read(directory / "export-manifest.json")
    for row in exports["files"]:
        path = directory / row["artifact"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row["artifact_sha256"]
        assert hashlib.sha256(raw(path)).hexdigest() == row["raw_sha256"]
    server = (directory / "server-attached.stderr.log").read_text()
    deadlocks = server.count("ERROR:  deadlock detected")
    assert deadlocks == {"baseline": 5, "candidate": 0, "old-regression": 4, "validation": 0}[name]
    proof["runs"][name] = {
        "junit_nodes": expected_count,
        "pass": expected_count - failures,
        "fail": failures,
        "skip": 0,
        "junit_collection_equal": True,
        "source_before_after_equal": True,
        "changed_original_source": changed,
        "server_deadlocks": deadlocks,
        "export_hashes_verified": len(exports["files"]),
        "census_zero": True,
        "owned_container_volume_absent": True,
        "wall_seconds": read(directory / "controller.json")["stages"][0]["wall_seconds"],
    }
old_nodes = read(REPO / "docs/evidence/engineering-pg-phase-20261008/first/collection.json")[
    "nodes"
]
current_nodes = read(ROOT / "default-collection.json")["nodes"]
new_nodes = [n for n in current_nodes if n not in set(old_nodes)]
assert len(old_nodes) == 1586 and len(current_nodes) == 1591 and len(new_nodes) == 5
assert collections.Counter(current_nodes) - collections.Counter(new_nodes) == collections.Counter(
    old_nodes
)
assert all(n.startswith("tests/test_resources_project_lock.py::") for n in new_nodes)
validation_nodes = read(ROOT / "validation/phase-audit.json")["nodes"]
assert set(new_nodes).issubset(validation_nodes)
proof["collection"] = {
    "original1586_preserved": True,
    "added_nodes": new_nodes,
    "current_count": 1591,
    "full_execution": "NOT_RUN for this fix",
}
lock_receipts = {}
for name in ["old-regression", "validation"]:
    receipts = [read(p) for p in (ROOT / name / "fixtures").glob("*/resources-graph-pg-lock.json")]
    assert len(receipts) == 4
    for receipt in receipts:
        assert len(set(receipt["pids"].values())) == 2 and receipt["source_mutation_absent"]
        if name == "old-regression":
            assert receipt["old_cycle_observed"] and receipt["source_wait_observed"]
            assert any(error["sqlstate"] == "40P01" for error in receipt["sql_errors"])
            assert 500 in receipt["statuses"].values()
        else:
            assert receipt["project_first_observed"] and not receipt["sql_errors"]
            assert receipt["statuses"]["resources"] == 200
            assert receipt["statuses"]["graph"] == (201 if receipt["operation"] == "plan" else 200)
    lock_receipts[name] = [
        {
            k: r[k]
            for k in [
                "first",
                "operation",
                "pids",
                "statuses",
                "old_cycle_observed",
                "project_first_observed",
            ]
        }
        for r in receipts
    ]
proof["controlled_lock_receipts"] = lock_receipts
analysis_old = read(ROOT / "baseline/analysis.json")
analysis_new = read(ROOT / "candidate/analysis.json")
paired = []
for node, old in analysis_old["nodes"].items():
    new = analysis_new["nodes"][node]
    assert (
        old["functions_nested"]["Store.initialize"]["count"]
        == new["functions_nested"]["Store.initialize"]["count"]
        == 1
    )
    a, b = old["phases"][1]["seconds"], new["phases"][1]["seconds"]
    paired.append(
        {
            "node": node,
            "old_call_seconds": a,
            "new_call_seconds": b,
            "observed_delta_seconds": b - a,
            "initialize_count_each": 1,
            "old_http500": len(old["node_process"][0]["http_500"]),
            "new_http500": len(new["node_process"][0]["http_500"]),
        }
    )
proof["single_paired_observations"] = paired
historical = REPO / "docs/evidence/engineering-pg-phase-20261008/full-verification"
timeline = [json.loads(line) for line in (historical / "timeline.jsonl").read_text().splitlines()]
start = next(
    r["utc"] for r in timeline if r.get("kind") == "stage-start" and r.get("stage") == "pytest"
)
start = datetime.datetime.fromisoformat(start)
audit = read(historical / "phase-audit.json")
elapsed = 0.0
for report in audit["reports"]:
    if (
        report["nodeid"].endswith("test_delivery_graph_actual_http_dom[REPORT]")
        and report["phase"] == "call"
    ):
        begin = start + datetime.timedelta(seconds=elapsed)
        end = begin + datetime.timedelta(seconds=report["seconds"])
        break
    elapsed += report["seconds"]
gap = read(historical / "controller.json")["stages"][-1]["wall_seconds"] - sum(
    r["seconds"] for r in audit["reports"]
)
proof["historical_attribution"] = {
    "estimated_report_call_utc_without_framework_gap": [begin.isoformat(), end.isoformat()],
    "total_unassigned_framework_seconds": gap,
    "three_deadlock_times_utc": [
        "2026-10-08T04:24:26.134+00:00",
        "2026-10-08T04:24:31.138+00:00",
        "2026-10-08T04:24:33.640+00:00",
    ],
    "classification": "Observed natural reproduction and controlled schedule establish real product race. Historical REPORT node is strongly supported by phase timing and same SQL shape; exact historical request parameters/HTTP status were not retained and are not reconstructed as fact.",
}
proof["limits"] = (
    "Single paired samples with passive observer, overlapping nested spans. No general speed guarantee, global deadlock freedom, full new-source run, Windows/native/provider/CI acceptance. Original900/240/150 and NO_GO retained. Original instance untouched."
)
(ROOT / "verification.json").write_text(json.dumps(proof, indent=2) + "\n")
print(
    json.dumps(
        {
            "verified": True,
            "original_source_files": len(baseline),
            "current_collection": len(current_nodes),
            "runs": {name: (row["pass"], row["fail"]) for name, row in proof["runs"].items()},
        }
    )
)
