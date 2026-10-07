"""Deadline/rate blockers reproduced through ordinary API and Worker, offline."""

import asyncio
import time
from dataclasses import replace
from types import SimpleNamespace

import httpx
import pytest
from test_natural_activation_flow import approved, setup, submit, wire
from test_natural_goal_planning import response, rows

from sim2act import db
from sim2act import natural_activations as activation
from sim2act.db import attempts, operations, reservations, runs
from sim2act.errors import DomainError
from sim2act.model import InternModel
from sim2act.worker import Worker


def test_created_run_121_seconds_old_never_reserves_or_sends(env, monkeypatch):
    value = setup(env)
    store, settings, client, *_ = value
    session, _ = approved(value)
    rid = submit(value, session).json()["run_id"]
    now = time.time() + 121
    monkeypatch.setattr(db, "time", SimpleNamespace(time=lambda: now))
    monkeypatch.setattr(activation, "now", lambda: now)
    sent = []
    def handler(request):
        sent.append(request.content)
        return httpx.Response(200, json=response(wire(value)))
    worker = Worker(store, settings, goal_planner_transport=httpx.MockTransport(handler))
    assert worker.once()
    assert sent == []
    assert not rows(store, attempts) and not rows(store, reservations) and not rows(store, operations)
    assert client.get(f"/api/runs/{rid}").json()["result"] is None
    assert rows(store, runs)[0]["lease_until"] == 0


def test_default_rpm30_cannot_send_two_activated_goals_in_one_minute(env):
    value = setup(env)
    store, settings, client, *_ = value
    assert settings.rpm == 30
    session, _ = approved(value)
    sent = []
    for kind in activation.KINDS:
        accepted = submit(value, session, kind, kind)
        assert accepted.status_code == 202
        def handler(request, kind=kind):
            sent.append(request.content)
            return httpx.Response(200, json=response(wire(value, kind)))
        assert Worker(store, settings, goal_planner_transport=httpx.MockTransport(handler)).once()
    assert len(sent) == len(rows(store, attempts)) == len(rows(store, reservations)) == 1
    assert not rows(store, operations)
    assert client.get(f"/api/natural-activations/{session['id']}").json()["charged_requests"] == 1


def test_model_request_has_total_deadline_not_repeated_phase_timeout(env):
    settings = replace(env[1], live_enabled=True, token="synthetic-offline-only")
    observed = []
    async def handler(request):
        observed.append("started")
        await asyncio.sleep(1)
        observed.append("completed")
        return httpx.Response(200, json={"choices": []})
    provider = InternModel(settings, transport=httpx.MockTransport(handler))
    started = time.monotonic()
    with pytest.raises(DomainError) as error:
        provider.request_serialized(b'{"model":"intern-s2"}',
                                    lambda request: {"deadline": time.time() + .05})
    assert error.value.code == "MODEL_TIMEOUT_OR_TRUNCATED"
    assert time.monotonic() - started < .5 and observed == ["started"]
