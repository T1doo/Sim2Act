"""Synthetic prospective CSV sum-only owner declarations; never a model claim."""

import copy
import json
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import pytest
from sqlalchemy import event, select, update
from test_internal_lifecycle import create
from test_internal_lifecycle import release as make_release
from test_natural_receipt_candidate import table_snapshot
from test_ordinary_csv_extraction import options_body
from test_ordinary_csv_extraction import setup as ordinary_source
from test_persistent_app_runs import NoModel, setup

from sim2act import csv_owner_review as human
from sim2act.db import (
    csv_owner_records,
    csv_owner_seals,
    fingerprint,
    grants,
    internal_app_runs,
    internal_instance_data,
    internal_run_bindings,
    operations,
    resources,
    runs,
)
from sim2act.worker import Worker


def test_prospective_csv_sum_scope(env):
    release, instance, _, _ = setup(env)
    response = env[2].post(
        f"/api/internal/instances/{instance['id']}/runs",
        json=dict(
            expected_revision=instance["revision"],
            expected_release_fingerprint=release["fingerprint"],
            input={"column": "amount"},
            request_key="freeze-csv-scope",
            csv_review="FREEZE_SUM_ONLY_WITHOUT_MD",
        ),
    )
    assert response.status_code == 202, response.text
    state = env[2].get(
        f"/api/internal/instances/{instance['id']}/runs/{response.json()['run_id']}/csv-owner-review"
    )
    assert state.status_code == 200, state.text
    assert state.json()["content_access"] is False


def start(env, rel, instance, key="csv-review", review=True):
    body = dict(
        expected_revision=instance["revision"],
        expected_release_fingerprint=rel["fingerprint"],
        input={"column": "amount"},
        request_key=key,
    )
    if review:
        body["csv_review"] = human.CONSENT
    response = env[2].post(f"/api/internal/instances/{instance['id']}/runs", json=body)
    assert response.status_code == 202, response.text
    return response.json()["run_id"], body


def endpoint(i, rid):
    return f"/api/internal/instances/{i['id']}/runs/{rid}/csv-owner-review"


def state(env, i, rid, key=None):
    response = env[2].get(endpoint(i, rid), params={"request_key": key} if key else None)
    assert response.status_code == 200, response.text
    return response.json()


def prepare_review(env, i, rid):
    current = state(env, i, rid)
    assert current["content_access"], current
    request = dict(
        command="PREPARE",
        expected_sequence=current["sequence"],
        request_key="prepare",
        expected_contract_fingerprint=fingerprint(current["current"]),
    )
    response = env[2].post(endpoint(i, rid) + "-requests", json=request)
    assert response.status_code == 201, response.text
    return current, response.json()["record"], request


def choices(prepared, accept=True):
    return dict(
        command="DECIDE",
        expected_sequence=prepared["sequence"],
        request_key="decide",
        review_id=prepared["id"],
        review_fingerprint=prepared["fingerprint"],
        choices=[
            dict(
                item_id=item["id"],
                decision="ACCEPT" if accept or n else "REJECT",
                reason="Synthetic declaration only; not a real person or semantic validation",
            )
            for n, item in enumerate(human.ITEMS)
        ],
    )


@pytest.mark.parametrize("accept", [True, False])
def test_sum_only_exact_result_explicit_choices_idempotent_and_no_authority(env, tmp_path, accept):
    rel, instance, _, _ = setup(env)
    rid, request = start(env, rel, instance)
    with env[0].tx() as c:
        frozen = c.execute(
            select(internal_run_bindings.c.snapshot).where(internal_run_bindings.c.run_id == rid)
        ).scalar_one()
    assert frozen["csv_owner_review"]["scope"] == "SUM_ONLY_WITHOUT_MD"
    assert frozen["csv_owner_review"]["input"] == request["input"]
    assert not state(env, instance, rid)["content_access"]
    assert Worker(env[0], env[1], NoModel()).once()
    before = table_snapshot(env[0])
    original = env[2].get(f"/api/runs/{rid}").json()
    current, prepared, body = prepare_review(env, instance, rid)
    assert current["current"]["result_version"] == 1
    assert current["current"]["release_fingerprint"] == rel["fingerprint"]
    assert current["current"]["output"] == original["result"]
    intent = choices(prepared, accept)
    for invalid in (
        intent["choices"][:-1],
        list(reversed(intent["choices"])),
        [{**x, "reason": " "} for x in intent["choices"]],
    ):
        assert env[2].post(
            endpoint(instance, rid) + "-requests", json={**intent, "choices": invalid}
        ).status_code in (400, 409)
    with ThreadPoolExecutor(2) as pool:
        replies = list(
            pool.map(
                lambda _: env[2].post(endpoint(instance, rid) + "-requests", json=intent), range(2)
            )
        )
    assert all(r.status_code == 201 for r in replies), [r.text for r in replies]
    assert replies[0].json() == replies[1].json()
    saved = state(env, instance, rid, "decide")
    assert saved["owner_acceptance"] == ("ACCEPTED" if accept else "REJECTED")
    assert (
        saved["semantic_goal_acceptance"] == "NOT_RUN" and saved["full_md_report_included"] is False
    )
    assert (
        saved["current"]["technical_status"] == "SUCCEEDED"
        and saved["current"]["independent_sum_check"] == "PASS"
    )
    changed = copy.deepcopy(intent)
    changed["choices"][0]["reason"] = "different"
    assert env[2].post(endpoint(instance, rid) + "-requests", json=changed).status_code == 409
    after = table_snapshot(env[0])
    assert all(
        before[k] == after[k] for k in before if k not in {"csv_owner_records", "csv_owner_seals"}
    )
    assert env[2].get(f"/api/runs/{rid}").json() == original
    (tmp_path / "declaration.json").write_text(
        json.dumps(
            dict(
                frozen=frozen,
                before=original,
                current=current,
                prepare=body,
                decision=intent,
                state=saved,
                real_model_requests=0,
            ),
            ensure_ascii=False,
            indent=2,
        )
    )


def test_no_retroactive_scope_new_result_does_not_inherit_or_sign_old_run(env):
    rel, i, _, _ = setup(env)
    old, _ = start(env, rel, i, "old", review=False)
    assert Worker(env[0], env[1], NoModel()).once()
    assert not state(env, i, old)["content_access"]
    rid, _ = start(env, rel, i)
    assert Worker(env[0], env[1], NoModel()).once()
    _, p, _ = prepare_review(env, i, rid)
    assert env[2].post(endpoint(i, rid) + "-requests", json=choices(p)).status_code == 201
    newer, _ = start(env, rel, i, "newer")
    assert state(env, i, rid)["owner_acceptance"] == "STALE"
    assert Worker(env[0], env[1], NoModel()).once()
    assert (
        state(env, i, newer)["owner_acceptance"] == "PENDING"
        and state(env, i, newer)["sequence"] == 0
    )
    assert state(env, i, rid)["owner_acceptance"] == "STALE"
    assert not state(env, i, old)["content_access"]
    other = create(env, rel)
    assert env[2].get(endpoint(other, rid)).status_code == 403
    assert (
        env[2]
        .get(endpoint(i, rid), headers={"Authorization": "Bearer synthetic-test-B"})
        .status_code
        == 403
    )


@pytest.mark.parametrize(
    "change",
    ["grant", "grant_redirect", "typed", "expiry", "seal", "receipt_bool", "receipt_float"],
)
def test_current_authority_result_expiry_seal_and_metadata_stop(env, tmp_path, change):
    rel, i, _, _ = setup(env)
    rid, _ = start(env, rel, i)
    assert Worker(env[0], env[1], NoModel()).once()
    _, p, _ = prepare_review(env, i, rid)
    intent = choices(p)
    sql = []
    if change in {"grant", "grant_redirect"}:
        with env[0].tx() as c:
            c.execute(
                update(grants).where(grants.c.principal_id == i["runtime_id"]).values(revoked=True)
            )
    if change == "grant_redirect":
        spare = (
            env[2]
            .post(
                f"/api/projects/{env[5]}/resources",
                json=dict(name="spare.csv", format="csv", content="amount\n8\n"),
            )
            .json()["id"]
        )
        with env[0].tx() as c:
            c.execute(update(runs).where(runs.c.id == rid).values(resource_refs=[spare]))
    elif change in {"receipt_bool", "receipt_float"}:
        with env[0].tx() as c:
            op = c.execute(select(operations).where(operations.c.run_id == rid)).mappings().one()
            receipt = {**op["receipt"], "result_version": True if change == "receipt_bool" else 1.0}
            c.execute(update(operations).where(operations.c.id == op["id"]).values(receipt=receipt))
    elif change == "typed":
        with env[0].tx() as c:
            c.execute(
                update(internal_instance_data)
                .where(internal_instance_data.c.instance_id == i["id"])
                .values(fingerprint="0" * 64)
            )
    elif change == "seal":
        with env[0].tx() as c:
            c.execute(
                update(csv_owner_seals)
                .where(csv_owner_seals.c.record_id == p["id"])
                .values(metadata_fingerprint="0" * 64)
            )
    event.listen(
        env[0].engine,
        "before_cursor_execute",
        lambda conn, cursor, statement, *args: sql.append(statement),
    )
    with (
        patch("sim2act.owner_acceptance.time.time", return_value=__import__("time").time() + 901)
        if change == "expiry"
        else patch("sim2act.owner_acceptance.MAX_RECORDS", 256)
    ):
        response = env[2].post(endpoint(i, rid) + "-requests", json=intent)
    assert response.status_code in (400, 403, 409), response.text
    if change != "seal":
        stale = state(env, i, rid)
        if change in ("grant", "grant_redirect", "typed", "receipt_bool", "receipt_float"):
            assert not stale["content_access"] and stale["owner_acceptance"] == "STALE"
        stopped = env[2].post(
            endpoint(i, rid) + "-requests",
            json=dict(
                command="CANCEL",
                expected_sequence=1,
                request_key="stop",
                target_id=p["id"],
                target_fingerprint=p["fingerprint"],
                reason="explicit synthetic stop",
            ),
        )
        assert stopped.status_code == 201, stopped.text
        assert state(env, i, rid)["owner_acceptance"] == "CANCELLED"
    if change in {"grant", "grant_redirect"}:
        assert not any(
            "runs.result" in s
            or "csv_owner_records.payload" in s
            or "internal_instance_data.data" in s
            for s in sql
        )
    (tmp_path / "scope-sql.json").write_text(json.dumps(sql, indent=2))


def test_final_commit_change_rolls_back_and_original_key_receipt_readonly(env, monkeypatch):
    rel, i, _, _ = setup(env)
    rid, _ = start(env, rel, i)
    assert Worker(env[0], env[1], NoModel()).once()
    _, p, _ = prepare_review(env, i, rid)
    original = human.final_gate

    def changed(store, c, user, iid, run_id, limits, fresh, **kw):
        c.execute(
            update(grants).where(grants.c.principal_id == i["runtime_id"]).values(revoked=True)
        )
        original(store, c, user, iid, run_id, limits, fresh, **kw)

    monkeypatch.setattr(human, "final_gate", changed)
    response = env[2].post(endpoint(i, rid) + "-requests", json=choices(p))
    assert response.status_code in (403, 409), response.text
    assert (
        response.json()["error"]["submission_rejection"]["namespace"]
        == "csv-owner-submission-rejection.v1"
    )
    with env[0].tx() as c:
        assert len(c.execute(select(csv_owner_records)).all()) == 1
    assert state(env, i, rid)["sequence"] == 1
    assert env[2].get(endpoint(i, rid), params={"request_key": "absent"}).status_code == 409


def test_ordinary_success_derived_sum_declaration_keeps_complete_md_contract_separate(
    env, tmp_path
):
    origin, original, target, _ = ordinary_source(env)
    _, body = options_body(env, origin, target)
    made = env[2].post(f"/api/runs/{origin}/csv-sum-candidates", json=body).json()
    rel, _, _ = make_release(env, made["id"], made["candidate_fingerprint"])
    i = create(env, rel)
    rid, _ = start(env, rel, i)
    assert Worker(env[0], env[1], NoModel()).once()
    _, p, _ = prepare_review(env, i, rid)
    response = env[2].post(endpoint(i, rid) + "-requests", json=choices(p))
    assert response.status_code == 201, response.text
    review = state(env, i, rid)
    assert review["owner_acceptance"] == "ACCEPTED" and not review["full_md_report_included"]
    assert env[2].get(f"/api/runs/{origin}").json() == original
    assert "source_goal" not in review["current"]
    (tmp_path / "ordinary-separate.json").write_text(
        json.dumps(dict(original=original, review=review), ensure_ascii=False, indent=2)
    )


@pytest.mark.parametrize("case", ["deliver", "lost", "navigation"])
def test_actual_page_prospective_csv_declaration(env, tmp_path, case):
    import hashlib
    import os
    import subprocess
    import threading
    from pathlib import Path

    from sim2act.db import Store

    material = (
        env[2]
        .post(
            f"/api/projects/{env[5]}/resources",
            json=dict(
                name="two-columns.csv", format="csv", content="amount,quantity\n1.25,6\n2.75,9\n"
            ),
        )
        .json()["id"]
    )
    rel, i, _, _ = setup((*env[:6], material))
    env[0].project(env[4], "other account")
    before = table_snapshot(env[0])
    info = dict(
        case=case, project=env[5], instance=i["id"], output=str(tmp_path / "page-result.json")
    )
    (tmp_path / "info.json").write_text(json.dumps(info))
    worker_results = []
    process = None
    watchdog = None
    try:
        with (tmp_path / "node.stderr").open("w") as errors:
            process = subprocess.Popen(
                ["node", "tests/csv_owner_ui.cjs", str(tmp_path / "info.json")],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=errors,
                text=True,
                env={
                    **os.environ,
                    "NODE_PATH": str(Path.cwd() / "scripts/engineering-ci/node_modules"),
                },
            )
            watchdog = threading.Timer(90, process.kill)
            watchdog.start()
            for line in process.stdout:
                request = json.loads(line)
                if request.get("done"):
                    break
                if request.get("command") == "worker":
                    cold = Store(env[1].database_url, test_only=True)
                    try:
                        assert Worker(cold, env[1], NoModel()).once()
                    finally:
                        cold.engine.dispose()
                    result = env[2].get(f"/api/runs/{request['run']}")
                    assert result.status_code == 200, result.text
                    worker_results.append(result.json())
                    answer = dict(status=200, text="{}")
                elif request.get("command") == "revoke":
                    with env[0].tx() as c:
                        c.execute(
                            update(grants)
                            .where(grants.c.principal_id == i["runtime_id"])
                            .values(revoked=True)
                        )
                    answer = dict(status=200, text="{}")
                else:
                    response = env[2].request(
                        request["method"],
                        request["path"],
                        json=request.get("body"),
                        headers=request.get("headers") or {},
                    )
                    answer = dict(
                        status=response.status_code,
                        text=response.text,
                        content_type=response.headers.get("content-type"),
                    )
                process.stdin.write(json.dumps(dict(id=request["id"], **answer)) + "\n")
                process.stdin.flush()
            process.stdin.close()
            code = process.wait(timeout=15)
        assert code == 0, (tmp_path / "node.stderr").read_text()
        result = json.loads((tmp_path / "page-result.json").read_text())
        assert result["status"] == "PASS"
        for asset in result["assets"]:
            p = Path("src/sim2act/web") / (asset["path"].lstrip("/") or "index.html")
            assert hashlib.sha256(p.read_bytes()).hexdigest() == asset["sha256"]
        assert len(worker_results) == 1 and worker_results[0]["status"] == "SUCCEEDED"
        after = table_snapshot(env[0])
        assert (
            before["resources"] == after["resources"]
            and before["principals"] == after["principals"]
        )
        assert len(after["grants"]) == len(before["grants"])
    finally:
        if watchdog:
            watchdog.cancel()
        if process and process.poll() is None:
            process.kill()
            process.wait(timeout=10)
        (tmp_path / "page-worker-proof.json").write_text(
            json.dumps(
                dict(worker_results=worker_results, real_model_requests=0),
                ensure_ascii=False,
                indent=2,
            )
        )


def test_coherent_old_run_rehash_cannot_create_prospective_declaration(env, tmp_path):
    rel, i, _, _ = setup(env)
    rid, _ = start(env, rel, i, review=False)
    assert Worker(env[0], env[1], NoModel()).once()
    with env[0].tx() as c:
        b = (
            c.execute(select(internal_run_bindings).where(internal_run_bindings.c.run_id == rid))
            .mappings()
            .one()
        )
        s = copy.deepcopy(b["snapshot"])
        source = c.execute(select(resources).where(resources.c.id == env[6])).mappings().one()
        s["csv_review"] = human.CONSENT
        s["csv_owner_review"] = human.prospective(rel, source, s["input"], human.CONSENT)
        request = {
            k: s[k]
            for k in [
                "instance_id",
                "expected_revision",
                "expected_release_fp",
                "input",
                "csv_review",
            ]
        }
        s["request_fingerprint"] = fingerprint(request)
        c.execute(
            update(internal_run_bindings)
            .where(internal_run_bindings.c.run_id == rid)
            .values(snapshot=s, fingerprint=fingerprint(s))
        )
        c.execute(update(runs).where(runs.c.id == rid).values(fingerprint=fingerprint(s)))
        c.execute(
            update(internal_app_runs)
            .where(internal_app_runs.c.id == b["app_run_id"])
            .values(fingerprint=fingerprint(request))
        )
    before = table_snapshot(env[0])
    reviewed = state(env, i, rid)
    assert not reviewed["content_access"] and "current" not in reviewed
    response = env[2].post(
        endpoint(i, rid) + "-requests",
        json=dict(
            command="PREPARE",
            request_key="no-retroactive",
            expected_sequence=0,
            expected_contract_fingerprint="0" * 64,
        ),
    )
    assert response.status_code == 409, response.text
    assert table_snapshot(env[0]) == before
    assert before["csv_owner_records"] == before["csv_owner_seals"] == []
    (tmp_path / "coherent-retroactive.json").write_text(
        json.dumps(
            dict(binding=s, state=reviewed, rejection=response.json()), ensure_ascii=False, indent=2
        )
    )
