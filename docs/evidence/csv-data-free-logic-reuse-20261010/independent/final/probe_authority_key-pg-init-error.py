import sys,json,pathlib,hashlib,subprocess,copy,traceback,secrets
sys.path.insert(0,'/tmp/sim2act-dag-new-csv-independent-20261010/final')
import common as h
from sqlalchemy import text
from sim2act import csv_logic_reuse as logic
ROOT=pathlib.Path('/tmp/sim2act-csv-data-free-logic-independent-20261010/final'); REPO=pathlib.Path('/workspace/Sim2Act'); SHA='4e66136866d5a46347785af45f517dd75de1aeac'
def freeze(name):
 m=json.loads(pathlib.Path('/tmp/sim2act-csv-data-free-logic-20261010/source-freeze.json').read_text());d={}
 assert m['source_sha']==SHA and len(m['files'])==378
 for f in m['files']:
  p=f['path'];b=(REPO/p).read_bytes();g=subprocess.check_output(['git','show',SHA+':'+p],cwd=REPO);d[p]={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()};assert b==g and d[p]['sha256']==f['sha256'] and len(b)==f['bytes'],p
 out=dict(source_sha=SHA,actual_HEAD=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),count=len(d),products=sum(p.startswith('src/') for p in d),Git_worktree_manifest_match=True,files=d);assert out['products']==72
 (ROOT/('source-'+name+'.json')).write_text(json.dumps(out,indent=2));return out

def pgenv(folder):
 folder.mkdir(exist_ok=True);url='postgresql+psycopg://postgres@/logic_reuse_fixture?host=/tmp/sim2act-csv-data-free-logic-20261010/pg-socket';st=h.Store(url,test_only=True);schema='indlogic_'+secrets.token_hex(8)
 with st.engine.begin() as c:c.execute(text('CREATE SCHEMA "'+schema+'"'))
 st.engine=st.engine.execution_options(schema_translate_map={None:schema});st.initialize(fresh_test_schema=schema);a=st.user('Review A','review-A');b=st.user('Review B','review-B');s=h.Settings(url,folder,mode='mock');cl=h.TestClient(h.create_app(st,s));cl.headers['Authorization']='Bearer review-A';pid=cl.post('/api/projects',json={'name':'Independent PG authority key'}).json()['id'];return [st,s,cl,a,b,pid,None],schema

def probe(backend):
 folder=ROOT/backend
 e,schema=(pgenv(folder) if backend=='pg' else (h.env(folder),None));out={'backend':backend,'own_schema':schema,'source_sha':SHA,'scope':'actual canonical three-node source, explicit minted logic, independent authority intent tamper'}
 try:
  aid,rid,p,source,rel=h.make_release(e)
  body={'expected_release_fingerprint':rel['fingerprint'],'consent':logic.CONSENT,'request_key':'review-original-authority'}
  obj=h.request(e,'POST',f'/api/internal/releases/{rel["id"]}/csv-logic-authorizations',body,201)['logic'];lid=obj['id'];expected='csvlogic_'+h.fingerprint([e[3],rel['id'],body['request_key']])[:32];assert lid==expected
  good=h.request(e,'GET','/api/internal/csv-logics/'+lid);assert good==obj
  with e[0].engine.begin() as c:
   rows=c.execute(h.select(h.delivery_graph_requests).where(h.delivery_graph_requests.c.request_key==lid,h.delivery_graph_requests.c.kind.in_([logic.AUTH_KIND,logic.AUTH_KIND+'_seal']))).mappings().all();assert len(rows)==2
   before=[dict(r) for r in rows];after=[]
   for r in rows:
    s=copy.deepcopy(r['snapshot']);s['request']['request_key']='review-tampered-authority';v={'snapshot':s,'fingerprint':h.fingerprint(s),'request_fingerprint':h.fingerprint(s['request'])};c.execute(h.update(h.delivery_graph_requests).where(h.delivery_graph_requests.c.app_id==r['app_id'],h.delivery_graph_requests.c.principal_id==r['principal_id'],h.delivery_graph_requests.c.kind==r['kind'],h.delivery_graph_requests.c.request_key==r['request_key']).values(**v));after.append(dict(r,**v))
  dbbefore=h.snapshot(e);r=e[2].get('/api/internal/csv-logics/'+lid);dbafter=h.snapshot(e)
  out.update(original_body=body,logic_id=lid,original_expected_id=expected,tampered_request_key='review-tampered-authority',tampered_expected_id='csvlogic_'+h.fingerprint([e[3],rel['id'],'review-tampered-authority'])[:32],original_GET=good,tampered_GET_status=r.status_code,tampered_GET_body=r.json(),entire_db_zero_write=dbbefore==dbafter,auth_pair_before=before,auth_pair_after=after)
  assert dbbefore==dbafter
  out['result']='BLOCK_ACCEPTED_TAMPERED_AUTHORITY_REQUEST' if r.status_code==200 else 'REJECTED'
  (ROOT/(backend+'-authority-key.json')).write_text(json.dumps(out,indent=2,ensure_ascii=False,default=str))
  print(json.dumps({k:out[k] for k in ['backend','result','tampered_GET_status','entire_db_zero_write']}),flush=True)
 finally:
  e[2].close()
  if schema:
   with e[0].engine.begin() as c:c.execute(text('DROP SCHEMA "'+schema+'" CASCADE'));exists=c.execute(text('SELECT count(*) FROM pg_namespace WHERE nspname=:n'),{'n':schema}).scalar_one();assert exists==0
   (ROOT/'pg-own-cleanup.json').write_text(json.dumps({'schema':schema,'own_schema_absent':True,'parent_schema_untouched':True}))
  e[0].engine.dispose()
if __name__=='__main__':
 freeze('before')
 for backend in ['pg']:
  try:probe(backend)
  except Exception:
   (ROOT/(backend+'-HARNESS_FAILURE.log')).write_text(traceback.format_exc());raise
 freeze('after')
