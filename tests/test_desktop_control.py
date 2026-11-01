"""Desktop-owned EOF/STOP reaches the existing real service shutdown receipt."""

import io
import json
import os
import queue
import subprocess
import sys
import threading
import time
import httpx
from pathlib import Path
import sim2act

from sim2act.synthetic_workspace import DATABASE, _read_owned_control


def test_reopen_ready_precedes_first_dispatch_and_pending_csv_finishes(tmp_path):
    """Actual queued data, real server and Worker; monitor never replaces it."""
    from fastapi.testclient import TestClient
    from sim2act import synthetic_workspace as workspace
    root, store, _ = workspace.open_workspace(tmp_path / "pending", new=True)
    client = TestClient(workspace.workspace_app(store, workspace.settings_for(root)))
    client.headers["Authorization"] = "Bearer " + workspace.TOKEN
    def request(path, body, status=201):
        response=client.post(path,json=body);assert response.status_code==status,response.text
        return response.json()
    project=request('/api/projects',dict(name='queued desktop reopen'))['id']
    resource=request(f'/api/projects/{project}/resources',dict(name='queued.csv',format='csv',content='item,amount\nA,10\nB,20\n'))
    app=request(f'/api/projects/{project}/apps/csv-preview',dict(name='queued sum',resource_id=resource['id'],goal='Sum amount'))
    app=client.get('/api/apps/'+app['id']).json()
    approval=request(f"/api/internal/apps/{app['id']}/release-approvals",dict(expected_draft_fingerprint=app['fingerprint'],sample_input=dict(column='amount')))
    release=request(f"/api/internal/approvals/{approval['id']}/commit",dict(fingerprint=approval['fingerprint']),200)
    instance=request(f"/api/internal/releases/{release['id']}/instances",dict(expected_release_fingerprint=release['fingerprint'],request_key='ready-instance'))
    accepted=request(f"/api/internal/instances/{instance['id']}/runs",dict(expected_release_fingerprint=release['fingerprint'],expected_revision=instance['revision'],input=dict(column='amount'),request_key='queued-before-desktop'),202)
    client.close();store.engine.dispose()
    script='''
import sys,json
from sim2act.worker import Worker
from sim2act.cli import main
slot=next(i for i in (3,4,5) if sys.monitoring.get_tool(i) is None)
sys.monitoring.use_tool_id(slot,'desktop-dispatch-order')
def first(code,offset):
 print(json.dumps({'diagnostic':'REAL_WORKER_ONCE_ENTERED'}),flush=True)
 sys.monitoring.set_local_events(slot,Worker.once.__code__,0)
sys.monitoring.register_callback(slot,sys.monitoring.events.PY_START,first)
sys.monitoring.set_local_events(slot,Worker.once.__code__,sys.monitoring.events.PY_START)
main()
'''
    source=Path(sim2act.__file__).resolve().parent.parent
    child=subprocess.Popen([sys.executable,'-u','-c',script,'synthetic-workspace','--data-dir',str(root),'--control-stdin'],
        stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,
        env={**os.environ,'PYTHONPATH':str(source)})
    lines=[];messages=queue.Queue()
    def drain():
        for line in child.stdout:lines.append(line);messages.put(line)
        messages.put(None)
    reader=threading.Thread(target=drain,daemon=True);reader.start()
    try:
        ready=None;end=time.monotonic()+20
        while time.monotonic()<end:
            line=messages.get(timeout=max(.01,end-time.monotonic()));assert line is not None,''.join(lines)
            try:event=json.loads(line)
            except ValueError:continue
            if event.get('diagnostic')=='REAL_WORKER_ONCE_ENTERED':
                assert ready is not None,'First dispatch blocked desktop READY'
                break
            if event.get('event')=='SYNTHETIC_WORKSPACE_READY':ready=event
        assert ready is not None
        with httpx.Client(base_url=ready['url'],headers={'Authorization':'Bearer '+workspace.TOKEN},trust_env=False,timeout=5) as http:
            assert http.get('/health').status_code==200
            route=f"/api/internal/instances/{instance['id']}/runs/{accepted['run_id']}"
            end=time.monotonic()+15
            while time.monotonic()<end:
                reply=http.get(route);assert reply.status_code==200,reply.text
                result=reply.json()
                if result['status'] not in {'QUEUED','RUNNING'}:break
                time.sleep(.05)
            assert result['status']=='SUCCEEDED' and result['result']['sum']=='30'
    finally:
        child.stdin.close();assert child.wait(timeout=20)==0,''.join(lines)
        reader.join(5);child.stdout.close();assert not reader.is_alive()
    receipt=next(json.loads(line) for line in lines if 'SYNTHETIC_WORKSPACE_STOPPED' in line)
    assert receipt['clean'] and receipt['data_preserved']


def test_bound_stop_and_eof_only_request_original_shutdown():
    requested = []
    worker = "worker_" + "a" * 32
    _read_owned_control(
        io.StringIO(json.dumps(dict(command="stop", worker_id=worker)) + "\n"),
        worker,
        lambda: requested.append("stop"),
    )
    assert requested == ["stop"]
    requested.clear()
    _read_owned_control(io.StringIO(""), worker, lambda: requested.append("eof"))
    assert requested == ["eof"]


def test_wrong_worker_does_not_stop_until_pipe_eof():
    requested = []

    class Stream:
        def __init__(self):
            self.first = True

        def readline(self, limit):
            assert limit == 512 and requested == []
            if self.first:
                self.first = False
                return json.dumps(dict(command="stop", worker_id="worker_" + "b" * 32)) + "\n"
            return ""

    _read_owned_control(Stream(), "worker_" + "a" * 32, lambda: requested.append("eof"))
    assert requested == ["eof"]


def test_real_consoleless_child_eof_preserves_existing_shutdown_receipt(tmp_path):
    source = Path(sim2act.__file__).resolve().parent.parent
    child = subprocess.Popen(
        [
            sys.executable,
            "-B",
            "-m",
            "sim2act.cli",
            "synthetic-workspace",
            "--data-dir",
            str(tmp_path / "workspace"),
            "--new",
            "--control-stdin",
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env={**os.environ, "PYTHONPATH": str(source)},
        **({"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}),
    )
    lines, pending = [], queue.Queue()

    def drain():
        for line in child.stdout:
            lines.append(line)
            pending.put(line)
        pending.put(None)

    reader = threading.Thread(target=drain, daemon=True)
    reader.start()
    try:
        end = time.monotonic() + 20
        worker = None
        while time.monotonic() < end:
            line = pending.get(timeout=max(0.01, end - time.monotonic()))
            assert line is not None, "".join(lines)
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if event.get("event") == "SYNTHETIC_WORKSPACE_READY":
                assert event["control_stdin"] is True
                worker = event["worker_id"]
                break
        assert worker is not None, "".join(lines)
        child.stdin.close()
        assert child.wait(timeout=20) == 0
        reader.join(timeout=5)
        assert not reader.is_alive()
        receipts = [json.loads(line) for line in lines if line.startswith("{")]
        stopped = next(r for r in receipts if r.get("event") == "SYNTHETIC_WORKSPACE_STOPPED")
        assert stopped["worker_id"] == worker
        assert stopped["worker_stopped"] and stopped["clean"] and stopped["data_preserved"]
        assert (tmp_path / "workspace" / DATABASE).is_file()
    finally:
        if child.poll() is None:
            child.stdin.close()
            child.wait(timeout=20)
        child.stdout.close()
