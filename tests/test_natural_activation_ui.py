"""Ordinary page to an exact approved OFFLINE_TEST session; never a LIVE fixture."""
import json
import socket
import subprocess
import threading
import time

import httpx
import pytest
import uvicorn
from sqlalchemy import select
from test_natural_activation_flow import approved, setup, wire
from test_natural_goal_planning import authority, response, rows

from sim2act import natural_activations as activation
from sim2act.api import create_app
from sim2act.db import attempts, events, meta, natural_activations, operations, runs
from sim2act.worker import Worker


def test_project_activation_list_is_scoped_readonly_and_honest(env):
    value = setup(env)
    store, settings, client, owner, other, project, *_ = value
    session, _ = approved(value)
    def snapshot():
        with store.tx() as c:
            return {table.name: [dict(r) for r in c.execute(select(table)).mappings()]
                    for table in meta.sorted_tables}
    before = snapshot()
    body = client.get(f"/api/projects/{project}/natural-activations").json()
    assert body["general_live_request_allowance"] == 0
    assert len(body["items"]) == 1
    item = body["items"][0]
    assert item["id"] == session["id"] and item["scope"]["mode"] == "OFFLINE_TEST"
    assert item["submission_available"] and item["charged_kinds"] == []
    assert snapshot() == before
    other_project = store.project(owner, "different owned project")
    assert client.get(f"/api/projects/{other_project}/natural-activations").json()["items"] == []
    client.headers["Authorization"] = "Bearer synthetic-test-B"
    assert client.get(f"/api/projects/{project}/natural-activations").status_code == 403
    assert client.get(f"/api/natural-activations/{session['id']}").status_code == 403


@pytest.mark.parametrize("case", ["valid", "expired", "revoked"])
def test_activation_actual_http_complete_page_path(env, tmp_path, monkeypatch, case):
    value = setup(env)
    store, settings, client, owner, _, project, resource, cards = value
    session, _ = approved(value)
    other_project = store.project(owner, "Other activation page project")
    before = authority(store)
    sent = []
    def handler(request):
        payload = json.loads(request.content)
        content = json.loads(payload["messages"][1]["content"])
        fp = content["saved_goal"]["fingerprint"]
        kind = next(k for k,c in cards.items() if c["fingerprint"] == fp)
        sent.append(kind)
        return httpx.Response(200, json=response(wire(value, kind)))
    app = create_app(store, settings)
    clock = [time.time()]
    @app.post("/test-only-activation-worker")
    def work():
        assert store.test_only and settings.mode == "mock"
        assert Worker(store, settings, goal_planner_transport=httpx.MockTransport(handler)).once()
        return {"offline_test": True}
    @app.post("/test-only-activation-control/{action}")
    def control(action: str):
        assert store.test_only and settings.mode == "mock"
        if action == "next-minute":
            clock[0] = time.time()+60
            monkeypatch.setattr(activation, "now", lambda: clock[0])
        elif action == "expire-run":
            clock[0] = time.time()+121
            monkeypatch.setattr(activation, "now", lambda: clock[0])
        elif action == "revoke":
            body={"expected_version":session["version"],"expected_scope_fingerprint":session["scope_fingerprint"],"request_key":"owned-test-revoke"}
            activation.revoke(store, owner, session["id"], body, settings)
        else:
            raise AssertionError("Closed test action")
        return {"offline_test": True}
    with socket.socket() as sock:
        sock.bind(("127.0.0.1",0))
        port=sock.getsockname()[1]
    info={"base":f"http://127.0.0.1:{port}","project":project,"other":other_project,
          "session":session["id"],"case":case,"cards":{k:c["id"] for k,c in cards.items()}}
    (tmp_path/'info.json').write_text(json.dumps(info))
    server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=port,log_level='error'))
    thread=threading.Thread(target=server.run,daemon=True)
    thread.start()
    try:
        end=time.monotonic()+10
        while not server.started:
            assert thread.is_alive() and time.monotonic()<end
            time.sleep(.01)
        p=subprocess.run(['node','tests/natural_activation_ui.cjs',str(tmp_path)],
                         capture_output=True,text=True,timeout=60)
        (tmp_path/'driver.log').write_text(p.stdout+p.stderr)
        assert p.returncode == 0,p.stdout+p.stderr
        result=json.loads((tmp_path/'results.json').read_text())
        assert result['status']=='PASS' and result['browser']=='JSDOM_NOT_NATIVE'
        assert authority(store)==before
        assert not any(a['mode']=='LIVE' for a in rows(store, attempts))
        if case=='valid':
            assert sent==['read_preview','sum_quantity_z']
            assert len(rows(store,attempts))==len(rows(store,operations))==2
            assert len(rows(store,runs))==2
            assert rows(store,natural_activations)[0]['status']=='APPROVED'
        else:
            assert len(sent)==len(rows(store,attempts))==1 and not rows(store,operations)
            assert not [e for e in rows(store,events) if e['kind']=='NL_PLAN_CONFIRMED']
    finally:
        server.should_exit=True
        thread.join(8)
        assert not thread.is_alive()
