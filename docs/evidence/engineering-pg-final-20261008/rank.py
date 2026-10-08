"""Read-only rankings from completed full-run receipts; starts no DB or tests."""

import collections
import hashlib
import json
import sys
from pathlib import Path


def rank(root):
    audit = json.loads((root / "phase-audit.json").read_text())
    controller = json.loads((root / "controller.json").read_text())
    wall = next(s["wall_seconds"] for s in controller["stages"] if s["name"] == "pytest")
    definitions = {}
    for row in audit["fixture_setup_reports"]:
        key = (
            row["baseid"],
            row["name"],
            row["scope"],
            row["function_module"],
            row["function_qualname"],
        )
        group = definitions.setdefault(
            key,
            {
                "baseid": key[0],
                "name": key[1],
                "scope": key[2],
                "function_module": key[3],
                "function_qualname": key[4],
                "count": 0,
                "failed": 0,
                "seconds": 0.0,
                "max_seconds": 0.0,
            },
        )
        group["count"] += 1
        group["failed"] += int(row["failed"])
        group["seconds"] += row["seconds"]
        group["max_seconds"] = max(group["max_seconds"], row["seconds"])
    phase_totals = collections.defaultdict(float)
    modules = collections.defaultdict(float)
    for row in audit["reports"]:
        phase_totals[row["phase"]] += row["seconds"]
        if row["phase"] == "call":
            modules[row["nodeid"].split("::", 1)[0]] += row["seconds"]
    before = json.loads((root / "source-before.json").read_text())
    after = json.loads((root / "source-after.json").read_text())
    assert before == after
    assert all(
        hashlib.sha256(Path(x["path"]).read_bytes()).hexdigest() == x["sha256"] for x in after
    )
    cleanup = json.loads((root / "cleanup.json").read_text())
    assert cleanup["owned_container_absent"]
    assert all(x["absent"] for x in cleanup["owned_volume_absence"])
    assert all(v == 0 for v in json.loads((root / "census-after.json").read_text()).values())
    engineering_total = sum(
        s["wall_seconds"] for s in controller["stages"] if s["name"] != "collection"
    )
    return {
        "source_sha": controller["source_sha"],
        "pytest_process_wall_seconds": wall,
        "phase_seconds": dict(phase_totals),
        "phase_wall_fractions": {k: v / wall for k, v in phase_totals.items()},
        "remaining_process_wall_seconds": wall - sum(phase_totals.values()),
        "engineering_stages_excluding_collection_seconds": engineering_total,
        "stage_wall_fractions": {
            s["name"]: s["wall_seconds"] / engineering_total
            for s in controller["stages"]
            if s["name"] != "collection"
        },
        "slowest_call_reports": sorted(
            (x for x in audit["reports"] if x["phase"] == "call"),
            key=lambda x: x["seconds"],
            reverse=True,
        )[:30],
        "call_module_totals": sorted(
            ({"module": k, "call_seconds": v} for k, v in modules.items()),
            key=lambda x: x["call_seconds"],
            reverse=True,
        ),
        "slowest_setup_reports": sorted(
            (x for x in audit["reports"] if x["phase"] == "setup"),
            key=lambda x: x["seconds"],
            reverse=True,
        )[:30],
        "fixture_definitions_by_setup_total": sorted(
            definitions.values(), key=lambda x: x["seconds"], reverse=True
        ),
        "slowest_individual_fixture_setups": sorted(
            audit["fixture_setup_reports"], key=lambda x: x["seconds"], reverse=True
        )[:30],
        "env_fixture_definitions": audit["env_fixture_definitions"],
        "source_hashes_before_after_current_match": True,
        "source_files": len(after),
        "cleanup_verified": True,
        "limits": [
            "fixture spans may nest and overlap; do not add definition totals to phase totals",
            "setup fixture ranks do not attribute teardown or subprocess internals",
            "SQL aggregates do not identify source-level duplicate work",
            "mypy cache and environment are warm; baseline has different source/outcomes",
            "no uninstrumented pair; no measured causal speedup or Windows qualification",
            "ranking supports subsequent profiling/experiments; no optimization applied",
        ],
    }


if __name__ == "__main__":
    print(json.dumps(rank(Path(sys.argv[1])), indent=2))
