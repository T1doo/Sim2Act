import socket

import httpx
import pytest
from protocol_socket_oracle import forbid_external_network


def test_stdlib_windows_fallback_pair_remains_local_and_authenticated(monkeypatch):
    forbid_external_network(monkeypatch, "external")
    a, b = socket._fallback_socketpair()
    try:
        assert a.getsockname() == b.getpeername()
        assert b.getsockname() == a.getpeername()
        a.sendall(b"selfpipe")
        assert b.recv(8) == b"selfpipe"
    finally:
        a.close()
        b.close()


@pytest.mark.parametrize("host", ["127.0.0.1", "::1", "192.0.2.1"])
def test_direct_connection_never_inherits_socketpair_exception(monkeypatch, host):
    forbid_external_network(monkeypatch, "external")
    sock = socket.socket(socket.AF_INET6 if host == "::1" else socket.AF_INET)
    try:
        with pytest.raises(pytest.fail.Exception, match="external"):
            sock.connect((host, 1))
    finally:
        sock.close()


def test_real_http_transport_remains_blocked(monkeypatch):
    forbid_external_network(monkeypatch, "external")
    with httpx.Client() as client, pytest.raises(pytest.fail.Exception, match="external"):
        client.get("http://127.0.0.1:1/")
