import os,json,pathlib,hashlib,subprocess,copy,shutil,time,traceback
from sqlalchemy import select,update,delete,insert,event
from fastapi.testclient import TestClient
from sim2act.api import create_app
from sim2act.config import Settings
from sim2act.contracts import Limits
from sim2act.db import *
from sim2act import report_presentations as presentation,delivery_graph_apps as graph
ROOT=pathlib.Path('/tmp/sim2act-read-stability-independent-20261010');REPO=pathlib.Path('/workspace/Sim2Act');SHA='47388f573746daa27f8d5790ca358eef91378ad5'
def freeze(label):
 m=json.loads(pathlib.Path('/tmp/sim2act-read-stability-20261010/source-freeze.json').read_text())['files'];a={p:hashlib.sha256((REPO/p).read_bytes()).hexdigest() for p in m};g={p:hashlib.sha256(subprocess.check_output(['git','show',SHA+':'+p],cwd=REPO)).hexdigest() for p in m};head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip();out={'sha':head,'count':len(m),'worktree_match':a==m,'git_match':g==m,'files':a};(ROOT/('source-'+label+'.json')).write_text(json.dumps(out,indent=2));assert head==SHA and a==g==m;return out
def state(store):
 with store.engine.connect() as c:return {t.name:sorted([dict(x) for x in c.execute(select(t)).mappings()],key=fingerprint) for t in meta.sorted_tables}
def clone(name):
 folder=ROOT/name;folder.mkdir(exist_ok=True);shutil.copy2(ROOT/'seed'/'fixture.db',folder/'fixture.db');url='sqlite:///'+str(folder/'fixture.db');st=Store(url,test_only=True);s=Settings(url,ROOT/'seed',mode='mock');cl=TestClient(create_app(st,s));cl.headers['Authorization']='Bearer synthetic-test-A';cfg=json.loads((ROOT/'seed.json').read_text());return folder,st,s,cl,cfg

def mutate_pair(c,cfg,kind,key,fn):
 rows=c.execute(select(delivery_graph_requests).where(delivery_graph_requests.c.app_id==cfg['app']['id'],delivery_graph_requests.c.principal_id==cfg['owner'],delivery_graph_requests.c.kind.in_([kind,kind+'_seal']),delivery_graph_requests.c.request_key==key)).mappings().all();assert len(rows)==2
 for row in rows:
  value=copy.deepcopy(row['snapshot']);fn(value);answer=value['response'];selfhash='check_fingerprint' if kind==presentation.CHECK else 'patch_fingerprint';answer[selfhash]=fingerprint({k:v for k,v in answer.items() if k!=selfhash});c.execute(update(delivery_graph_requests).where(delivery_graph_requests.c.app_id==row['app_id'],delivery_graph_requests.c.principal_id==row['principal_id'],delivery_graph_requests.c.kind==row['kind'],delivery_graph_requests.c.request_key==row['request_key']).values(snapshot=value,fingerprint=fingerprint(value),request_fingerprint=fingerprint(value['request'])))
