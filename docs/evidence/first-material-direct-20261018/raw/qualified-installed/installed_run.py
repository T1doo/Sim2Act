"""Exact new installed wheel, original blank launcher/Worker and real UI HTTP."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import queue
import signal
import sqlite3
import subprocess
import threading
import time
import zipfile

ROOT = Path('/workspace/first-material-direct-20261018/qualified-installed')
REPO = Path('/workspace/Sim2Act')
PY = Path('/workspace/sim2act-venv/bin/python')
VENV = ROOT / 'installed-venv'
SITE = VENV / 'lib/python3.12/site-packages'
CWD = ROOT / 'outside-checkout'
DATA = ROOT / '首版换材料 已授权'
WHEEL = ROOT / 'wheel/sim2act-0.1.0-py3-none-any.whl'
DRIVER = ROOT / 'execution-source/tests/initial_material_revision.cjs'
ENV = {k:v for k,v in os.environ.items() if k not in {
    'INTERN_API_TOKEN','SIM2ACT_INTERN_TOKEN','SIM2ACT_TEST_DATABASE_URL',
    'PYTHONPATH','PYTHONHOME','PIP_INDEX_URL','PIP_EXTRA_INDEX_URL'}}
ENV.update(PIP_CONFIG_FILE='/dev/null', NODE_PATH='/workspace/node-tools/node_modules',
           SIM2ACT_DATABASE_URL='synthetic-invalid-dsn-must-not-be-read', SIM2ACT_LIVE_ENABLED='invalid-synthetic-flag')
REPORT = dict(status='RUNNING', started=datetime.datetime.now(datetime.UTC).isoformat(), commands=[], processes=[], checks=[],
              dependencies='explicit shared existing locked directory; no clean-machine dependency download claim', whole_page_deadline_seconds=900, deadline_basis='three ordinary jobs each retain original run_seconds300; previous overall300 window FAIL retained; no product budget/lease changed')

def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

def save(): dump(ROOT / 'installed-result.json', REPORT)

def check(ok, label):
    assert ok, label
    REPORT['checks'].append(label)
    save()

def command(name, args, *, cwd=CWD, timeout=180):
    row=dict(name=name,command=[str(x) for x in args],cwd=str(cwd),started=datetime.datetime.now(datetime.UTC).isoformat())
    REPORT['commands'].append(row);save();start=time.monotonic()
    with (ROOT/(name+'.stdout')).open('wb')as out,(ROOT/(name+'.stderr')).open('wb')as err:
        result=subprocess.run(args,cwd=cwd,env=ENV,stdout=out,stderr=err,timeout=timeout)
    row.update(exit_code=result.returncode,seconds=time.monotonic()-start);save()
    check(result.returncode==0,name+' exit0');print(name+': PASS',flush=True)

def snapshot(name):
    con=sqlite3.connect((DATA/'synthetic-workspace.db').as_uri()+'?mode=ro',uri=True)
    try:
        con.row_factory=sqlite3.Row
        result={}
        for table, in con.execute("SELECT name FROM sqlite_schema WHERE type='table' ORDER BY name").fetchall():
            assert table.replace('_','').isalnum()
            types={row[1]:row[2] for row in con.execute('PRAGMA table_info("'+table+'")')}
            values=[]
            for row in con.execute('SELECT * FROM "'+table+'"'):
                value=dict(row)
                for key in value:
                    if types[key]=='JSON' and value[key] is not None:value[key]=json.loads(value[key])
                values.append(value)
            result[table]=sorted(values,key=lambda row:json.dumps(row,sort_keys=True))
    finally:con.close()
    dump(ROOT/(name+'.json'),result);return result

class Owned:
    def __init__(self,name,new):
        self.name=name;self.lines=[];self.events=queue.Queue();self.out=(ROOT/(name+'.stdout')).open('w');self.err=(ROOT/(name+'.stderr')).open('w')
        args=[str(VENV/'bin/sim2act'),'synthetic-workspace','--data-dir',str(DATA),'--port','0']+(['--new']if new else[])
        self.row=dict(name=name,command=args,cwd=str(CWD));REPORT['processes'].append(self.row)
        self.p=subprocess.Popen(args,cwd=CWD,env=ENV,stdout=subprocess.PIPE,stderr=self.err,text=True,bufsize=1);self.row['pid']=self.p.pid;save()
        def reader():
            for line in self.p.stdout:
                self.out.write(line);self.out.flush();self.lines.append(line)
                try:self.events.put(json.loads(line))
                except json.JSONDecodeError:pass
        self.thread=threading.Thread(target=reader,daemon=True);self.thread.start()
    def ready(self):
        deadline=time.monotonic()+25
        while time.monotonic()<deadline:
            try:
                value=self.events.get(timeout=.1)
                if value.get('event')=='SYNTHETIC_WORKSPACE_READY':self.row['ready']=value;save();return value
            except queue.Empty:
                if self.p.poll() is not None:break
        raise AssertionError(self.name+' READY not observed; raw logs retained')
    def stop(self):
        if self.p.poll() is None:
            self.p.send_signal(signal.SIGINT)
            try:self.p.wait(timeout=15)
            except subprocess.TimeoutExpired:
                self.row['owned_sigterm_required']=True;self.p.terminate();self.p.wait(timeout=10)
        self.thread.join(timeout=3);self.out.close();self.err.close()
        events=[json.loads(x)for x in self.lines if 'SYNTHETIC_WORKSPACE_STOPPED'in x]
        self.row.update(exit_code=self.p.returncode,stopped=events);save()
        check(self.p.returncode==0 and len(events)==1 and all(events[0][key]for key in ['worker_stopped','clean','data_preserved']),self.name+' Ctrl+C clean and data preserved')

def page(name,base,mode,previous=None):
    args=['node',str(DRIVER),base,str(ROOT/(name+'-proof.json')),mode]+([str(previous)]if previous else[])
    row=dict(name=name,command=args,cwd=str(CWD));REPORT['commands'].append(row);save();start=time.monotonic()
    with (ROOT/(name+'.stdout')).open('w')as out,(ROOT/(name+'.stderr')).open('w')as err:
        p=subprocess.Popen(args,cwd=CWD,env=ENV,stdout=subprocess.PIPE,stderr=err,stdin=subprocess.PIPE,text=True,bufsize=1)
        lines=queue.Queue()
        def reader():
            for line in p.stdout:lines.put(line)
        thread=threading.Thread(target=reader,daemon=True);thread.start()
        try:
            while p.poll()is None or not lines.empty():
                if time.monotonic()-start>900:raise AssertionError(name+' observer deadline exceeded')
                try:line=lines.get(timeout=.1)
                except queue.Empty:continue
                out.write(line);out.flush();message=json.loads(line)
                if 'stage'in message:
                    snapshot(message['stage']);p.stdin.write('snapshot-read-only-complete\n');p.stdin.flush();print('snapshot '+message['stage'],flush=True)
            p.wait(timeout=5)
        finally:
            if p.poll()is None:p.terminate();p.wait(timeout=10)
            thread.join(timeout=2);p.stdin.close()
    row.update(exit_code=p.returncode,seconds=time.monotonic()-start);save();check(p.returncode==0,name+' actual page PASS');return json.loads((ROOT/(name+'-proof.json')).read_text())

owned=None
try:
    save();CWD.mkdir()
    command('wheel-build',[str(PY),'-m','pip','wheel','--no-deps','--no-cache-dir','--retries','0','--timeout','15','--index-url','https://pypi.org/simple','--wheel-dir',str(ROOT/'wheel'),'.'],cwd=REPO)
    command('venv-create',[str(PY),'-m','venv','--without-pip',str(VENV)])
    command('wheel-install',[str(PY),'-m','pip','--python',str(VENV/'bin/python'),'install','--no-index','--no-deps',str(WHEEL)])
    (SITE/'explicit-existing-locked-dependencies.pth').write_text('/workspace/sim2act-venv/lib/python3.12/site-packages\n')
    command('import-path',[str(VENV/'bin/python'),'-c',"import sim2act,sim2act.synthetic_workspace,sys,json;print(json.dumps(dict(package=sim2act.__file__,workspace=sim2act.synthetic_workspace.__file__,sys_path=sys.path)))"])
    paths=json.loads((ROOT/'import-path.stdout').read_text());check(Path(paths['workspace']).is_relative_to(SITE)and'/workspace/Sim2Act/src'not in paths['sys_path'],'all execution outside checkout from fresh installed package')
    with zipfile.ZipFile(WHEEL)as archive:
        hashes={name:hashlib.sha256(archive.read(name)).hexdigest()for name in archive.namelist()if name.startswith('sim2act/')and not name.endswith('/')}
    check(len(hashes)==139 and all(hashlib.sha256((SITE/name).read_bytes()).hexdigest()==digest for name,digest in hashes.items()),'all139 package files match exact final wheel')
    dump(ROOT/'wheel-files.json',hashes);REPORT['wheel']=dict(bytes=WHEEL.stat().st_size,sha256=hashlib.sha256(WHEEL.read_bytes()).hexdigest());save()
    command('fixture-prepare',[str(VENV/'bin/python'),str(ROOT/'execution-source/prepare_installed_fixture.py')])
    fixture=json.loads((ROOT/'fixture.json').read_text());before=snapshot('fixture-before-ui');check(not before['runs'] and len(before['internal_releases'])==len(before['internal_instances'])==1 and before['internal_instances'][0]['revision']==1,'API-prepared ORIGINAL spec1 fixture has no prior Run column revision or adoption')
    check(len(fixture['precondition_app_B_grants'])==2,'two explicit synthetic App/B authority rows are preconditions, never product-grant qualification')
    owned=Owned('new-process',False);first=owned.ready();result=page('new-page',first['url'],'new',ROOT/'fixture.json');owned.stop();owned=None;after=snapshot('first-stop')
    pre=json.loads((ROOT/'before-preview.json').read_text());preview=json.loads((ROOT/'after-preview.json').read_text())
    check(all(pre[t]==preview[t]for t in pre if t not in {'delivery_graph_requests','heartbeats'}),'preview53 tables unchanged except original journal and heartbeat')
    initial=json.loads((ROOT/'before-edit.json').read_text())
    check(all(before[t]==after[t]for t in ['principals','grants','resources','goal_cards','goal_card_versions','app_drafts']),'all identity Grant resource Goal and original draft bytes preserved after measured UI')
    for t in ['internal_releases','internal_app_runs','internal_instance_data','internal_run_bindings','run_contracts','runs','operations','operation_intents']:
        check(all(row in after[t]for row in initial[t]),'original historical rows retained '+t)
    runs={r['id']:r for r in after['runs']};ids=[result['old_run_id'],result['check_run_id'],result['new_run_id']]
    check(set(runs)==set(ids)and all(runs[x]['status']=='SUCCEEDED'and runs[x]['worker_id']==first['worker_id']and runs[x]['fence']==1 for x in ids),'exact three ordinary Worker jobs oldA CHECKB newB all SUCCEEDED fence1')
    check(len([r for r in after['events']if r['kind']=='CLAIMED'])==3 and not after['attempts'] and not after['reservations'],'three claims zero model Attempts or reservations')
    for rid,expected,version,resource,sourcehash in [(result['old_run_id'],'30',1,fixture['resource_id'],fixture['A_hash']),(result['new_run_id'],'350',2,fixture['B_id'],fixture['B_hash'])]:
        binding=next(r for r in after['internal_run_bindings']if r['run_id']==rid);typed=next(r for r in after['internal_instance_data']if r['run_id']==binding['app_run_id']);output=typed['data']['result']
        check(typed['version']==version and output['sum']==expected and output['resource_id']==resource and output['source_hash']==sourcehash,'immutable core AppRun typed binding exact material '+rid)
    check(result['preview']['context']['parent']['spec_revision']==1 and result['preview']['spec_revision']==2 and result['preview']['context']['goal']['version']==1,'direct original1 to material2 retains Goal1, no fake prior revision')
    owned=Owned('cold-process',False);second=owned.ready();check(second['worker_id']!=first['worker_id']and second['principal_id']==first['principal_id'],'cold Worker new identity same principal')
    page('cold-page',second['url'],'cold',ROOT/'new-page-proof.json');owned.stop();owned=None;cold=snapshot('cold-stop')
    check([t for t in after if after[t]!=cold[t]]==['heartbeats'],'cold all54 nonheartbeat tables exactly unchanged')
    REPORT.update(status='PASS',scope='API-prepared first Release with two explicit pre-existing synthetic App/B Grants; actual installed direct material UI and Worker plus cold page, not blank-UI authority provision',finished=datetime.datetime.now(datetime.UTC).isoformat(),core_run_ids=ids,first_worker=first['worker_id'],cold_worker=second['worker_id'],real_models=0,native_browser='NOT_RUN',Win='NOT_RUN',PG='NOT_RUN',remote_CI='NOT_RUN');save();print('FIRST DIRECT MATERIAL INSTALLED PATH PASS',flush=True)
except BaseException as error:
    REPORT.update(status='FAIL',error=dict(type=type(error).__name__,message=str(error)),finished=datetime.datetime.now(datetime.UTC).isoformat());save();print('FAIL '+repr(error),flush=True);raise
finally:
    if owned is not None:owned.stop()
