"""Independent hand gold, offline wire protocol and existing durable R0 AppRun path."""

import copy
import hashlib
import json
import time
from pathlib import Path

import pytest
from sqlalchemy import func, insert, select, update

from sim2act import app_jobs as jobs
from sim2act.agent_apps import (
    CHECK,
    GOAL,
    ReplayModel,
    extract_agent_candidate,
    persist_agent_candidate,
    schemas,
    verified_source,
)
from sim2act.apps import object_schema
from sim2act.contracts import Limits
from sim2act.db import (
    Store,
    app_drafts,
    fingerprint,
    grants,
    internal_app_runs,
    internal_instance_data,
    new_id,
    operations,
    principals,
    projects,
    resources,
    runs,
    task_extractions,
)
from sim2act.errors import DomainError
from sim2act.lifecycle import commit_release, create_instance, prepare_release
from sim2act.worker import Worker

EVIDENCE = Path(__file__).parents[1] / "docs/evidence/bounded-agent-offline-20261006"
GOLD = json.loads((EVIDENCE / "independent-gold.json").read_text())


def limits(env):
    return Limits(**{k: getattr(env[1], k) for k in Limits.model_fields})


def candidate(rid, content):
    # Typed manifest fixture is an offline candidate, not autonomous generation evidence.
    aid, action = new_id("app"), new_id("action")
    inp, out = schemas()
    cap = Limits(
        max_requests=2,
        max_tools=1,
        max_repairs=0,
        max_total_tokens=32000,
        max_output_tokens=1024,
        run_seconds=30,
    ).model_dump()
    permission = [{"tool_ref": "resource.read", "resource_ref": rid}]
    return {
        "goal": GOAL,
        "source_hash": hashlib.sha256(content.encode()).hexdigest(),
        "source_revision": 1,
        "manifest": {
            "schema_version": "1.0-draft",
            "app_id": aid,
            "revision": 1,
            "origin": "goal",
            "goal_ref": new_id("goal"),
            "source_run_ref": None,
            "input_schema": object_schema({"term": inp["properties"]["term"]}),
            "output_schema": out,
            "outputs": {
                k: {"source": "step", "ref": "evidence", "field": k} for k in out["properties"]
            },
            "views": [{"component_ref": "table", "output_field": "citations"}],
            "workflow": [
                {
                    "step_id": "evidence",
                    "binding_id": "agent",
                    "depends_on": [],
                    "inputs": {
                        "resource_id": {"source": "data", "ref": "source", "field": "resource_id"},
                        "term": {"source": "input", "field": "term"},
                    },
                }
            ],
            "action_bindings": [{"binding_id": "agent", "action_id": action, "revision": 1}],
            "data_bindings": [{"binding_id": "source", "resource_ref": rid}],
            "runtime_identity_requirements": {"mode": "user_and_app_intersection"},
            "permission_requirements": permission,
            "dependency_lock": [
                {"kind": "resource", "ref": rid, "version": "1"},
                {"kind": "tool", "ref": "resource.read", "version": "1"},
                {"kind": "prompt", "ref": "intern.system.v1", "version": "1"},
                {"kind": "check", "ref": CHECK, "version": "1"},
            ],
            "validation_suite_ref": CHECK,
            "runtime_limits": cap,
            "data_schema_version": 1,
        },
        "actions": [
            {
                "schema_version": "1.0-draft",
                "action_id": action,
                "revision": 1,
                "input_schema": inp,
                "output_schema": out,
                "executor": {"kind": "bounded_agent", "ref": "intern.agent", "version": "1"},
                "allowed_tool_refs": ["resource.read"],
                "dependencies": [{"kind": "resource", "ref": rid, "version": "1"}],
                "permission_requirements": permission,
                "effect": "read",
                "preconditions": [],
                "postcheck_refs": [CHECK],
                "limits": cap,
                "idempotency": "read_only",
                "reconcile_ref": "operation.lookup.v1",
                "error_contract": ["INVALID_INPUT"],
            }
        ],
    }


def output(rid, content, key):
    gold = GOLD[key]
    return {
        "resource_id": rid,
        "revision": 1,
        "source_hash": hashlib.sha256(content.encode()).hexdigest(),
        "term": gold["term"],
        "citations": copy.deepcopy(gold["citations"]),
        "semantic_status": "UNKNOWN",
    }


def wire_read(rid, name="resource.read"):
    return {
        "model": "OFFLINE-REPLAY",
        "choices": [
            {
                "finish_reason": "tool_calls",
                "message": {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "read-1",
                            "type": "function",
                            "function": {
                                "name": name,
                                "arguments": json.dumps({"resource_id": rid}),
                            },
                        }
                    ],
                },
            }
        ],
    }


def wire_final(value):
    return {
        "model": "OFFLINE-REPLAY",
        "choices": [
            {
                "finish_reason": "stop",
                "message": {"role": "assistant", "content": json.dumps(value)},
            }
        ],
    }


def replay(rid, value):
    return ReplayModel([wire_read(rid), wire_final(value)])


def counts(store):
    with store.tx() as c:
        return {
            t.name: c.execute(select(func.count()).select_from(t)).scalar_one()
            for t in [principals, grants, internal_instance_data, internal_app_runs, operations]
        }


def setup(env):
    store, _, client, user, _, pid, csv = env
    # Already-authorized independent app domain is test setup only, before all product counters.
    existing = client.post(
        f"/api/projects/{pid}/apps/csv-preview",
        json={"name": "existing R0 app domain", "resource_id": csv, "goal": "fixture"},
    ).json()["id"]
    content_a = (EVIDENCE / "source-a.md").read_bytes().decode()
    content_b = (EVIDENCE / "source-b.md").read_bytes().decode()
    ids = []
    with store.tx() as c:
        runtime = c.execute(
            select(app_drafts.c.runtime_id).where(app_drafts.c.id == existing)
        ).scalar_one()
        for name, content in [("a", content_a), ("b", content_b)]:
            rid = new_id("res")
            c.execute(
                insert(resources).values(
                    id=rid,
                    project_id=pid,
                    name=name,
                    format="md",
                    content=content,
                    hash=hashlib.sha256(content.encode()).hexdigest(),
                )
            )
            store.add_grants(c, user, runtime, pid, rid, ["resource.read"])
            ids.append(rid)
    before = counts(store)
    cand = candidate(ids[0], content_a)
    aid = persist_agent_candidate(store, user, pid, runtime, cand, "evidence app", limits(env))[
        "id"
    ]
    assert counts(store) == before
    value = output(ids[0], content_a, "source_a")
    rel, inst = release(env, aid, cand, value)
    return runtime, ids, [content_a, content_b], aid, cand, rel, inst, value


def release(env, aid, cand, value):
    a = prepare_release(
        env[0],
        env[3],
        aid,
        fingerprint(cand),
        limits(env),
        {"term": value["term"]},
        replay=replay(value["resource_id"], value),
    )
    rel = commit_release(env[0], env[3], a["id"], a["fingerprint"], limits(env))
    inst = create_instance(env[0], env[3], rel["id"], rel["fingerprint"], limits(env))
    return rel, inst


def run(env, inst, rel, rid, value, key="run", store=None, model=None):
    store = store or env[0]
    accepted = jobs.enqueue(
        store,
        env[3],
        inst["id"],
        inst["revision"],
        rel["fingerprint"],
        {"term": value["term"]},
        key,
        limits(env),
    )
    Worker(store, env[1], model or replay(rid, value)).once()
    return accepted, store.inspect(env[3], accepted["run_id"])


def test_real_manifest_source_proof_extraction_new_md_cold_worker_zero_grants(env):
    runtime, ids, texts, aid, cand, rel, inst, value = setup(env)
    before = counts(env[0])
    protocol = replay(ids[0], value)
    accepted, result = run(env, inst, rel, ids[0], value, model=protocol)
    assert result["status"] == "SUCCEEDED" and result["result"] == value
    assert len(protocol.requests) == 2
    feedback = protocol.requests[1]["messages"][-1]
    assert (
        feedback["role"] == "tool"
        and json.loads(feedback["content"])["data"]["content"] == texts[0]
    )
    assert [t["function"]["name"] for t in protocol.requests[0]["tools"]] == ["resource.read"]
    with env[0].tx() as c:
        proof = verified_source(env[0], c, env[3], accepted["run_id"], limits(env))
    target = candidate(ids[1], texts[1])
    created = extract_agent_candidate(
        env[0],
        env[3],
        accepted["run_id"],
        fingerprint(proof),
        target,
        runtime,
        "reusable evidence",
        "extract",
        limits(env),
    )
    cached = extract_agent_candidate(
        env[0],
        env[3],
        accepted["run_id"],
        fingerprint(proof),
        target,
        runtime,
        "reusable evidence",
        "extract",
        limits(env),
    )
    assert cached["id"] == created["id"] and cached["cached"]
    with env[0].tx() as c:
        frozen = c.execute(
            select(app_drafts.c.candidate).where(app_drafts.c.id == created["id"])
        ).scalar_one()
    second = output(ids[1], texts[1], "source_b")
    rel2, inst2 = release(env, created["id"], frozen, second)
    cold = Store(env[1].database_url, test_only=True)
    if not env[0].sqlite:
        cold.engine = cold.engine.execution_options(**env[0].engine.get_execution_options())
    try:
        a2, result2 = run(env, inst2, rel2, ids[1], second, store=cold)
        assert result2["status"] == "SUCCEEDED" and result2["result"] == second != value
        cached_run = jobs.enqueue(
            cold,
            env[3],
            inst2["id"],
            inst2["revision"],
            rel2["fingerprint"],
            {"term": second["term"]},
            "run",
            limits(env),
        )
        assert cached_run["run_id"] == a2["run_id"] and cached_run["cached"]
        assert cold.inspect(env[3], a2["run_id"])["result_version"] == 1
    finally:
        cold.engine.dispose()
    after = counts(env[0])
    assert after["principals"] == before["principals"] and after["grants"] == before["grants"]
    assert after["internal_instance_data"] == before["internal_instance_data"] + 2
    assert after["internal_app_runs"] == before["internal_app_runs"] + 2


@pytest.mark.parametrize(
    "mutation", ["wrong_quote", "missing", "extra", "revision", "hash", "semantic"]
)
def test_wrong_evidence_failed_no_result(env, mutation):
    _, ids, _, _, _, rel, inst, value = setup(env)
    bad = copy.deepcopy(value)
    if mutation == "wrong_quote":
        bad["citations"][0]["quote"] += " changed"
    elif mutation == "missing":
        bad["citations"].pop()
    elif mutation == "extra":
        bad["citations"].append(copy.deepcopy(bad["citations"][0]))
    elif mutation == "revision":
        bad["revision"] = 2
    elif mutation == "hash":
        bad["source_hash"] = "0" * 64
    else:
        bad["semantic_status"] = "VERIFIED"
    before = counts(env[0])
    _, result = run(env, inst, rel, ids[0], bad)
    assert result["status"] == "FAILED" and result["result"] is None
    assert counts(env[0])["internal_instance_data"] == before["internal_instance_data"]


@pytest.mark.parametrize(
    "case",
    [
        "final_before_read",
        "wrong_tool",
        "foreign_resource",
        "extra_round",
        "truncated",
        "oversized",
        "live_adapter",
    ],
)
def test_wire_rejection_no_tool_escape(env, case):
    _, ids, _, _, _, rel, inst, value = setup(env)
    seq = [wire_read(ids[0]), wire_final(value)]
    if case == "final_before_read":
        seq = [wire_final(value)]
    elif case == "wrong_tool":
        seq[0] = wire_read(ids[0], "artifact.save_text")
        seq[0]["choices"][0]["message"]["tool_calls"][0]["function"]["arguments"] = json.dumps(
            {"text": "escape"}
        )
    elif case == "foreign_resource":
        seq[0] = wire_read(ids[1])
    elif case == "extra_round":
        seq[1] = wire_read(ids[0])
    elif case == "truncated":
        seq[0]["choices"][0]["finish_reason"] = "length"
    elif case == "oversized":
        seq[1] = wire_final("x" * 10000)
    model = ReplayModel(seq)
    if case == "live_adapter":

        class Forbidden:
            def request(self, *_):
                raise AssertionError("No real adapter may be invoked")

        model = Forbidden()
    before = counts(env[0])
    _, result = run(env, inst, rel, ids[0], value, model=model)
    assert result["status"] == "FAILED"
    after = counts(env[0])
    for t in ["principals", "grants", "internal_instance_data"]:
        assert after[t] == before[t]


@pytest.mark.parametrize("identity", ["user", "app"])
@pytest.mark.parametrize("case", ["revoked", "expired"])
def test_current_read_grant_rechecked_before_dispatch(env, identity, case):
    runtime, ids, _, _, _, rel, inst, value = setup(env)
    accepted = jobs.enqueue(
        env[0],
        env[3],
        inst["id"],
        inst["revision"],
        rel["fingerprint"],
        {"term": value["term"]},
        "queued",
        limits(env),
    )
    with env[0].tx() as c:
        c.execute(
            update(grants)
            .where(
                grants.c.principal_id == (env[3] if identity == "user" else runtime),
                grants.c.resource_id == ids[0],
            )
            .values(**({"revoked": True} if case == "revoked" else {"expires_at": time.time() - 1}))
        )
    protocol = replay(ids[0], value)
    Worker(env[0], env[1], protocol).once()
    assert not protocol.requests
    with env[0].tx() as c:
        assert (
            c.execute(select(runs.c.status).where(runs.c.id == accepted["run_id"])).scalar_one()
            == "WAITING_RESOURCE"
        )


def test_no_project_runtime_fallback_no_cross_owner_project(env):
    runtime, ids, texts, _, _, _, _, _ = setup(env)
    with env[0].tx() as c:
        project_runtime = c.execute(
            select(projects.c.runtime_id).where(projects.c.id == env[5])
        ).scalar_one()
    for user, pid, rt in [(env[3], env[5], project_runtime), (env[4], env[5], runtime)]:
        with pytest.raises(DomainError):
            persist_agent_candidate(
                env[0], user, pid, rt, candidate(ids[0], texts[0]), "bad", limits(env)
            )
    foreign_pid = env[2].post("/api/projects", json={"name": "other"}).json()["id"]
    with pytest.raises(DomainError):
        persist_agent_candidate(
            env[0], env[3], foreign_pid, runtime, candidate(ids[0], texts[0]), "bad", limits(env)
        )
    with env[0].tx() as c:
        c.execute(
            update(grants)
            .where(grants.c.principal_id == runtime, grants.c.resource_id == ids[0])
            .values(revoked=True)
        )
    with pytest.raises(DomainError):
        persist_agent_candidate(
            env[0], env[3], env[5], runtime, candidate(ids[0], texts[0]), "bad", limits(env)
        )


@pytest.mark.parametrize("status", ["FAILED", "PARTIAL", "RECONCILING"])
def test_untrusted_source_status_never_extract(env, status):
    runtime, ids, texts, _, _, rel, inst, value = setup(env)
    accepted, _ = run(env, inst, rel, ids[0], value)
    with env[0].tx() as c:
        proof = verified_source(env[0], c, env[3], accepted["run_id"], limits(env))
        c.execute(update(runs).where(runs.c.id == accepted["run_id"]).values(status=status))
    with pytest.raises(DomainError):
        extract_agent_candidate(
            env[0],
            env[3],
            accepted["run_id"],
            fingerprint(proof),
            candidate(ids[1], texts[1]),
            runtime,
            "bad",
            "key",
            limits(env),
        )


def test_independent_marker_prevents_provenance_strip_coherent_candidate_rewrite(env):
    runtime, ids, texts, _, _, rel, inst, value = setup(env)
    accepted, _ = run(env, inst, rel, ids[0], value)
    with env[0].tx() as c:
        proof = verified_source(env[0], c, env[3], accepted["run_id"], limits(env))
    target = candidate(ids[1], texts[1])
    made = extract_agent_candidate(
        env[0],
        env[3],
        accepted["run_id"],
        fingerprint(proof),
        target,
        runtime,
        "new",
        "key",
        limits(env),
    )
    with env[0].tx() as c:
        c.execute(
            update(app_drafts)
            .where(app_drafts.c.id == made["id"])
            .values(candidate=target, fingerprint=fingerprint(target))
        )
    from sim2act.apps import inspect_draft

    with pytest.raises(DomainError, match="Independent extraction marker"):
        inspect_draft(env[0], env[3], made["id"], limits(env))


@pytest.mark.parametrize(
    "what", ["source_bytes", "source_hash", "receipt", "transcript", "result", "intent"]
)
def test_cold_success_read_rejects_source_and_lineage_tamper(env, what):
    _, ids, texts, _, _, rel, inst, value = setup(env)
    accepted, _ = run(env, inst, rel, ids[0], value)
    with env[0].tx() as c:
        if what in {"source_bytes", "source_hash"}:
            changed = texts[0] + "backup changed\n"
            fields = {"content": changed}
            if what == "source_hash":
                fields["hash"] = hashlib.sha256(changed.encode()).hexdigest()
            c.execute(update(resources).where(resources.c.id == ids[0]).values(**fields))
        elif what == "result":
            bad = copy.deepcopy(value)
            bad["citations"].pop()
            c.execute(
                update(internal_app_runs)
                .where(internal_app_runs.c.id == accepted["app_run_id"])
                .values(output=bad)
            )
            c.execute(
                update(internal_instance_data)
                .where(internal_instance_data.c.run_id == accepted["app_run_id"])
                .values(data={"result": bad}, fingerprint=fingerprint({"result": bad}))
            )
        else:
            from sim2act.db import operation_intents

            op = (
                c.execute(select(operations).where(operations.c.run_id == accepted["run_id"]))
                .mappings()
                .one()
            )
            if what == "intent":
                c.execute(
                    update(operation_intents)
                    .where(operation_intents.c.operation_id == op["id"])
                    .values(request={"tool": "resource.read", "args": {"resource_id": ids[1]}})
                )
            else:
                receipt = copy.deepcopy(op["receipt"])
                if what == "receipt":
                    receipt["check_results"] = []
                else:
                    receipt["protocol"]["messages"][2]["tool_calls"][0]["function"]["arguments"] = (
                        json.dumps({"resource_id": ids[1]})
                    )
                    receipt["protocol"]["fingerprint"] = fingerprint(
                        receipt["protocol"]["messages"]
                    )
                c.execute(
                    update(operations).where(operations.c.id == op["id"]).values(receipt=receipt)
                )
    with pytest.raises(DomainError):
        env[0].inspect(env[3], accepted["run_id"])


def test_source_changed_after_read_and_revoke_before_commit(env, monkeypatch):
    runtime, ids, texts, _, _, rel, inst, value = setup(env)
    original = jobs.commit_result

    def revoked(worker, run_row, plan, result):
        with env[0].tx() as c:
            c.execute(
                update(grants)
                .where(grants.c.principal_id == runtime, grants.c.resource_id == ids[0])
                .values(revoked=True)
            )
        return original(worker, run_row, plan, result)

    monkeypatch.setattr(jobs, "commit_result", revoked)
    accepted = jobs.enqueue(
        env[0],
        env[3],
        inst["id"],
        1,
        rel["fingerprint"],
        {"term": value["term"]},
        "race",
        limits(env),
    )
    before = counts(env[0])
    Worker(env[0], env[1], replay(ids[0], value)).once()
    with env[0].tx() as c:
        assert (
            c.execute(select(runs.c.status).where(runs.c.id == accepted["run_id"])).scalar_one()
            == "WAITING_RESOURCE"
        )
    assert counts(env[0])["internal_instance_data"] == before["internal_instance_data"]


def test_bad_semantic_candidate_and_client_gold_rejected(env):
    runtime, ids, texts, _, _, _, _, _ = setup(env)
    for field, value in [
        ("goal", "extract_normative_obligations"),
        ("client_gold", GOLD),
        ("source_revision", True),
    ]:
        bad = candidate(ids[0], texts[0])
        bad[field] = value
        with pytest.raises(DomainError):
            persist_agent_candidate(env[0], env[3], env[5], runtime, bad, "bad", limits(env))


def test_same_run_key_changed_input_conflict_and_parallel_single_result(env):
    from concurrent.futures import ThreadPoolExecutor

    _, ids, _, _, _, rel, inst, value = setup(env)

    def accept():
        return jobs.enqueue(
            env[0],
            env[3],
            inst["id"],
            1,
            rel["fingerprint"],
            {"term": value["term"]},
            "parallel",
            limits(env),
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _: accept(), range(2)))
    assert responses[0]["run_id"] == responses[1]["run_id"]
    with pytest.raises(DomainError):
        jobs.enqueue(
            env[0],
            env[3],
            inst["id"],
            1,
            rel["fingerprint"],
            {"term": "rollback"},
            "parallel",
            limits(env),
        )
    Worker(env[0], env[1], replay(ids[0], value)).once()
    assert env[0].inspect(env[3], responses[0]["run_id"])["result_version"] == 1


def test_runtime_role_existing_tables_no_ddl(env, runtime_role):
    runtime, ids, texts, _, _, _, _, value = setup(env)
    store = Store(runtime_role, test_only=True)
    try:
        cand = candidate(ids[0], texts[0])
        made = persist_agent_candidate(
            store, env[3], env[5], runtime, cand, "role app", limits(env)
        )
        a = prepare_release(
            store,
            env[3],
            made["id"],
            fingerprint(cand),
            limits(env),
            {"term": value["term"]},
            replay=replay(ids[0], value),
        )
        rel = commit_release(store, env[3], a["id"], a["fingerprint"], limits(env))
        inst = create_instance(store, env[3], rel["id"], rel["fingerprint"], limits(env))
        accepted, result = run(env, inst, rel, ids[0], value, store=store)
        assert result["status"] == "SUCCEEDED"
        with store.tx() as c:
            proof = verified_source(store, c, env[3], accepted["run_id"], limits(env))
        made2 = extract_agent_candidate(
            store,
            env[3],
            accepted["run_id"],
            fingerprint(proof),
            candidate(ids[1], texts[1]),
            runtime,
            "new",
            "key",
            limits(env),
        )
        assert made2["id"] != made["id"]
        from sqlalchemy import text
        from sqlalchemy.exc import ProgrammingError

        with pytest.raises(ProgrammingError), store.tx() as c:
            c.execute(text("CREATE TABLE forbidden_agent_ddl (id integer)"))
    finally:
        store.engine.dispose()


@pytest.mark.parametrize(
    "field,value",
    [
        ("status", "FAILED"),
        ("operation_id", "op_" + "0" * 32),
        ("instance_id", "iinstance_" + "0" * 32),
        ("release_id", "irelease_" + "0" * 32),
        ("output_fingerprint", "0" * 64),
        ("artifact_refs", ["res_" + "0" * 32]),
        ("result_version", True),
        ("run_id", "run_" + "0" * 32),
    ],
)
def test_exact_receipt_status_identity_shape_before_proof_or_cold_read(env, field, value):
    _, ids, _, _, _, rel, inst, expected = setup(env)
    accepted, _ = run(env, inst, rel, ids[0], expected)
    with env[0].tx() as c:
        op = (
            c.execute(select(operations).where(operations.c.run_id == accepted["run_id"]))
            .mappings()
            .one()
        )
        receipt = copy.deepcopy(op["receipt"])
        receipt[field] = value
        c.execute(update(operations).where(operations.c.id == op["id"]).values(receipt=receipt))
    with pytest.raises(DomainError):
        with env[0].tx() as c:
            verified_source(env[0], c, env[3], accepted["run_id"], limits(env))
    with pytest.raises(DomainError):
        env[0].inspect(env[3], accepted["run_id"])


@pytest.mark.parametrize(
    "field,value", [("requests", 2.0), ("provider_requests", False), ("tools", True)]
)
def test_protocol_proof_numeric_types_are_strict(env, field, value):
    _, ids, _, _, _, rel, inst, expected = setup(env)
    accepted, _ = run(env, inst, rel, ids[0], expected)
    with env[0].tx() as c:
        op = (
            c.execute(select(operations).where(operations.c.run_id == accepted["run_id"]))
            .mappings()
            .one()
        )
        receipt = copy.deepcopy(op["receipt"])
        receipt["protocol"][field] = value
        c.execute(update(operations).where(operations.c.id == op["id"]).values(receipt=receipt))
    with pytest.raises(DomainError):
        env[0].inspect(env[3], accepted["run_id"])


def test_independent_extraction_request_anchor_rejects_coherent_source_substitution(env):
    runtime, ids, texts, _, _, rel, inst, value = setup(env)
    accepted, _ = run(env, inst, rel, ids[0], value, key="first")
    accepted2, _ = run(env, inst, rel, ids[0], value, key="second")
    with env[0].tx() as c:
        first = verified_source(env[0], c, env[3], accepted["run_id"], limits(env))
        second = verified_source(env[0], c, env[3], accepted2["run_id"], limits(env))
    target = candidate(ids[1], texts[1])
    made = extract_agent_candidate(
        env[0],
        env[3],
        accepted["run_id"],
        fingerprint(first),
        target,
        runtime,
        "new",
        "extract",
        limits(env),
    )
    from sim2act.apps import inspect_draft

    with env[0].tx() as c:
        c.execute(
            update(task_extractions)
            .where(task_extractions.c.app_id == made["id"])
            .values(request_fingerprint="0" * 64)
        )
    with pytest.raises(DomainError):
        inspect_draft(env[0], env[3], made["id"], limits(env))
    with env[0].tx() as c:
        marker = (
            c.execute(select(task_extractions).where(task_extractions.c.app_id == made["id"]))
            .mappings()
            .one()
        )
        old_request = fingerprint(
            {"proof": fingerprint(first), "candidate": target, "runtime": runtime, "name": "new"}
        )
        rewritten = c.execute(
            select(app_drafts.c.candidate).where(app_drafts.c.id == made["id"])
        ).scalar_one()
        rewritten = copy.deepcopy(rewritten)
        rewritten["agent_provenance"] = second
        rewritten["manifest"]["source_run_ref"] = accepted2["run_id"]
        snap = copy.deepcopy(marker["snapshot"])
        snap["proof"] = second
        snap["candidate_fingerprint"] = fingerprint(rewritten)
        c.execute(
            update(app_drafts)
            .where(app_drafts.c.id == made["id"])
            .values(candidate=rewritten, fingerprint=fingerprint(rewritten))
        )
        c.execute(
            update(task_extractions)
            .where(task_extractions.c.app_id == made["id"])
            .values(task_id=accepted2["run_id"], snapshot=snap, request_fingerprint=old_request)
        )
    with pytest.raises(DomainError, match="Independent accepted extraction"):
        inspect_draft(env[0], env[3], made["id"], limits(env))
