"""Synthetic transport fixtures are independent expected answers, not live acceptance."""

import copy
import hashlib
import json
import re
from dataclasses import replace

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from test_goal_text_applications import wire

from sim2act import pa_spec_apps as spec
from sim2act.api import create_app
from sim2act.db import Store, attempts, operations
from sim2act.worker import Worker

SOURCE = "# Spec synthetic_model_example v1\n- [retain] MUST Keep earlier decisions.\n- [cancel] MUST_NOT Commit cancelled work.\n"
COLD = "# Spec synthetic_unseen_board v7\n- [budget] MUST Stop before the local deadline.\n- [ownership] MUST_NOT Accept stale ownership.\n- [lock] MUST Preserve manual locks.\n"


def expected(rid, content):
    # Manually fixed explicit label/line gold. The product parser is never called.
    if content == SOURCE:
        document, version, end = "synthetic_model_example", 1, 3
        values = [
            ("retain", 2, "MUST", "Keep earlier decisions."),
            ("cancel", 3, "MUST_NOT", "Commit cancelled work."),
        ]
    else:
        assert content == COLD
        document, version, end = "synthetic_unseen_board", 7, 4
        values = [
            ("budget", 2, "MUST", "Stop before the local deadline."),
            ("ownership", 3, "MUST_NOT", "Accept stale ownership."),
            ("lock", 4, "MUST", "Preserve manual locks."),
        ]
    return dict(
        check_version="spec.labeled_citations.v1",
        source=dict(
            resource_id=rid,
            hash=hashlib.sha256(content.encode()).hexdigest(),
            document_id=document,
            document_version=version,
            coordinate_space="whole_resource",
            line_start=1,
            line_end=end,
        ),
        rules=[
            dict(
                rule_id=key,
                line_start=line,
                line_end=line,
                quote=f"- [{key}] {modality} {statement}",
                modality=modality,
                statement=statement,
            )
            for key, line, modality, statement in values
        ],
    )


def recipe(staged):
    refs = (
        ["resource.read", spec.RULES, spec.JSON_TOOL, spec.SAVE]
        if staged
        else ["resource.read", spec.FUSED, spec.SAVE]
    )
    ids = (
        ["fetch_chosen", "parse_chosen", "render_chosen", "save_chosen"]
        if staged
        else ["read_pick", "collect_pick", "save_pick"]
    )
    ports = {
        spec.RULES: ["resource_id", "content", "hash", "format"],
        spec.FUSED: ["resource_id", "content", "hash", "format"],
        spec.JSON_TOOL: ["checklist"],
        spec.SAVE: ["text"],
    }
    return dict(
        version=spec.CODEC,
        steps=[
            dict(
                step_id=ids[i],
                operator=ref,
                depends_on=[] if i == 0 else [ids[i - 1]],
                inputs={"resource_id": dict(source="data", ref="source", field="resource_id")}
                if i == 0
                else {k: dict(source="step", ref=ids[i - 1], field=k) for k in ports[ref]},
            )
            for i, ref in enumerate(refs)
        ],
    )


def setup(env):
    store, settings, _, user, _, pid, _ = env
    settings = replace(settings, goal_planner_provider="intern-s2")
    client = TestClient(create_app(store, settings))
    client.headers["Authorization"] = "Bearer synthetic-test-A"
    rid, card = material(client, pid, SOURCE)
    return store, settings, client, user, pid, rid, card


def material(client, pid, content, title="Cited constraints"):
    response = client.post(
        f"/api/projects/{pid}/resources",
        json=dict(name="synthetic.md", format="md", content=content),
    )
    assert response.status_code == 201, response.text
    rid = response.json()["id"]
    body = dict(
        title=title,
        goal="Build exact labelled constraints and save one JSON checklist",
        known=["Explicit labels only"],
        assumptions=["Synthetic grammar"],
        unresolved=["Natural language completeness unverified"],
        constraints=["Whole source quotes", "Preserve source coordinates"],
        acceptance_checks=["Citation correctness separately checked"],
        resource_refs=[rid],
    )
    made = client.post(f"/api/projects/{pid}/goal-cards", json=body)
    assert made.status_code == 201, made.text
    card = client.get(f"/api/goal-cards/{made.json()['id']}").json()
    return rid, card


def synthetic_sample_from_feedback(source):
    """Fake model adapter reads actual feedback; private manual gold is never input."""
    lines = source["content"].splitlines()
    header = re.fullmatch(r"# Spec (synthetic_[a-z][a-z0-9_]*) v([1-9][0-9]*)", lines[0])
    assert header
    rules = []
    for line_number, line in enumerate(lines[1:], 2):
        match = re.fullmatch(r"- \[([a-z][a-z0-9_]*)\] (MUST|MUST_NOT) (.+)", line)
        assert match
        key, modality, statement = match.groups()
        rules.append(
            dict(
                rule_id=key,
                modality=modality,
                statement=statement,
                quote=line,
                line_start=line_number,
                line_end=line_number,
            )
        )
    return dict(
        check_version="spec.labeled_citations.v1",
        source=dict(
            resource_id=source["resource_id"],
            hash=source["hash"],
            document_id=header[1],
            document_version=int(header[2]),
            coordinate_space="whole_resource",
            line_start=1,
            line_end=len(lines),
        ),
        rules=rules,
    )


def generate(data, staged=True, repair=False, mutation=None):
    store, settings, client, user, pid, rid, card = data
    sent = []

    def handler(request):
        payload = json.loads(request.content)
        sent.append(payload)
        initial = json.loads(payload["messages"][1]["content"])
        candidate = dict(
            recipe=recipe(staged),
            sample_checklist={},
            source_hash=hashlib.sha256(SOURCE.encode()).hexdigest(),
            goal=initial["saved_goal"]["snapshot"]["content"],
        )
        feedback = [json.loads(m["content"]) for m in payload["messages"] if m["role"] == "tool"]
        if feedback:
            candidate["sample_checklist"] = synthetic_sample_from_feedback(feedback[0]["data"])
        if len(sent) == 1:
            message = dict(
                role="assistant",
                content="",
                tool_calls=[
                    dict(
                        id="read-1",
                        type="function",
                        function=dict(
                            name="resource.read", arguments=json.dumps(dict(resource_id=rid))
                        ),
                    )
                ],
            )
        elif len(sent) == 2:
            actual = json.loads(
                next(x["content"] for x in payload["messages"] if x["role"] == "tool")
            )
            assert actual["data"]["content"] == SOURCE
            if repair:
                candidate["sample_checklist"]["rules"][0]["quote"] = "Invented source quote"
            message = dict(
                role="assistant",
                content="",
                tool_calls=[
                    dict(
                        id="check-1",
                        type="function",
                        function=dict(
                            name=spec.CHECK_TOOL, arguments=json.dumps(dict(candidate=candidate))
                        ),
                    )
                ],
            )
        else:
            feedback = [
                json.loads(x["content"]) for x in payload["messages"] if x["role"] == "tool"
            ][-1]
            assert feedback["data"]["status"] == ("FAIL" if repair else "PASS")
            assert not payload["tools"]
            message = dict(role="assistant", content=json.dumps(candidate))
        raw = wire(message, "tool_calls" if "tool_calls" in message else "stop")
        if mutation:
            mutation(raw, len(sent), payload)
        return httpx.Response(200, json=raw)

    body = dict(
        expected_version=card["version"],
        expected_fingerprint=card["fingerprint"],
        request_key="spec-generation",
        family="spec_checklist",
    )
    response = client.post(
        f"/api/projects/{pid}/goal-cards/{card['id']}/application-runs", json=body
    )
    assert response.status_code == 202, response.text
    job = response.json()["run_id"]
    assert Worker(store, settings, goal_planner_transport=httpx.MockTransport(handler)).once()
    result = client.get(f"/api/runs/{job}")
    assert result.status_code == 200, result.text
    return job, result.json(), sent


def confirm(data, rid, result, consent=True):
    body = dict(
        expected_version=result["version"],
        candidate_fingerprint=result["result"]["candidate_fingerprint"],
        request_key="confirm-spec",
        name="Model chosen checklist",
    )
    if consent:
        body["artifact_write_consent"] = spec.CONSENT
    return data[2].post(f"/api/runs/{rid}/confirm-application-candidate", json=body)


def instance(data, aid):
    client = data[2]
    draft = client.get(f"/api/apps/{aid}")
    assert draft.status_code == 200, draft.text
    response = client.post(
        f"/api/internal/apps/{aid}/release-approvals",
        json=dict(expected_draft_fingerprint=draft.json()["fingerprint"], sample_input={}),
    )
    assert response.status_code == 201, response.text
    a = response.json()
    response = client.post(
        f"/api/internal/approvals/{a['id']}/commit", json=dict(fingerprint=a["fingerprint"])
    )
    assert response.status_code == 200, response.text
    release = response.json()
    response = client.post(
        f"/api/internal/releases/{release['id']}/instances",
        json=dict(expected_release_fingerprint=release["fingerprint"], request_key="spec-instance"),
    )
    assert response.status_code == 201, response.text
    return release, response.json()


def enqueue(data, release, inst, key="spec-actual", value=None):
    response = data[2].post(
        f"/api/internal/instances/{inst['id']}/runs",
        json=dict(
            expected_revision=inst["revision"],
            expected_release_fingerprint=release["fingerprint"],
            input={} if value is None else value,
            request_key=key,
        ),
    )
    assert response.status_code == 202, response.text
    return response.json()["run_id"]


def inspect(data, inst, rid):
    return data[2].get(f"/api/internal/instances/{inst['id']}/runs/{rid}")


@pytest.mark.parametrize("staged", [True, False])
@pytest.mark.parametrize("repair", [True, False])
def test_actual_feedback_confirmation_and_transactional_worker(env, staged, repair):
    data = setup(env)
    rid, result, sent = generate(data, staged, repair)
    assert result["status"] == "PARTIAL", (result["error"], len(sent))
    assert len(sent) == 3 and result["result"]["goal_acceptance"] == "NOT_RUN"
    assert confirm(data, rid, result, False).status_code == 403
    response = confirm(data, rid, result)
    assert response.status_code == 200, response.text
    aid = response.json()["id"]
    release, inst = instance(data, aid)
    actual = enqueue(data, release, inst)
    assert Worker(data[0], data[1]).once()
    response = inspect(data, inst, actual)
    assert response.status_code == 200, response.text
    value = response.json()
    assert value["status"] == "SUCCEEDED", value
    assert value["result"]["checklist"] == expected(data[5], SOURCE)
    assert value["semantic_goal_acceptance"] == "NOT_RUN"
    artifact = data[2].get(f"/api/internal/app-run-jobs/{actual}/spec-artifact")
    assert artifact.status_code == 200
    assert json.loads(artifact.json()["resource"]["content"]) == expected(data[5], SOURCE)
    with data[0].tx() as c:
        ops = c.execute(select(operations).where(operations.c.run_id == actual)).mappings().all()
        assert len(ops) == (4 if staged else 3) and all(o["status"] == "VERIFIED" for o in ops)
        assert c.execute(select(attempts.c.id).where(attempts.c.run_id == actual)).first() is None
    history = data[2].get(f"/api/internal/instances/{inst['id']}")
    assert history.status_code == 200, history.text


def prepared(data, staged=True):
    rid, result, _ = generate(data, staged)
    response = confirm(data, rid, result)
    assert response.status_code == 200, response.text
    release, inst = instance(data, response.json()["id"])
    return rid, response.json()["id"], release, inst


def test_cold_unseen_material_preserves_model_recipe_and_no_model(env):
    data = setup(env)
    rid, aid, _, _ = prepared(data)
    new_resource, card = material(data[2], data[4], COLD)
    index = data[2].get(f"/api/projects/{data[4]}/spec-model-candidates")
    assert index.status_code == 200 and [r["run_id"] for r in index.json()["options"]] == [rid]
    old_index = data[2].get(f"/api/projects/{data[4]}/pa-model-candidates")
    assert old_index.status_code == 200 and old_index.json()["options"] == []
    options = data[2].get(
        f"/api/projects/{data[4]}/spec-model-runs/{rid}/binding-options",
        params=dict(card_id=card["id"]),
    )
    assert options.status_code == 200, options.text
    p = options.json()
    body = dict(
        card_id=card["id"],
        expected_goal_version=card["version"],
        expected_goal_fingerprint=card["fingerprint"],
        expected_source_hash=p["source_hash"],
        expected_model_candidate_fingerprint=p["model_candidate_fingerprint"],
        expected_recipe_fingerprint=p["recipe_fingerprint"],
        name="Unseen checklist",
        consent=spec.CONSENT,
        request_key="cold-bind",
    )
    before = data[2].get(f"/api/apps/{aid}").json()["candidate"]
    response = data[2].post(f"/api/projects/{data[4]}/spec-model-runs/{rid}/bindings", json=body)
    assert response.status_code == 201, response.text
    target_aid = response.json()["id"]
    after = data[2].get(f"/api/apps/{target_aid}").json()["candidate"]
    assert before["spec_recipe"] == after["spec_recipe"] == recipe(True)
    assert "Keep earlier decisions" not in json.dumps(after) and "Invented" not in json.dumps(after)
    release, inst = instance(data, target_aid)
    cold = Store(data[1].database_url, test_only=True)
    with TestClient(create_app(cold, data[1])) as client:
        client.headers["Authorization"] = "Bearer synthetic-test-A"
        cold_data = (cold, data[1], client, *data[3:])
        recovery = client.get(
            f"/api/projects/{data[4]}/spec-model-runs/{rid}/bindings/by-key/cold-bind"
        )
        assert recovery.status_code == 200 and recovery.json()["id"] == target_aid
        job = enqueue(cold_data, release, inst)
        worker = Worker(cold, data[1])

        class NoModel:
            def request(self, *args, **kwargs):
                raise AssertionError("Cold spec never calls model")

        worker.model = NoModel()
        assert worker.once()
        result = inspect(cold_data, inst, job)
        assert result.status_code == 200 and result.json()["status"] == "SUCCEEDED", result.text
        assert result.json()["result"]["checklist"] == expected(new_resource, COLD)
        assert "Keep earlier decisions" not in json.dumps(result.json()["result"])
        saved = client.get(f"/api/internal/app-run-jobs/{job}/spec-artifact")
        assert saved.status_code == 200 and saved.json()["resource"]["format"] == "json"
        assert json.loads(saved.json()["resource"]["content"]) == expected(new_resource, COLD)
        with cold.tx() as c:
            assert c.execute(select(attempts.c.id).where(attempts.c.run_id == job)).first() is None
    cold.engine.dispose()


@pytest.mark.parametrize(
    "fault",
    [
        "final_quote",
        "final_graph",
        "checker_tool",
        "source_hash",
        "usage",
        "truncated",
        "two_tools",
    ],
)
def test_generation_failure_history_no_app_and_no_extra_response(env, fault):
    from sim2act.db import app_drafts, goal_application_candidates

    data = setup(env)

    def mutate(raw, index, payload):
        message = raw["choices"][0]["message"]
        if fault == "checker_tool" and index == 2:
            message["tool_calls"][0]["function"]["name"] = "artifact.save_text"
            message["tool_calls"][0]["function"]["arguments"] = json.dumps(dict(text="Do not save"))
        if fault == "two_tools" and index == 2:
            call = copy.deepcopy(message["tool_calls"][0])
            call["id"] = "extra-check"
            message["tool_calls"].append(call)
        if index == 3 and fault in {"final_quote", "final_graph", "source_hash"}:
            value = json.loads(message["content"])
            if fault == "final_quote":
                value["sample_checklist"]["rules"][0]["quote"] = "Invented"
            if fault == "final_graph":
                value["recipe"] = recipe(False)
            if fault == "source_hash":
                value["source_hash"] = "0" * 64
            message["content"] = json.dumps(value)
        if index == 2 and fault == "usage":
            raw.pop("usage")
        if index == 2 and fault == "truncated":
            raw["choices"][0]["finish_reason"] = "length"

    rid, result, sent = generate(data, mutation=mutate)
    assert result["status"] in {"FAILED", "WAITING_RESOURCE"} and result["result"] is None
    assert len(sent) <= 3
    with data[0].tx() as c:
        assert c.execute(select(app_drafts.c.id)).first() is None
        assert c.execute(select(goal_application_candidates.c.app_id)).first() is None
        rows = c.execute(select(attempts).where(attempts.c.run_id == rid)).mappings().all()
        assert any(a["error"] is not None for a in rows)
    assert not Worker(data[0], data[1]).once()


def claim(data, rid):
    from sim2act.contracts import Limits

    worker = Worker(data[0], data[1])
    worker.id = "spec-manual-worker"
    run = data[0].claim(worker.id, data[1].lease_seconds)
    assert run["id"] == rid
    return worker, run, Limits(**{k: getattr(data[1], k) for k in Limits.model_fields})


@pytest.mark.parametrize(
    "fault",
    [
        "save_write",
        "effect_pointer",
        "typed_record",
        "terminal_event",
        "late_stop",
        "expired_lease",
        "audit_attempt_extra",
        "audit_event_extra",
    ],
)
def test_final_save_failure_rolls_back_artifact_grants_effect_and_result(env, monkeypatch, fault):
    import time

    from sqlalchemy import func

    from sim2act.db import grants, internal_instance_data, local_effects, resources, runs
    from sim2act.errors import DomainError

    data = setup(env)
    origin, _, release, inst = prepared(data)
    job = enqueue(data, release, inst)
    worker, run, limits = claim(data, job)
    for _ in range(3):
        assert spec.advance(worker, run)

    def count(table):
        with data[0].tx() as c:
            return c.execute(select(func.count()).select_from(table)).scalar_one()

    tables = [resources, grants, local_effects, internal_instance_data]
    counts = [count(t) for t in tables]
    if fault == "save_write":
        original = spec.write_text_artifact

        def save(*args, **kwargs):
            original(*args, **kwargs)
            raise DomainError("VERIFICATION_FAILED", "Injected after real save")

        monkeypatch.setattr(spec, "write_text_artifact", save)
    elif fault == "effect_pointer":
        original = spec.insert

        def insertion(table):
            if table is local_effects:
                raise DomainError("VERIFICATION_FAILED", "Injected effect pointer failure")
            return original(table)

        monkeypatch.setattr(spec, "insert", insertion)
    elif fault == "typed_record":
        original = spec.insert

        def insertion(table):
            if table is internal_instance_data:
                raise DomainError("VERIFICATION_FAILED", "Injected typed append failure")
            return original(table)

        monkeypatch.setattr(spec, "insert", insertion)
    elif fault in {"terminal_event", "late_stop", "audit_attempt_extra", "audit_event_extra"}:
        original = data[0].event

        def event(c, rid, kind, value):
            result = original(c, rid, kind, value)
            if kind == "SPEC_COMMITTED":
                if fault == "late_stop":
                    worker.stop.set()
                elif fault in {"audit_attempt_extra", "audit_event_extra"}:
                    from sqlalchemy import update

                    from sim2act.db import events

                    table = attempts if fault == "audit_attempt_extra" else events
                    query = select(table).where(table.c.run_id == origin)
                    if table is events:
                        query = query.where(events.c.kind == "STATE")
                    row = c.execute(query.order_by(table.c.id)).mappings().first()
                    field = "parameters" if table is attempts else "data"
                    changed = copy.deepcopy(row[field])
                    changed["controlled_late_extra"] = "Must roll back these unused protected bytes"
                    c.execute(
                        update(table).where(table.c.id == row["id"]).values(**{field: changed})
                    )
                else:
                    raise DomainError("VERIFICATION_FAILED", "Injected final event failure")
            return result

        monkeypatch.setattr(data[0], "event", event)
    else:
        from sqlalchemy import update

        with data[0].tx() as c:
            c.execute(update(runs).where(runs.c.id == job).values(lease_until=time.time() - 1))
    with pytest.raises(DomainError):
        spec.advance(worker, run)
    assert [count(t) for t in tables] == counts
    with data[0].tx() as c:
        ops = c.execute(select(operations).where(operations.c.run_id == job)).mappings().all()
        assert len(ops) == 3 and all(o["status"] == "VERIFIED" for o in ops)
        current = c.execute(select(runs).where(runs.c.id == job)).mappings().one()
        assert current["result"] is None and current["context"]["tools"] == 3


@pytest.mark.parametrize(
    "fault", ["receipt", "intent", "effect", "artifact", "record", "run_scope", "counter"]
)
def test_actual_success_corruption_denies_readback(env, fault):
    from sqlalchemy import delete, update

    from sim2act.db import (
        delivery_graph_requests,
        internal_instance_data,
        local_effects,
        operation_intents,
        resources,
        runs,
    )

    data = setup(env)
    _, _, release, inst = prepared(data)
    job = enqueue(data, release, inst)
    assert Worker(data[0], data[1]).once()
    result = inspect(data, inst, job)
    assert result.status_code == 200 and result.json()["status"] == "SUCCEEDED", result.text
    with data[0].tx() as c:
        op = (
            c.execute(
                select(operations).where(
                    operations.c.run_id == job, operations.c.tool_ref == spec.SAVE
                )
            )
            .mappings()
            .one()
        )
        if fault == "receipt":
            value = copy.deepcopy(op["receipt"])
            value["predecessor_receipts"] = []
            c.execute(update(operations).where(operations.c.id == op["id"]).values(receipt=value))
        elif fault == "intent":
            c.execute(
                update(operation_intents)
                .where(operation_intents.c.operation_id == op["id"])
                .values(request=dict(tool=spec.SAVE, args=dict(text="Invented")))
            )
        elif fault == "effect":
            c.execute(delete(local_effects).where(local_effects.c.operation_id == op["id"]))
        elif fault == "artifact":
            c.execute(
                update(resources)
                .where(resources.c.id == op["receipt"]["data"]["resource_id"])
                .values(content="{}")
            )
        elif fault == "record":
            c.execute(
                delete(internal_instance_data).where(
                    internal_instance_data.c.instance_id == inst["id"]
                )
            )
        elif fault == "run_scope":
            c.execute(
                delete(delivery_graph_requests).where(
                    delivery_graph_requests.c.app_id == job,
                    delivery_graph_requests.c.kind == spec.RUN_META,
                )
            )
        else:
            current = c.execute(select(runs.c.context).where(runs.c.id == job)).scalar()
            current["tools"] = 2
            c.execute(update(runs).where(runs.c.id == job).values(context=current))
    assert inspect(data, inst, job).status_code in {400, 409}
    assert data[2].get(f"/api/internal/instances/{inst['id']}").status_code in {400, 409}


@pytest.mark.parametrize(
    "fault",
    [
        "user_read",
        "app_save",
        "audit_read",
        "goal_version",
        "source_bytes",
        "instance_version",
        "deadline",
        "cancel",
    ],
)
def test_changed_authority_or_versions_between_nodes_never_save(env, fault):
    import time

    from sqlalchemy import func, update

    from sim2act.db import (
        app_drafts,
        goal_cards,
        grants,
        internal_instances,
        local_effects,
        projects,
        resources,
        runs,
    )
    from sim2act.errors import DomainError

    data = setup(env)
    _, aid, release, inst = prepared(data)
    job = enqueue(data, release, inst)
    worker, run, _ = claim(data, job)
    for _ in range(3):
        assert spec.advance(worker, run)
    tables = [resources, grants, local_effects]
    with data[0].tx() as c:
        runtime = c.execute(
            select(app_drafts.c.runtime_id).where(app_drafts.c.id == aid)
        ).scalar_one()
        if fault in {"user_read", "app_save", "audit_read"}:
            principal = data[3] if fault == "user_read" else runtime
            tool, ref = (spec.SAVE, data[4]) if fault == "app_save" else ("resource.read", data[5])
            if fault == "audit_read":
                principal = c.execute(
                    select(projects.c.runtime_id).where(projects.c.id == data[4])
                ).scalar_one()
            c.execute(
                update(grants)
                .where(
                    grants.c.principal_id == principal,
                    grants.c.project_id == data[4],
                    grants.c.resource_id == ref,
                    grants.c.tool_ref == tool,
                )
                .values(revoked=True)
            )
        elif fault == "goal_version":
            c.execute(
                update(goal_cards)
                .where(goal_cards.c.id == data[6]["id"])
                .values(version=data[6]["version"] + 1)
            )
        elif fault == "source_bytes":
            c.execute(update(resources).where(resources.c.id == data[5]).values(content=COLD))
        elif fault == "instance_version":
            c.execute(
                update(internal_instances)
                .where(internal_instances.c.id == inst["id"])
                .values(revision=inst["revision"] + 1)
            )
        elif fault == "deadline":
            c.execute(update(runs).where(runs.c.id == job).values(created_at=time.time() - 400))
        else:
            c.execute(
                update(runs)
                .where(runs.c.id == job)
                .values(status="CANCEL_REQUESTED", cancel_intent=True)
            )
        before = [c.execute(select(func.count()).select_from(t)).scalar_one() for t in tables]
    if fault == "cancel":
        assert spec.advance(worker, run) is False
    else:
        with pytest.raises(DomainError):
            spec.advance(worker, run)
    with data[0].tx() as c:
        assert [
            c.execute(select(func.count()).select_from(t)).scalar_one() for t in tables
        ] == before
        current = c.execute(select(runs).where(runs.c.id == job)).mappings().one()
        assert current["result"] is None and current["context"]["tools"] == 3
        if fault == "cancel":
            assert current["status"] == "CANCELLED"


def test_default_off_real_adapter_has_zero_attempts(env):
    from sim2act.db import app_drafts

    data = setup(env)
    card = data[6]
    response = data[2].post(
        f"/api/projects/{data[4]}/goal-cards/{card['id']}/application-runs",
        json=dict(
            expected_version=card["version"],
            expected_fingerprint=card["fingerprint"],
            request_key="default-off",
            family="spec_checklist",
        ),
    )
    assert response.status_code == 202
    assert Worker(data[0], data[1]).once()
    result = data[2].get(f"/api/runs/{response.json()['run_id']}").json()
    assert (
        result["status"] == "WAITING_RESOURCE" and result["error"]["code"] == "RESOURCE_UNAVAILABLE"
    )
    with data[0].tx() as c:
        assert c.execute(select(attempts.c.id)).first() is None
        assert c.execute(select(app_drafts.c.id)).first() is None
