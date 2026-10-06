"""Offline real Store/Worker/InternModel wire integration; synthetic evaluation only."""

import copy
import json
from dataclasses import replace
from pathlib import Path

import httpx
import pytest
from sqlalchemy import select, update

from sim2act.config import Settings
from sim2act.db import Store, attempts, fingerprint, grants, principals, protocol_jobs, runs
from sim2act.errors import DomainError
from sim2act.model import InternModel
from sim2act.model_budget import BudgetedProvider, initialize_ledger
from sim2act.model_protocol import obj
from sim2act.protocol_api import ProtocolAttemptRunner
from sim2act.protocol_jobs import enqueue, inspect, process_job
from sim2act.protocol_reviews import contract_snapshot, evaluation_contract, review
from sim2act.worker import Worker

ROOT = Path(__file__).resolve().parents[1]
LIMITS = __import__("sim2act.contracts", fromlist=["Limits"]).Limits(
    max_requests=3,
    max_tools=4,
    max_repairs=0,
    max_total_tokens=64000,
    max_output_tokens=1024,
    run_seconds=300,
)


def wire(value=None, rid=None):
    message = {"role": "assistant", "content": json.dumps(value, ensure_ascii=False)}
    if rid:
        message = {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "material_read",
                    "type": "function",
                    "function": {
                        "name": "resource.read",
                        "arguments": json.dumps({"resource_id": rid}),
                    },
                }
            ],
        }
    return {
        "model": "intern-s2",
        "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20},
        "choices": [{"message": message, "finish_reason": "tool_calls" if rid else "stop"}],
    }


@pytest.fixture
def env(tmp_path):
    store = Store("sqlite:///" + str(tmp_path / "jobs.sqlite"), test_only=True)
    store.initialize()
    user = store.user("synthetic protocol owner", "secret test token")
    pid = store.project(user, "synthetic protocol project")
    materials = ROOT / "docs/evidence/model-protocol-preparation-20261006/materials"
    a = store.resource(user, pid, "A source", "md", (materials / "a-source/policy.txt").read_text())
    b = store.resource(user, pid, "A unseen", "md", (materials / "a-cold/policy.txt").read_text())
    s = Settings(database_url="sqlite://", data_dir=tmp_path, max_requests=3, max_repairs=0)
    worker = Worker(store, s)
    return store, user, pid, a, b, worker, tmp_path


def source_payload(rid):
    contract, _ = evaluation_contract("protocol.synthetic.a-source.v1")
    return {
        "contract_id": contract["id"],
        "goal": contract["public_goal"],
        "inputs": contract["expected_inputs"],
        "resource_ids": [rid],
    }


def factory_for(env, responses, stage):
    store, user, pid, a, b, worker, tmp_path = env
    requests = []

    def factory(worker, run, snapshot):
        pending = list(responses)

        def transport(request):
            requests.append(json.loads(request.content))
            return httpx.Response(200, json=pending.pop(0))

        model = InternModel(
            replace(worker.s, live_enabled=True, token="synthetic offline token"),
            transport=httpx.MockTransport(transport),
        )
        path = tmp_path / (run["id"] + ".json")
        initialize_ledger(path, snapshot["scope"])
        clock = [0]

        def now():
            clock[0] += 7
            return clock[0]

        def authorize(scope):
            with store.tx() as c:
                for ref in scope["resource_ids"]:
                    store.authorize(c, user, run["runtime_id"], pid, ref, "resource.read")
            return True

        provider = BudgetedProvider(
            model, path, snapshot["scope"], stage, authorize=authorize, clock=now
        )
        return ProtocolAttemptRunner(worker, run, snapshot, provider)

    worker.protocol_runner_factory = factory
    return requests


def execute(env):
    worker = env[5]
    claimed = worker.store.claim(worker.id, worker.s.lease_seconds)
    assert claimed
    process_job(worker, claimed)
    return inspect(worker.store, env[1], claimed["id"])


def reviewed_source(env):
    store, user, pid, a, b, worker, tmp = env
    accepted = enqueue(store, user, pid, "source", source_payload(a), "source", LIMITS)
    contract, _ = evaluation_contract("protocol.synthetic.a-source.v1")
    factory_for(env, [wire(rid=a), wire(contract["expected_output"])], "source_a")
    complete = execute(env)
    decision = review(
        store,
        user,
        accepted["run_id"],
        {
            "contract_id": contract["id"],
            "expected_result_fingerprint": complete["result_fingerprint"],
            "expected_fence": complete["fence"],
            "expected_version": complete["version"],
            "request_key": "review-source",
        },
    )
    assert decision["decision"] == "PASS"
    return inspect(store, user, accepted["run_id"])


def test_source_technical_completion_waits_for_independent_review_and_preserves_authority(env):
    store, user, pid, a, b, worker, tmp = env
    with store.engine.connect() as c:
        before = (c.execute(select(grants)).all(), c.execute(select(principals)).all())
    enqueue(store, user, pid, "source", source_payload(a), "source", LIMITS)
    contract, _ = evaluation_contract("protocol.synthetic.a-source.v1")
    requests = factory_for(env, [wire(rid=a), wire(contract["expected_output"])], "source_a")
    done = execute(env)
    assert done["status"] == "WAITING_APPROVAL"
    assert done["result"]["protocol_result"]["semantic_status"] == "UNKNOWN"
    assert done["result"]["protocol_result"]["verification"] is None
    assert len(done["result"]["operation_refs"]) == 1 and len(done["result"]["attempt_refs"]) == 2
    assert len(requests) == 2
    assert (
        enqueue(store, user, pid, "source", source_payload(a), "source", LIMITS)["cached"] is True
    )
    with store.engine.connect() as c:
        assert before == (c.execute(select(grants)).all(), c.execute(select(principals)).all())
        assert all(row.status == "RECEIVED" for row in c.execute(select(attempts)).all())


def test_default_provider_missing_waits_without_calls(env):
    store, user, pid, a, b, worker, tmp = env
    enqueue(store, user, pid, "source", source_payload(a), "source", LIMITS)
    done = execute(env)
    assert done["status"] == "WAITING_RESOURCE" and done["error"]["code"] == "RESOURCE_UNAVAILABLE"
    with store.engine.connect() as c:
        assert not c.execute(select(attempts)).first()


@pytest.mark.parametrize(
    "change",
    [
        {"contract_id": "unknown"},
        {"replay": []},
        {"candidate": {}},
        {"gold": {}},
        {"resource_ids": ["res_" + "f" * 32]},
    ],
)
def test_closed_request_and_unregistered_or_foreign_material_fail_before_enqueue(env, change):
    store, user, pid, a, *_ = env
    with pytest.raises(DomainError):
        enqueue(store, user, pid, "source", {**source_payload(a), **change}, "reject", LIMITS)
    with store.engine.connect() as c:
        assert not c.execute(select(runs)).first()


@pytest.mark.parametrize(
    "tamper", [None, "cold_response", "cold_response_parameter_rehash", "cold_operation_callid"]
)
def test_reviewed_source_model_extract_compiles_and_cold_reads_unseen_material(env, tamper):
    store, user, pid, a, b, worker, tmp = env
    source = reviewed_source(env)
    output_schema = contract_snapshot("protocol.synthetic.a-source.v1")["output_schema"]
    candidate = {
        "schema_version": "model-protocol.v1",
        "input_schema": obj({"format": {"type": "string"}}),
        "resources": {"material": a},
        "steps": [
            {
                "id": "read",
                "kind": "registered_tool",
                "depends_on": [],
                "inputs": {
                    "resource_id": {"source": "data", "ref": "material", "field": "resource_id"}
                },
                "tool_ref": "resource.read",
            },
            {
                "id": "interpret",
                "kind": "language",
                "depends_on": ["read"],
                "inputs": {
                    "content": {"source": "step", "ref": "read", "field": "content"},
                    "format": {"source": "input", "ref": "input", "field": "format"},
                },
                "instruction": source_payload(a)["goal"],
                "output_schema": output_schema,
            },
        ],
        "output_schema": output_schema,
        "outputs": {
            k: {"source": "step", "ref": "interpret", "field": k}
            for k in output_schema["properties"]
        },
    }
    enqueue(
        store,
        user,
        pid,
        "extract",
        {
            "source_run_id": source["run_id"],
            "expected_source_fingerprint": source["result_fingerprint"],
        },
        "extract",
        LIMITS,
    )
    factory_for(env, [wire(candidate)], "extract_a")
    extracted = execute(env)
    assert extracted["status"] == "SUCCEEDED"
    plan = extracted["result"]["compiled_plan"]
    cold, _ = evaluation_contract("protocol.synthetic.a-cold.v1")
    enqueue(
        store,
        user,
        pid,
        "cold",
        {
            "contract_id": cold["id"],
            "extraction_run_id": extracted["run_id"],
            "expected_plan_fingerprint": plan["plan_fingerprint"],
            "inputs": cold["expected_inputs"],
            "resource_bindings": {"material": b},
        },
        "cold",
        LIMITS,
    )
    requests = factory_for(env, [wire(cold["expected_output"])], "cold_a")
    completed = execute(env)
    assert completed["status"] == "WAITING_APPROVAL"
    trace = completed["result"]["protocol_result"]["evidence"]["tool_trace"]
    assert trace[0]["args"]["resource_id"] == b
    assert (
        trace[0]["data"]["hash"]
        != source["result"]["protocol_result"]["evidence"]["tool_trace"][0]["data"]["hash"]
    )
    body = json.dumps(requests[0], ensure_ascii=False)
    assert "海岚工作室" not in body
    if tamper:
        if tamper == "cold_operation_callid":
            from sim2act.db import operations

            with store.tx() as c:
                c.execute(
                    update(operations)
                    .where(operations.c.run_id == completed["run_id"])
                    .values(call_id="protocol:unrelated")
                )
            with pytest.raises(DomainError):
                review(
                    store,
                    user,
                    completed["run_id"],
                    {
                        "contract_id": cold["id"],
                        "expected_result_fingerprint": completed["result_fingerprint"],
                        "expected_fence": completed["fence"],
                        "expected_version": completed["version"],
                        "request_key": "tampered-cold-op",
                    },
                )
            return
        with store.tx() as c:
            attempt = (
                c.execute(select(attempts).where(attempts.c.run_id == completed["run_id"]))
                .mappings()
                .one()
            )
            raw = copy.deepcopy(attempt["response"])
            raw["choices"][0]["message"]["content"] = '{"unrelated":true}'
            values = {"response": raw}
            if tamper == "cold_response_parameter_rehash":
                params = copy.deepcopy(attempt["parameters"])
                params["safe_response_fingerprint"] = fingerprint(raw)
                values["parameters"] = params
            c.execute(update(attempts).where(attempts.c.id == attempt["id"]).values(**values))
        with pytest.raises(DomainError):
            review(
                store,
                user,
                completed["run_id"],
                {
                    "contract_id": cold["id"],
                    "expected_result_fingerprint": completed["result_fingerprint"],
                    "expected_fence": completed["fence"],
                    "expected_version": completed["version"],
                    "request_key": "tampered-cold",
                },
            )
        with store.engine.connect() as c:
            assert (
                c.execute(
                    select(runs.c.status).where(runs.c.id == completed["run_id"])
                ).scalar_one()
                == "WAITING_APPROVAL"
            )
        return
    decision = review(
        store,
        user,
        completed["run_id"],
        {
            "contract_id": cold["id"],
            "expected_result_fingerprint": completed["result_fingerprint"],
            "expected_fence": completed["fence"],
            "expected_version": completed["version"],
            "request_key": "review-cold",
        },
    )
    assert decision["decision"] == "PASS"


def test_source_snapshot_coherent_rehash_is_not_accepted(env):
    store, user, pid, a, b, worker, tmp = env
    source = reviewed_source(env)
    changed = copy.deepcopy(source["result"])
    changed["protocol_result"]["evidence"]["output"] = {"invented": "successful"}
    with store.tx() as c:
        c.execute(
            update(protocol_jobs)
            .where(protocol_jobs.c.run_id == source["run_id"])
            .values(result_snapshot=changed, result_fingerprint=fingerprint(changed))
        )
        c.execute(update(runs).where(runs.c.id == source["run_id"]).values(result=changed))
    with pytest.raises(DomainError):
        inspect(store, user, source["run_id"])


def test_source_revoked_runtime_blocks_cached_and_derivation(env):
    store, user, pid, a, b, worker, tmp = env
    source = reviewed_source(env)
    with store.tx() as c:
        c.execute(
            update(grants)
            .where(grants.c.resource_id == a, grants.c.principal_id != user)
            .values(revoked=True)
        )
    with pytest.raises(DomainError, match="GRANT_REVOKED"):
        enqueue(store, user, pid, "source", source_payload(a), "source", LIMITS)
    with pytest.raises(DomainError):
        enqueue(
            store,
            user,
            pid,
            "extract",
            {
                "source_run_id": source["run_id"],
                "expected_source_fingerprint": source["result_fingerprint"],
            },
            "extract",
            LIMITS,
        )


def test_pending_or_ordinary_f1_partial_source_cannot_extract(env):
    store, user, pid, a, b, worker, tmp = env
    source = enqueue(store, user, pid, "source", source_payload(a), "source", LIMITS)
    with pytest.raises(DomainError):
        enqueue(
            store,
            user,
            pid,
            "extract",
            {"source_run_id": source["run_id"], "expected_source_fingerprint": fingerprint(None)},
            "extract",
            LIMITS,
        )
    original = store.submit(user, pid, "ordinary F1 task", [a], "ordinary")
    with store.tx() as c:
        c.execute(update(runs).where(runs.c.id == original).values(status="PARTIAL"))
    with pytest.raises(DomainError):
        enqueue(
            store,
            user,
            pid,
            "extract",
            {"source_run_id": original, "expected_source_fingerprint": fingerprint(None)},
            "extract-other",
            LIMITS,
        )


def test_key_changed_payload_and_wrong_identity_rejected(env):
    store, user, pid, a, b, worker, tmp = env
    source = enqueue(store, user, pid, "source", source_payload(a), "source", LIMITS)
    tighter = LIMITS.model_copy(update={"max_requests": 2})
    with pytest.raises(DomainError, match="VERSION_CONFLICT"):
        enqueue(store, user, pid, "source", source_payload(a), "source", tighter)
    outsider = store.user("other", "other synthetic token")
    with pytest.raises(DomainError, match="PERMISSION_DENIED"):
        inspect(store, outsider, source["run_id"])


def test_live_worker_rejected_before_factory_or_attempt(env):
    store, user, pid, a, b, worker, tmp = env
    enqueue(store, user, pid, "source", source_payload(a), "source", LIMITS)
    worker.s = replace(worker.s, mode="live", live_enabled=True)

    def forbidden(*args):
        raise AssertionError("LIVE factory must not run")

    worker.protocol_runner_factory = forbidden
    done = execute(env)
    assert done["status"] == "FAILED" and done["error"]["code"] == "PERMISSION_DENIED"
    with store.engine.connect() as c:
        assert not c.execute(select(attempts)).first()


def test_received_incomplete_continuation_is_not_implicitly_resent(env):
    store, user, pid, a, b, worker, tmp = env
    source = enqueue(store, user, pid, "source", source_payload(a), "source", LIMITS)
    with store.tx() as c:
        ctx = c.execute(select(runs.c.context).where(runs.c.id == source["run_id"])).scalar_one()
        c.execute(
            update(runs).where(runs.c.id == source["run_id"]).values(context={**ctx, "requests": 1})
        )

    def forbidden(*args):
        raise AssertionError("No implicit resend")

    worker.protocol_runner_factory = forbidden
    done = execute(env)
    assert done["status"] == "WAITING_RESOURCE" and done["error"]["code"] == "OUTCOME_UNKNOWN"


def test_stale_worker_fence_cannot_finalize_or_dispatch(env):
    store, user, pid, a, b, worker, tmp = env
    accepted = enqueue(store, user, pid, "source", source_payload(a), "source", LIMITS)
    claimed = store.claim(worker.id, worker.s.lease_seconds)
    with store.tx() as c:
        c.execute(update(runs).where(runs.c.id == claimed["id"]).values(fence=claimed["fence"] + 1))
    process_job(worker, claimed)
    assert inspect(store, user, accepted["run_id"])["status"] == "RUNNING"
    with store.engine.connect() as c:
        assert not c.execute(select(attempts)).first()


def test_custom_factory_runner_is_rejected_without_model_or_tools(env):
    store, user, pid, a, b, worker, tmp = env
    enqueue(store, user, pid, "source", source_payload(a), "source", LIMITS)
    worker.protocol_runner_factory = lambda *args: object()
    done = execute(env)
    assert done["status"] == "FAILED" and done["error"]["code"] == "PERMISSION_DENIED"
    with store.engine.connect() as c:
        assert not c.execute(select(attempts)).first()


def test_actual_received_tool_call_tamper_blocks_source_reuse(env):
    store, user, pid, a, b, worker, tmp = env
    source = reviewed_source(env)
    with store.tx() as c:
        attempt = (
            c.execute(
                select(attempts)
                .where(attempts.c.run_id == source["run_id"])
                .order_by(attempts.c.created_at)
            )
            .mappings()
            .first()
        )
        raw = copy.deepcopy(attempt["response"])
        raw["choices"][0]["message"]["tool_calls"][0]["function"]["arguments"] = json.dumps(
            {"resource_id": b}
        )
        c.execute(update(attempts).where(attempts.c.id == attempt["id"]).values(response=raw))
    with pytest.raises(DomainError):
        enqueue(
            store,
            user,
            pid,
            "extract",
            {
                "source_run_id": source["run_id"],
                "expected_source_fingerprint": source["result_fingerprint"],
            },
            "extract",
            LIMITS,
        )


@pytest.mark.parametrize(
    "field",
    [
        "tool_ref",
        "operation_id",
        "receipt_ref",
        "check_results",
        "artifact_refs",
        "usage_ref",
        "error",
        "extra",
        "call_id",
        "attempt_call_id",
        "attempt_identity",
    ],
)
def test_operation_and_full_receipt_identity_tampering_rejects_review(env, field):
    from sim2act.db import operations

    store, user, pid, a, b, worker, tmp = env
    accepted = enqueue(store, user, pid, "source", source_payload(a), "source", LIMITS)
    contract, _ = evaluation_contract("protocol.synthetic.a-source.v1")
    factory_for(env, [wire(rid=a), wire(contract["expected_output"])], "source_a")
    complete = execute(env)
    with store.tx() as c:
        operation = (
            c.execute(select(operations).where(operations.c.run_id == accepted["run_id"]))
            .mappings()
            .one()
        )
        if field == "tool_ref":
            c.execute(
                update(operations)
                .where(operations.c.id == operation["id"])
                .values(tool_ref="artifact.save_text")
            )
        elif field == "call_id":
            c.execute(
                update(operations)
                .where(operations.c.id == operation["id"])
                .values(call_id="protocol:unrelated")
            )
        elif field.startswith("attempt"):
            attempt = (
                c.execute(
                    select(attempts)
                    .where(attempts.c.run_id == accepted["run_id"])
                    .order_by(attempts.c.created_at)
                )
                .mappings()
                .first()
            )
            if field == "attempt_call_id":
                raw = copy.deepcopy(attempt["response"])
                raw["choices"][0]["message"]["tool_calls"][0]["id"] = "unrelated"
                c.execute(
                    update(attempts).where(attempts.c.id == attempt["id"]).values(response=raw)
                )
            else:
                parameters = copy.deepcopy(attempt["parameters"])
                parameters["model_identity"]["enforced"] = 1
                c.execute(
                    update(attempts)
                    .where(attempts.c.id == attempt["id"])
                    .values(parameters=parameters)
                )
        else:
            receipt = copy.deepcopy(operation["receipt"])
            receipt[field] = {
                "operation_id": "op_" + "f" * 32,
                "receipt_ref": "op_" + "f" * 32,
                "check_results": [{"check": "receipt.readback.v1", "status": "FAIL"}],
                "artifact_refs": ["res_" + "f" * 32],
                "usage_ref": "invented",
                "error": {"code": "fake"},
                "extra": True,
            }[field]
            c.execute(
                update(operations).where(operations.c.id == operation["id"]).values(receipt=receipt)
            )
    with pytest.raises(DomainError):
        review(
            store,
            user,
            accepted["run_id"],
            {
                "contract_id": contract["id"],
                "expected_result_fingerprint": complete["result_fingerprint"],
                "expected_fence": complete["fence"],
                "expected_version": complete["version"],
                "request_key": "tampered-review",
            },
        )
    with store.engine.connect() as c:
        assert (
            c.execute(select(runs.c.status).where(runs.c.id == accepted["run_id"])).scalar_one()
            == "WAITING_APPROVAL"
        )


def test_revoked_authority_still_allows_metadata_cancel_and_blocks_resume(env):
    from sim2act.protocol_jobs import command_job

    store, user, pid, a, b, worker, tmp = env
    accepted = enqueue(store, user, pid, "source", source_payload(a), "source", LIMITS)
    with store.tx() as c:
        c.execute(update(grants).where(grants.c.resource_id == a).values(revoked=True))
    paused = command_job(store, user, accepted["run_id"], "pause", accepted["version"])
    assert paused["status"] == "PAUSED" and "result" not in paused
    with pytest.raises(DomainError, match="GRANT_REVOKED"):
        command_job(store, user, accepted["run_id"], "resume", paused["version"])
    cancelled = command_job(store, user, accepted["run_id"], "cancel", paused["version"])
    assert cancelled["status"] == "CANCELLED" and "result" not in cancelled


def test_cancel_pending_approval_blocks_review_without_deleting_completed_evidence(env):
    from sim2act.protocol_jobs import command_job

    store, user, pid, a, b, worker, tmp = env
    accepted = enqueue(store, user, pid, "source", source_payload(a), "source", LIMITS)
    contract, _ = evaluation_contract("protocol.synthetic.a-source.v1")
    factory_for(env, [wire(rid=a), wire(contract["expected_output"])], "source_a")
    completed = execute(env)
    command_job(store, user, accepted["run_id"], "cancel", completed["version"])
    with pytest.raises(DomainError):
        review(
            store,
            user,
            accepted["run_id"],
            {
                "contract_id": contract["id"],
                "expected_result_fingerprint": completed["result_fingerprint"],
                "expected_fence": completed["fence"],
                "expected_version": completed["version"],
                "request_key": "cancelled-review",
            },
        )
    with store.engine.connect() as c:
        assert (
            c.execute(
                select(protocol_jobs.c.result_snapshot).where(
                    protocol_jobs.c.run_id == accepted["run_id"]
                )
            ).scalar_one()
            == completed["result"]
        )


def test_deleted_protocol_binding_cannot_fall_back_to_f1_namespace(env):
    from sqlalchemy import delete

    from sim2act.protocol_jobs import is_protocol_job

    store, user, pid, a, b, worker, tmp = env
    accepted = enqueue(store, user, pid, "source", source_payload(a), "source", LIMITS)
    with store.tx() as c:
        c.execute(delete(protocol_jobs).where(protocol_jobs.c.run_id == accepted["run_id"]))
        c.execute(
            update(runs)
            .where(runs.c.id == accepted["run_id"])
            .values(
                context={
                    "messages": [],
                    "requests": 0,
                    "tools": 0,
                    "repairs": 0,
                    "reserved_tokens": 0,
                }
            )
        )
    assert is_protocol_job(store, accepted["run_id"])
    with pytest.raises(DomainError):
        inspect(store, user, accepted["run_id"])


@pytest.mark.parametrize("initial", ["RUNNING", "PAUSED", "WAITING_RESOURCE"])
def test_unknown_started_attempt_two_cancels_never_claim_terminal_absence(env, initial):
    from sim2act.protocol_jobs import command_job

    store, user, pid, a, b, worker, tmp = env
    accepted = enqueue(store, user, pid, "source", source_payload(a), "source", LIMITS)
    claimed = store.claim(worker.id, worker.s.lease_seconds)
    worker.reserve(claimed["id"], claimed["fence"], copy.deepcopy(claimed["context"]))
    with store.tx() as c:
        c.execute(update(runs).where(runs.c.id == claimed["id"]).values(status=initial))
    first = command_job(store, user, claimed["id"], "cancel", accepted["version"])
    second = command_job(store, user, claimed["id"], "cancel", first["version"])
    assert second["status"] == "RECONCILING" and "result" not in second
    with store.tx() as c:
        assert store.has_unknown(c, claimed["id"])
        assert (
            c.execute(
                select(attempts.c.status).where(attempts.c.run_id == claimed["id"])
            ).scalar_one()
            == "STARTED"
        )


def test_unknown_started_attempt_pause_preserves_unresolved_ledger(env):
    from sim2act.protocol_jobs import command_job

    store, user, pid, a, b, worker, tmp = env
    accepted = enqueue(store, user, pid, "source", source_payload(a), "source", LIMITS)
    claimed = store.claim(worker.id, worker.s.lease_seconds)
    worker.reserve(claimed["id"], claimed["fence"], copy.deepcopy(claimed["context"]))
    first = command_job(store, user, claimed["id"], "pause", accepted["version"])
    second = command_job(store, user, claimed["id"], "pause", first["version"])
    assert first["status"] == "PAUSE_REQUESTED" and second["status"] == "WAITING_RESOURCE"
    with pytest.raises(DomainError) as raised:
        command_job(store, user, claimed["id"], "resume", second["version"])
    assert raised.value.code == "OUTCOME_UNKNOWN"


def test_coherent_rehash_accepted_payload_cannot_replace_original_request(env):
    store, user, pid, a, b, worker, tmp = env
    accepted = enqueue(store, user, pid, "source", source_payload(a), "source", LIMITS)
    with store.tx() as c:
        snapshot = c.execute(
            select(protocol_jobs.c.accepted_snapshot).where(
                protocol_jobs.c.run_id == accepted["run_id"]
            )
        ).scalar_one()
        snapshot["payload"]["inputs"] = {"format": "substituted"}
        c.execute(
            update(protocol_jobs)
            .where(protocol_jobs.c.run_id == accepted["run_id"])
            .values(accepted_snapshot=snapshot, fingerprint=fingerprint(snapshot))
        )
        c.execute(
            update(runs)
            .where(runs.c.id == accepted["run_id"])
            .values(fingerprint=fingerprint(snapshot))
        )
    with pytest.raises(DomainError) as raised:
        inspect(store, user, accepted["run_id"])
    assert raised.value.code == "VERSION_CONFLICT"
