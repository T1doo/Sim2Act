"""Zero-network transport boundary, durable failure and concurrent-send tests."""
import json
from dataclasses import replace
from threading import Event, Thread

import httpx
import pytest

from sim2act.config import Settings
from sim2act.errors import DomainError
from sim2act.model import InternModel
from sim2act.model_budget import BudgetedProvider, initialize_ledger


@pytest.fixture
def fixture(tmp_path):
    scope = {"approval_id": "OFFLINE_TEST_ONLY", "mode": "offline", "project_id": "synthetic",
             "resource_ids": [], "tool_refs": ["resource.read"], "model": "intern-s2", "max_requests": 3}
    path = tmp_path / "approval.json"
    initialize_ledger(path, scope)
    settings = Settings("sqlite://", tmp_path, live_enabled=True, token="OFFLINE_FAKE",
                        max_repairs=0)
    ticks = [100.0]
    sent = []
    def handler(request):
        sent.append(request.content)
        return httpx.Response(200, json={"model": "Intern-S2", "usage": {
            "prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8}, "choices": []})
    model = InternModel(settings, httpx.MockTransport(handler))
    def runner(stage="source_a", authorize=lambda _: True):
        return BudgetedProvider(model, path, scope, stage, authorize=authorize, clock=lambda: ticks[0])
    return scope, path, model, ticks, sent, runner


def code(expected, callable):
    with pytest.raises(DomainError) as exc:
        callable()
    assert exc.value.code == expected


def test_explicit_scope_no_reset_and_actual_serialization(fixture):
    scope, path, model, ticks, sent, runner = fixture
    r = runner()
    r.call([{"role": "user", "content": "合成测试"}], [])
    data = json.loads(path.read_text())
    assert len(data["slots"]) == 1 and data["known_tokens"] == 8
    assert data["slots"][0]["bytes"] == len(sent[0])
    assert data["slots"][0]["chars"] == len(sent[0].decode())
    assert "OFFLINE_FAKE" not in path.read_text() and "合成测试" not in path.read_text()
    code("VERSION_CONFLICT", lambda: initialize_ledger(path, scope))
    code("PERMISSION_DENIED", lambda: r.require_scope({**scope, "approval_id": "different"}))
    code("RATE_LIMITED", lambda: runner("source_b").call([], []))
    ticks[0] += 6
    runner("source_b").call([], [])
    assert len(sent) == 2


def test_oversize_or_denial_never_reserves_or_sends(fixture):
    _, path, _, _, sent, runner = fixture
    code("BUDGET_EXHAUSTED", lambda: runner().call([{"role": "user", "content": "x" * 8000}], []))
    code("BUDGET_EXHAUSTED", lambda: runner().call([{"role": "user", "content": "中" * 4000}], []))
    code("PERMISSION_DENIED", lambda: runner(authorize=lambda _: False).call([], []))
    assert not sent and not json.loads(path.read_text())["slots"]


@pytest.mark.parametrize("text", ["x" * 8000, "中" * 4000])
def test_complete_wire_preflight_refuses_character_or_byte_overflow_without_consumption(fixture, text):
    _, path, _, _, sent, runner = fixture
    provider = runner()
    before = json.loads(path.read_text())
    messages = [{"role": "user", "content": text}]
    body, chars = provider._request_body(messages, [])
    assert chars > 8000 if text.isascii() else chars < 8000 and len(body) > 10000
    code("BUDGET_EXHAUSTED", lambda: provider.preflight(messages, []))
    assert json.loads(path.read_text()) == before and sent == []


def test_per_stage_cap_is_durable_across_instances(fixture):
    _, path, _, ticks, sent, runner = fixture
    runner("extract_a").call([], [])
    ticks[0] += 6
    code("BUDGET_EXHAUSTED", lambda: runner("extract_a").call([], []))
    assert len(sent) == 1 and len(json.loads(path.read_text())["slots"]) == 1


@pytest.mark.parametrize("response", [{"model": "Intern-S2"}, {"model": "wrong"}])
def test_unknown_usage_or_identity_stops_every_stage(fixture, response):
    _, path, model, ticks, _, runner = fixture
    model.transport = httpx.MockTransport(lambda _: httpx.Response(200, json=response))
    with pytest.raises(DomainError):
        runner().call([], [])
    data = json.loads(path.read_text())
    assert data["halted"] and data["slots"][0]["status"] == "FAILED_OR_UNKNOWN"
    ticks[0] += 6
    code("OUTCOME_UNKNOWN", lambda: runner("cold_b").call([], []))
    assert len(json.loads(path.read_text())["slots"]) == 1


def test_crash_start_and_missing_ledger_fail_closed(fixture):
    _, path, _, _, sent, runner = fixture
    r = runner()
    data = json.loads(path.read_text())
    data["slots"] = [{"stage": "source_a", "status": "STARTED", "time": 0, "reserved": 1100}]
    data["reserved"] = 1100
    path.write_text(json.dumps(data))
    code("OUTCOME_UNKNOWN", lambda: r.call([], []))
    path.unlink()
    code("OUTCOME_UNKNOWN", lambda: r.call([], []))
    assert not sent


def test_concurrent_sender_cannot_cross_network_lock(fixture):
    _, path, model, ticks, _, runner = fixture
    entered, release = Event(), Event()
    def handler(_):
        entered.set()
        assert release.wait(5)
        return httpx.Response(200, json={"model": "intern-s2", "usage": {
            "prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}})
    model.transport = httpx.MockTransport(handler)
    a, b = runner(), runner("source_b")
    errors = []
    def send():
        try:
            a.call([], [])
        except BaseException as e:
            errors.append(e)
    thread = Thread(target=send)
    thread.start()
    try:
        assert entered.wait(5)
        code("LOCK_CONFLICT", lambda: b.call([], []))
    finally:
        release.set()
        thread.join(5)
    assert not thread.is_alive() and not errors
    assert len(json.loads(path.read_text())["slots"]) == 1


def test_offline_cannot_use_network_and_unapproved_live_disabled(fixture):
    scope, path, model, _, sent, _ = fixture
    model.transport = None
    code("PERMISSION_DENIED", lambda: BudgetedProvider(model, path, scope, "source_a", authorize=lambda _: True))
    code("PERMISSION_DENIED", lambda: BudgetedProvider(model, path, {**scope, "mode": "live"}, "source_a", authorize=lambda _: True))
    assert not sent


def test_global_reservation_stops_before_send(fixture):
    _, path, _, ticks, sent, runner = fixture
    # Three stages each reserve ~14k; fourth would cross 64k despite unused slots.
    for stage in ["source_a", "cold_a", "source_b"]:
        runner(stage).call([{"role": "user", "content": "x" * 6000}], [])
        ticks[0] += 6
        runner(stage).call([{"role": "user", "content": "x" * 6000}], [])
        ticks[0] += 6
    # Six calls are ~43k; three more fit global but stage limits remain independently enforced.
    runner("cold_b").call([{"role": "user", "content": "x" * 6000}], [])
    ticks[0] += 6
    runner("cold_b").call([{"role": "user", "content": "x" * 6000}], [])
    ticks[0] += 6
    code("BUDGET_EXHAUSTED", lambda: runner("cold_b").call([{"role": "user", "content": "x" * 6000}], []))
    assert len(sent) == 8 and len(json.loads(path.read_text())["slots"]) == 8


def test_all_fourteen_slots_share_one_persistent_approval(fixture):
    _, path, _, ticks, sent, runner = fixture
    from sim2act.model_budget import STAGES
    for stage, count in STAGES.items():
        for _ in range(count):
            runner(stage).call([], [])
            ticks[0] += 6
    assert len(sent) == 14
    code("BUDGET_EXHAUSTED", lambda: runner().call([], []))
    assert len(json.loads(path.read_text())["slots"]) == 14


def test_changed_transport_or_output_cap_rejected_before_network(fixture):
    _, path, model, _, sent, runner = fixture
    r = runner()
    model.settings = replace(model.settings, max_output_tokens=1023)
    code("PERMISSION_DENIED", lambda: r.call([], []))
    model.settings = replace(model.settings, max_output_tokens=1024)
    model.transport = None
    code("PERMISSION_DENIED", lambda: r.call([], []))
    assert not sent and not json.loads(path.read_text())["slots"]


def test_protocol_failure_explicitly_halts_next_stage(fixture):
    _, path, _, ticks, sent, runner = fixture
    r = runner()
    r.call([], [])
    r.halt()
    ticks[0] += 6
    code("OUTCOME_UNKNOWN", lambda: runner("extract_b").call([], []))
    assert len(sent) == 1 and json.loads(path.read_text())["halted"]


def test_authorization_hook_cannot_mutate_frozen_wire(fixture):
    _, path, _, _, sent, runner = fixture
    messages = [{"role": "user", "content": "small"}]
    def authorize(_):
        messages[0]["content"] = "x" * 20000
        return True
    runner(authorize=authorize).call(messages, [])
    assert json.loads(sent[0])["messages"][0]["content"] == "small"
    assert json.loads(path.read_text())["slots"][0]["bytes"] == len(sent[0])


def test_approved_request_cap_can_only_tighten_stage(fixture):
    scope, path, model, ticks, sent, _ = fixture
    path.unlink()
    scope["max_requests"] = 1
    initialize_ledger(path, scope)
    r = BudgetedProvider(model, path, scope, "source_a", authorize=lambda _: True, clock=lambda: ticks[0])
    r.call([], [])
    ticks[0] += 6
    code("BUDGET_EXHAUSTED", lambda: r.call([], []))
    assert len(sent) == 1


@pytest.mark.parametrize("usage", [
    {"prompt_tokens": 19999, "completion_tokens": 1, "total_tokens": 20000},
    {"prompt_tokens": 1, "completion_tokens": 1025, "total_tokens": 1026},
])
def test_actual_usage_excess_persists_and_halts(fixture, usage):
    _, path, model, ticks, _, runner = fixture
    model.transport = httpx.MockTransport(lambda _: httpx.Response(200, json={"model": "intern-s2", "usage": usage}))
    code("BUDGET_EXHAUSTED", lambda: runner("extract_a").call([], []))
    data = json.loads(path.read_text())
    assert data["halted"] and data["known_tokens"] == usage["total_tokens"]
    assert data["slots"][0]["tokens"] == usage["total_tokens"]
    ticks[0] += 6
    code("OUTCOME_UNKNOWN", lambda: runner("source_b").call([], []))


def test_boolean_integer_tool_schema_tamper_is_not_equal(fixture):
    _, path, _, _, sent, runner = fixture
    from sim2act.tools import definitions
    tools = json.loads(json.dumps([x for x in definitions() if x["function"]["name"] == "resource.read"]))
    tools[0]["function"]["parameters"]["additionalProperties"] = 0
    code("PERMISSION_DENIED", lambda: runner().call([], tools))
    assert not sent and not json.loads(path.read_text())["slots"]


def test_durable_candidate_anchor_survives_cold_reopen_and_rejects_rebinding(fixture):
    from sim2act.db import fingerprint
    scope, path, model, ticks, _, runner = fixture
    candidate = {"schema_version": "synthetic", "steps": ["model_decided"]}
    model.transport = httpx.MockTransport(lambda _: httpx.Response(200, json={
        "model": "intern-s2", "usage": {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
        "choices": [{"message": {"content": json.dumps(candidate)}}]}))
    extraction = runner("extract_a")
    extraction.call([], [])
    receipt = extraction.accept_candidate(fingerprint(candidate), "source-proof")
    cold = BudgetedProvider(model, path, scope, "cold_a", authorize=lambda _: True, clock=lambda: ticks[0])
    assert cold.verify_candidate_receipt(receipt, fingerprint(candidate), "source-proof")
    code("VERIFICATION_FAILED", lambda: cold.verify_candidate_receipt(receipt, "substituted", "source-proof"))
    code("VERIFICATION_FAILED", lambda: cold.verify_candidate_receipt(receipt, fingerprint(candidate), "other-proof"))
    code("VERIFICATION_FAILED", lambda: extraction.accept_candidate(fingerprint(candidate), "other-proof"))
    cold.halt()
    code("OUTCOME_UNKNOWN", lambda: cold.require_scope(scope))


def test_stage_wall_limit_persists_across_reopen(fixture):
    scope, path, _, ticks, sent, runner = fixture
    r = runner()
    ticks[0] += 301
    code("BUDGET_EXHAUSTED", lambda: r.call([], []))
    assert json.loads(path.read_text())["halted"]
    code("OUTCOME_UNKNOWN", lambda: runner("source_b"))
    assert not sent
