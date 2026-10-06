"""Deny external I/O while preserving the stdlib's authenticated internal socketpair."""

import inspect
import socket

import httpx
import pytest


def forbid_external_network(monkeypatch, message):
    original_connect = socket.socket.connect

    def connect(sock, address):
        frame = inspect.currentframe().f_back
        fallback = getattr(socket, "_fallback_socketpair", None)
        allowed = (
            fallback is not None
            and frame.f_code is fallback.__code__
            and frame.f_locals.get("csock") is sock
            and isinstance(address, tuple)
            and len(address) == 2
            and address[0] in {"127.0.0.1", "::1"}
        )
        listener = frame.f_locals.get("lsock") if allowed else None
        if listener is not None and listener.getsockname()[:2] == address:
            return original_connect(sock, address)
        pytest.fail(message)

    def forbidden(*args, **kwargs):
        pytest.fail(message)

    monkeypatch.setattr(socket.socket, "connect", connect)
    monkeypatch.setattr(socket.socket, "connect_ex", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", forbidden)
