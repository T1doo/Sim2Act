"""Disposable fixture is local/mock only, with ordinary activation and tool gates."""
import importlib.util
from pathlib import Path

from fastapi.testclient import TestClient

SPEC = importlib.util.spec_from_file_location('natural_demo', Path(__file__).parents[1]/'scripts/natural_activation_demo.py')
DEMO = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DEMO)


def test_owned_offline_demo_uses_normal_confirmation_and_removes_only_own_data():
    with DEMO.demo() as fixture:
        root = fixture['root']
        settings = fixture['settings']
        assert fixture['store'].test_only and settings.mode == 'mock'
        assert not settings.live_enabled and not settings.token and not settings.natural_activation_live_id
        client = TestClient(fixture['app'])
        with client:
            client.headers['Authorization'] = 'Bearer '+DEMO.PUBLIC_FIXTURE_TOKEN
            assert client.get('/').status_code == 200
            session=client.get(f"/api/projects/{fixture['project']}/natural-activations").json()['items'][0]
            assert session['scope']['mode']=='OFFLINE_TEST' and session['submission_available']
            card=fixture['cards']['sum_quantity_z']
            r=client.post(f"/api/natural-activations/{session['id']}/goal-cards/{card['id']}/planned-runs",json={
                'expected_version':card['version'],'expected_fingerprint':card['fingerprint'],'request_key':'demo-one'})
            assert r.status_code==202
            rid=r.json()['run_id']
            assert fixture['worker'].once()
            view=client.get('/api/runs/'+rid).json()
            assert view['status']=='WAITING_APPROVAL' and not view['known_effects']
            assert client.post('/api/runs/'+rid+'/confirm-natural-plan',json={
                'expected_version':view['version'],'expected_plan_fingerprint':view['natural_plan']['fingerprint'],
                'request_key':'demo-exact-confirm'}).status_code==200
            assert fixture['worker'].once()
            final=client.get('/api/runs/'+rid).json()
            assert final['status']=='PARTIAL' and final['result']['goal_acceptance']=='NOT_RUN'
            assert final['result']['receipts'][0]['data']['sum']=='19'
            assert fixture['calls']==['sum_quantity_z']
    assert not root.exists()


def test_demo_cli_serves_loopback_and_cleans_own_fixture_on_interrupt(tmp_path):
    import signal
    import socket
    import subprocess
    import sys
    import time

    import httpx

    repo=Path(__file__).parents[1]
    owned=tmp_path/'owned-cli-temp'
    owned.mkdir()
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0))
        port=sock.getsockname()[1]
    output=tmp_path/'cli.log'
    with output.open('w') as log:
        process=subprocess.Popen([sys.executable,str(repo/'scripts/natural_activation_demo.py'),
                                  '--port',str(port)],cwd=repo,stdout=log,stderr=log,
            env={'PYTHONPATH':str(repo/'src'),'PATH':'/usr/bin:/bin','TMPDIR':str(owned)})
        try:
            with httpx.Client(base_url=f'http://127.0.0.1:{port}',trust_env=False,timeout=1) as client:
                deadline=time.monotonic()+15
                while True:
                    assert process.poll() is None, output.read_text()
                    try:
                        page=client.get('/')
                        if page.status_code==200:
                            break
                    except httpx.TransportError:
                        pass
                    assert time.monotonic()<deadline, output.read_text()
                    time.sleep(.05)
                assert 'natural-activation-select' in page.text
                client.headers['Authorization']='Bearer '+DEMO.PUBLIC_FIXTURE_TOKEN
                projects=client.get('/api/projects').json()
                assert len(projects)==1
                sessions=client.get('/api/projects/'+projects[0]['id']+'/natural-activations').json()['items']
                assert len(sessions)==1 and sessions[0]['scope']['mode']=='OFFLINE_TEST'
                assert sessions[0]['charged_requests']==0
                assert len(list(owned.glob('sim2act-natural-offline-*')))==1
        finally:
            if process.poll() is None:
                process.send_signal(signal.SIGINT)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()  # Only this owned test process, then fail cleanup oracle.
                process.wait(timeout=5)
                raise AssertionError('Owned demo did not shut down within 10 seconds') from None
    assert process.returncode==0, output.read_text()
    assert not list(owned.iterdir()), output.read_text()
    assert 'No real model or LIVE authority.' in output.read_text()
