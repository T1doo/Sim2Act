"""Cancellation of the real adapter task using only synthetic HTTP transports."""

import asyncio
import time
from dataclasses import replace
from threading import Event, Timer

import httpx
import pytest

from sim2act.errors import DomainError
from sim2act.model import CapturedResponse, InternModel


@pytest.mark.parametrize("phase", ["before", "headers", "body", "deadline", "complete"])
def test_guarded_adapter_stop_has_one_task_and_bounded_cleanup(env, phase):
    stop = Event()
    sends, closed, cancelled = [], [], []
    prefix = b'{"model":"intern-s2","usage":{"prompt_tokens":5}}'

    class Stream(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield prefix
            if phase == "complete":
                return
            try:
                await asyncio.sleep(10)
            finally:
                cancelled.append("body")

        async def aclose(self):
            closed.append("body")

    async def handler(request):
        sends.append(request)
        if phase == "headers":
            try:
                await asyncio.sleep(10)
            finally:
                cancelled.append("headers")
        return httpx.Response(200, stream=Stream())

    adapter = InternModel(replace(env[1], live_enabled=True, token="SYNTHETIC_ONLY"),
                          transport=httpx.MockTransport(handler))
    if phase == "before":
        stop.set()
    timer = Timer(.1, stop.set) if phase in {"headers", "body"} else None
    if timer:
        timer.start()
    began = time.monotonic()
    try:
        guard = lambda request: {"deadline": time.time() + (.1 if phase == "deadline" else 3)}
        if phase == "complete":
            result = adapter.request_serialized_captured(b"{}", guard, _stop_event=stop)
            assert isinstance(result, CapturedResponse) and result.body == prefix
            assert result.parsed["usage"] == {"prompt_tokens": 5}
        else:
            with pytest.raises(DomainError) as failed:
                adapter.request_serialized_captured(b"{}", guard, _stop_event=stop)
            assert failed.value.code == "MODEL_TIMEOUT_OR_TRUNCATED"
            if phase in {"body", "deadline"}:
                assert failed.value._received_body == prefix
                assert failed.value._received_body_complete is False
            if phase == "body":
                assert failed.value._received_status_code == 200
            assert len(sends) == (0 if phase == "before" else 1)
            assert cancelled == ([] if phase == "before" else ["headers" if phase == "headers" else "body"])
        assert time.monotonic() - began < 2
        assert closed == (["body"] if phase in {"body", "deadline", "complete"} else [])
    finally:
        if timer:
            timer.cancel()
            timer.join()


def test_stop_contract_requires_original_event_and_finite_guard(env):
    sent = []
    adapter = InternModel(replace(env[1], live_enabled=True, token="SYNTHETIC_ONLY"),
        transport=httpx.MockTransport(lambda request: sent.append(request)))
    class FakeEvent:
        def is_set(self):
            return False
    for event, guard in [(FakeEvent(), lambda request: {"deadline": time.time()+2}),
                         (Event(), lambda request: None)]:
        with pytest.raises(DomainError) as failed:
            adapter.request_serialized_captured(b"{}", guard, _stop_event=event)
        assert failed.value.code == "PERMISSION_DENIED"
    assert sent == []


def test_last_chunk_stop_is_observed_without_watcher_schedule_and_preserves_complete_body(env):
    stop = Event()
    payload = b'{"model":"intern-s2","usage":{"prompt_tokens":5,"completion_tokens":3,"total_tokens":8}}'
    class FinishedAtStop(httpx.AsyncByteStream):
        async def __aiter__(self):
            stop.set()
            yield payload
    adapter = InternModel(replace(env[1], live_enabled=True, token="SYNTHETIC_ONLY"),
        transport=httpx.MockTransport(lambda request: httpx.Response(200, stream=FinishedAtStop())))
    with pytest.raises(DomainError) as failed:
        adapter.request_serialized_captured(b"{}", lambda request: {"deadline": time.time()+2}, _stop_event=stop)
    assert failed.value._received_body == payload
    assert failed.value._received_body_complete is True
    assert failed.value._received_status_code == 200
    assert failed.value._received_response['usage']['total_tokens'] == 8
