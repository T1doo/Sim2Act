"""Adapter body evidence uses MockTransport only, with synthetic header canaries."""

import asyncio
import json
import time
from dataclasses import replace

import httpx
import pytest

from sim2act.config import Settings
from sim2act.errors import DomainError
from sim2act.model import CapturedResponse, InternModel

CANARY = "SYNTHETIC_HEADER_CANARY_NOT_A_REAL_CREDENTIAL"


def model(tmp_path, handler):
    settings = replace(Settings("sqlite://", tmp_path), live_enabled=True, token=CANARY)
    return InternModel(settings, transport=httpx.MockTransport(handler))


@pytest.mark.parametrize("payload", [b'{ "value" : 1 }\n', '{"value":"离线"}'.encode()])
def test_captured_body_preserves_exact_bytes_and_old_dict_contract(tmp_path, payload):
    sent = []

    def handler(request):
        assert request.headers["Authorization"] == "Bearer " + CANARY
        sent.append(request.content)
        return httpx.Response(200, content=payload)

    adapter = model(tmp_path, handler)
    captured = adapter.request_serialized_captured(b'{"model":"intern-s2"}', lambda _: None)
    assert type(captured) is CapturedResponse
    assert captured.body == payload and captured.parsed == json.loads(payload)
    assert CANARY.encode() not in captured.body
    old = adapter.request_serialized(b'{"model":"intern-s2"}', lambda _: None)
    assert type(old) is dict and old == captured.parsed
    assert sent == [b'{"model":"intern-s2"}'] * 2


@pytest.mark.parametrize("status,payload,code", [
    (200, b'{"broken":', "INVALID_INPUT"),
    (200, b'', "INVALID_INPUT"),
    (429, b'{"quota":"denied"}', "RATE_LIMITED"),
    (503, b'{"error":"offline"}', "RESOURCE_UNAVAILABLE"),
])
def test_received_invalid_or_refused_body_is_private_failure_evidence(tmp_path, status, payload, code):
    adapter = model(tmp_path, lambda _: httpx.Response(status, content=payload))
    with pytest.raises(DomainError) as rejected:
        adapter.request_serialized_captured(b"{}", lambda _: None)
    error = rejected.value
    assert error.code == code
    assert error._received_body == payload and error._received_body_complete is True
    assert getattr(error, "_received_response", None) is None
    if payload:
        assert payload.decode() not in json.dumps(error.public())
    assert CANARY not in json.dumps(error.public())


class InterruptedBody(httpx.AsyncByteStream):
    def __init__(self, tail):
        self.tail = tail

    async def __aiter__(self):
        yield b'{"received":"partial"}'
        if self.tail == "network":
            raise httpx.ReadError("Explicit offline stream fault")
        await asyncio.sleep(1)


@pytest.mark.parametrize("tail", ["deadline", "network"])
def test_partial_body_remains_incomplete_and_old_send_contract_stays_unchanged(tmp_path, tail):
    adapter = model(tmp_path, lambda _: httpx.Response(200, stream=InterruptedBody(tail)))
    with pytest.raises(DomainError) as rejected:
        adapter.request_serialized_captured(b"{}", lambda _: dict(deadline=time.time() + .05))
    error = rejected.value
    assert error.code == "MODEL_TIMEOUT_OR_TRUNCATED"
    assert error._received_body == b'{"received":"partial"}'
    assert error._received_body_complete is False
    assert error._received_response == ({"received": "partial"} if tail == "deadline" else None)
    assert "partial" not in json.dumps(error.public())
    if tail == "network":
        with pytest.raises(DomainError) as old:
            adapter.request_serialized(b"{}", lambda _: dict(deadline=time.time() + 1))
        assert old.value.code == "MODEL_TIMEOUT_OR_TRUNCATED"
        assert getattr(old.value, "_received_body", None) is None
        assert getattr(old.value, "_received_response", None) is None


def test_decoded_body_and_canonical_ascii_are_distinct_evidence(tmp_path):
    from sim2act.goal_applications import response_archive

    payload = '{ "value" : "离线" }\n'.encode()
    captured = model(tmp_path, lambda _: httpx.Response(200, content=payload)).request_serialized_captured(
        b"{}", lambda _: dict(deadline=time.time() + 1))
    canonical, evidence = response_archive(captured.parsed)
    assert captured.body == payload
    assert canonical.isascii() and canonical.encode() != payload
    assert evidence["bytes"] == len(canonical.encode())


def test_overlimit_failure_capture_is_a_finite_prefix_not_a_complete_body(tmp_path):
    payload = b"x" * 150000
    adapter = model(tmp_path, lambda _: httpx.Response(503, content=payload))
    with pytest.raises(DomainError) as rejected:
        adapter.request_serialized_captured(b"{}", lambda _: None)
    assert rejected.value._received_body == payload[:131072]
    assert rejected.value._received_body_complete is False


class OverLimitBody(httpx.AsyncByteStream):
    async def __aiter__(self):
        yield b"x" * 131073


def test_single_overlimit_chunk_does_not_become_a_complete_archived_response(tmp_path):
    adapter = model(tmp_path, lambda _: httpx.Response(200, stream=OverLimitBody()))
    with pytest.raises(DomainError) as rejected:
        adapter.request_serialized_captured(b"{}", lambda _: dict(deadline=time.time() + 1))
    assert rejected.value.code == "MODEL_OUTPUT_INVALID"
    assert rejected.value._received_body == b""  # Retained prefix before the rejected chunk.
    assert rejected.value._received_body_complete is False
