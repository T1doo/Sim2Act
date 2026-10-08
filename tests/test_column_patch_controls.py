"""Every patch-key boundary rejects controls before binding SQL parameters."""

import copy
import json
import socket
from types import SimpleNamespace
from urllib.parse import quote

import pytest
from sqlalchemy import event, select, update
from test_column_patch_keys import http as owned_http
from test_column_patches import check_body, setup, url

from sim2act.column_patches import CheckInput, check, load, propose, read_pair, validate_request_key
from sim2act.db import delivery_graph_requests, fingerprint
from sim2act.errors import DomainError

CONTROLS = ["nul\0check", "tab\tcheck", "lf\ncheck", "cr\rcheck", "unit\x1fcheck", "del\x7fcheck"]


@pytest.fixture
def http(env):
    yield from owned_http.__wrapped__(env)


def collect_sql(store):
    seen = []

    def inspect(conn, cursor, statement, parameters, context, executemany):
        def visit(value):
            if isinstance(value, str):
                seen.append(value)
            elif isinstance(value, dict):
                for item in value.values():
                    visit(item)
            elif isinstance(value, (list, tuple)):
                for item in value:
                    visit(item)
        visit(parameters)

    event.listen(store.engine, "before_cursor_execute", inspect)
    return seen, inspect


@pytest.mark.parametrize("char", [chr(i) for i in range(32)] + [chr(127)])
def test_shared_validator_all_ascii_controls_and_read_before_any_sql(char):
    key = "owned" + char + "key"
    # A bare object has no DB API: attempted SQL would raise AttributeError.
    for call in (
        lambda: validate_request_key(key),
        lambda: read_pair(object(), "user", "app", "column_check", key, CheckInput),
        lambda: load(object(), object(), "user", "project", "app", key, None),
        lambda: propose(object(), "user", "project", "app", SimpleNamespace(request_key=key), None),
        lambda: check(object(), "user", "project", "app", key, CheckInput(expected_patch_fingerprint="0" * 64, request_key="safe"), None),
        lambda: check(object(), "user", "project", "app", "safe", CheckInput(expected_patch_fingerprint="0" * 64, request_key=key), None),
    ):
        with pytest.raises(DomainError) as error:
            call()
        assert error.value.code == "INVALID_INPUT"


@pytest.mark.parametrize("key", CONTROLS)
def test_check_json_control_rejected_before_sql_and_history_unchanged(env, http, key):
    aid, _, _, body, _ = setup(env)
    target = url(env, aid)
    patch = http.post(target, json=body).json()
    before = http.get(target).json()
    seen, listener = collect_sql(env[0])
    try:
        for _ in range(2):
            response = http.post(target + "/new-definition/checks", json=check_body(patch, key))
            assert response.status_code == 400, response.text
            assert response.json()["error"]["code"] == "INVALID_INPUT"
        assert not any(key in value for value in seen)
    finally:
        event.remove(env[0].engine, "before_cursor_execute", listener)
    assert http.get(target).json() == before


@pytest.mark.parametrize("key", CONTROLS)
def test_decoded_control_path_rejected_without_sql_or_receipt(env, http, key):
    aid, _, _, body, _ = setup(env)
    target = url(env, aid)
    patch = http.post(target, json=body).json()
    before = http.get(target).json()
    seen, listener = collect_sql(env[0])
    try:
        response = http.post(target + "/" + quote(key, safe="") + "/checks", json=check_body(patch, "safe"))
        # LF cannot match the router's path converter; it is refused before the
        # handler. Other decoded controls reach the shared SQL-before boundary.
        assert response.status_code in {400, 404}, response.text
        assert not any(key in value for value in seen)
    finally:
        event.remove(env[0].engine, "before_cursor_execute", listener)
    assert http.get(target).json() == before


@pytest.mark.parametrize("key", ["literal%00/key", "literal%0A/key", "独立/check key", "../check-key"])
def test_acceptable_check_body_keys_and_literal_percent_definition_path(env, http, key):
    aid, _, _, body, _ = setup(env)
    target = url(env, aid)
    definition_key = "literal%00/definition"
    patch = http.post(target, json={**body, "request_key": definition_key}).json()
    path = target + "/" + quote(definition_key, safe="") + "/checks"
    confirmed = http.post(path, json=check_body(patch, key))
    assert confirmed.status_code == 201, confirmed.text
    replay = http.post(path, json=check_body(patch, key))
    assert replay.status_code == 201 and replay.json()["cached"]
    assert http.get(target).json()["items"][0]["checks"][0]["request_key"] == key


def test_sqlite_legacy_control_receipts_retained_but_not_current_proof(env, http):
    if not env[0].sqlite:
        pytest.skip("PostgreSQL cannot historically store NUL text; SQLite legacy fixture only")
    aid, _, _, body, _ = setup(env)
    target = url(env, aid)
    patch = http.post(target, json=body).json()
    confirmation = check_body(patch, "old-check")
    assert http.post(target + "/new-definition/checks", json=confirmation).status_code == 201
    with env[0].tx() as c:
        records = c.execute(select(delivery_graph_requests).where(
            delivery_graph_requests.c.app_id == aid,
            delivery_graph_requests.c.kind.in_(["column_check", "column_check_seal"]))).mappings().all()
        for row in records:
            saved = copy.deepcopy(row["snapshot"])
            saved["request"]["request_key"] = "nul\0legacy"
            saved["response"]["request_key"] = "nul\0legacy"
            saved["response"].pop("check_fingerprint")
            saved["response"]["check_fingerprint"] = fingerprint(saved["response"])
            c.execute(update(delivery_graph_requests).where(
                delivery_graph_requests.c.app_id == aid, delivery_graph_requests.c.principal_id == env[3],
                delivery_graph_requests.c.kind == row["kind"], delivery_graph_requests.c.request_key == row["request_key"]).values(
                request_key="nul\0legacy", request_fingerprint=fingerprint(saved["request"]),
                snapshot=saved, fingerprint=fingerprint(saved)))
        before = [dict(r) for r in c.execute(select(delivery_graph_requests).where(delivery_graph_requests.c.app_id == aid)).mappings()]
    history = http.get(target)
    assert history.status_code == 200, history.text
    assert history.json()["items"][0]["patch"]["request_key"] == "new-definition"
    assert history.json()["items"][0]["checks"] == []
    assert history.json()["unsupported_keys"] == [dict(kind="column_check", request_key="nul\0legacy", state="UNSUPPORTED_KEY", reason="INVALID_INPUT")]
    with env[0].tx() as c:
        after = [dict(r) for r in c.execute(select(delivery_graph_requests).where(delivery_graph_requests.c.app_id == aid)).mappings()]
    assert before == after


@pytest.mark.parametrize("control", [b"\x00", b"\t", b"\n", b"\r", b"\x7f"])
def test_raw_http_control_request_target_never_reaches_key_sql(env, http, control):
    aid, _, _, body, _ = setup(env)
    target = url(env, aid)
    patch = http.post(target, json=body).json()
    before = http.get(target).json()
    payload = json.dumps(check_body(patch, "raw-safe")).encode()
    request = (b"POST " + target.encode() + b"/raw" + control + b"key/checks HTTP/1.1\r\n"
               + f"Host: 127.0.0.1:{http.base_url.port}\r\n".encode()
               + b"Authorization: Bearer synthetic-test-A\r\nContent-Type: application/json\r\n"
               + f"Content-Length: {len(payload)}\r\nConnection: close\r\n\r\n".encode() + payload)
    seen, listener = collect_sql(env[0])
    try:
        with socket.create_connection(("127.0.0.1", http.base_url.port), timeout=30) as sock:
            sock.sendall(request)
            first = sock.recv(4096)
        assert first.startswith(b"HTTP/1.1 400") or first.startswith(b"HTTP/1.1 404"), repr(first)
        assert not any("raw" + control.decode() + "key" in value for value in seen)
    finally:
        event.remove(env[0].engine, "before_cursor_execute", listener)
    assert http.get(target).json() == before
