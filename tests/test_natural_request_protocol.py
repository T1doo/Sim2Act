import json

import pytest

from sim2act import natural_request as request
from sim2act import natural_spec_runtime as runtime
from sim2act import production_trial_sender as sender
from sim2act.errors import DomainError
from sim2act.goal_applications import body as old_body
from sim2act.natural_live_admission import TrialCaps


def test_complete_unicode_coordinates_and_old_wire_identity():
    content = "A😀e\u0301\r\n Z"
    points = request.coordinates(content)
    assert [n for n, char in points] == list(range(len(content)))
    assert "".join(char for n, char in points) == content
    messages = [{"role": "user", "content": content}]
    assert request.body(messages, [], 1024) == old_body(messages, [], 1024)


def test_v2_messages_and_fixed_wire_have_exact_source_and_version():
    binding = {"draft": {"candidate": {"goal": {"goal": "Read"}}}}
    intent = {"args": {"content": "A😀B"}}
    step, action = {"step_id": "read"}, {"executor": {"ref": "model.spec.all"}}
    legacy = runtime.messages(binding, step, action, intent)
    current = runtime.messages(binding, step, action, intent, protocol=request.VERSION)
    assert "source_codepoints" not in json.loads(legacy[1]["content"])
    payload = json.loads(current[1]["content"])
    assert payload["current_inputs"] == intent["args"]
    assert payload["source_codepoints"] == [[0,"A"],[1,"😀"],[2,"B"]]
    wire = request.body(current, [], 1024, request_protocol=request.VERSION)
    parsed = json.loads(wire)
    assert parsed["thinking_mode"] is False
    from types import SimpleNamespace
    contract = SimpleNamespace(caps=TrialCaps(), model="intern-s2")
    sender._wire(contract, wire, stage="source")
    for value in (True, 0, None, "false"):
        with pytest.raises(DomainError):
            sender._wire(contract, json.dumps(parsed | {"thinking_mode": value}).encode(), stage="source")
    with pytest.raises(DomainError):
        sender._wire(contract, wire, stage="generate")
    no_thinking = dict(parsed)
    no_thinking.pop("thinking_mode")
    with pytest.raises(DomainError):
        sender._wire(contract, json.dumps(no_thinking).encode(), stage="source")
    for key, value in (("request_protocol", None), ("request_protocol", "future")):
        modified = {**payload, key: value}
        bad = {**no_thinking, "messages": [current[0], {"role": "user", "content": json.dumps(modified)}]}
        with pytest.raises(DomainError):
            sender._wire(contract, json.dumps(bad).encode(), stage="source")
    for invalid in ("bad", {"role": "user", "content": "[]"}):
        bad = {**parsed, "messages": [current[0], invalid]}
        with pytest.raises(DomainError):
            sender._wire(contract, json.dumps(bad).encode(), stage="source")


def test_unknown_protocol_and_tools_stay_closed():
    with pytest.raises(DomainError):
        request.body([], [], 1024, request_protocol="future")
    with pytest.raises(DomainError):
        request.body([], [{"name":"unexpected"}], 1024, request_protocol=request.VERSION)
