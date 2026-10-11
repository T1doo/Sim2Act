"""Received rejected JSON is preserved; a true lost response invents none."""

import copy
import hashlib
import json

import pytest
import test_goal_text_applications as helper
from sqlalchemy import select, update

from sim2act.db import attempts, events, fingerprint, operations, run_contracts


@pytest.mark.parametrize("fault", ["usage", "identity", "truncated", "refusal"])
def test_received_rejected_original_json_is_preserved(env, fault):
    data = helper.setup(env)
    received = {}

    def mutation(raw, index, payload):
        if index != 1:
            return
        if fault == "usage":
            raw.pop("usage")
        elif fault == "identity":
            raw["model"] = "other"
        elif fault == "truncated":
            raw["choices"][0]["finish_reason"] = "length"
        else:
            raw["choices"][0]["message"]["refusal"] = "Synthetic refused fixture; no external model"
        received.update(copy.deepcopy(raw))

    rid, result, sent = helper.generate(data, mutation=mutation)
    assert len(sent) == 1 and result["result"] is None and result["status"] != "PARTIAL"
    with data[0].tx() as c:
        row = c.execute(select(attempts).where(attempts.c.run_id == rid)).mappings().one()
    original = row["parameters"]["generation_rejected_raw"]
    assert row["status"] == "FAILED"
    assert len(original.encode("ascii")) <= 32768
    assert json.loads(original) == received
    assert (
        json.loads(original)["choices"][0]["message"]["tool_calls"]
        == received["choices"][0]["message"]["tool_calls"]
    )


@pytest.mark.parametrize(
    "fault", ["wrong-target", "second-tools", "wrong-goal", "repair", "terminal"]
)
def test_rejection_after_received_preserves_original_json(env, fault, capsys):
    data = helper.setup(env)
    received = {}
    secret = "SYNTHETIC_PRIVATE_REASONING_FOR_" + fault

    def mutation(raw, index, payload):
        raw["id"] = "synthetic-response-" + str(index)
        raw["choices"][0]["message"]["reasoning_content"] = secret
        if fault == "wrong-target" and index == 1:
            raw["choices"][0]["message"]["tool_calls"][0]["function"]["arguments"] = json.dumps(
                {"resource_id": env[6]}
            )
        elif fault == "second-tools" and index == 2:
            raw["choices"][0] = {
                "finish_reason": "tool_calls",
                "message": {
                    "role": "assistant",
                    "content": "",
                    "reasoning_content": secret,
                    "tool_calls": [
                        {
                            "id": "forbidden-candidate-read",
                            "type": "function",
                            "function": {
                                "name": "resource.read",
                                "arguments": json.dumps({"resource_id": data[5]}),
                            },
                        }
                    ],
                },
            }
        elif fault == "wrong-goal" and index == 2:
            value = json.loads(raw["choices"][0]["message"]["content"])
            value["goal"]["constraints"] = []
            raw["choices"][0]["message"]["content"] = json.dumps(value)
        elif fault in {"repair", "terminal"} and index == 2 or fault == "terminal" and index == 3:
            value = json.loads(raw["choices"][0]["message"]["content"])
            value["manifest"]["workflow"][0]["inputs"].pop("term")
            raw["choices"][0]["message"]["content"] = json.dumps(value)
        received[index] = copy.deepcopy(raw)

    rid, result, sent = helper.generate(data, mutation=mutation)
    with data[0].tx() as c:
        rows = (
            c.execute(
                select(attempts).where(attempts.c.run_id == rid).order_by(attempts.c.created_at)
            )
            .mappings()
            .all()
        )
    rejected = [1] if fault == "wrong-target" else [2, 3] if fault == "terminal" else [2]
    for index in rejected:
        assert rows[index - 1]["status"] == "RECEIVED"
        original = rows[index - 1]["parameters"]["generation_rejected_raw"]
        assert len(original.encode("ascii")) <= 32768
        assert json.loads(original) == received[index]
    assert (result["status"] == "PARTIAL") is (fault == "repair")
    if fault != "repair":
        assert result["result"] is None
    assert secret not in json.dumps(result)
    assert secret not in capsys.readouterr().out
    denied = data[2].get(f"/api/runs/{rid}", headers={"Authorization": "Bearer synthetic-test-B"})
    assert denied.status_code == 403 and secret not in denied.text


def test_oversized_original_json_cannot_execute_and_is_explicitly_omitted(env):
    data = helper.setup(env)
    received = {}

    def mutation(raw, index, payload):
        raw["extra_opaque"] = "SYNTHETIC_PRIVATE_OVERSIZE" * 1600
        received.update(copy.deepcopy(raw))

    rid, result, sent = helper.generate(data, mutation=mutation)
    original = json.dumps(received, ensure_ascii=True, allow_nan=False, separators=(",", ":"))
    with data[0].tx() as c:
        row = c.execute(select(attempts).where(attempts.c.run_id == rid)).mappings().one()
        assert not c.execute(select(operations.c.id).where(operations.c.run_id == rid)).all()
    metadata = row["parameters"]["generation_raw_evidence"]
    assert metadata == {
        "status": "OMITTED_OVERSIZE",
        "bytes": len(original.encode("ascii")),
        "sha256": hashlib.sha256(original.encode("ascii")).hexdigest(),
    }
    assert "generation_rejected_raw" not in row["parameters"]
    assert "generation_received_raw" not in row["parameters"]
    assert len(sent) == 1 and result["status"] == "FAILED" and result["result"] is None
    assert "SYNTHETIC_PRIVATE_OVERSIZE" not in json.dumps(result)


@pytest.mark.parametrize("tamper", ["resigned-raw", "stripped-archives", "stripped-policy"])
def test_new_archive_policy_and_original_response_cannot_be_downgraded(env, tamper):
    data = helper.setup(env)
    rid, result, _ = helper.generate(data, repair=True)
    aid, _ = helper.confirm(data, rid, result)
    with data[0].tx() as c:
        rows = c.execute(select(attempts).where(attempts.c.run_id == rid)).mappings().all()
        if tamper == "resigned-raw":
            row = rows[-1]
            parameters = copy.deepcopy(row["parameters"])
            raw = json.loads(parameters["generation_received_raw"])
            raw["changed_opaque"] = "SYNTHETIC_AUDIT_TAMPER"
            original = json.dumps(raw, ensure_ascii=True, separators=(",", ":"))
            parameters["generation_received_raw"] = original
            parameters["generation_raw_evidence"] = {
                "status": "COMPLETE",
                "bytes": len(original),
                "sha256": hashlib.sha256(original.encode("ascii")).hexdigest(),
            }
            c.execute(
                update(attempts).where(attempts.c.id == row["id"]).values(parameters=parameters)
            )
        elif tamper == "stripped-archives":
            for row in rows:
                parameters = {
                    key: value
                    for key, value in row["parameters"].items()
                    if key
                    not in {
                        "generation_received_raw",
                        "generation_rejected_raw",
                        "generation_raw_evidence",
                    }
                }
                c.execute(
                    update(attempts).where(attempts.c.id == row["id"]).values(parameters=parameters)
                )
            for event in (
                c.execute(
                    select(events).where(events.c.run_id == rid, events.c.kind == "GA_RECEIVED")
                )
                .mappings()
                .all()
            ):
                payload = dict(event["data"])
                payload.pop("raw_fingerprint")
                c.execute(update(events).where(events.c.id == event["id"]).values(data=payload))
        else:
            contract = copy.deepcopy(
                c.execute(
                    select(run_contracts.c.snapshot).where(run_contracts.c.run_id == rid)
                ).scalar_one()
            )
            contract["application_generation"].pop("response_archive_policy")
            c.execute(
                update(run_contracts)
                .where(run_contracts.c.run_id == rid)
                .values(snapshot=contract, fingerprint=fingerprint(contract))
            )
    assert data[2].get(f"/api/apps/{aid}").status_code == 409


def test_legacy_shaped_acceptance_remains_readable_without_inventing_raw(env, monkeypatch):
    from sim2act import goal_applications

    original_policy = goal_applications.policy

    def legacy_policy(*args):
        value = original_policy(*args)
        value.pop("response_archive_policy")
        return value

    monkeypatch.setattr(goal_applications, "policy", legacy_policy)
    data = helper.setup(env)
    rid, result, _ = helper.generate(data, repair=True)
    aid, _ = helper.confirm(data, rid, result)
    with data[0].tx() as c:
        for row in c.execute(select(attempts).where(attempts.c.run_id == rid)).mappings().all():
            parameters = {
                key: value
                for key, value in row["parameters"].items()
                if key
                not in {
                    "generation_received_raw",
                    "generation_rejected_raw",
                    "generation_raw_evidence",
                }
            }
            c.execute(
                update(attempts).where(attempts.c.id == row["id"]).values(parameters=parameters)
            )
        for event in (
            c.execute(select(events).where(events.c.run_id == rid, events.c.kind == "GA_RECEIVED"))
            .mappings()
            .all()
        ):
            payload = dict(event["data"])
            payload.pop("raw_fingerprint")
            c.execute(update(events).where(events.c.id == event["id"]).values(data=payload))
    assert data[2].get(f"/api/apps/{aid}").status_code == 200
    with data[0].tx() as c:
        rows = (
            c.execute(select(attempts.c.parameters).where(attempts.c.run_id == rid)).scalars().all()
        )
    assert all("generation_received_raw" not in row for row in rows)
