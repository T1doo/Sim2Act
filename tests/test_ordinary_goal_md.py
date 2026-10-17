"""Prospective ordinary saved Goal -> real MD; synthetic Mock, never semantic signoff."""

import hashlib
import json

import pytest
from sqlalchemy import select, update
from test_ordinary_owner_review import decision, prepare, review

from sim2act.db import grants, operations, run_contracts, runs
from sim2act.model import MockModel
from sim2act.worker import Worker

REPORT = "# 工程合成报告😀\r\n原材料中的未决事项仍需本人核对。\r\n<script>window.mdUnsafe=true</script>\r\n"


def card(env):
    source = (
        env[2]
        .post(
            f"/api/projects/{env[5]}/resources",
            json=dict(
                name="notes.txt", format="txt", content="合成材料：允许 Alpha；例外 Beta 尚待确认。"
            ),
        )
        .json()["id"]
    )
    body = dict(
        title="明确交付一个MD",
        goal="读取所选说明，保存一份完整MD，保留例外和未决事项。",
        known=["这是合成数据"],
        assumptions=["含义需本人核对"],
        unresolved=["例外语义尚未验收"],
        constraints=["仅本项目一个MD"],
        acceptance_checks=["保存完整文件并可回读", "不遗漏未决事项"],
        resource_refs=[source],
    )
    result = env[2].post(f"/api/projects/{env[5]}/goal-cards", json=body)
    assert result.status_code == 201, result.text
    return result.json(), source


def start(env, goal, key="md-first", route="reviewable-artifact-runs"):
    return env[2].post(
        f"/api/projects/{env[5]}/goal-cards/{goal['id']}/{route}",
        json=dict(
            expected_version=goal["version"],
            expected_fingerprint=goal["fingerprint"],
            request_key=key,
        ),
    )


class ScriptedMd(MockModel):
    def __init__(self, source, mode="normal"):
        self.source, self.mode, self.calls = source, mode, 0

    def request(self, messages, tools):
        self.calls += 1
        feedback = [m for m in messages if m["role"] == "tool"]
        allowed = {t["function"]["name"] for t in tools}
        assert ("artifact.save_text" in allowed) == (self.mode != "v1")
        if not feedback:
            calls = [("read", "resource.read", {"resource_id": self.source})]
        elif len(feedback) == 1 and self.mode != "missing":
            calls = [("save", "artifact.save_text", {"text": REPORT})]
            if self.mode == "two":
                calls.append(("save-again", "artifact.save_text", {"text": REPORT + "second"}))
        elif self.mode == "sequential" and len(feedback) == 2:
            calls = [("save-again", "artifact.save_text", {"text": REPORT + "second"})]
        else:
            calls = []
        message = {"role": "assistant", "content": "SIMULATED 工程返回；语义未验收"}
        if calls:
            message["tool_calls"] = [
                dict(id=i, type="function", function=dict(name=name, arguments=json.dumps(args)))
                for i, name, args in calls
            ]
        return dict(
            model="MOCK-intern-contract",
            usage=None,
            choices=[dict(finish_reason="tool_calls" if calls else "stop", message=message)],
        )


def execute(env, mode="normal"):
    goal, source = card(env)
    r = start(env, goal)
    assert r.status_code == 202, r.text
    model = ScriptedMd(source, mode)
    assert Worker(env[0], env[1], model).once()
    result = env[2].get("/api/runs/" + r.json()["run_id"])
    assert result.status_code == 200, result.text
    return goal, source, r.json(), model, result.json()


def test_explicit_md_contract_actual_artifact_same_run_and_simulated_declaration(env, tmp_path):
    goal, source, receipt, model, result = execute(env)
    rid = receipt["run_id"]
    assert result["status"] == "PARTIAL" and result["result"]["goal_acceptance"] == "NOT_RUN"
    assert model.calls == 3
    policy = result["contract"]["snapshot"]["artifact_delivery"]
    assert policy["required"] is True and policy["format"] == "md" and policy["max_artifacts"] == 1
    assert result["contract"]["snapshot"]["human_review"]["version"] == "owner.ordinary-goal-md.v2"
    output = result["artifact_delivery"]
    assert output["status"] == "DELIVERED" and len(output["artifacts"]) == 1
    file = output["artifacts"][0]
    assert file["content"] == REPORT and file["hash"] == hashlib.sha256(REPORT.encode()).hexdigest()
    assert file["project_id"] == env[5] and file["format"] == "md" and file["id"] != source
    with env[0].tx() as c:
        derived = (
            c.execute(select(grants).where(grants.c.resource_id == file["id"])).mappings().all()
        )
        assert len(derived) == 2 and {r["tool_ref"] for r in derived} == {"resource.read"}
        assert (
            len(
                c.execute(
                    select(operations).where(
                        operations.c.run_id == rid, operations.c.tool_ref == "artifact.save_text"
                    )
                ).all()
            )
            == 1
        )
    current, _, _ = prepare(env, rid)
    assert current["current"]["artifacts"] == [file]
    declared = review(env, rid, "post", decision(env, rid))
    assert declared.status_code == 201, declared.text
    assert review(env, rid).json()["owner_acceptance"] == "ACCEPTED"
    assert start(env, goal).json()["run_id"] == rid
    assert env[2].get("/api/runs/" + rid).json() == result
    (tmp_path / "actual-md-proof.json").write_text(
        json.dumps(
            dict(
                goal=goal,
                receipt=receipt,
                result=result,
                declaration=declared.json(),
                synthetic_model_calls=model.calls,
                real_model_calls=0,
                real_human_signoff="NOT_RUN",
            ),
            ensure_ascii=False,
            indent=2,
        )
    )


@pytest.mark.parametrize("mode", ["missing", "two", "sequential"])
def test_required_file_and_one_save_bound_no_false_delivery_or_signoff(env, mode):
    _, _, receipt, _, result = execute(env, mode)
    rid = receipt["run_id"]
    assert result["status"] == "FAILED" and result["error"]["code"] == "VERIFICATION_FAILED"
    assert result["artifact_delivery"]["status"] == "INCOMPLETE"
    expected = 1 if mode == "sequential" else 0
    assert len(result["artifact_delivery"]["artifacts"]) == expected
    state = review(env, rid).json()
    assert not state["content_access"] and "current" not in state
    with env[0].tx() as c:
        saved = c.execute(
            select(operations.c.id).where(
                operations.c.run_id == rid, operations.c.tool_ref == "artifact.save_text"
            )
        ).all()
        assert len(saved) == expected


@pytest.mark.parametrize("target", ["project-save", "source-read", "artifact-read"])
def test_current_permissions_protect_execution_and_declaration(env, target):
    goal, source = card(env)
    with env[0].tx() as c:
        if target == "project-save":
            c.execute(
                update(grants)
                .where(
                    grants.c.principal_id == env[3],
                    grants.c.resource_id == env[5],
                    grants.c.tool_ref == "artifact.save_text",
                )
                .values(revoked=True)
            )
    if target == "project-save":
        assert start(env, goal).status_code == 403
        with env[0].tx() as c:
            assert not c.execute(select(runs)).first()
        return
    receipt = start(env, goal).json()
    rid = receipt["run_id"]
    assert Worker(env[0], env[1], ScriptedMd(source)).once()
    _, _, _ = prepare(env, rid)
    intent = decision(env, rid)
    data = env[2].get("/api/runs/" + rid).json()
    file = data["artifact_delivery"]["artifacts"][0]
    with env[0].tx() as c:
        c.execute(
            update(grants)
            .where(
                grants.c.principal_id == env[3],
                grants.c.resource_id == (source if target == "source-read" else file["id"]),
                grants.c.tool_ref == "resource.read",
            )
            .values(revoked=True)
        )
    assert env[2].get("/api/runs/" + rid).status_code == 403
    assert review(env, rid, "post", intent).status_code == 403
    state = review(env, rid).json()
    assert (
        state["owner_acceptance"] == "STALE"
        and not state["content_access"]
        and "record" not in state
    )


@pytest.mark.parametrize("damage", ["strip", "tool-fingerprint", "integer-bool", "integer-float"])
def test_md_policy_cannot_be_removed_or_relabelled_after_acceptance(env, damage):
    from sim2act.db import fingerprint

    goal, source = card(env)
    rid = start(env, goal).json()["run_id"]
    with env[0].tx() as c:
        contract = c.execute(
            select(run_contracts.c.snapshot).where(run_contracts.c.run_id == rid)
        ).scalar_one()
        if damage == "strip":
            contract.pop("artifact_delivery")
        elif damage == "tool-fingerprint":
            contract["artifact_delivery"]["tool_definitions_fingerprint"] = "0" * 64
        else:
            contract["artifact_delivery"]["max_artifacts"] = (
                True if damage == "integer-bool" else 1.0
            )
        c.execute(
            update(run_contracts)
            .where(run_contracts.c.run_id == rid)
            .values(snapshot=contract, fingerprint=fingerprint(contract))
        )
    model = ScriptedMd(source)
    assert Worker(env[0], env[1], model).once()
    assert model.calls == 0
    with env[0].tx() as c:
        assert not c.execute(select(operations)).first()


def test_original_call_retrieves_exact_file_and_new_call_cannot_write_again(env):
    from sim2act.db import resources
    from sim2act.errors import DomainError
    from sim2act.tools import dispatch

    goal, source = card(env)
    rid = start(env, goal).json()["run_id"]
    job = env[0].claim("synthetic-md-gateway", 30)
    assert job["id"] == rid
    call = dict(id="one-save", function={"name": "artifact.save_text"}, args={"text": REPORT})
    receipt = dispatch(env[0], rid, job["fence"], call)
    assert dispatch(env[0], rid, job["fence"], call) == receipt
    with pytest.raises(DomainError) as conflict:
        dispatch(env[0], rid, job["fence"], {**call, "id": "second-save"})
    assert conflict.value.code == "VERIFICATION_FAILED"
    with env[0].tx() as c:
        assert (
            len(
                c.execute(
                    select(resources).where(resources.c.id == receipt["data"]["resource_id"])
                ).all()
            )
            == 1
        )
        assert (
            len(
                c.execute(
                    select(grants).where(grants.c.resource_id == receipt["data"]["resource_id"])
                ).all()
            )
            == 2
        )
        assert len(c.execute(select(operations).where(operations.c.run_id == rid)).all()) == 1
    # This test exercises the real gateway on an unfinished synthetic Run, not a completed Worker.


def test_current_project_write_revoke_between_model_read_and_save_has_no_effect(env):
    goal, source = card(env)
    rid = start(env, goal).json()["run_id"]

    class RevokeBeforeSave(ScriptedMd):
        def request(self, messages, tools):
            if self.calls == 1:
                with env[0].tx() as c:
                    c.execute(
                        update(grants)
                        .where(
                            grants.c.principal_id == env[3],
                            grants.c.resource_id == env[5],
                            grants.c.tool_ref == "artifact.save_text",
                        )
                        .values(revoked=True)
                    )
            return super().request(messages, tools)

    model = RevokeBeforeSave(source)
    assert Worker(env[0], env[1], model).once() and model.calls == 2
    with env[0].tx() as c:
        row = c.execute(select(runs).where(runs.c.id == rid)).mappings().one()
        assert row["status"] == "WAITING_RESOURCE"
        assert not c.execute(
            select(operations).where(
                operations.c.run_id == rid, operations.c.tool_ref == "artifact.save_text"
            )
        ).first()


def test_final_commit_and_independent_owner_reject_altered_artifact_format(env, monkeypatch):
    from sim2act.db import resources

    goal, source = card(env)
    rid = start(env, goal).json()["run_id"]
    original = Worker.finish

    def alter(self, run_id, fence, state, *args, **kwargs):
        if state == "PARTIAL":
            with self.store.tx() as c:
                receipt = c.execute(
                    select(operations.c.receipt).where(
                        operations.c.run_id == rid, operations.c.tool_ref == "artifact.save_text"
                    )
                ).scalar_one()
                c.execute(
                    update(resources)
                    .where(resources.c.id == receipt["data"]["resource_id"])
                    .values(format="json")
                )
        return original(self, run_id, fence, state, *args, **kwargs)

    monkeypatch.setattr(Worker, "finish", alter)
    assert Worker(env[0], env[1], ScriptedMd(source)).once()
    with env[0].tx() as c:
        row = c.execute(select(runs).where(runs.c.id == rid)).mappings().one()
        assert row["status"] == "FAILED" and row["result"] is None
    denied = env[2].get("/api/runs/" + rid)
    assert denied.status_code == 400 and denied.json()["error"]["code"] == "VERIFICATION_FAILED"
    assert not review(env, rid).json()["content_access"]
