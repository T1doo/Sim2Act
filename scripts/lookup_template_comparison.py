"""One fixed local SQLite comparison; no Worker, model, transport or network."""

import hashlib
import json
import runpy
import statistics
import sys
import time
from pathlib import Path

from sqlalchemy import create_engine, event

from sim2act import delivery_graph_apps as graph
from sim2act.db import delivery_graph_requests as requests

CONTRACT = dict(rounds=12, queries_per_arm=200, warmup_per_arm=32, setup_lookup_queries=1,
                rows=8, payload_characters=8192, work_seconds=30,
                minimum_wall_wins=9, maximum_wall_median_ratio=0.95,
                maximum_cpu_median_ratio=0.95, retries=0)


def main(output):
    start = time.monotonic()
    helpers = runpy.run_path("tests/test_request_lookup_template.py")
    legacy, body = helpers["legacy_lookup"], helpers["Body"]
    engine = create_engine("sqlite+pysqlite:///:memory:")
    result = dict(contract=CONTRACT, scope="local 8-row SQLite, 8KiB synthetic payload; not Cold/G0",
                  sources={p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in (
                      "src/sim2act/delivery_graph_apps.py", "tests/test_request_lookup_template.py",
                      "scripts/lookup_template_comparison.py")}, rounds=[], selects=0)

    def count_select(_c, _cursor, statement, _params, _context, _many):
        if statement.startswith("SELECT "):
            result["selects"] += 1

    try:
        with engine.begin() as c:
            requests.create(c)
            event.listen(c, "before_cursor_execute", count_select)
            arguments = []
            for i in range(CONTRACT["rows"]):
                args = (f"user-{i % 2}", f"app-{i % 3}", "proof-kind", f"key-{i}")
                arguments.append(args)
                graph.remember(c, *args, body(value=i),
                               {"sequence": i, "payload": "x" * CONTRACT["payload_characters"]})
            result["serialized_snapshot_bytes"] = len(json.dumps(
                dict(graph.lookup(c, *arguments[0]))["snapshot"]).encode())

            def run(implementation, iterations):
                if time.monotonic() - start >= CONTRACT["work_seconds"]:
                    raise TimeoutError("Fixed comparison deadline; no retry")
                wall, cpu = time.perf_counter_ns(), time.thread_time_ns()
                checksum = 0
                for i in range(iterations):
                    value = implementation(c, *arguments[i % len(arguments)])
                    checksum += value["snapshot"]["response"]["sequence"]
                return dict(wall_ns=time.perf_counter_ns() - wall,
                            cpu_ns=time.thread_time_ns() - cpu, checksum=checksum)

            for implementation in (legacy, graph.lookup):
                run(implementation, CONTRACT["warmup_per_arm"])
            for i in range(CONTRACT["rounds"]):
                row = dict(index=i, order=["legacy", "candidate"] if i % 2 == 0
                           else ["candidate", "legacy"])
                for name in row["order"]:
                    row[name] = run(legacy if name == "legacy" else graph.lookup,
                                    CONTRACT["queries_per_arm"])
                assert row["legacy"]["checksum"] == row["candidate"]["checksum"]
                result["rounds"].append(row)
            result["wall_median_ratio"] = statistics.median(
                r["candidate"]["wall_ns"] / r["legacy"]["wall_ns"] for r in result["rounds"])
            result["cpu_median_ratio"] = statistics.median(
                r["candidate"]["cpu_ns"] / r["legacy"]["cpu_ns"] for r in result["rounds"])
            result["wall_wins"] = sum(r["candidate"]["wall_ns"] < r["legacy"]["wall_ns"]
                                      for r in result["rounds"])
            assert result["selects"] == 4865
            if time.monotonic() - start > CONTRACT["work_seconds"]:
                raise TimeoutError("Fixed comparison deadline; no retry")
            result["qualified"] = (result["wall_wins"] >= CONTRACT["minimum_wall_wins"]
                and result["wall_median_ratio"] <= CONTRACT["maximum_wall_median_ratio"]
                and result["cpu_median_ratio"] <= CONTRACT["maximum_cpu_median_ratio"])
            result["status"] = "QUALIFIED_LOCAL_CANDIDATE" if result["qualified"] else "NOT_ADMITTED"
    except BaseException as error:
        result.update(status="FAILED_NO_RETRY", qualified=False, error=type(error).__name__ + ": " + str(error))
        raise
    finally:
        engine.dispose()
        result.update(elapsed_seconds=time.monotonic() - start, engine_disposed=True,
                      models=0, http=0, automatic_retry=0)
        Path(output).write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps({k: v for k, v in result.items() if k not in ("rounds", "sources")}))


if __name__ == "__main__":
    main(sys.argv[1])
