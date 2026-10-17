"""Explicit ordinary correction; synthetic reasons, users and models only."""

import copy
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, event, select, update
from test_goal_card_runs import authority
from test_ordinary_goal_md import REPORT, ScriptedMd, execute
from test_ordinary_owner_review import decision, prepare, review

from sim2act.api import create_app
from sim2act.db import (
    fingerprint,
    goal_card_versions,
    grants,
    operations,
    ordinary_correction_links,
    ordinary_owner_records,
    ordinary_owner_seals,
    resources,
    run_contracts,
    runs,
)
from sim2act.model import MockModel
from sim2act.worker import Worker


def rejected(env, md=True):
    if md:
        goal, source, receipt, model, result = execute(env)
        rid = receipt["run_id"]
    else:
        from test_goal_card_runs import card
        from test_ordinary_owner_review import execute as execute_readonly

        goal, _ = card(env)
        source = env[6]
        rid = execute_readonly(env, goal)
        result = env[2].get(f"/api/runs/{rid}").json()
    prepare(env, rid)
    body = decision(env, rid, accept=False)
    body["choices"][0]["reason"] = (
        "SIMULATED: retain Beta exception, do not grant access <script>unsafe()</script>"
    )
    response = review(env, rid, "post", body)
    assert response.status_code == 201, response.text
    return goal, source, rid, result, response.json()["record"]


def post(env, rid, body):
    return env[2].post(f"/api/runs/{rid}/correction-runs", json=body)


def original_rows(store, rid):
    with store.tx() as c:
        return {
            t.name: [
                dict(r)
                for r in c.execute(
                    select(t).where((t.c.id if t is runs else t.c.run_id) == rid)
                ).mappings()
            ]
            for t in (runs, run_contracts, ordinary_owner_records, ordinary_owner_seals)
        } | {
            "goal_history": [dict(r) for r in c.execute(select(goal_card_versions)).mappings()],
            "resources": {r["id"]: dict(r) for r in c.execute(select(resources)).mappings()},
        }


class CorrectionModel(ScriptedMd):
    def __init__(self, source, expected, md=True, before_save=None):
        super().__init__(source)
        self.expected, self.md, self.before_save, self.observed = expected, md, before_save, []

    def request(self, messages, tools):
        data = json.loads(messages[1]["content"])
        assert data["human_correction"]["feedback"] == self.expected
        assert (
            messages[1]["role"] == "user"
            and len([m for m in messages if m["role"] == "system"]) == 1
        )
        self.observed.append(copy.deepcopy(dict(input=data, tools=tools)))
        if self.before_save and any(m["role"] == "tool" for m in messages):
            callback, self.before_save = self.before_save, None
            callback()
        if self.md:
            result = super().request(messages, tools)
            for call in result["choices"][0]["message"].get("tool_calls", []):
                if call["function"]["name"] == "artifact.save_text":
                    call["function"]["arguments"] = json.dumps(
                        dict(text=REPORT + "SIMULATED correction; not semantic proof\n")
                    )
            return result
        self.calls += 1
        return MockModel.request(self, messages, tools)


def preview(env, rid):
    response = env[2].get(f"/api/runs/{rid}/correction-preview")
    assert response.status_code == 200, response.text
    return response.json()


def correction_body(value, key="explicit-correction"):
    return dict(
        expected_preview_fingerprint=value["preview_fingerprint"],
        declaration_id=value["feedback"]["declaration_id"],
        declaration_fingerprint=value["feedback"]["declaration_fingerprint"],
        expected_sequence=value["feedback"]["declaration_sequence"],
        request_key=key,
        consent="RUN_NEW_CORRECTION_KEEP_GOAL_CRITERIA_AND_HISTORY",
    )


def test_rejected_ordinary_result_previews_exact_new_request_without_mutation(env, tmp_path):
    goal, source, rid, result, declaration = rejected(env)
    value = preview(env, rid)
    assert value["parent_run_id"] == rid
    assert value["feedback"]["declaration_id"] == declaration["id"]
    assert value["feedback"]["issues"][0]["reason"].startswith("SIMULATED: retain Beta")
    assert value["source_goal"]["version"] == goal["version"]
    assert value["source_goal"]["snapshot"]["content"]["resource_refs"] == [source]
    assert env[2].get(f"/api/runs/{rid}").json() == result
    (tmp_path / "preview.json").write_text(json.dumps(value, ensure_ascii=False, indent=2))


@pytest.mark.parametrize("md", [True, False])
def test_explicit_new_run_preserves_parent_and_receives_exact_feedback(env, tmp_path, md):
    goal, source, parent, before, declaration = rejected(env, md)
    rows = original_rows(env[0], parent)
    auth = authority(env[0])
    value = preview(env, parent)
    assert original_rows(env[0], parent) == rows and authority(env[0]) == auth
    body = correction_body(value)
    response = post(env, parent, body)
    assert response.status_code == 202, response.text
    accepted = response.json()
    child = accepted["run_id"]
    assert child != parent and accepted["request_fingerprint"] == fingerprint(body)
    assert original_rows(env[0], parent) == rows and authority(env[0]) == auth
    assert post(env, parent, body).json() == accepted
    changed = {**body, "expected_preview_fingerprint": "0" * 64}
    assert post(env, parent, changed).status_code == 409
    queued = env[2].get(f"/api/runs/{child}").json()
    frozen = queued["contract"]["snapshot"]
    assert queued["status"] == "QUEUED" and queued["result"] is None
    assert frozen["source_goal_card"] == before["contract"]["snapshot"]["source_goal_card"]
    assert frozen["resources"] == before["contract"]["snapshot"]["resources"]
    assert frozen["ordinary_correction"]["feedback"] == value["feedback"]
    assert frozen["goal"] == before["contract"]["snapshot"]["goal"]
    model = CorrectionModel(source, value["feedback"], md)
    assert Worker(env[0], env[1], model).once()
    result = env[2].get(f"/api/runs/{child}")
    assert result.status_code == 200, result.text
    result = result.json()
    assert result["status"] == "PARTIAL" and result["result"]["goal_acceptance"] == "NOT_RUN"
    assert model.calls == (3 if md else 2)
    assert all(
        (
            {t["function"]["name"] for t in observed["tools"]}
            == (
                {"resource.read", "data.aggregate_csv", "artifact.save_text"}
                if md
                else {"resource.read", "data.aggregate_csv"}
            )
        )
        for observed in model.observed
    )
    assert env[2].get(f"/api/runs/{parent}").json() == before
    after = original_rows(env[0], parent)
    assert {k: v for k, v in after.items() if k != "resources"} == {
        k: v for k, v in rows.items() if k != "resources"
    }
    assert all(after["resources"][k] == v for k, v in rows["resources"].items())
    if md:
        artifact = result["artifact_delivery"]["artifacts"][0]
        assert artifact["content"].endswith("SIMULATED correction; not semantic proof\n")
        assert artifact["id"] != before["artifact_delivery"]["artifacts"][0]["id"]
        with env[0].tx() as c:
            assert (
                len(c.execute(select(grants).where(grants.c.resource_id == artifact["id"])).all())
                == 2
            )
    else:
        assert authority(env[0]) == auth
    state = review(env, child).json()
    assert (
        state["owner_acceptance"] == "PENDING"
        and state["current"]["human_correction"]["feedback"] == value["feedback"]
    )
    prepare(env, child)
    manual = review(env, child, "post", decision(env, child))
    assert manual.status_code == 201 and manual.json()["record"]["status"] == "ACCEPTED"
    assert env[2].get(f"/api/runs/{child}").json() == result
    assert (
        env[2].get(f"/api/runs/{parent}/correction-requests/{body['request_key']}").json()
        == accepted
    )
    assert post(env, parent, body).json() == accepted
    assert env[2].get(f"/api/runs/{child}/correction-preview").status_code == 409
    (tmp_path / "actual-correction.json").write_text(
        json.dumps(
            dict(
                preview=value,
                body=body,
                receipt=accepted,
                parent_before=before,
                parent_after=env[2].get(f"/api/runs/{parent}").json(),
                result=result,
                model_calls=model.calls,
                model_inputs=model.observed,
                real_model_calls=0,
                real_human_signoff="NOT_RUN",
            ),
            ensure_ascii=False,
            indent=2,
        )
    )


@pytest.mark.parametrize(
    "change",
    [
        "goal",
        "source-read",
        "output-read",
        "project-save",
        "declaration",
        "source-content",
        "result",
        "seal",
    ],
)
def test_changed_preview_or_current_authority_never_accepts_new_run(env, change):
    goal, source, parent, result, declaration = rejected(env)
    body = correction_body(preview(env, parent))
    with env[0].tx() as c:
        if change in {"source-read", "output-read", "project-save"}:
            target = (
                source
                if change == "source-read"
                else env[5]
                if change == "project-save"
                else result["artifact_delivery"]["artifacts"][0]["id"]
            )
            c.execute(
                update(grants)
                .where(
                    grants.c.principal_id == env[3],
                    grants.c.resource_id == target,
                    grants.c.tool_ref
                    == ("artifact.save_text" if change == "project-save" else "resource.read"),
                )
                .values(revoked=True)
            )
        elif change == "source-content":
            c.execute(
                update(resources).where(resources.c.id == source).values(content="different source")
            )
        elif change == "result":
            c.execute(
                update(runs)
                .where(runs.c.id == parent)
                .values(result={**result["result"], "answer": "changed"})
            )
        elif change == "seal":
            c.execute(
                update(ordinary_owner_seals)
                .where(ordinary_owner_seals.c.record_id == declaration["id"])
                .values(metadata_fingerprint="0" * 64)
            )
    if change == "goal":
        content = env[2].get(f"/api/goal-cards/{goal['id']}").json()["content"]
        assert (
            env[2]
            .put(
                f"/api/goal-cards/{goal['id']}",
                json={**content, "expected_version": goal["version"], "goal": "new Goal"},
            )
            .status_code
            == 200
        )
    if change == "declaration":
        assert (
            review(
                env,
                parent,
                "post",
                dict(
                    command="REVOKE",
                    target_id=declaration["id"],
                    target_fingerprint=declaration["fingerprint"],
                    expected_sequence=2,
                    request_key="explicit-revoke",
                    reason="Withdraw correction source",
                ),
            ).status_code
            == 201
        )
    response = post(env, parent, body)
    assert response.status_code in (400, 403, 409), response.text
    with env[0].tx() as c:
        assert len(c.execute(select(runs)).all()) == 1
        assert not c.execute(select(ordinary_correction_links)).first()


@pytest.mark.parametrize(
    "change",
    ["source-read", "output-read", "declaration", "feedback", "resumed-input", "live-worker"],
)
def test_accepted_child_rechecks_before_any_model_or_tool_dispatch(env, change):
    _, source, parent, result, declaration = rejected(env)
    value = preview(env, parent)
    made = post(env, parent, correction_body(value))
    assert made.status_code == 202, made.text
    child = made.json()["run_id"]
    with env[0].tx() as c:
        if change in {"source-read", "output-read"}:
            target = (
                source
                if change == "source-read"
                else result["artifact_delivery"]["artifacts"][0]["id"]
            )
            c.execute(
                update(grants)
                .where(grants.c.principal_id == env[3], grants.c.resource_id == target)
                .values(revoked=True)
            )
        elif change == "feedback":
            value_snapshot = copy.deepcopy(
                c.execute(
                    select(run_contracts.c.snapshot).where(run_contracts.c.run_id == child)
                ).scalar_one()
            )
            value_snapshot["ordinary_correction"]["feedback"]["issues"][0]["reason"] = (
                "coherent rewritten feedback"
            )
            c.execute(
                update(run_contracts)
                .where(run_contracts.c.run_id == child)
                .values(snapshot=value_snapshot, fingerprint=fingerprint(value_snapshot))
            )
        elif change == "resumed-input":
            from sim2act.model import SYSTEM_PROMPT

            ctx = dict(c.execute(select(runs.c.context).where(runs.c.id == child)).scalar_one())
            ctx["messages"] = [
                dict(role="system", content=SYSTEM_PROMPT),
                dict(role="user", content=json.dumps({"goal": "changed"})),
            ]
            c.execute(update(runs).where(runs.c.id == child).values(context=ctx))
    if change == "declaration":
        assert (
            review(
                env,
                parent,
                "post",
                dict(
                    command="REVOKE",
                    target_id=declaration["id"],
                    target_fingerprint=declaration["fingerprint"],
                    expected_sequence=2,
                    request_key="withdraw-after-accept",
                    reason="Withdraw original",
                ),
            ).status_code
            == 201
        )
    model = CorrectionModel(source, value["feedback"])
    Worker(
        env[0], replace(env[1], live_enabled=True) if change == "live-worker" else env[1], model
    ).once()
    assert model.calls == 0
    with env[0].tx() as c:
        assert not c.execute(select(operations).where(operations.c.run_id == child)).first()


def test_between_model_feedback_and_save_authority_is_rechecked(env):
    _, source, parent, result, _ = rejected(env)
    value = preview(env, parent)
    response = post(env, parent, correction_body(value))
    assert response.status_code == 202, response.text
    child = response.json()["run_id"]

    def revoke():
        with env[0].tx() as c:
            c.execute(
                update(grants)
                .where(grants.c.principal_id == env[3], grants.c.resource_id == source)
                .values(revoked=True)
            )

    model = CorrectionModel(source, value["feedback"], before_save=revoke)
    Worker(env[0], env[1], model).once()
    assert model.calls == 2
    with env[0].tx() as c:
        assert not c.execute(
            select(operations).where(
                operations.c.run_id == child, operations.c.tool_ref == "artifact.save_text"
            )
        ).first()


def test_one_child_unique_and_concurrent_different_keys_cannot_create_siblings(env):
    _, _, parent, _, _ = rejected(env)
    value = preview(env, parent)
    with ThreadPoolExecutor(max_workers=2) as pool:
        replies = list(
            pool.map(
                lambda key: post(env, parent, correction_body(value, key)),
                ["one-child-A", "one-child-B"],
            )
        )
    assert sorted(r.status_code for r in replies) == [202, 409], [r.text for r in replies]
    accepted = next(r.json() for r in replies if r.status_code == 202)
    with env[0].tx() as c:
        assert len(c.execute(select(runs)).all()) == 2
        assert len(c.execute(select(ordinary_correction_links)).all()) == 1
        c.execute(
            delete(ordinary_correction_links).where(
                ordinary_correction_links.c.run_id == accepted["run_id"]
            )
        )
    assert post(env, parent, correction_body(value, "third-key")).status_code == 409
    with env[0].tx() as c:
        assert len(c.execute(select(runs)).all()) == 2


def test_exact_consent_schema_identity_and_mock_admission_required(env):
    _, _, parent, _, _ = rejected(env)
    body = correction_body(preview(env, parent))
    for changed in (
        {**body, "consent": ""},
        {**body, "issues": []},
        {**body, "expected_sequence": True},
    ):
        assert post(env, parent, changed).status_code == 422
    other = TestClient(create_app(env[0], replace(env[1], live_enabled=True)))
    other.headers.update(env[2].headers)
    assert other.get(f"/api/runs/{parent}/correction-preview").status_code == 403
    assert other.post(f"/api/runs/{parent}/correction-runs", json=body).status_code == 403
    other.close()
    env[2].headers["Authorization"] = "Bearer synthetic-test-B"
    assert env[2].get(f"/api/runs/{parent}/correction-preview").status_code == 403
    assert post(env, parent, body).status_code == 403


def test_parent_effect_authority_precedes_child_feedback_body_with_damaged_receipt(env):
    _, _, parent, result, _ = rejected(env)
    made = post(env, parent, correction_body(preview(env, parent)))
    assert made.status_code == 202, made.text
    child = made.json()["run_id"]
    with env[0].tx() as c:
        operation = (
            c.execute(
                select(operations).where(
                    operations.c.run_id == parent, operations.c.tool_ref == "artifact.save_text"
                )
            )
            .mappings()
            .one()
        )
        c.execute(
            update(operations)
            .where(operations.c.id == operation["id"])
            .values(receipt={**operation["receipt"], "artifact_refs": []})
        )
        c.execute(
            update(grants)
            .where(
                grants.c.principal_id == env[3],
                grants.c.resource_id == result["artifact_delivery"]["artifacts"][0]["id"],
            )
            .values(revoked=True)
        )
    statements = []

    def trace(connection, cursor, statement, parameters, context, many):
        statements.append(statement)

    event.listen(env[0].engine, "before_cursor_execute", trace)
    try:
        assert env[2].get(f"/api/runs/{child}").status_code == 403
    finally:
        event.remove(env[0].engine, "before_cursor_execute", trace)
    assert not any(
        "runs.goal" in sql or "SELECT run_contracts.run_id, run_contracts.snapshot" in sql
        for sql in statements
    )


def test_final_commit_rechecks_rejection_and_preserves_already_saved_child_file(
    env, monkeypatch, tmp_path
):
    _, source, parent, _, declaration = rejected(env)
    value = preview(env, parent)
    accepted = post(env, parent, correction_body(value))
    assert accepted.status_code == 202, accepted.text
    child = accepted.json()["run_id"]
    worker = Worker(env[0], env[1], CorrectionModel(source, value["feedback"]))
    original, withdrawn = worker.finish, []

    def finish(run_id, fence, state, *args, **kwargs):
        if state == "PARTIAL" and not withdrawn:
            response = review(
                env,
                parent,
                "post",
                dict(
                    command="REVOKE",
                    target_id=declaration["id"],
                    target_fingerprint=declaration["fingerprint"],
                    expected_sequence=2,
                    request_key="withdraw-at-final-commit",
                    reason="SIMULATED stop after known save",
                ),
            )
            assert response.status_code == 201, response.text
            withdrawn.append(response.json())
        return original(run_id, fence, state, *args, **kwargs)

    monkeypatch.setattr(worker, "finish", finish)
    worker.once()
    assert withdrawn and worker.model.calls == 3
    with env[0].tx() as c:
        run = dict(c.execute(select(runs).where(runs.c.id == child)).mappings().one())
        saved = dict(
            c.execute(
                select(operations).where(
                    operations.c.run_id == child, operations.c.tool_ref == "artifact.save_text"
                )
            )
            .mappings()
            .one()
        )
        assert run["status"] != "PARTIAL" and run["result"] is None
        assert saved["status"] == "VERIFIED"
        artifact = saved["receipt"]["artifact_refs"][0]
        assert len(c.execute(select(grants).where(grants.c.resource_id == artifact)).all()) == 2
        assert (
            c.execute(select(resources.c.id).where(resources.c.id == artifact)).scalar_one()
            == artifact
        )
        assert len(c.execute(select(runs)).all()) == 2
    assert (
        post(env, parent, correction_body(value, "no-new-child-after-failure")).status_code == 409
    )
    (tmp_path / "known-save-rejected-final.json").write_text(
        json.dumps(
            dict(run=run, saved=saved, withdrawal=withdrawn, real_model_requests=0),
            ensure_ascii=False,
            indent=2,
        )
    )
