"""Synthetic persisted faults at the exact old-worker continuation boundary."""

import copy
import json
import os
from pathlib import Path

import pytest
from sql_private_barrier import PrivateReadBarrier
from sqlalchemy import delete, select, update
from test_text_continuations import legacy as legacy
from test_text_continuations import legacy_failure as legacy_failure
from test_text_continuations import open_legacy, path, prepared, rows

from sim2act import text_run_checks
from sim2act.db import (
    internal_app_runs,
    internal_instance_data,
    internal_instances,
    internal_run_bindings,
    new_id,
    operations,
    runs,
)


class RunCellObserver(PrivateReadBarrier):
    """Observe real SQLite cell evaluation without changing the cell value."""

    def __init__(self, store, foreign_id):
        super().__init__(store, {foreign_id})
        self.rules = {"runs": self.rules["runs"]}

    def _cell(self, table, rid, column, value):
        fact = {"table": table, "row_id": rid, "column": column}
        self.evaluated.append(fact)
        if rid in self.rules[table][2]:
            self.blocked.append(fact)
        return value


def command(data, phase):
    if phase == "commit":
        _, _, body = prepared(data)
        return path(data[3]), body
    _, _, client, info = data
    options = client.get("/api/projects/" + info["project"] + "/software-continuation-options")
    assert options.status_code == 200, options.text
    chosen = next(x for x in options.json()["items"] if x["id"] == info["instance"]["id"])
    return path(info).replace("software-continuations", "software-continuation-preflights"), dict(
        expected_revision=chosen["revision"], expected_release_fingerprint=chosen["release_fingerprint"],
        expected_candidate_fingerprint=chosen["fingerprint"], expected_source_implementation=chosen["source_implementation"],
        input={"term": "Alpha"}, request_key="boundary-preflight")


def save(info, phase, case, proof):
    folder = os.environ.get("SIM2ACT_CONTINUATION_BOUNDARY_DIR")
    if folder:
        target = Path(folder)
        target.mkdir(parents=True, exist_ok=True)
        name = info["software_fp"][:8] + ("-failed" if info.get("failed_old_run_id") else "")
        (target / f"{name}-{phase}-{case}.json").write_text(json.dumps(proof, indent=2) + "\n")


def verifier_calls(monkeypatch):
    calls = []
    original = text_run_checks.verify

    def observed(store, c, user, job, limits, **kwargs):
        calls.append(job["id"])
        return original(store, c, user, job, limits, **kwargs)

    monkeypatch.setattr(text_run_checks, "verify", observed)
    return calls


@pytest.mark.parametrize("phase", ["prepare", "commit"])
@pytest.mark.parametrize("scope", ["principal_id", "project_id", "runtime_id"])
def test_wrong_linked_run_scope_is_excluded_before_private_cell_evaluation(legacy, phase, scope):
    store, _, client, info = legacy
    url, body = command(legacy, phase)
    with store.tx() as c:
        foreign = dict(c.execute(select(runs).where(runs.c.id == info["successful_old_run_id"])).mappings().one())
        foreign_id = new_id("synthetic_foreign_run")
        foreign.update(id=foreign_id, request_key="synthetic-foreign-" + scope,
                       context={"private": "synthetic foreign context"}, result={"private": "synthetic foreign result"})
        foreign[scope] = new_id("synthetic_foreign_scope")
        c.execute(runs.insert().values(**foreign))
        c.execute(update(internal_run_bindings).where(internal_run_bindings.c.run_id == info["successful_old_run_id"])
                  .values(run_id=foreign_id))
    before = rows(store)
    observer = RunCellObserver(store, foreign_id)
    with observer:
        # Calibrate actual evaluation independently of the product request.
        with store.tx() as c:
            assert c.execute(select(runs.c.context, runs.c.result).where(runs.c.id == foreign_id)).first()
        calibration = list(observer.blocked)
        assert {x["column"] for x in calibration} == {"context", "result"}
        observer.blocked.clear()
        observer.evaluated.clear()
        observer.statements.clear()
        reply = client.post(url, json=body)
        private_cells = list(observer.blocked)
        statements = list(observer.statements)
    after = rows(store)
    save(info, phase, scope, dict(kind="SYNTHETIC_WRONG_LINK_NOT_REAL_ATTACK", scope=scope,
        foreign_run=foreign_id, calibration=calibration, private_cell_evaluations=private_cells,
        statements=statements, response_status=reply.status_code, response=reply.json(),
        database_unchanged=after == before))
    assert reply.status_code == 409 and after == before, reply.text
    assert private_cells == [], private_cells


@pytest.mark.parametrize("phase", ["prepare", "commit"])
def test_succeeded_job_missing_typed_is_verified_and_rejected_without_writes(legacy, phase, monkeypatch):
    store, _, client, info = legacy
    url, body = command(legacy, phase)
    with store.tx() as c:
        c.execute(delete(internal_instance_data).where(internal_instance_data.c.instance_id == info["instance"]["id"]))
        c.execute(update(internal_instances).where(internal_instances.c.id == info["instance"]["id"]).values(data_version=0))
    before = rows(store)
    calls = verifier_calls(monkeypatch)
    reply = client.post(url, json=body)
    after = rows(store)
    save(info, phase, "missing-typed", dict(response_status=reply.status_code, response=reply.json(),
        verified_jobs=calls, succeeded_job=info["successful_old_run_id"], database_unchanged=after == before))
    assert reply.status_code == 409 and after == before, reply.text
    assert info["successful_old_run_id"] in calls


@pytest.mark.parametrize("phase", ["prepare", "commit"])
@pytest.mark.parametrize("residual", ["app-output", "app-version", "run-result", "typed", "verified-operation"])
def test_failed_job_with_any_result_residue_enters_complete_verification(legacy_failure, phase, residual, monkeypatch):
    store, _, client, info = legacy_failure
    url, body = command(legacy_failure, phase)
    failed = info["failed_old_run_id"]
    with store.tx() as c:
        aid = c.execute(select(internal_run_bindings.c.app_run_id).where(internal_run_bindings.c.run_id == failed)).scalar_one()
        if residual == "app-output":
            c.execute(update(internal_app_runs).where(internal_app_runs.c.id == aid).values(output={"synthetic": "unexpected residual"}))
        elif residual == "app-version":
            c.execute(update(internal_app_runs).where(internal_app_runs.c.id == aid).values(result_version=99))
        elif residual == "run-result":
            c.execute(update(runs).where(runs.c.id == failed).values(result={"synthetic": "unexpected residual"}))
        elif residual == "typed":
            row = dict(c.execute(select(internal_instance_data).where(internal_instance_data.c.instance_id == info["instance"]["id"])).mappings().one())
            row.update(version=2, run_id=aid)
            c.execute(internal_instance_data.insert().values(**row))
            c.execute(update(internal_instances).where(internal_instances.c.id == info["instance"]["id"]).values(data_version=2))
        else:
            existing = c.execute(select(operations.c.id).where(operations.c.run_id == failed, operations.c.call_id == "instance_result")).scalar_one_or_none()
            if existing:
                c.execute(update(operations).where(operations.c.id == existing).values(status="VERIFIED"))
            else:
                op = dict(c.execute(select(operations).where(operations.c.run_id == info["successful_old_run_id"], operations.c.call_id == "instance_result")).mappings().one())
                op.update(id=new_id("synthetic_verified_operation"), run_id=failed)
                c.execute(operations.insert().values(**op))
    before = rows(store)
    calls = verifier_calls(monkeypatch)
    reply = client.post(url, json=body)
    after = rows(store)
    save(info, phase, residual, dict(response_status=reply.status_code, response=reply.json(),
        verified_jobs=calls, failed_job=failed, database_unchanged=after == before,
        fault="synthetic persisted residue; original old failed Worker had no typed result"))
    assert reply.status_code in {400, 409} and after == before, reply.text
    assert failed in calls


def test_actual_old_unrun_instance_can_continue_with_empty_data(legacy):
    store, _, client, info = legacy
    empty = copy.deepcopy(info)
    empty["instance"] = empty["other_instance"]
    data = (store, legacy[1], client, empty)
    before = rows(store)
    _, _, body = prepared(data)
    reply = client.post(path(empty), json=body)
    assert reply.status_code == 201 and reply.json()["data_version_at_commit"] == 0, reply.text
    current = client.get("/api/internal/instances/" + empty["instance"]["id"])
    assert current.status_code == 200 and current.json()["data_version"] == 0
    assert rows(store)["internal_instance_data"] == before["internal_instance_data"]


@pytest.fixture(params=["233-empty-terminals", "a747-empty-terminals"])
def legacy_empty_terminal(request, tmp_path, monkeypatch):
    yield from open_legacy(request.param, tmp_path, monkeypatch)


@pytest.mark.parametrize("terminal", ["FAILED", "CANCELLED"])
def test_actual_old_result_free_terminal_instance_remains_eligible(legacy_empty_terminal, terminal):
    store, settings, client, info = legacy_empty_terminal
    selected = copy.deepcopy(info)
    selected["instance"] = selected["terminal_only_instances"][terminal]["instance"]
    old_job = selected["terminal_only_instances"][terminal]["run"]
    data = (store, settings, client, selected)
    before = rows(store)
    _, _, body = prepared(data)
    reply = client.post(path(selected), json=body)
    assert reply.status_code == 201 and reply.json()["data_version_at_commit"] == 0, reply.text
    current = client.get("/api/internal/instances/" + selected["instance"]["id"] + "/runs/" + old_job["id"])
    assert current.status_code == 200, current.text
    assert current.json()["status"] == terminal and current.json()["result_version"] is None
    assert current.json()["result"] is None and current.json()["known_effects"] == []
    assert rows(store)["internal_instance_data"] == before["internal_instance_data"]
