"""Unlabelled neutral material and synthetic transport, never real semantics."""

import copy
import hashlib
import json
from dataclasses import replace

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update
from test_goal_text_applications import wire
from test_pa_spec_apps import confirm, enqueue, inspect, instance

from sim2act import natural_specs as natural
from sim2act.api import create_app
from sim2act.db import (
    attempts,
    internal_instance_data,
    operations,
    runs,
)
from sim2act.errors import DomainError
from sim2act.worker import Worker

SOURCE = "The desk lamp dims after five idle minutes when battery powered. During a software update it stays bright. The default brightness for visitors remains undecided."
COLD = "The garden sensor samples each hour while solar power is available. On a rainy day it waits until noon. The winter interval has yet to be agreed."


def facts(content):
    # These are private fake model outputs. No product parser/gold is used.
    sentences = content.split(". ")
    kinds = ["requirement", "exception", "open_question"]
    result = []
    for i, sentence in enumerate(sentences):
        if i < len(sentences) - 1:
            sentence += "."
        begin = content.index(sentence)
        result.append(
            dict(
                item_id=f"fact_{i}",
                kind=kinds[i],
                summary=sentence,
                citations=[dict(start=begin, end=begin + len(sentence), quote=sentence)],
                targets=["fact_0"] if i == 1 else [],
            )
        )
    phrase = "when battery powered" if content == SOURCE else "while solar power is available"
    begin = content.index(phrase)
    result.insert(
        1,
        dict(
            item_id="qualifier",
            kind="condition",
            summary=phrase,
            citations=[dict(start=begin, end=begin + len(phrase), quote=phrase)],
            targets=["fact_0"],
        ),
    )
    return result


def recipe(style="single"):
    def ports(sid, fields):
        return {k: dict(source="step", ref=sid, field=k) for k in fields}

    source = ports("read_pick", ["resource_id", "content", "hash", "format"])
    steps = [
        dict(
            step_id="read_pick",
            operator=natural.READ,
            depends_on=[],
            inputs=dict(resource_id=dict(source="data", ref="source", field="resource_id")),
        )
    ]
    if style == "single":
        steps.append(
            dict(
                step_id="infer_pick",
                operator="model.spec.all",
                depends_on=["read_pick"],
                inputs=source,
            )
        )
        joined = "infer_pick"
    else:
        steps.append(
            dict(
                step_id="duties_pick",
                operator="model.spec.requirements",
                depends_on=["read_pick"],
                inputs=source,
            )
        )
        inputs = copy.deepcopy(source)
        deps = ["read_pick"]
        if style == "sequential":
            inputs.update(
                prior_items=dict(source="step", ref="duties_pick", field="items"),
                prior_feedback=dict(source="step", ref="duties_pick", field="feedback"),
            )
            deps.append("duties_pick")
        steps += [
            dict(
                step_id="qualifiers_pick",
                operator="model.spec.qualifiers",
                depends_on=deps,
                inputs=inputs,
            ),
            dict(
                step_id="merge_pick",
                operator=natural.MERGE,
                depends_on=["duties_pick", "qualifiers_pick"],
                inputs=dict(
                    first=dict(source="step", ref="duties_pick", field="items"),
                    second=dict(source="step", ref="qualifiers_pick", field="items"),
                ),
            ),
        ]
        joined = "merge_pick"
    steps += [
        dict(
            step_id="check_pick",
            operator=natural.VERIFY,
            depends_on=["read_pick", joined],
            inputs={**source, "items": dict(source="step", ref=joined, field="items")},
        ),
        dict(
            step_id="save_pick",
            operator=natural.SAVE,
            depends_on=["check_pick"],
            inputs=ports("check_pick", ["text"]),
        ),
    ]
    return dict(version=natural.CODEC, steps=steps)


def material(client, pid, content, title="Operating notes"):
    made = client.post(
        f"/api/projects/{pid}/resources",
        json=dict(name="neutral.txt", format="txt", content=content),
    )
    assert made.status_code == 201, made.text
    rid = made.json()["id"]
    body = dict(
        title=title,
        goal="Extract duties, conditions, exceptions and pending choices into a reusable cited review checklist",
        known=[],
        assumptions=[],
        unresolved=[f"Human question {i}" for i in range(16)],
        constraints=["Preserve the full source and uncertain relations"],
        acceptance_checks=["Human review of completeness and meaning"],
        resource_refs=[rid],
    )
    made = client.post(f"/api/projects/{pid}/goal-cards", json=body)
    assert made.status_code == 201, made.text
    card = client.get(f"/api/goal-cards/{made.json()['id']}").json()
    return rid, card


def setup(env):
    store, settings, _, user, _, pid, _ = env
    settings = replace(settings, goal_planner_provider="intern-s2")
    client = TestClient(create_app(store, settings))
    client.headers["Authorization"] = "Bearer synthetic-test-A"
    rid, card = material(client, pid, SOURCE)
    return store, settings, client, user, pid, rid, card


def generate(data, style="single", repair=False):
    store, settings, client, _, pid, rid, card = data
    sent = []
    source_rid = rid

    def handler(request):
        payload = json.loads(request.content)
        sent.append(payload)
        native = json.loads(payload["messages"][1]["content"])["saved_goal"]["snapshot"]["content"]
        graph = recipe(style)
        samples = []
        for step in graph["steps"]:
            if step["operator"] in natural.MODEL_KINDS:
                samples.append(
                    dict(
                        step_id=step["step_id"],
                        items=[
                            i
                            for i in facts(SOURCE)
                            if i["kind"] in natural.MODEL_KINDS[step["operator"]]
                        ],
                    )
                )
        candidate = dict(
            recipe=graph,
            sample_nodes=samples,
            source_hash=hashlib.sha256(SOURCE.encode()).hexdigest(),
            goal=native,
        )
        if len(sent) == 1:
            tool, args = natural.READ, dict(resource_id=source_rid)
        elif len(sent) == 2:
            actual = json.loads(
                next(m["content"] for m in payload["messages"] if m["role"] == "tool")
            )
            assert actual["data"]["content"] == SOURCE
            if repair:
                candidate["sample_nodes"][0]["items"][0]["citations"][0]["quote"] = "Wrong quote"
            tool, args = "spec.check_candidate", dict(candidate=candidate)
        else:
            feedback = json.loads(
                [m["content"] for m in payload["messages"] if m["role"] == "tool"][-1]
            )
            assert feedback["data"]["status"] == ("FAIL" if repair else "PASS")
            message = dict(role="assistant", content=json.dumps(candidate))
            return httpx.Response(200, json=wire(message, "stop"))
        message = dict(
            role="assistant",
            content="",
            tool_calls=[
                dict(
                    id=f"call-{len(sent)}",
                    type="function",
                    function=dict(name=tool, arguments=json.dumps(args)),
                )
            ],
        )
        return httpx.Response(200, json=wire(message, "tool_calls"))

    made = client.post(
        f"/api/projects/{pid}/goal-cards/{card['id']}/application-runs",
        json=dict(
            expected_version=card["version"],
            expected_fingerprint=card["fingerprint"],
            request_key="natural-generation",
            family="natural_spec",
        ),
    )
    assert made.status_code == 202, made.text
    rid = made.json()["run_id"]
    assert Worker(store, settings, goal_planner_transport=httpx.MockTransport(handler)).once()
    result = client.get(f"/api/runs/{rid}")
    assert result.status_code == 200, result.text
    assert result.json()["status"] == "PARTIAL", result.text
    return rid, result.json(), sent


def ready(data, style="single", repair=False):
    rid, result, sent = generate(data, style, repair)
    sample = data[2].get(f"/api/projects/{data[4]}/natural-spec-model-runs/{rid}/sample-preview")
    assert sample.status_code == 200, sample.text
    assert sample.json()["preview"]["checklist"]["items"][2]["kind"] == "exception"
    assert confirm(data, rid, result, False).status_code == 403
    saved = confirm(data, rid, result)
    assert saved.status_code == 200, saved.text
    release, inst = instance(data, saved.json()["id"])
    return rid, saved.json()["id"], release, inst, sent


def transport(sent, content=SOURCE, mutate=None):
    def handler(request):
        payload = json.loads(request.content)
        sent.append(payload)
        values = json.loads(payload["messages"][1]["content"])
        assert values["current_inputs"]["content"] == content
        assert len(values["goal"]["unresolved"]) == 16
        assert "sample_nodes" not in json.dumps(payload) and not payload["tools"]
        if "prior_feedback" in values["current_inputs"]:
            assert values["current_inputs"]["prior_feedback"]["check"] == natural.CHECK
            assert values["current_inputs"]["prior_feedback"]["coverage_status"] == "PARTIAL"
            assert values["current_inputs"]["prior_items"] == facts(content)[:1]
        values = [i for i in facts(content) if i["kind"] in values["focus"]]
        raw = wire(dict(role="assistant", content=json.dumps(dict(items=values))), "stop")
        if mutate:
            mutate(raw, payload)
        return httpx.Response(200, json=raw)

    return httpx.MockTransport(handler)


@pytest.mark.parametrize("style", ["single", "parallel", "sequential"])
@pytest.mark.parametrize("repair", [False, True])
def test_actual_nodes_and_atomic_pending_checklist(env, style, repair):
    data = setup(env)
    _, _, release, inst, generation = ready(data, style, repair)
    rid = enqueue(data, release, inst)
    sent = []
    assert Worker(data[0], data[1], goal_planner_transport=transport(sent)).once()
    result = inspect(data, inst, rid)
    assert result.status_code == 200, result.text
    assert result.json()["status"] == "SUCCEEDED", result.text
    checklist = result.json()["result"]["checklist"]
    assert (
        checklist["source_content"] == SOURCE
        and checklist["human_unresolved"] == data[6]["content"]["unresolved"]
    )
    assert [i["kind"] for i in checklist["items"]] == [
        "requirement",
        "condition",
        "exception",
        "open_question",
    ]
    assert (
        checklist["semantic_goal_acceptance"] == "NOT_RUN"
        and checklist["owner_acceptance"] == "PENDING"
    )
    assert checklist["items"][3]["decision_status"] == "OPEN" and len(generation) == 3
    assert len(sent) == (1 if style == "single" else 2)
    with data[0].tx() as c:
        job = c.execute(select(runs).where(runs.c.id == rid)).mappings().one()
        assert job["context"]["requests"] == len(sent) and job["context"]["tools"] == (
            3 if style == "single" else 4
        )
        rows = c.execute(select(attempts).where(attempts.c.run_id == rid)).mappings().all()
        assert len(rows) == len(sent) and all(
            a["status"] == "VERIFIED" and a["response"]["received_raw"] for a in rows
        )
        assert (
            c.execute(
                select(internal_instance_data).where(
                    internal_instance_data.c.instance_id == inst["id"]
                )
            )
            .mappings()
            .one()["version"]
            == 1
        )
    saved = data[2].get(f"/api/internal/app-run-jobs/{rid}/spec-artifact")
    assert saved.status_code == 200 and json.loads(saved.json()["resource"]["content"]) == checklist


def test_default_off_no_model_reservation(env):
    data = setup(env)
    _, _, release, inst, _ = ready(data)
    rid = enqueue(data, release, inst)
    assert Worker(data[0], data[1]).once()
    with data[0].tx() as c:
        assert c.execute(select(attempts.c.id).where(attempts.c.run_id == rid)).first() is None
        assert (
            c.execute(
                select(internal_instance_data).where(
                    internal_instance_data.c.instance_id == inst["id"]
                )
            ).first()
            is None
        )


@pytest.mark.parametrize("fault", ["quote", "usage", "identity", "extra", "truncated"])
def test_known_bad_raw_retained_without_save(env, fault):
    data = setup(env)
    _, _, release, inst, _ = ready(data)
    rid = enqueue(data, release, inst)
    sent = []

    def mutate(raw, payload):
        if fault == "quote":
            value = json.loads(raw["choices"][0]["message"]["content"])
            value["items"][0]["citations"][0]["quote"] = "Invented"
            raw["choices"][0]["message"]["content"] = json.dumps(value)
        elif fault == "usage":
            raw.pop("usage")
        elif fault == "identity":
            raw["model"] = "wrong-model"
        elif fault == "extra":
            raw["choices"][0]["message"]["content"] = '{"items":[],"resolved":true}'
        else:
            raw["choices"][0]["finish_reason"] = "length"

    assert Worker(data[0], data[1], goal_planner_transport=transport(sent, mutate=mutate)).once()
    with data[0].tx() as c:
        a = c.execute(select(attempts).where(attempts.c.run_id == rid)).mappings().one()
        assert (
            a["status"] == "REJECTED_KNOWN"
            and a["response"]["received_raw"]
            and a["reserved_tokens"] > 0
        )
        assert not c.execute(
            select(internal_instance_data).where(internal_instance_data.c.instance_id == inst["id"])
        ).first()
        assert not c.execute(
            select(operations.c.id).where(
                operations.c.run_id == rid, operations.c.tool_ref == natural.SAVE
            )
        ).first()
    assert len(sent) == 1


def test_citation_pass_never_semantic_acceptance_unicode_and_unassigned():
    text = "The lamp ☀ stays dim. Visitors may choose later."
    source = dict(
        resource_id="logical",
        content=text,
        hash=hashlib.sha256(text.encode()).hexdigest(),
        format="txt",
    )
    items = [
        dict(
            item_id="x",
            kind="condition",
            summary="An intentionally inaccurate summary",
            citations=[dict(start=0, end=len(text), quote=text)],
            targets=[],
        )
    ]
    result = natural.report(source, items, dict(unresolved=["Human pending"]))
    assert result["citation_status"] == "PASS" and result["semantic_status"] == "UNKNOWN"
    assert result["checklist"]["items"][0]["relation_status"] == "UNASSIGNED"
    items[0]["citations"][0]["start"] = True
    with pytest.raises(DomainError):
        natural.report(source, items, dict(unresolved=[]))


@pytest.mark.parametrize(
    "fault",
    ["nine_items", "unknown_target", "duplicate_id", "extra_decision", "bad_span", "goal_overflow"],
)
def test_complete_preservation_bounds_fail_without_truncation(fault):
    source = dict(
        resource_id="logical",
        content=SOURCE,
        hash=hashlib.sha256(SOURCE.encode()).hexdigest(),
        format="txt",
    )
    items = facts(SOURCE)
    goal = dict(unresolved=["Human pending"])
    if fault == "nine_items":
        items = [{**copy.deepcopy(items[0]), "item_id": f"item_{i}"} for i in range(9)]
    elif fault == "unknown_target":
        items[1]["targets"] = ["absent_requirement"]
    elif fault == "duplicate_id":
        items[1]["item_id"] = items[0]["item_id"]
    elif fault == "extra_decision":
        items[3]["resolved"] = True
    elif fault == "bad_span":
        items[0]["citations"][0]["end"] += 1
    else:
        goal["unresolved"] = ["pending " + "x" * 993 for _ in range(16)]
    original = copy.deepcopy((source, items, goal))
    with pytest.raises(DomainError):
        natural.report(source, items, goal)
    assert (source, items, goal) == original


def test_cold_new_store_reads_new_material_without_old_answers(env):
    from sim2act.db import Store

    data = setup(env)
    origin, aid, _, _, _ = ready(data, "sequential")
    new_resource, card = material(data[2], data[4], COLD)
    path = f"/api/projects/{data[4]}/natural-spec-model-runs/{origin}"
    options = data[2].get(path + "/binding-options", params=dict(card_id=card["id"]))
    assert options.status_code == 200, options.text
    p = options.json()
    assert p["preview"]["status"] == "MODEL_EXECUTION_REQUIRED" and p["model_requests"] == 0
    body = dict(
        card_id=card["id"],
        expected_goal_version=card["version"],
        expected_goal_fingerprint=card["fingerprint"],
        expected_source_hash=p["source_hash"],
        expected_model_candidate_fingerprint=p["model_candidate_fingerprint"],
        expected_recipe_fingerprint=p["recipe_fingerprint"],
        name="New neutral source",
        consent=natural.CONSENT,
        request_key="natural-cold",
    )
    made = data[2].post(path + "/bindings", json=body)
    assert made.status_code == 201, made.text
    target = made.json()["id"]
    assert made.json()["namespace"] == natural.VERSION
    candidate = data[2].get(f"/api/apps/{target}").json()["candidate"]
    assert candidate["spec_recipe"] == recipe("sequential") and SOURCE not in json.dumps(candidate)
    release, inst = instance(data, target)
    cold = Store(data[1].database_url, test_only=True)
    with TestClient(create_app(cold, data[1])) as client:
        client.headers["Authorization"] = "Bearer synthetic-test-A"
        cold_data = (cold, data[1], client, *data[3:])
        recovered = client.get(path + "/bindings/by-key/natural-cold")
        assert recovered.status_code == 200 and recovered.json()["id"] == target
        job = enqueue(cold_data, release, inst)
        sent = []
        assert Worker(cold, data[1], goal_planner_transport=transport(sent, COLD)).once()
        result = inspect(cold_data, inst, job)
        assert result.status_code == 200 and result.json()["status"] == "SUCCEEDED", result.text
        assert result.json()["result"]["checklist"]["source"]["resource_id"] == new_resource
        assert result.json()["result"]["checklist"]["source_content"] == COLD
        assert SOURCE not in json.dumps(sent) and len(sent) == 2
    cold.engine.dispose()


@pytest.mark.parametrize("fault", ["cancel", "revoke", "goal", "fence", "stop", "parameters"])
def test_received_late_or_changed_response_never_saves(env, fault):
    from sim2act.db import goal_cards, grants

    data = setup(env)
    _, _, release, inst, _ = ready(data)
    job = enqueue(data, release, inst)
    sent = []
    worker = Worker(data[0], data[1])

    def mutate(raw, payload):
        if fault == "stop":
            worker.stop.set()
            return
        with data[0].tx() as c:
            if fault == "cancel":
                c.execute(update(runs).where(runs.c.id == job).values(cancel_intent=True))
            elif fault == "fence":
                c.execute(update(runs).where(runs.c.id == job).values(fence=2))
            elif fault == "version":
                c.execute(update(runs).where(runs.c.id == job).values(version=2))
            elif fault == "goal":
                c.execute(
                    update(goal_cards).where(goal_cards.c.id == data[6]["id"]).values(version=2)
                )
            elif fault == "revoke":
                c.execute(
                    update(grants).where(grants.c.resource_id == data[5]).values(revoked=True)
                )
            else:
                row = c.execute(select(attempts).where(attempts.c.run_id == job)).mappings().one()
                params = copy.deepcopy(row["parameters"])
                params["weight_version"] = "changed unused byte"
                c.execute(
                    update(attempts).where(attempts.c.id == row["id"]).values(parameters=params)
                )

    worker.goal_planner_transport = transport(sent, mutate=mutate)
    assert worker.once()
    with data[0].tx() as c:
        a = c.execute(select(attempts).where(attempts.c.run_id == job)).mappings().one()
        assert a["response"]["received_raw"] and a["status"] == "REJECTED_KNOWN"
        assert not c.execute(
            select(internal_instance_data).where(internal_instance_data.c.instance_id == inst["id"])
        ).first()
        assert not c.execute(
            select(operations.c.id).where(
                operations.c.run_id == job, operations.c.tool_ref == natural.SAVE
            )
        ).first()
        assert a["reserved_tokens"] > 0
        if fault == "parameters":
            assert a["parameters"]["weight_version"] == "changed unused byte"
    assert len(sent) == 1


def test_unknown_send_original_key_read_never_resends(env):
    data = setup(env)
    _, _, release, inst, _ = ready(data)
    job = enqueue(data, release, inst)
    sent = []

    def handler(request):
        sent.append(request.content)
        raise httpx.ReadTimeout("synthetic unknown response")

    assert Worker(data[0], data[1], goal_planner_transport=httpx.MockTransport(handler)).once()
    for _ in range(2):
        response = inspect(data, inst, job)
        assert response.status_code == 200 and response.json()["status"] == "WAITING_RESOURCE", (
            response.text
        )
    assert not Worker(data[0], data[1], goal_planner_transport=httpx.MockTransport(handler)).once()
    with data[0].tx() as c:
        a = c.execute(select(attempts).where(attempts.c.run_id == job)).mappings().one()
        assert a["status"] == "STARTED" and a["response"] is None and a["reserved_tokens"] > 0
    assert len(sent) == 1


@pytest.mark.parametrize(
    "fault",
    ["artifact", "runtime_unused", "original_unused", "typed", "terminal", "fake_rejection"],
)
def test_final_transaction_rolls_back_every_table_and_preserves_model_history(
    env, monkeypatch, fault
):
    from sim2act import pa_spec_apps as spec
    from sim2act.db import meta

    data = setup(env)
    origin, _, release, inst, _ = ready(data)
    job = enqueue(data, release, inst)
    sent = []
    worker = Worker(data[0], data[1], goal_planner_transport=transport(sent))
    run = data[0].claim(worker.id, data[1].lease_seconds)
    assert run["id"] == job
    for _ in range(3):
        assert spec.advance(worker, run)

    def all_tables():
        with data[0].tx() as c:
            return {
                t.name: sorted(
                    (dict(row) for row in c.execute(select(t)).mappings()),
                    key=lambda row: json.dumps(row, sort_keys=True, default=str),
                )
                for t in meta.sorted_tables
            }

    before = all_tables()
    if fault == "artifact":
        original = spec.write_text_artifact

        def fail(*args, **kwargs):
            original(*args, **kwargs)
            raise DomainError("VERIFICATION_FAILED", "After actual artifact write")

        monkeypatch.setattr(spec, "write_text_artifact", fail)
    elif fault == "typed":
        original = spec.insert

        def fail(table):
            if table is internal_instance_data:
                raise DomainError("VERIFICATION_FAILED", "Before typed append")
            return original(table)

        monkeypatch.setattr(spec, "insert", fail)
    else:
        original = data[0].event

        def fail(c, rid, kind, value):
            result = original(c, rid, kind, value)
            if kind == "SPEC_COMMITTED":
                if fault == "terminal":
                    raise DomainError("VERIFICATION_FAILED", "After terminal writes")
                if fault == "fake_rejection":
                    row = (
                        c.execute(select(attempts).where(attempts.c.run_id == job)).mappings().one()
                    )
                    original(
                        c,
                        job,
                        "NS_REJECTED",
                        dict(
                            attempt_id=row["id"],
                            error="fake rejected response",
                            attempt_fingerprint="0" * 64,
                            operation_id="fake",
                        ),
                    )
                    return result
                target = job if fault == "runtime_unused" else origin
                row = (
                    c.execute(
                        select(attempts).where(attempts.c.run_id == target).order_by(attempts.c.id)
                    )
                    .mappings()
                    .first()
                )
                params = copy.deepcopy(row["parameters"])
                params["unused_extra"] = "late audit byte"
                c.execute(
                    update(attempts).where(attempts.c.id == row["id"]).values(parameters=params)
                )
            return result

        monkeypatch.setattr(data[0], "event", fail)
    with pytest.raises(DomainError):
        spec.advance(worker, run)
    assert all_tables() == before and len(sent) == 1
    with data[0].tx() as c:
        assert (
            c.execute(select(attempts.c.status).where(attempts.c.run_id == job)).scalar_one()
            == "VERIFIED"
        )
        assert not c.execute(
            select(internal_instance_data).where(internal_instance_data.c.instance_id == inst["id"])
        ).first()


def test_lower_budget_rejected_before_any_reservation(env):
    data = setup(env)
    _, _, release, inst, _ = ready(data, "parallel")
    job = enqueue(data, release, inst)
    sent = []
    assert Worker(
        data[0], replace(data[1], max_requests=1), goal_planner_transport=transport(sent)
    ).once()
    with data[0].tx() as c:
        assert not c.execute(select(attempts.c.id).where(attempts.c.run_id == job)).first()
        assert not c.execute(
            select(internal_instance_data).where(internal_instance_data.c.instance_id == inst["id"])
        ).first()
    assert not sent


@pytest.mark.parametrize(
    "fault",
    ["cancel", "goal", "lease", "runtime_unused", "original_unused", "version", "created_at"],
)
def test_node_last_callback_rechecks_live_gate_before_verification(env, monkeypatch, fault):
    from sim2act.db import goal_cards

    data = setup(env)
    origin, _, release, inst, _ = ready(data)
    job = enqueue(data, release, inst)
    sent = []
    original = data[0].event

    def event(c, rid, kind, value):
        result = original(c, rid, kind, value)
        if rid == job and kind == "SPEC_STEP_VERIFIED" and value["step_id"] == "infer_pick":
            if fault == "cancel":
                c.execute(update(runs).where(runs.c.id == job).values(cancel_intent=True))
            elif fault == "lease":
                c.execute(update(runs).where(runs.c.id == job).values(lease_until=0))
            elif fault == "version":
                c.execute(update(runs).where(runs.c.id == job).values(version=2))
            elif fault == "created_at":
                c.execute(update(runs).where(runs.c.id == job).values(created_at=run_created + 60))
            elif fault == "goal":
                c.execute(
                    update(goal_cards).where(goal_cards.c.id == data[6]["id"]).values(version=2)
                )
            else:
                row = (
                    c.execute(
                        select(attempts)
                        .where(attempts.c.run_id == (job if fault == "runtime_unused" else origin))
                        .order_by(attempts.c.id)
                    )
                    .mappings()
                    .first()
                )
                params = copy.deepcopy(row["parameters"])
                params["late_unused"] = "after last node callback"
                c.execute(
                    update(attempts).where(attempts.c.id == row["id"]).values(parameters=params)
                )
        return result

    with data[0].tx() as c:
        run_created = c.execute(select(runs.c.created_at).where(runs.c.id == job)).scalar_one()
    monkeypatch.setattr(data[0], "event", event)
    assert Worker(data[0], data[1], goal_planner_transport=transport(sent)).once()
    with data[0].tx() as c:
        row = c.execute(select(attempts).where(attempts.c.run_id == job)).mappings().one()
        assert row["status"] == "REJECTED_KNOWN" and row["response"]["received_raw"]
        op = (
            c.execute(
                select(operations).where(
                    operations.c.run_id == job, operations.c.call_id == "infer_pick"
                )
            )
            .mappings()
            .one()
        )
        assert op["status"] == "REJECTED_KNOWN" and op["receipt"] is None
        assert not c.execute(
            select(internal_instance_data).where(internal_instance_data.c.instance_id == inst["id"])
        ).first()
    assert len(sent) == 1


def test_revoked_receiver_only_preserves_owned_raw_no_protected_full_read(env, tmp_path):
    from sql_private_barrier import PrivateReadBarrier
    from sqlalchemy.exc import DatabaseError

    from sim2act.db import grants

    data = setup(env)
    origin, _, release, inst, _ = ready(data)
    job = enqueue(data, release, inst)
    sent = []
    holder = {}

    def mutate(raw, payload):
        barrier = PrivateReadBarrier(data[0], {origin, job}, {data[5]})
        barrier.rules["attempts"] = (attempts, "run_id", {origin, job}, {"parameters", "usage"})
        with data[0].tx() as c:
            c.execute(update(grants).where(grants.c.resource_id == data[5]).values(revoked=True))
        barrier.__enter__()
        holder["barrier"] = barrier

    try:
        assert Worker(
            data[0], data[1], goal_planner_transport=transport(sent, mutate=mutate)
        ).once()
        barrier = holder["barrier"]
        assert not barrier.blocked and not barrier.evaluated
        response = inspect(data, inst, job)
        assert response.status_code == 403 and not barrier.blocked and not barrier.evaluated
        (tmp_path / "barrier.json").write_text(
            json.dumps(
                dict(blocked=barrier.blocked, evaluated=barrier.evaluated, sql=barrier.statements),
                indent=2,
            )
        )
        # Prove this is an actual row-cell barrier, after the zero-read check.
        with pytest.raises(DatabaseError):
            with data[0].tx() as c:
                c.execute(select(attempts).where(attempts.c.run_id == job)).mappings().all()
        assert barrier.blocked
    finally:
        if holder:
            holder["barrier"].__exit__(None, None, None)
    with data[0].tx() as c:
        row = c.execute(select(attempts).where(attempts.c.run_id == job)).mappings().one()
        assert row["response"]["received_raw"] and row["status"] == "REJECTED_KNOWN"


@pytest.mark.parametrize(
    "fault", ["operation_run", "app_instance", "app_fingerprint", "missing_slot"]
)
def test_rejected_scope_damage_never_mutates_other_history(env, fault):
    from sqlalchemy import delete

    from sim2act.db import internal_app_runs, internal_run_bindings, reservations

    data = setup(env)
    _, _, release, inst, _ = ready(data)
    job = enqueue(data, release, inst)
    sent = []
    held = {}
    second = data[2].post(
        f"/api/internal/releases/{release['id']}/instances",
        json=dict(
            expected_release_fingerprint=release["fingerprint"], request_key="other-instance"
        ),
    )
    assert second.status_code == 201, second.text
    other = second.json()
    other_job = enqueue(data, release, other, key="other-untouched")

    def mutate(raw, payload):
        with data[0].tx() as c:
            if fault == "operation_run":
                row = (
                    c.execute(
                        select(operations).where(
                            operations.c.run_id == job, operations.c.call_id == "infer_pick"
                        )
                    )
                    .mappings()
                    .one()
                )
                c.execute(
                    update(operations).where(operations.c.id == row["id"]).values(run_id=other_job)
                )
                held["operation"] = {**dict(row), "run_id": other_job}
            elif fault == "missing_slot":
                aid = c.execute(select(attempts.c.id).where(attempts.c.run_id == job)).scalar_one()
                c.execute(delete(reservations).where(reservations.c.id == aid))
            else:
                aid = c.execute(
                    select(internal_run_bindings.c.app_run_id).where(
                        internal_run_bindings.c.run_id == job
                    )
                ).scalar_one()
                row = (
                    c.execute(select(internal_app_runs).where(internal_app_runs.c.id == aid))
                    .mappings()
                    .one()
                )
                values = (
                    {"instance_id": other["id"]}
                    if fault == "app_instance"
                    else {"fingerprint": "0" * 64}
                )
                c.execute(
                    update(internal_app_runs).where(internal_app_runs.c.id == aid).values(**values)
                )
                held["app_run"] = {**dict(row), **values}

    assert Worker(data[0], data[1], goal_planner_transport=transport(sent, mutate=mutate)).once()
    with data[0].tx() as c:
        assert not c.execute(
            select(internal_instance_data).where(
                internal_instance_data.c.instance_id.in_([inst["id"], other["id"]])
            )
        ).first()
        if "operation" in held:
            assert (
                dict(
                    c.execute(select(operations).where(operations.c.id == held["operation"]["id"]))
                    .mappings()
                    .one()
                )
                == held["operation"]
            )
        if "app_run" in held:
            assert (
                dict(
                    c.execute(
                        select(internal_app_runs).where(
                            internal_app_runs.c.id == held["app_run"]["id"]
                        )
                    )
                    .mappings()
                    .one()
                )
                == held["app_run"]
            )
        assert (
            c.execute(select(runs.c.status).where(runs.c.id == other_job)).scalar_one() == "QUEUED"
        )
        row = c.execute(select(attempts).where(attempts.c.run_id == job)).mappings().one()
        assert row["status"] == "REJECTED_KNOWN" and row["response"]["received_raw"]
    assert len(sent) == 1
