"""Real HTTP path decoding and compatibility of immutable column-patch keys."""

import socket
import threading
import time
from urllib.parse import quote

import httpx
import pytest
import uvicorn
from test_column_patches import check_body, setup, url

from sim2act.api import create_app


@pytest.fixture
def http(env):
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(create_app(env[0], env[1]), host="127.0.0.1", port=port, log_level="error"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        end = time.monotonic() + 10
        while not server.started:
            assert thread.is_alive() and time.monotonic() < end
            time.sleep(.01)
        with httpx.Client(base_url=f"http://127.0.0.1:{port}", headers={"Authorization": "Bearer synthetic-test-A"}) as client:
            yield client
    finally:
        server.should_exit = True
        thread.join(10)
        assert not thread.is_alive()


@pytest.mark.parametrize("key", ["independent/key", "encoded%2Fkey", "独立/键 空格", "safe-uuid_123", "/leading/trailing/"])
def test_real_http_key_confirmation_replay_and_cold_history(env, http, key):
    aid, _, _, body, _ = setup(env)
    target = url(env, aid)
    body["request_key"] = key
    response = http.post(target, json=body)
    assert response.status_code == 201, response.text
    patch = response.json()
    path = target + "/" + quote(key, safe="") + "/checks"
    confirmation = check_body(patch, "independent-check")
    result = http.post(path, json=confirmation)
    assert result.status_code == 201, result.text
    assert result.json()["outputs"]["baseline"]["sum"] == "30"
    assert result.json()["outputs"]["patched"]["sum"] == "15"
    # Original accepted request/receipt remains byte-for-byte recoverable.
    definition_replay = http.post(target, json=body)
    assert definition_replay.status_code == 201 and definition_replay.json()["cached"]
    assert {k: v for k, v in definition_replay.json().items() if k != "cached"} == {k: v for k, v in patch.items() if k != "cached"}
    replay = http.post(path, json=confirmation)
    assert replay.status_code == 201 and replay.json()["cached"]
    assert {k: v for k, v in replay.json().items() if k != "cached"} == {k: v for k, v in result.json().items() if k != "cached"}
    if key == "independent/key":
        assert http.post(target + "/independent/key/checks", json=confirmation).status_code == 201
        assert http.post(target + "/independent%252Fkey/checks", json=confirmation).status_code == 409
    history = http.get(target)
    assert history.status_code == 200
    item = next(i for i in history.json()["items"] if i["patch"]["request_key"] == key)
    assert item["patch"] == {k: v for k, v in patch.items() if k != "cached"}
    assert item["checks"] == [{k: v for k, v in result.json().items() if k != "cached"}]
    # Different parameters under the original key cannot replace history.
    rejected = http.post(path, json={**confirmation, "expected_patch_fingerprint": "0" * 64})
    assert rejected.status_code == 409
    assert http.get(target).json() == history.json()


@pytest.mark.parametrize("key", ["line\nbreak", "nul\0key", "del\x7fkey", ".", "..", "a/../b", "a/./b"])
def test_unaddressable_new_keys_rejected_before_acceptance(env, http, key):
    aid, _, _, body, _ = setup(env)
    target = url(env, aid)
    before = http.get(target).json()
    response = http.post(target, json={**body, "request_key": key})
    assert response.status_code == 400, response.text
    assert response.json()["error"]["code"] == "INVALID_INPUT"
    assert http.get(target).json() == before
