"""Pure local synthetic review probe. No provider network or credentials.
Run from repo root using PYTHONPATH=src:tests. Existing jobs fixture defaults SQLite.
The original accepted baseline is retained; --assert-closed expects guard rejection.
"""
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

import httpx
import pytest
from sqlalchemy import delete, select

import test_protocol_experiment as experiment_tests
import test_protocol_jobs as jobs
from sim2act.db import events
from sim2act.errors import DomainError
from sim2act.model import InternModel
from sim2act.protocol_experiment import BOUND, GENESIS, BINDING, STOPPED, is_experiment_run
from sim2act.protocol_pool import OFFLINE_POOL


def run_probe(mode):
    with tempfile.TemporaryDirectory(prefix="independent-experiment-") as temporary:
        fixture = jobs.env.__wrapped__(Path(temporary))
        env = next(fixture)
        patch = pytest.MonkeyPatch()
        try:
            wired = experiment_tests.wired.__wrapped__(env, patch)
            _, ticks, eid, run, runner = wired
            sent = []

            def transport(request):
                sent.append(ticks[0])
                return httpx.Response(200, json=jobs.wire({"public": "synthetic"}))

            model = InternModel(
                replace(env[5].s, live_enabled=True, token="MOCK_ONLY"),
                httpx.MockTransport(transport),
            )
            if mode in {"binding", "markers"}:
                patch.undo()  # Test the real integrated Worker hooks, without legacy fixture shim.
                with env[0].tx() as connection:
                    if mode == "binding":
                        connection.execute(delete(events).where(events.c.run_id == eid, events.c.kind == BOUND))
                    else:
                        connection.execute(delete(events).where(events.c.run_id == OFFLINE_POOL, events.c.kind == GENESIS))
                        connection.execute(delete(events).where(events.c.run_id == run["id"], events.c.kind == BINDING))
                        if not is_experiment_run(connection, run["id"]):
                            print("marker oracle lost retained origin")
                try:
                    if mode == "binding":
                        experiment_tests.preflight(env[0], env[1], run["id"], clock=lambda: ticks[0])
                    else:
                        experiment_tests.reserve(wired)
                except DomainError:
                    if mode == "binding":
                        with env[0].tx() as connection:
                            assert connection.execute(select(events.c.id).where(events.c.run_id == eid, events.c.kind == STOPPED)).first()
                    return "CLOSED"
                except IndexError:
                    return "RAW_INDEXERROR"
                return "ACCEPTED_LEGACY_FALLBACK"
            aid = experiment_tests.reserve(wired)
            ticks[0] = 1005
            raw = model.request([], [])
            runner._record(aid, raw, 0, "RECEIVED")
            ticks[0] = 1006
            if mode == "spacing":
                try:
                    second = experiment_tests.reserve(wired)
                except DomainError as error:
                    assert error.code in {"RATE_LIMITED", "OUTCOME_UNKNOWN"}
                    return "CLOSED"
                raw = model.request([], [])
                runner._record(second, raw, 0, "RECEIVED")
                assert sent == [1005, 1006]
                return "ACCEPTED_1SECOND_SPACING"
            with env[0].tx() as connection:
                connection.execute(
                    delete(events).where(
                        events.c.kind.in_([experiment_tests.SEND, experiment_tests.SETTLED]),
                        events.c.run_id.in_([eid, aid]),
                    )
                )
            try:
                summary = experiment_tests.inspect_experiment(env[0], env[1], eid)
                assert summary["requests"] == 0 and summary["settled"] == 0
                experiment_tests.reserve(wired)
            except DomainError:
                return "CLOSED"
            return "ACCEPTED_DELETED_STAGE_EVENTS"
        finally:
            patch.undo()
            try:
                next(fixture)
            except StopIteration:
                pass


if __name__ == "__main__":
    for name in ("spacing", "deleted_events", "binding", "markers"):
        result = run_probe(name)
        print(name + ": " + result)
        if "--assert-closed" in sys.argv and result != "CLOSED":
            raise SystemExit(1)
