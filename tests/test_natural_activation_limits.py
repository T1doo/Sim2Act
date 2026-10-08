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


def test_stalled_body_and_slow_cleanup_are_bounded(env):
    settings = replace(env[1], live_enabled=True, token="synthetic-offline-only")
    observed = []
    class Stream(httpx.AsyncByteStream):
        async def __aiter__(self):
            observed.append("reading")
            await asyncio.sleep(1)
            yield b"{}"
        async def aclose(self):
            observed.append("closing")
            await asyncio.sleep(1)
            observed.append("closed")
    async def handler(request):
        return httpx.Response(200, stream=Stream())
    provider = InternModel(settings, transport=httpx.MockTransport(handler))
    started = time.monotonic()
    with pytest.raises(DomainError) as error:
        provider.request_serialized(b'{"model":"intern-s2"}',
                                    lambda request: {"deadline": time.time() + .05})
    assert error.value.code == "MODEL_TIMEOUT_OR_TRUNCATED"
    assert time.monotonic() - started < .3
    assert observed == ["reading", "closing"]


def test_aged_other_account_attempt_blocks_final_activated_send(env):
    from sqlalchemy import insert
    from test_natural_activation import make_run, reserve, sending
    from test_natural_activation import setup as unit_setup

    from sim2act.db import new_id
    value = unit_setup(env)
    store, settings, *_ = value
    run = make_run(value, "read_preview")
    aid = reserve(value, run)
    other = new_id("attempt")
    with store.tx() as c:
        c.execute(insert(attempts).values(id=other, run_id="other-owned-synthetic-run",
                  status="STARTED", created_at=time.time()-65))
        c.execute(insert(reservations).values(id=other, run_id="other-owned-synthetic-run",
                  subject=settings.quota_subject, created_at=time.time()-65))
    with pytest.raises(DomainError) as error:
        sending(value, run, aid)
    assert error.value.code == "RATE_LIMITED"
    assert rows(store, activation.natural_activations)[0]["ledger"][0]["status"] == "STARTED"


def test_paired_queued_deadline_tamper_is_not_readable_or_sendable(env):
    import copy

    from sqlalchemy import update

    from sim2act.db import events
    value = setup(env)
    store, settings, client, *_ = value
    session, _ = approved(value)
    rid = submit(value, session).json()["run_id"]
    with store.tx() as c:
        run = next(r for r in rows(store, runs) if r["id"] == rid)
        context = copy.deepcopy(run["context"])
        context["natural_run_deadline"]["deadline"] += 1
        c.execute(update(runs).where(runs.c.id == rid).values(context=context))
        c.execute(update(events).where(events.c.run_id == rid,
                  events.c.kind == "NL_RUN_DEADLINE_FROZEN").values(
                  data=context["natural_run_deadline"]))
    denied = client.get(f"/api/runs/{rid}")
    assert denied.status_code == 409 and denied.json()["error"]["code"] == "VERSION_CONFLICT"
    sent = []
    def handler(request):
        sent.append(request.content)
        return httpx.Response(200, json=response(wire(value)))
    assert Worker(store, settings, goal_planner_transport=httpx.MockTransport(handler)).once()
    assert not sent and not rows(store, attempts) and not rows(store, reservations)
    assert not rows(store, operations)
