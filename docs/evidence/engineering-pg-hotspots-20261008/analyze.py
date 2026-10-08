"""Recompute owned paired DOM phase/request observations; nested spans overlap."""

import collections
import gzip
import json
import re
import sys
from pathlib import Path


def contents(path):
    if path.suffix == ".gz":
        return gzip.decompress(path.read_bytes()).decode()
    if path.exists():
        return path.read_text()
    return gzip.decompress(Path(str(path) + ".gz").read_bytes()).decode()


def load_lines(path):
    return [json.loads(line) for line in contents(path).splitlines()]


def shape(path):
    return re.sub(r"(?:proj|app|res|run|grant|job|user)_[a-f0-9]{32}", "ID", path)


root = Path(sys.argv[1])
audit = json.loads((root / "phase-audit.json").read_text())
groups = json.loads(contents(root / "hotspot-groups.json"))
timeline = load_lines(root / "python-timeline.jsonl")
answer = {
    "limits": "Single paired samples, observer enabled identically; function/SQL/request spans overlap. SQL cursor timing excludes fetch, commit and pool. No Windows or native acceptance inference.",
    "nodes": {},
}
for node in audit["nodes"]:
    events = [r for r in timeline if r["node"] == node]
    rows = [r for r in groups["groups"] if r["node"] == node]
    functions = collections.defaultdict(lambda: {"count": 0, "seconds": 0})
    for row in rows:
        if row["kind"] == "function":
            functions[row["identity"]]["count"] += row["count"]
            functions[row["identity"]]["seconds"] += row["seconds"]
    ends = [r for r in events if r["event"] == "request_end"]
    requests = collections.defaultdict(lambda: {"count": 0, "seconds": 0, "max_seconds": 0})
    for row in ends:
        key = shape(row["request"].split(":", 1)[1])
        requests[key]["count"] += 1
        requests[key]["seconds"] += row["seconds"]
        requests[key]["max_seconds"] = max(requests[key]["max_seconds"], row["seconds"])
    probe_nodes = []
    for file in root.glob("node-*.jsonl*"):
        child = load_lines(file)
        driver = child[0]["argv"][1]
        if ("delivery_graph" in driver) != ("delivery_graph" in node):
            continue
        headers = [r for r in child if r["event"] == "http_headers"]
        starts = [r for r in child if r["event"] == "http_start"]
        probe_nodes.append(
            {
                "file": file.name.removesuffix(".gz"),
                "process_seconds": child[-1]["elapsed_ms"] / 1000,
                "headers_count": len(headers),
                "first_http_elapsed_ms": starts[0]["elapsed_ms"],
                "static_http_count": len(
                    [r for r in headers if r["path"] == "/" or r["path"].endswith(".js")]
                ),
                "health_http_count": len([r for r in headers if r["path"] == "/health"]),
                "mock_worker_http": [
                    r for r in headers if r["path"].startswith("/test-only-manifest-worker/")
                ],
                "http_500": [r for r in headers if r["status"] == 500],
                "header_seconds_overlap": sum(r["seconds"] for r in headers),
                "body_seconds": sum(r["seconds"] for r in child if r["event"] == "body"),
                "largest_http": sorted(headers, key=lambda r: r["seconds"], reverse=True)[:12],
            }
        )
    progress = []
    for directory in (root / "fixtures").glob("*0"):
        matches = ("delivery_graph" in directory.name) == ("delivery_graph" in node)
        if not matches:
            continue
        driver = directory / "driver-progress.jsonl"
        checks = (
            [r for r in load_lines(driver) if r["event"] == "check"]
            if driver.exists() or Path(str(driver) + ".gz").exists()
            else [
                r
                for line in (directory / "driver.log").read_text().splitlines()
                if line.startswith('{"check":')
                for r in [json.loads(line)]
            ]
        )
        before = 0
        for check in checks:
            elapsed = check["elapsed_ms"]
            progress.append(
                {
                    "label": check["label"],
                    "elapsed_ms": elapsed,
                    "since_previous_ms": elapsed - before,
                }
            )
            before = elapsed
    answer["nodes"][node] = {
        "phases": [r for r in audit["reports"] if r["nodeid"] == node],
        "functions_nested": dict(functions),
        "requests_overlap": dict(
            sorted(requests.items(), key=lambda p: p[1]["seconds"], reverse=True)
        ),
        "requests_longest": sorted(ends, key=lambda r: r["seconds"], reverse=True)[:12],
        "sql_cursor_seconds": sum(r["seconds"] for r in rows if r["kind"] == "sql"),
        "sql_cursor_count": sum(r["count"] for r in rows if r["kind"] == "sql"),
        "sql_errors": [r for r in events if r.get("sqlstate")],
        "node_process": probe_nodes,
        "check_milestones": progress,
        "pending_sql": groups["pending_sql"],
    }
output = root / "analysis.json"
if output.exists():
    assert json.loads(output.read_text()) == answer, "saved analysis differs from recomputation"
else:
    output.write_text(json.dumps(answer, indent=2) + "\n")
for node, value in answer["nodes"].items():
    print(
        node,
        value["phases"],
        "sql",
        value["sql_cursor_count"],
        round(value["sql_cursor_seconds"], 3),
        "deadlocks",
        len([r for r in value["sql_errors"] if r["sqlstate"] == "40P01"]),
    )
