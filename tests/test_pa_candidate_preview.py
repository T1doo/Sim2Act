"""Original P-A prompt/compiler over actual owned GoalCard; all HTTP is Mock only."""

import copy
import gzip
import hashlib
import json
import os
import time
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError
from sqlalchemy import event, insert, select, update
from test_goal_text_applications import fixture_candidate

from sim2act import goal_applications as ga
from sim2act import pa_candidate_preview as preview
from sim2act.config import Settings
from sim2act.contracts import Limits
from sim2act.db import Store, grants, meta, new_id, principals, resources
from sim2act.errors import DomainError
from sim2act.goals import GoalCardInput, create_card, revise_card
from sim2act.model import InternModel

TEXT = "Cedar valve check at dawn.\nMoss valve check at noon.\nCedar backup owner undecided.\n"
CAP = Limits(max_requests=2, max_tools=1, max_repairs=0, max_total_tokens=64000,
             max_output_tokens=1024, run_seconds=300)


@pytest.fixture
def case(tmp_path):
    store = Store("sqlite:///" + str(tmp_path / "candidate.sqlite"), test_only=True)
    store.initialize()
    user = new_id("user")
    with store.tx() as c:
        c.execute(insert(principals).values(id=user, name="synthetic P-A owner"))
    pid = store.project(user, "synthetic P-A candidate")
    rid = new_id("res")
    with store.tx() as c:
        runtime = store.own_project(c, user, pid)["runtime_id"]
        c.execute(insert(resources).values(id=rid, project_id=pid, name="notes.txt", format="txt",
            content=TEXT, hash=hashlib.sha256(TEXT.encode()).hexdigest()))
        store.add_grants(c, user, runtime, pid, rid, ["resource.read"])
    goal = GoalCardInput(title="Literal source lookup", goal="Return all whole matching lines and exact line numbers; do not infer meaning",
        known=["Matching is case sensitive"], assumptions=[],
        unresolved=["The meaning of these statements requires owner review"],
        constraints=["Return every matching whole line", "Do not summarize or infer obligations"],
        acceptance_checks=["Compare returned lines against the authorized source"], resource_refs=[rid])
    card = create_card(store, user, pid, goal.model_dump())
    request = dict(expected_version=card["version"], expected_fingerprint=card["fingerprint"],
                   request_key="pa-literal-preview-current")
    with store.engine.connect() as c:
        context = preview.prepare(store, c, user, card["id"], request, CAP)
    yield store, user, pid, rid, card, context
    store.engine.dispose()


def response(message, reason="stop", model="Intern-S2"):
    return dict(model=model, choices=[dict(finish_reason=reason, message=message)],
        usage=dict(prompt_tokens=100, completion_tokens=900, total_tokens=1000))


def proposed(context):
    initial = json.loads(context["messages"][1]["content"])
    value = fixture_candidate(initial)
    value["source_hash"] = context["source"]["hash"]
    return value


def final(context, value=None):
    return response(dict(role="assistant", content=json.dumps(
        proposed(context) if value is None else value, separators=(",", ":"))))


def snapshot(store):
    with store.engine.connect() as c:
        return {name: sorted(json.dumps(dict(row), sort_keys=True) for row in
            c.execute(select(table)).mappings()) for name, table in meta.tables.items()}


def test_original_adapter_read_candidate_compile_samples_and_zero_writes(case, tmp_path):
    store, user, _pid, rid, _card, context = case
    before, sql, sent = snapshot(store), [], []
    event.listen(store.engine, "before_cursor_execute",
                 lambda _c, _cur, s, _p, _ctx, _many: sql.append(s))

    def receive(request):
        body = json.loads(request.content)
        sent.append(body)
        if len(sent) == 1:
            assert TEXT not in json.dumps(body)
            return httpx.Response(200, json=response(dict(role="assistant", content="", tool_calls=[
                dict(id="real-mock-read", type="function", function=dict(name="resource.read",
                    arguments=json.dumps({"resource_id": rid})))]), "tool_calls"))
        tool = body["messages"][-1]
        assert tool["tool_call_id"] == "real-mock-read"
        assert json.loads(tool["content"]) == context["source"]
        return httpx.Response(200, json=final(context))

    settings = Settings("unused", tmp_path, mode="live", live_enabled=True,
                        token="synthetic-only", max_output_tokens=1024)
    model = InternModel(settings, httpx.MockTransport(receive))
    raw = model.request_serialized_captured(ga.body(context["messages"], ga.READ_TOOLS, 1024),
                                           lambda _: {"deadline": time.time() + 120})
    with store.engine.connect() as c:
        feedback = preview.read_feedback(store, c, user, context, raw.parsed)
    second = model.request_serialized_captured(ga.body(feedback["messages"], [], 1024),
                                               lambda _: {"deadline": time.time() + 120})
    with store.engine.connect() as c:
        result = preview.preview(store, c, user, context, second.parsed,
            sample_inputs=[{"term": "Cedar"}, {"term": "Moss"}, {"term": "cedar"}, {"term": "absent"}])
    assert len(sent) == 2 and sent[1]["tools"] == []
    assert result["candidate"] == proposed(context)
    assert result["state"] == "PREVIEW_ONLY" and result["generation_provenance"] == "NOT_ATTESTED"
    assert result["publishable"] is False and result["semantic_status"] == "UNKNOWN"
    assert [[v["start_line"] for v in s["result"]["citations"]] for s in result["samples"]] == [[1, 3], [2], [], []]
    assert [[v["quote"] for v in s["result"]["citations"]] for s in result["samples"]] == [
        ["Cedar valve check at dawn.", "Cedar backup owner undecided."],
        ["Moss valve check at noon."], [], []]
    assert all(v["start_line"] == v["end_line"] for s in result["samples"]
               for v in s["result"]["citations"])
    assert all(s.lstrip().upper().startswith("SELECT ") for s in sql)
    assert snapshot(store) == before
    if os.environ.get("SIM2ACT_PA_PREVIEW_EVIDENCE_DIR"):
        folder = Path(os.environ["SIM2ACT_PA_PREVIEW_EVIDENCE_DIR"])
        folder.mkdir(parents=True, exist_ok=False)
        artifacts = {"context.json": context, "read-feedback.json": feedback,
                     "preview.json": result, "table-vector.json": before,
                     "sql.json": sql, "mock-wires.json": sent}
        for name, value in artifacts.items():
            (folder / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
        (folder / "fixture.sqlite.gz").write_bytes(gzip.compress(
            Path(store.engine.url.database).read_bytes(), mtime=0))
        second_wire = ga.body(feedback["messages"], [], 1024)
        first_wire = ga.body(context["messages"], ga.READ_TOOLS, 1024)
        candidate_bytes = len(json.dumps(proposed(context), separators=(",", ":")).encode())
        (folder / "sizes.json").write_text(json.dumps(dict(
            classification="MOCK_SIZES_NOT_PROVIDER_TOKEN_ESTIMATE", first_body_bytes=len(first_wire),
            second_body_bytes=len(second_wire), reservation=len(first_wire)+len(second_wire)+2048,
            complete_fixture_candidate_bytes=candidate_bytes, live_requests=0), indent=2) + "\n")


@pytest.mark.parametrize("change", ["id", "hash", "goal", "port", "extra_permission", "executor", "unknown_field", "limit"])
def test_bad_complete_candidate_rejected_with_zero_writes(case, change):
    store, user, _pid, _rid, _card, context = case
    value = proposed(context)
    if change == "id":
        value["manifest"]["app_id"] = "app_" + "f" * 32
    elif change == "hash":
        value["source_hash"] = "0" * 64
    elif change == "goal":
        value["goal"]["unresolved"] = []
    elif change == "port":
        value["manifest"]["workflow"][0]["inputs"].pop("term")
    elif change == "extra_permission":
        value["actions"][0]["permission_requirements"].append(
            dict(tool_ref="artifact.save_text", resource_ref=context["project_id"]))
    elif change == "executor":
        value["actions"][0]["executor"]["ref"] = "unregistered.shell"
    elif change == "unknown_field":
        value["actions"][0]["extra"] = True
    elif change == "limit":
        value["manifest"]["runtime_limits"]["max_requests"] = 3
    before = snapshot(store)
    with store.engine.connect() as c, pytest.raises((DomainError, ValidationError)):
        preview.preview(store, c, user, context, final(context, value))
    assert snapshot(store) == before


@pytest.mark.parametrize("term", ["", " Cedar", "Cedar ", "x" * 81])
def test_invalid_sample_input_not_accepted(case, term):
    store, user, _pid, _rid, _card, context = case
    with store.engine.connect() as c, pytest.raises(DomainError):
        preview.preview(store, c, user, context, final(context), sample_inputs=[{"term": term}])


def test_current_revoke_and_context_tamper_rejected(case):
    store, user, _pid, rid, _card, context = case
    changed = copy.deepcopy(context)
    changed["saved_goal"]["snapshot"]["content"]["unresolved"] = []
    with store.engine.connect() as c, pytest.raises(DomainError):
        preview.preview(store, c, user, changed, final(context))
    with store.tx() as c:
        c.execute(update(grants).where(grants.c.resource_id == rid).values(revoked=True))
    before = snapshot(store)
    with store.engine.connect() as c, pytest.raises(DomainError) as error:
        preview.preview(store, c, user, context, final(context))
    assert error.value.code == "GRANT_REVOKED" and snapshot(store) == before


@pytest.mark.parametrize("fault", ["wrong_model", "truncated", "unknown_usage"])
def test_reply_failure_no_preview(case, fault):
    store, user, _pid, _rid, _card, context = case
    raw = final(context)
    if fault == "wrong_model":
        raw["model"] = "other"
    elif fault == "truncated":
        raw["choices"][0]["finish_reason"] = "length"
    else:
        raw.pop("usage")
    with store.engine.connect() as c, pytest.raises(DomainError):
        preview.preview(store, c, user, context, raw)


def test_foreign_owner_rejected_and_invalid_json_not_accepted(case):
    store, user, _pid, _rid, _card, context = case
    with store.engine.connect() as c, pytest.raises(DomainError):
        preview.prepare(store, c, new_id("user"), context["card_id"], context["request"], CAP)
    raw = response(dict(role="assistant", content='{"manifest":{},"manifest":{}}'))
    with store.engine.connect() as c, pytest.raises(DomainError):
        preview.preview(store, c, user, context, raw)


@pytest.mark.parametrize("mutation", ["grant", "goal"])
def test_gateway_return_cannot_publish_feedback_after_concurrent_change(case, monkeypatch, mutation):
    store, user, pid, rid, card, context = case
    original, calls = preview.authorized_read, []

    def read(*args, **kwargs):
        result = original(*args, **kwargs)
        calls.append(True)
        if len(calls) == 2:
            if mutation == "grant":
                with store.tx() as writer:
                    writer.execute(update(grants).where(grants.c.resource_id == rid).values(revoked=True))
            else:
                changed = copy.deepcopy(context["saved_goal"]["snapshot"]["content"])
                changed["constraints"].append("New owner constraint")
                revise_card(store, user, card["id"], GoalCardInput.model_validate(changed).model_dump(), 1)
        return result

    monkeypatch.setattr(preview, "authorized_read", read)
    raw = response(dict(role="assistant", content="", tool_calls=[dict(
        id="read-change", type="function", function=dict(name="resource.read",
            arguments=json.dumps({"resource_id": rid})))]), "tool_calls")
    with store.engine.connect() as c, pytest.raises(DomainError):
        preview.read_feedback(store, c, user, context, raw)
    assert len(calls) == 2
