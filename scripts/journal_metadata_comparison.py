"""One bounded SQLite metadata comparison, excluding whole Cold guard costs."""

import hashlib
import json
import runpy
import statistics
import sys
import time
from pathlib import Path

from sqlalchemy import create_engine, event

from sim2act import pa_trial_dispatch as trial
from sim2act.db import delivery_graph_requests as rows
from sim2act.db import events

CONTRACT = dict(rounds=12, calls_per_arm=60, warmup_per_arm=8, cases=4,
    expected_selects=2912, expected_guards=8736, work_seconds=30,
    minimum_wall_wins=9, maximum_wall_median_ratio=0.95,
    maximum_cpu_median_ratio=0.95, retries=0)
SOURCES = ("src/sim2act/pa_trial_dispatch.py", "tests/test_journal_metadata_projection.py",
           "scripts/journal_metadata_comparison.py")


def hashes():
    return {name: hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in SOURCES}


def main(output):
    start = time.monotonic()
    helpers = runpy.run_path("tests/test_journal_metadata_projection.py")
    engine = create_engine("sqlite+pysqlite:///:memory:")
    report = dict(contract=CONTRACT, before=hashes(), rounds=[], selects=0, guards=0,
        scope="actual metadata helper on synthetic SQLite; lightweight counting guard, not full graph/Cold/G0")

    def count(_c, _cursor, statement, _params, _context, _many):
        if statement.startswith("SELECT "):
            report["selects"] += 1

    def guard():
        report["guards"] += 1

    try:
        with engine.begin() as c:
            rows.create(c)
            events.create(c)
            arguments = []
            for i in range(CONTRACT["cases"]):
                kind = trial.REQUEST if i % 2 == 0 else trial.RESPONSE
                run = dict(id=f"run-{i}", principal_id=f"user-{i % 2}",
                           project_id=f"project-{i}", runtime_id=f"runtime-{i}")
                helpers["seed"](c, run, aid=f"attempt-{i}", kind=kind)
                arguments.append((run, f"attempt-{i}", kind))
            event.listen(c, "before_cursor_execute", count)

            def run(implementation, calls):
                if time.monotonic() - start >= CONTRACT["work_seconds"]:
                    raise TimeoutError("Fixed local comparison deadline; no retry")
                wall, cpu = time.perf_counter_ns(), time.thread_time_ns()
                checksum = 0
                for index in range(calls):
                    result = implementation(c, *arguments[index % len(arguments)], _guard=guard)
                    checksum += result["byte_count"]
                return dict(wall_ns=time.perf_counter_ns() - wall,
                            cpu_ns=time.thread_time_ns() - cpu, checksum=checksum)

            legacy = helpers["legacy_metadata"]
            for implementation in (legacy, trial._metadata):
                run(implementation, CONTRACT["warmup_per_arm"])
            for i in range(CONTRACT["rounds"]):
                row = dict(index=i, order=["legacy", "candidate"] if i % 2 == 0
                           else ["candidate", "legacy"])
                for name in row["order"]:
                    row[name] = run(legacy if name == "legacy" else trial._metadata,
                                    CONTRACT["calls_per_arm"])
                assert row["legacy"]["checksum"] == row["candidate"]["checksum"] == 720
                report["rounds"].append(row)
            report["wall_median_ratio"] = statistics.median(
                row["candidate"]["wall_ns"] / row["legacy"]["wall_ns"] for row in report["rounds"])
            report["cpu_median_ratio"] = statistics.median(
                row["candidate"]["cpu_ns"] / row["legacy"]["cpu_ns"] for row in report["rounds"])
            report["wall_wins"] = sum(row["candidate"]["wall_ns"] < row["legacy"]["wall_ns"]
                                      for row in report["rounds"])
            assert report["selects"] == CONTRACT["expected_selects"]
            assert report["guards"] == CONTRACT["expected_guards"]
            assert time.monotonic() - start < CONTRACT["work_seconds"]
            report["qualified"] = (report["wall_wins"] >= CONTRACT["minimum_wall_wins"]
                and report["wall_median_ratio"] <= CONTRACT["maximum_wall_median_ratio"]
                and report["cpu_median_ratio"] <= CONTRACT["maximum_cpu_median_ratio"])
            report["status"] = "QUALIFIED_LOCAL_METADATA" if report["qualified"] else "NOT_ADMITTED"
    except BaseException as error:
        report.update(status="FAILED_NO_RETRY", qualified=False, error=type(error).__name__)
        raise
    finally:
        engine.dispose()
        report.update(after=hashes(), engine_disposed=True,
                      elapsed_seconds=time.monotonic() - start, http=0, model_calls=0)
        assert report["before"] == report["after"], "Frozen source changed"
        Path(output).write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps({key: value for key, value in report.items()
                          if key not in ("rounds", "before", "after")}))


if __name__ == "__main__":
    main(sys.argv[1])
