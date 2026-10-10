from common import *
from conftest import env as original
from test_conditional_run_bindings import env as bounded,facts,envelope,work,get,POLICY
from test_report_presentations import prepared
from test_report_manifest_apps import preview_path
os.environ.pop('SIM2ACT_TEST_DATABASE_URL',None);freeze('before');folder=ROOT/'seed';folder.mkdir(exist_ok=True);gen=original.__wrapped__(folder);env=bounded.__wrapped__(next(gen))
try:
 app,diagram,url,first_body,first_output,wires=prepared(env,folder,peer=True)
 text2='独立第二个归档：需补收据与批准；<img src=x onerror=window.independentExecuted=true>'
 lines=POLICY.read_text().splitlines();output2={'findings':[{'rule_id':f'R{n}','applies':'TRUE','citation':{'line':n+2,'quote':lines[n+1]}} for n in [1,2,3]],'decision':'BLOCK','next_actions':['obtain_receipt','obtain_prior_approval'],'deadline_days':10,'absolute_date':'UNKNOWN','receipt_restarts_deadline':False,'explanation':text2}
 accepted=env[2].post(preview_path(env,app['id']),json={'expected_candidate_fingerprint':app['fingerprint'],'input':facts(680,receipt_present=False),'request_key':'independent-second-result'});assert accepted.status_code==202,accepted.text;work(env,folder,[envelope(output2)],wires);second=get(env,accepted.json()['run_id']);body2={**first_body,'run_id':second['run_id'],'expected_run_version':second['version'],'expected_run_fence':second['fence'],'expected_result_fingerprint':second['result_fingerprint']}
 bodies={};patches={};expected={}
 for key,body,count,decision,text in [('alpha',first_body,2,'ALLOW',first_output['explanation']),('beta',body2,3,'BLOCK',text2),('gamma',first_body,1,'ALLOW',first_output['explanation'])]:
  body={**body,'request_key':'independent-'+key};r=env[2].post(url,json=body);assert r.status_code==201,r.text;patches[key]=r.json();bodies[key]=body;expected[body['request_key']]={'decision':decision,'text':text,'run_id':body['run_id'],'checks':[]}
  for n in range(count):
   name=f'independent-{key}-{n}';r=env[2].post(url+'/'+body['request_key']+'/checks',json={'expected_patch_fingerprint':patches[key]['patch_fingerprint'],'request_key':name});assert r.status_code==201,r.text;expected[body['request_key']]['checks'].append(name)
 with env[0].engine.connect() as c:peer=next(dict(r) for r in c.execute(select(app_drafts)).mappings() if r['candidate'].get('actions',[{}])[0].get('executor',{}).get('ref')=='data.aggregate_csv')
 cfg={'app':app,'graph':diagram,'url':url,'owner':env[3],'other':env[4],'project':env[5],'peer':peer,'bodies':bodies,'patches':patches,'expected':expected,'mock_exchanges':len(wires)};(ROOT/'seed.json').write_text(json.dumps(cfg,indent=2));(ROOT/'seed-state.json').write_text(json.dumps(state(env[0]),indent=2,default=str));print({'seed':'PASS','definitions':3,'checks':6,'archived_runs':2,'mock_exchanges':len(wires)},flush=True)
finally:gen.close()
