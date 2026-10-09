import json,os,socket,subprocess,threading,time
from pathlib import Path
import pytest,uvicorn
from test_independent import env,arrange,ROOT
from test_delivery_graph_apps import snapshot
from sim2act.api import create_app

@pytest.mark.parametrize('scenario',['readback422','lost-and-late'])
def test_private_actual_http_original_page_and_receipt_recovery(env,tmp_path,scenario):
    app,_,_,_,_,wires=arrange(env,tmp_path)
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    info=tmp_path/'server.json'
    label=os.environ.get('REVIEW_LABEL','eafea')
    evidence=ROOT/f'ui-{label}-{scenario}.json'
    info.write_text(json.dumps(dict(url=f'http://127.0.0.1:{port}',project=env[5],app=app['id'],scenario=scenario,evidence=str(evidence))))
    before=snapshot(env)
    server=uvicorn.Server(uvicorn.Config(create_app(env[0],env[1]),host='127.0.0.1',port=port,log_level='error'))
    thread=threading.Thread(target=server.run,daemon=True);thread.start()
    try:
        deadline=time.monotonic()+15
        while not server.started:
            assert thread.is_alive() and time.monotonic()<deadline
            time.sleep(.01)
        run=subprocess.run(['node',str(ROOT/'independent-ui.cjs'),str(info)],capture_output=True,text=True,timeout=120)
        (ROOT/f'ui-{label}-{scenario}.log').write_text(run.stdout+run.stderr)
        assert run.returncode==0,run.stdout+run.stderr
        proof=json.loads(evidence.read_text());assert proof['status']=='PASS'
        import hashlib
        for name,digest in proof['hashes'].items():
            assert hashlib.sha256((Path('/workspace/Sim2Act/src/sim2act/web')/name).read_bytes()).hexdigest()==digest
        after=snapshot(env)
        assert all(before[t]==after[t] for t in before if t!='delivery_graph_requests')
        assert len(wires)==4
    finally:
        server.should_exit=True;thread.join(15);assert not thread.is_alive()
