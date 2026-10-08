"""Recompute diagnostic findings from exported collection/JUnit/phase files."""

import collections
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def main(root):
    def read(name):
        return json.loads((root / name).read_text(encoding="utf-8"))

    collection = read("collection.json")
    phases = read("phase-audit.json")
    metrics = read("pg-metrics.json")
    controller = read("controller.json")
    nodes = collections.Counter(collection["nodes"])
    executed_nodes = collections.Counter(phases["nodes"])
    junit = ET.parse(root / "engineering.xml").getroot()
    cases = list(junit.iter("testcase"))
    junit_key_to_node = {}
    for node in nodes:
        path, _, qualified = node.partition("::")
        prefix, bracket, parameter = qualified.partition("[")
        parts = prefix.split("::")
        classname = path[:-3].replace("/", ".")
        if len(parts) > 1:
            classname += "." + ".".join(parts[:-1])
        name = parts[-1] + bracket + parameter
        junit_key_to_node[(classname, name)] = node
    junit_nodes = collections.Counter(
        junit_key_to_node.get((case.attrib["classname"], case.attrib["name"]),
                             "UNMATCHED::" + case.attrib["classname"] + "::" + case.attrib["name"])
        for case in cases
    )
    statuses = collections.Counter()
    skips = []
    failures = []
    for case in cases:
        skipped = case.find("skipped")
        failure = case.find("failure")
        error = case.find("error")
        if skipped is not None:
            statuses["skipped"] += 1
            skips.append({"classname": case.attrib["classname"], "name": case.attrib["name"],
                          "message": skipped.attrib.get("message", "")})
        elif error is not None or failure is not None:
            statuses["errors" if error is not None else "failed"] += 1
            failures.append({"classname": case.attrib["classname"],
                             "name": case.attrib["name"]})
        else:
            statuses["passed"] += 1
    report_phases = collections.defaultdict(lambda: {"count": 0, "seconds": 0.0})
    modules = collections.defaultdict(lambda: {"setup": 0.0, "call": 0.0, "teardown": 0.0})
    for report in phases["reports"]:
        group = report_phases[report["phase"]]
        group["count"] += 1
        group["seconds"] += report["seconds"]
        modules[report["nodeid"].split("::", 1)[0]][report["phase"]] += report["seconds"]
    module_rows = [{"module": module, **times, "phase_seconds": sum(times.values())}
                   for module, times in modules.items()]
    module_rows.sort(key=lambda row: row["phase_seconds"], reverse=True)
    stage_time = next(row["wall_seconds"] for row in controller["stages"]
                      if row["name"] == "pytest")
    initialize = [row for row in metrics["groups"] if row["family"] == "initialize"]
    env_setup = [row for row in metrics["groups"] if row["family"] == "fixture_setup"
                 and row["labels"][0] == "env"]
    env_initialize = [row for row in initialize if row["labels"][0] == "env"]
    sum_env = sum(row["seconds"] for row in env_setup)
    sum_env_initialize = sum(row["seconds"] for row in env_initialize)
    total_report_time = sum(row["seconds"] for row in report_phases.values())
    before = read("source-before.json")
    after = read("source-after.json")
    return {
        "source_sha": controller["source_sha"],
        "collection": len(collection["nodes"]), "unique_nodes": len(nodes),
        "execution_collection_matches": nodes == executed_nodes,
        "junit_multiset_matches_collection": nodes == junit_nodes,
        "junit_cases": len(cases), "outcomes": dict(statuses),
        "skips": skips, "failures": failures,
        "stages": controller["stages"], "pytest_process_wall_seconds": stage_time,
        "reported_phases": dict(report_phases),
        "env_fixture_definitions": phases.get("env_fixture_definitions", {}),
        "reported_phase_total_seconds": total_report_time,
        "wall_minus_reported_phase_seconds": stage_time - total_report_time,
        "modules_by_reported_phase_cost": module_rows,
        "slowest_30_reports": sorted(phases["reports"],
                                     key=lambda row: row["seconds"], reverse=True)[:30],
        "metrics": {"measurement_status": metrics["measurement_status"],
                    "pending_sql": metrics["pending_sql"],
                    "scope": metrics["scope"], "groups": metrics["groups"]},
        "env_setup_seconds": sum_env, "env_initialize_seconds": sum_env_initialize,
        "env_initialize_fraction_of_env_setup":
            sum_env_initialize / sum_env if sum_env else None,
        "initialize_total_seconds": sum(row["seconds"] for row in initialize),
        "initialize_fraction_of_pytest_process_wall":
            sum(row["seconds"] for row in initialize) / stage_time,
        "source_file_count": len(before),
        "before_after_and_baseline_bytes_match": before == after
            and all(row["matches_baseline"] for row in before),
        "census_before": read("census-before.json"),
        "census_after": read("census-after.json"), "cleanup": read("cleanup.json"),
        "windows900": "NO_GO; current native attribution and complete Edge cost unknown",
        "limits": ["Linux is not Windows capacity or performance acceptance",
                   "no uninstrumented whole-suite pair: instrumentation overhead unknown",
                   "initialize/has_table/SQL/fixture families overlap; do not add them",
                   "SQL cursor excludes fetch, commit and pool acquisition",
                   "plugin does not measure subprocess internals or Edge/native stages",
                   "phase-report durations cover teardown as a phase, not its SQL breakdown"],
    }


if __name__ == "__main__":
    directory = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent
    print(json.dumps(main(directory), indent=2))
