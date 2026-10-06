"""Actual offline sender + DB wire seals. Synthetic fixture only, never network.
Run PYTHONPATH=src:tests python this_file --assert-closed from repo root.
"""
import copy
import json
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

import httpx
from sqlalchemy import select, update

import conftest
import test_protocol_http as http_tests
from sim2act.db import attempts, events, protocol_jobs
from sim2act.errors import DomainError
from sim2act.model import InternModel
from sim2act.protocol_egress import READ_TOOLS, SOURCE_SYSTEM, project_request, serialized_body
from sim2act.protocol_experiment import bind_run, initialize_experiment
from sim2act.worker import Worker


def probe(mode):
    with tempfile.TemporaryDirectory(prefix="independent-wire-seal-") as temporary:
        fixture = conftest.env.__wrapped__(Path(temporary))
        base = next(fixture)
        try:
            env = http_tests.env.__wrapped__(base)
            store, user, pid = env[0], env[3], env[5]
            eid = initialize_experiment(store, user, pid, "wire-review", 14, clock=lambda: 1000)["experiment_id"]
            rid = env[2].post(http_tests.url(env) + "/source", json=http_tests.body(env)).json()["run_id"]
            bind_run(store, user, eid, rid, clock=lambda: 1000)
            worker = Worker(store, env[1], http_tests.NoProvider(), protocol_clock=lambda: 1000)
            run = store.claim(worker.id, 60)
            with store.tx() as connection:
                snapshot = connection.execute(select(protocol_jobs.c.accepted_snapshot).where(protocol_jobs.c.run_id == rid)).scalar_one()
            original = [
                {"role": "system", "content": SOURCE_SYSTEM},
                {"role": "user", "content": json.dumps({k: snapshot["payload"][k] for k in ["goal", "inputs", "resource_ids"]})},
            ]
            projected, tools, guard = project_request(store, snapshot, original, READ_TOOLS, clock=lambda: 1000)
            context = copy.deepcopy(run["context"])
            context["messages"] = projected
            aid = worker.reserve(rid, run["fence"], context, request_tools=tools)
            with store.tx() as connection:
                parameters = copy.deepcopy(connection.execute(select(attempts.c.parameters).where(attempts.c.id == aid)).scalar_one())
                event = connection.execute(select(events).where(events.c.run_id == rid, events.c.kind == "PROTOCOL_WIRE_RESERVED")).mappings().one()
                witness = copy.deepcopy(event["data"])
                if mode == "parameters":
                    parameters["protocol_wire"]["sha256"] = "0" * 64
                elif mode == "witness":
                    witness["wire"]["sha256"] = "0" * 64
                else:
                    parameters["protocol_wire"]["bytes"] = float(parameters["protocol_wire"]["bytes"])
                    witness["wire"]["bytes"] = float(witness["wire"]["bytes"])
                    witness["fence"] = True
                connection.execute(update(attempts).where(attempts.c.id == aid).values(parameters=parameters))
                connection.execute(update(events).where(events.c.id == event["id"]).values(data=witness))
            observed = []
            model = InternModel(replace(env[1], live_enabled=True, token="MOCK_ONLY"), httpx.MockTransport(lambda request: observed.append(request.content) or httpx.Response(200, json={"model": "intern-s2"})))
            try:
                model.request_serialized(serialized_body(projected, tools), guard)
            except DomainError as error:
                assert error.code == "VERSION_CONFLICT" and observed == []
                return "CLOSED_0SEND"
            return "ACCEPTED_" + str(len(observed)) + "MOCKSEND"
        finally:
            try:
                next(fixture)
            except StopIteration:
                pass


if __name__ == "__main__":
    for mode in ("parameters", "witness", "coherent_float_bool"):
        result = probe(mode)
        print(mode + ": " + result)
        if "--assert-closed" in sys.argv and result != "CLOSED_0SEND":
            raise SystemExit(1)
