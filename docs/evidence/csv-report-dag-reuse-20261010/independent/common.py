import json,hashlib,pathlib,subprocess,copy,csv,io
from decimal import Decimal
from fastapi.testclient import TestClient
from sim2act.api import create_app
from sim2act.config import Settings
from sim2act.db import *
from sim2act.contracts import Limits
from sim2act.worker import Worker
from sqlalchemy import select,update,delete,event
from sim2act import csv_dag as dag,csv_dag_instances as instances,lifecycle
ROOT=pathlib.Path('/tmp/sim2act-report-dag-reuse-independent-20261010');REPO=pathlib.Path('/workspace/Sim2Act');SHA='5588a94faeb90abb2052a8ae5327810b8d27c287'
RAW='item,amount,quantity,other\r\n"南,区",-0.5,7,0.125\r\n北区,2.25,-3,1.375\r\n'
class ForbiddenModel:
 def complete(self,*a,**kw):raise AssertionError('Independent mock forbids model')
 request=complete

def freeze(name):
 previous=json.loads(pathlib.Path('/tmp/sim2act-native-remaining11-20261010/source-freeze.json').read_text())['files']
 extra=subprocess.check_output(['git','diff','--name-only','--diff-filter=A','f13ff8d7661490a7e42a1f7ce3e9179bda54da4b..'+SHA],cwd=REPO,text=True).splitlines()
 paths=sorted(set(previous)|{p for p in extra if p.startswith(('src/','scripts/','tests/','.github/'))})
 a={p:hashlib.sha256((REPO/p).read_bytes()).hexdigest() for p in paths};g={p:hashlib.sha256(subprocess.check_output(['git','show',SHA+':'+p],cwd=REPO)).hexdigest() for p in paths}
 h=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip();src=[p for p in paths if p.startswith('src/')];changed=[p for p in src if hashlib.sha256(subprocess.check_output(['git','show','f13ff8d7661490a7e42a1f7ce3e9179bda54da4b:'+p],cwd=REPO)).hexdigest()!=a[p]]
 out={'sha':h,'count':len(paths),'Git_worktree_match':a==g,'products':len(src),'changed_products_vs_f13':changed,'files':a};(ROOT/('source-'+name+'.json')).write_text(json.dumps(out,indent=2));assert h==SHA and a==g and len(paths)==365 and len(src)==69 and len(changed)==3;return out

def snapshot(e):
 with e[0].engine.connect() as c:return {t.name:sorted([dict(x) for x in c.execute(select(t)).mappings()],key=fingerprint) for t in meta.sorted_tables}
def env(folder):
 folder.mkdir(exist_ok=True);url='sqlite:///'+str(folder/'db.sqlite');st=Store(url,test_only=True);st.initialize();a=st.user('Review A','review-A');b=st.user('Review B','review-B');s=Settings(url,folder,mode='mock');cl=TestClient(create_app(st,s));cl.headers['Authorization']='Bearer review-A';pid=cl.post('/api/projects',json={'name':'Independent frozen DAG'}).json()['id'];return [st,s,cl,a,b,pid,None]
def request(e,method,path,body=None,status=200):
 r=e[2].request(method,path,json=body) if body is not None else e[2].request(method,path);assert r.status_code==status,(method,path,r.status_code,r.text);return r.json()
def fixture(e,with_report=True):
 pid=e[5];rid=request(e,'POST',f'/api/projects/{pid}/resources',{'name':'Independent.csv','format':'csv','content':RAW},201)['id'];e[6]=rid
 a=request(e,'POST',f'/api/projects/{pid}/apps/csv-preview',{'name':'Independent actual read sum','goal':'New numeric inputs on fixed graph','resource_id':rid},201);aid=a['id'];a=request(e,'GET','/api/apps/'+aid)
 graph=request(e,'POST',f'/api/projects/{pid}/apps/{aid}/delivery-graph/derive',{'expected_candidate_fingerprint':a['fingerprint'],'request_key':'independent-derive'},201)
 nodes=[dict(step_id='read',action='resource.read',depends_on=[],inputs={'resource_id':dict(source='data',ref='source',field='resource_id')}),dict(step_id='total',action='data.aggregate_csv',column='amount',depends_on=['read'],inputs={'resource_id':dict(source='step',ref='read',field='resource_id'),'column':dict(source='input',field='total_column')})]
 if with_report:nodes.append(dict(step_id='writeup',action='intern.csv_report.v1',depends_on=['total'],inputs={k:dict(source='step',ref='total',field=k) for k in ['resource_id','column','count','sum','source_hash']}))
 base=f'/api/projects/{pid}/apps/{aid}/csv-dag';plan=request(e,'POST',base,{'expected_candidate_fingerprint':a['fingerprint'],'expected_graph_fingerprint':graph['graph_fingerprint'],'column':'amount','request_key':'independent-source-plan','composition':{'version':'csv.composition.v1','nodes':nodes}},201)
 accepted=request(e,'POST',base+'/independent-source-plan/runs',{'expected_plan_fingerprint':plan['plan_fingerprint'],'request_key':'independent-source-run','consent':'CONFIRM_EXACT_OFFLINE_CSV_DAG'},202);work(e,accepted['run_id']);plan.pop('cached',None);return aid,rid,plan,accepted['run_id']
def work(e,rid):
 w=Worker(e[0],e[1],ForbiddenModel());job=e[0].claim(w.id,e[1].lease_seconds);assert job['id']==rid;(w.process(job));return job

def make_release(e,f=None):
 aid,rid,p,source=f or fixture(e);a=request(e,'POST',f'/api/csv-dag/runs/{source}/release-approvals',{'expected_plan_fingerprint':p['plan_fingerprint'],'request_key':'independent-approval'},201);full=request(e,'GET','/api/internal/approvals/'+a['id']);assert full['fingerprint']==fingerprint(full['payload']);rel=request(e,'POST','/api/internal/approvals/'+a['id']+'/commit',{'fingerprint':a['fingerprint']});return aid,rid,p,source,rel
def make_instance(e,rel,key='independent-instance'):return request(e,'POST','/api/internal/releases/'+rel['id']+'/instances',{'expected_release_fingerprint':rel['fingerprint'],'request_key':key},201)
def enqueue(e,i,rel,col='quantity',key='independent-fresh'):
 body={'expected_revision':i['revision'],'expected_release_fingerprint':rel['fingerprint'],'input':{'column':col},'request_key':key};return request(e,'POST','/api/internal/instances/'+i['id']+'/runs',body,202),body
