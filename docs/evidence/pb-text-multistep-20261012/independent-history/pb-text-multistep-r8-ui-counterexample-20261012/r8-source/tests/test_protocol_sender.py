"""Actual sender checks the frozen bytes immediately before transport dispatch."""

from dataclasses import replace

import httpx
import pytest

from sim2act.errors import DomainError
from sim2act.model import InternModel
from sim2act.model_budget import ENDPOINT


def test_sender_uses_identical_serialized_body_with_no_second_json_encoding(env):
    seen = []
    body = b'{"model":"intern-s2","messages":[],"tools":[],"stream":false,"max_tokens":1024}'
    settings = replace(env[1], live_enabled=True, token="MOCK_ONLY")
    model = InternModel(
        settings,
        httpx.MockTransport(
            lambda req: seen.append(req.content) or httpx.Response(200, json={"model": "intern-s2"})
        ),
    )
    checks = []

    def validate(request):
        assert request.method == "POST" and str(request.url) == ENDPOINT
        assert request.content == body
        assert request.headers["content-type"] == "application/json"
        checks.append(request.content)

    assert model.request_serialized(body, validate) == {"model": "intern-s2"}
    assert seen == checks == [body]


def test_sender_guard_failure_never_dispatches_and_does_not_expose_body(env):
    seen = []
    settings = replace(env[1], live_enabled=True, token="MOCK_ONLY")
    model = InternModel(
        settings, httpx.MockTransport(lambda req: seen.append(req) or httpx.Response(200))
    )

    def reject(request):
        raise DomainError("PERMISSION_DENIED", "Frozen envelope differs")

    with pytest.raises(DomainError) as exc:
        model.request_serialized(b'{"private":"FORBIDDEN_SYNTHETIC_SENTINEL"}', reject)
    assert seen == [] and "FORBIDDEN" not in str(exc.value)


def test_sender_default_configuration_cannot_dispatch_even_with_validator(env):
    seen = []
    model = InternModel(
        env[1], httpx.MockTransport(lambda req: seen.append(req) or httpx.Response(200))
    )
    with pytest.raises(DomainError) as exc:
        model.request_serialized(b"{}", lambda _: None)
    assert exc.value.code == "RESOURCE_UNAVAILABLE" and seen == []


def test_authorization_hook_cannot_replace_frozen_credentials_with_source_answer(env, tmp_path):
    import json

    from sim2act.model_budget import BudgetedProvider, initialize_ledger

    sent = []
    settings = replace(env[1], live_enabled=True, token="MOCK_ONLY")
    model = InternModel(
        settings, httpx.MockTransport(lambda req: sent.append(req) or httpx.Response(200))
    )
    scope = {
        "approval_id": "OFFLINE_TEST_ONLY",
        "project_id": env[5],
        "resource_ids": [],
        "tool_refs": ["resource.read"],
        "max_requests": 3,
        "mode": "offline",
        "model": "intern-s2",
    }
    path = tmp_path / "sender.json"
    initialize_ledger(path, scope)

    def authorize(_):
        model.settings = replace(settings, token="SOURCE_ANSWER_NOT_ALLOWED")
        return True

    provider = BudgetedProvider(model, path, scope, "source_a", authorize=authorize)
    provider.wire_guard = lambda req: None
    with pytest.raises(DomainError) as exc:
        provider.call([], [])
    assert exc.value.code == "PERMISSION_DENIED" and sent == []
    assert json.loads(path.read_text())["slots"] == []


def test_actual_header_mutation_is_rejected_before_transport_and_consumes_unknown_slot(
    env, tmp_path, monkeypatch
):
    import json

    from sim2act.model_budget import BudgetedProvider, initialize_ledger

    sent = []
    settings = replace(env[1], live_enabled=True, token="MOCK_ONLY")
    model = InternModel(
        settings, httpx.MockTransport(lambda req: sent.append(req) or httpx.Response(200))
    )
    scope = {
        "approval_id": "OFFLINE_TEST_ONLY",
        "project_id": env[5],
        "resource_ids": [],
        "tool_refs": ["resource.read"],
        "max_requests": 3,
        "mode": "offline",
        "model": "intern-s2",
    }
    path = tmp_path / "sender.json"
    initialize_ledger(path, scope)
    provider = BudgetedProvider(model, path, scope, "source_a", authorize=lambda _: True)
    provider.wire_guard = lambda req: None
    build = httpx.Client.build_request

    def altered(client, *args, **kwargs):
        request = build(client, *args, **kwargs)
        request.headers["Authorization"] = "Bearer SOURCE_ANSWER_NOT_ALLOWED"
        return request

    monkeypatch.setattr(httpx.Client, "build_request", altered)
    with pytest.raises(DomainError) as exc:
        provider.call([], [])
    assert exc.value.code == "PERMISSION_DENIED" and sent == []
    data = json.loads(path.read_text())
    assert data["halted"] and len(data["slots"]) == 1
    assert "SOURCE_ANSWER_NOT_ALLOWED" not in path.read_text()
