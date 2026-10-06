"""Actual durable CSV source generation, with no additional execution authority."""

import copy

import pytest
from sqlalchemy import func, select, update
from test_internal_lifecycle import create, limits, release
from test_persistent_app_runs import enqueue, setup, worker

from sim2act.apps import load_draft
from sim2act.db import (
    Store,
    app_drafts,
    attempts,
    fingerprint,
    grants,
    internal_app_runs,
    internal_instance_data,
    operation_intents,
    operations,
    principals,
    runs,
    task_extractions,
)
from sim2act.errors import DomainError
from sim2act.registered_run_extraction import extract, options


def prepared(env):
    rel, inst, source_app, _ = setup(env)
    accepted = enqueue(env, inst, rel)
    assert worker(env).once()
    assert env[0].inspect(env[3], accepted["run_id"])["status"] == "SUCCEEDED"
    client, pid = env[2], env[5]
    rid = client.post(
        f"/api/projects/{pid}/resources",
        json={"name": "fresh.csv", "format": "csv", "content": "amount,quantity\n10,2\n30,3\n"},
    ).json()["id"]
    target = client.post(
        f"/api/projects/{pid}/apps/csv-preview",
        json={"name": "existing authorized domain", "resource_id": rid, "goal": "new data"},
    ).json()["id"]
    values = options(env[0], env[3], inst["id"], accepted["run_id"], limits(env))
    selected = next(t for t in values["targets"] if t["id"] == target)
    return inst, accepted, values, selected, source_app


def generate(env, context, **changes):
    inst, accepted, values, target, _ = context
    args = {
        "expected_proof_fp": values["source_proof_fingerprint"],
        "target_app_id": target["id"],
        "expected_target_fp": target["fingerprint"],
        "name": "derived",
        "key": "generate",
    }
    args.update(changes)
    return extract(env[0], env[3], inst["id"], accepted["run_id"], limits=limits(env), **args)


def counts(env):
    with env[0].tx() as c:
        return {
            t.name: c.execute(select(func.count()).select_from(t)).scalar_one()
            for t in [
                principals,
                grants,
                runs,
                internal_app_runs,
                internal_instance_data,
                attempts,
                app_drafts,
            ]
        }


def test_receipt_generation_cold_worker_new_column_no_new_authority(env):
    context = prepared(env)
    before = counts(env)
    with env[0].tx() as c:
        before_grants = [dict(x) for x in c.execute(select(grants)).mappings()]
    made = generate(env, context)
    assert not made["cached"] and made["model_requests"] == 0
    assert made["semantic_goal_acceptance"] == "NOT_RUN" and not made["publishable"]
    assert generate(env, context)["id"] == made["id"]
    assert generate(env, context)["cached"]
    after = counts(env)
    for name in before:
        assert after[name] == before[name] + (1 if name == "app_drafts" else 0)
    with env[0].tx() as c:
        assert before_grants == [dict(x) for x in c.execute(select(grants)).mappings()]
        draft, _, _, _ = load_draft(env[0], c, env[3], made["id"], limits(env))
        assert draft["runtime_id"] == context[3]["runtime_id"]
        assert draft["candidate"]["manifest"]["source_run_ref"] == context[1]["run_id"]
    rel, _, _ = release(env, made["id"], made["candidate_fingerprint"])
    inst = create(env, rel)
    accepted = enqueue(env, inst, rel, column="quantity")
    cold = Store(env[1].database_url, test_only=True)
    if not env[0].sqlite:
        cold.engine = cold.engine.execution_options(**env[0].engine.get_execution_options())
    try:
        assert worker(env, cold).once()
        result = cold.inspect(env[3], accepted["run_id"])
        assert result["status"] == "SUCCEEDED" and result["result"]["sum"] == "5"
        assert result["result"]["column"] == "quantity" and result["result_version"] == 1
        assert accepted["run_id"] != context[1]["run_id"]
        assert result["result"]["source_hash"] == context[3]["source_hash"]
    finally:
        cold.engine.dispose()
    bad = enqueue(env, inst, rel, key="bad", column="missing")
    assert worker(env).once()
    assert env[0].inspect(env[3], bad["run_id"])["status"] == "FAILED"


@pytest.mark.parametrize(
    "change", ["key_name", "proof", "target_version", "wrong_instance", "other_owner"]
)
def test_accepted_versions_identity_and_idempotency(env, change):
    context = prepared(env)
    generate(env, context)
    before = counts(env)
    with pytest.raises(DomainError):
        if change == "key_name":
            generate(env, context, name="different")
        elif change == "proof":
            generate(env, context, expected_proof_fp="0" * 64)
        elif change == "target_version":
            generate(env, context, expected_target_fp="0" * 64)
        else:
            extract(
                env[0],
                env[4] if change == "other_owner" else env[3],
                "iinstance_wrong" if change == "wrong_instance" else context[0]["id"],
                context[1]["run_id"],
                context[2]["proof_fingerprint"],
                context[3]["id"],
                context[3]["fingerprint"],
                "derived",
                "generate",
                limits(env),
            )
    assert counts(env) == before


@pytest.mark.parametrize(
    "change",
    ["PARTIAL", "FAILED", "cancel", "receipt", "intent", "record", "source_grant", "target_grant"],
)
def test_source_or_target_tampering_rejects_new_and_cached_generation(env, change):
    context = prepared(env)
    made = generate(env, context)
    with env[0].tx() as c:
        if change in {"PARTIAL", "FAILED", "cancel"}:
            c.execute(
                update(runs)
                .where(runs.c.id == context[1]["run_id"])
                .values(**({"cancel_intent": True} if change == "cancel" else {"status": change}))
            )
        elif change in {"receipt", "intent"}:
            op = (
                c.execute(select(operations).where(operations.c.run_id == context[1]["run_id"]))
                .mappings()
                .one()
            )
            if change == "receipt":
                receipt = copy.deepcopy(op["receipt"])
                receipt["unexpected"] = True
                c.execute(
                    update(operations).where(operations.c.id == op["id"]).values(receipt=receipt)
                )
            else:
                request = {
                    "tool": "data.aggregate_csv",
                    "args": {"resource_id": context[3]["resource_id"], "column": "amount"},
                }
                c.execute(
                    update(operation_intents)
                    .where(operation_intents.c.operation_id == op["id"])
                    .values(request=request)
                )
                c.execute(
                    update(operations)
                    .where(operations.c.id == op["id"])
                    .values(fingerprint=fingerprint(request))
                )
        elif change == "record":
            data = {"result": {"sum": "999"}}
            c.execute(
                update(internal_instance_data).values(data=data, fingerprint=fingerprint(data))
            )
        else:
            runtime = context[3]["runtime_id"]
            if change == "source_grant":
                runtime = c.execute(
                    select(app_drafts.c.runtime_id).where(app_drafts.c.id == context[4])
                ).scalar_one()
            c.execute(
                update(grants)
                .where(grants.c.principal_id == runtime, grants.c.tool_ref == "data.aggregate_csv")
                .values(revoked=True)
            )
    before = counts(env)
    with pytest.raises(DomainError):
        generate(env, context)
    with pytest.raises(DomainError):
        generate(env, context, key="another")
    with env[0].tx() as c, pytest.raises(DomainError):
        load_draft(env[0], c, env[3], made["id"], limits(env))
    assert counts(env) == before


@pytest.mark.parametrize("change", ["marker_kind", "marker_removed", "goal", "executor", "runtime"])
def test_candidate_self_rehash_cannot_replace_independent_origin(env, change):
    context = prepared(env)
    made = generate(env, context)
    with env[0].tx() as c:
        row = c.execute(select(app_drafts).where(app_drafts.c.id == made["id"])).mappings().one()
        candidate = copy.deepcopy(row["candidate"])
        if change == "marker_kind":
            snap = c.execute(
                select(task_extractions.c.snapshot).where(task_extractions.c.app_id == made["id"])
            ).scalar_one()
            snap = {**snap, "kind": "agent_source.v1"}
            c.execute(
                update(task_extractions)
                .where(task_extractions.c.app_id == made["id"])
                .values(snapshot=snap)
            )
        elif change == "marker_removed":
            candidate.pop("task_proof")
            candidate["manifest"].update(origin="goal", source_run_ref=None)
        elif change == "goal":
            candidate["goal"]["known"] = "mutated"
        elif change == "executor":
            candidate["actions"][0]["executor"] = {
                "kind": "bounded_agent",
                "ref": "intern.agent",
                "version": "1",
            }
        else:
            c.execute(
                update(app_drafts)
                .where(app_drafts.c.id == made["id"])
                .values(runtime_id="appruntime_unbound")
            )
        c.execute(
            update(app_drafts)
            .where(app_drafts.c.id == made["id"])
            .values(candidate=candidate, fingerprint=fingerprint(candidate))
        )
    with env[0].tx() as c, pytest.raises(DomainError):
        load_draft(env[0], c, env[3], made["id"], limits(env))


def test_ordinary_f1_partial_is_not_successful_source(env):
    request = (
        env[2]
        .post(
            f"/api/projects/{env[5]}/runs",
            json={"goal": "sum amount", "resource_refs": [env[6]], "request_key": "ordinary"},
        )
        .json()
    )
    from sim2act.worker import Worker

    assert Worker(env[0], env[1]).once()
    assert env[0].inspect(env[3], request["run_id"])["status"] == "PARTIAL"
    with pytest.raises(DomainError, match="Successful durable"):
        options(env[0], env[3], "unused", request["run_id"], limits(env))


def test_queued_cold_worker_rechecks_source_grant_before_result(env):
    context = prepared(env)
    made = generate(env, context)
    rel, _, _ = release(env, made["id"], made["candidate_fingerprint"])
    inst = create(env, rel)
    accepted = enqueue(env, inst, rel, column="quantity")
    with env[0].tx() as c:
        runtime = c.execute(
            select(app_drafts.c.runtime_id).where(app_drafts.c.id == context[4])
        ).scalar_one()
        c.execute(
            update(grants)
            .where(grants.c.principal_id == runtime, grants.c.tool_ref == "data.aggregate_csv")
            .values(revoked=True)
        )
        before = c.execute(select(func.count()).select_from(internal_instance_data)).scalar_one()
    cold = Store(env[1].database_url, test_only=True)
    if not env[0].sqlite:
        cold.engine = cold.engine.execution_options(**env[0].engine.get_execution_options())
    try:
        assert worker(env, cold).once()
        with cold.tx() as c:
            row = c.execute(select(runs).where(runs.c.id == accepted["run_id"])).mappings().one()
            assert row["status"] == "WAITING_RESOURCE" and row["error"]["code"] == "GRANT_REVOKED"
            assert (
                c.execute(select(func.count()).select_from(internal_instance_data)).scalar_one()
                == before
            )
    finally:
        cold.engine.dispose()


def test_other_project_and_agent_family_are_not_target_authority(env):
    context = prepared(env)
    pid = env[2].post("/api/projects", json={"name": "other"}).json()["id"]
    rid = (
        env[2]
        .post(
            f"/api/projects/{pid}/resources",
            json={"name": "other.csv", "format": "csv", "content": "amount\n9\n"},
        )
        .json()["id"]
    )
    aid = (
        env[2]
        .post(
            f"/api/projects/{pid}/apps/csv-preview",
            json={"name": "other", "resource_id": rid, "goal": "other"},
        )
        .json()["id"]
    )
    fp = env[2].get(f"/api/apps/{aid}").json()["fingerprint"]
    with pytest.raises(DomainError) as denied:
        generate(env, context, target_app_id=aid, expected_target_fp=fp)
    assert denied.value.code == "PERMISSION_DENIED"
    from test_bounded_agent_apps import setup as agent_setup

    agent = agent_setup(env)
    with pytest.raises(DomainError) as unsupported:
        generate(env, context, target_app_id=agent[3], expected_target_fp=fingerprint(agent[4]))
    assert unsupported.value.code == "UNSUPPORTED_CAPABILITY"
    targets = options(env[0], env[3], context[0]["id"], context[1]["run_id"], limits(env))[
        "targets"
    ]
    assert aid not in {t["id"] for t in targets} and agent[3] not in {t["id"] for t in targets}


def test_concurrent_same_request_creates_one_candidate(env):
    from concurrent.futures import ThreadPoolExecutor

    context = prepared(env)
    before = counts(env)
    with ThreadPoolExecutor(max_workers=2) as pool:
        replies = list(pool.map(lambda _: generate(env, context), range(2)))
    assert replies[0]["id"] == replies[1]["id"]
    assert sum(r["cached"] for r in replies) == 1
    assert counts(env)["app_drafts"] == before["app_drafts"] + 1


def test_no_existing_different_authorized_domain_needs_input(env):
    rel, inst, _, _ = setup(env)
    accepted = enqueue(env, inst, rel)
    assert worker(env).once()
    before = counts(env)
    with pytest.raises(DomainError) as missing:
        options(env[0], env[3], inst["id"], accepted["run_id"], limits(env))
    assert missing.value.code == "NEEDS_INPUT"
    assert counts(env) == before
