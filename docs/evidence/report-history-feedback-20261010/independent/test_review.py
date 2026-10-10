import contextvars,hashlib,json,os,socket,subprocess,threading,time
from pathlib import Path
import pytest,uvicorn
from sqlalchemy import event,select
from fastapi.responses import Response
from conftest import env as original_env
from test_conditional_run_bindings import env as bounded_env
from test_report_presentations import prepared
from sim2act.db import app_drafts
from sim2act.api import create_app

ROOT=Path('/tmp/sim2act-report-history-feedback-independent-20261010')
WEB=Path('/workspace/Sim2Act/src/sim2act/web')

@pytest.fixture
def env(tmp_path):
    owner=original_env.__wrapped__(tmp_path)
    try: yield bounded_env.__wrapped__(next(owner))
    finally: owner.close()

CASES=[(phase,branch,'current','final') for phase in ('definition','checks') for branch in ('canonical','envelope','item')]
CASES += [('definition','canonical',nav,'final') for nav in ('app','identity')]
CASES += [('definition',branch,'current','old112') for branch in ('canonical','envelope','item')]

@pytest.mark.parametrize('phase,branch,navigation,source',CASES)
def test_independent_lost_accepted_history_feedback_and_exact_context(env,tmp_path,phase,branch,navigation,source):
    app,_,_,_,output,wires=prepared(env,tmp_path,peer=True)
    with env[0].tx() as c:
        rows=c.execute(select(app_drafts).where(app_drafts.c.project_id==env[5])).mappings().all()
        peer=next(r['id'] for r in rows if r['candidate'].get('manifest',{}).get('workflow',[{}])[0].get('step_id')=='aggregate')
    other=env[0].project(env[4],'independent identity workspace')
    service=create_app(env[0],env[1])
    if source=='old112':
        old=(ROOT/'old-112-report-manifest.js').read_bytes()
        route=next(r for r in service.routes if getattr(r,'path',None)=='/report-manifest.js')
        route.dependant.call=lambda:Response(old,media_type='application/javascript')
    request_scope=contextvars.ContextVar('independent-request-scope',default=None)
    mutations=[]
    @service.middleware('http')
    async def record_context(request,call_next):
        mark=request_scope.set((request.method,request.url.path))
        try: return await call_next(request)
        finally: request_scope.reset(mark)
    def after_execute(conn,cursor,statement,params,context,many):
        if statement.lstrip().split(' ',1)[0].upper() in ('INSERT','UPDATE','DELETE'):
            mutations.append(dict(request=request_scope.get(),statement=statement))
    event.listen(env[0].engine,'after_cursor_execute',after_execute)
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    name=f'{source}-{phase}-{branch}-{navigation}'
    info=tmp_path/'info.json';info.write_text(json.dumps(dict(url=f'http://127.0.0.1:{port}',app=app['id'],peer=peer,project=env[5],other=other,phase=phase,branch=branch,navigation=navigation,evidence=str(ROOT/(name+'.json')),explanation=output['explanation'])))
    server=uvicorn.Server(uvicorn.Config(service,host='127.0.0.1',port=port,log_level='error'))
    thread=threading.Thread(target=server.run,daemon=True);thread.start()
    try:
        deadline=time.monotonic()+10
        while not server.started:
            assert thread.is_alive() and time.monotonic()<deadline
            time.sleep(.01)
        run=subprocess.run(['node',str(ROOT/'review-ui.cjs'),str(info)],capture_output=True,text=True,timeout=90)
        (ROOT/(name+'.log')).write_text(run.stdout+run.stderr)
        result=json.loads((ROOT/(name+'.json')).read_text())
        (ROOT/(name+'-mutations.json')).write_text(json.dumps(mutations,indent=2))
        assert all(m['request'] and m['request'][0]!='GET' for m in mutations)
        assert len(wires)==4 # synthetic original offline exchanges only
        for file,digest in result['hashes'].items():
            data=(ROOT/'old-112-report-manifest.js').read_bytes() if source=='old112' and file=='report-manifest.js' else (WEB/file).read_bytes()
            assert hashlib.sha256(data).hexdigest()==digest
        if source=='old112':
            assert run.returncode!=0 and result['status']=='FAIL'
            assert 'precise current self-cleared feedback' in result['error']
            assert any('original UNKNOWN intent' in x for x in result['checks'])
        else:
            assert run.returncode==0,run.stdout+run.stderr
            assert result['status']=='PASS'
    finally:
        server.should_exit=True;thread.join(10);assert not thread.is_alive()
        event.remove(env[0].engine,'after_cursor_execute',after_execute)
