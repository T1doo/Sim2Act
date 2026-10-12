"""Controlled bad 200 with another valid app, original R8 exact snapshot only."""
import hashlib,json,os,subprocess
import pytest
from pathlib import Path
from conftest import env
from test_text_workflows import draft,instance,enqueue,once,material
import sim2act

OUT=Path('/tmp/pb-text-multistep-independent-r11-20261012')

@pytest.mark.parametrize("attack_kind",["wrong-key","correct-key-other-app"])
def test_other_real_app_cannot_be_original_creation_key_result(env,tmp_path,attack_kind):
    assert '/workspace/Sim2Act/src' in sim2act.__file__,sim2act.__file__
    source,_=draft(env);release,inst=instance(env,source['id']);rid=enqueue(env,release,inst);once(env)
    target,card=material(env,'Cedar new owner\nQuartz tomorrow\nCedar reserved\n','md')
    title='Independent alternate-key target Goal'
    native=env[2].get('/api/goal-cards/'+card['id']).json()
    content=native['content'];content['title']=title
    saved=env[2].put('/api/goal-cards/'+card['id'],json={**content,'expected_version':native['version']})
    assert saved.status_code==200,saved.text
    info={'project':env[5],'source_run':rid,'resource':target,'goal_title':title,'scenario':'creation-lost',
          'attack_kind':attack_kind,'alternate_name':'Actual two-search task','alternate_receipt':{**source,'cached':True},'output':str(OUT/(attack_kind+'-page.json'))}
    path=tmp_path/'info.json';path.write_text(json.dumps(info))
    with (OUT/(attack_kind+'-node-stderr.log')).open('w') as err:
        p=subprocess.Popen(['node',str(OUT/'other-key.cjs'),str(path)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=err,text=True)
        try:
            for line in p.stdout:
                request=json.loads(line)
                if request.get('done'):break
                r=env[2].request(request['method'],request['path'],json=request.get('body'),headers=request.get('headers'))
                p.stdin.write(json.dumps({'id':request['id'],'status':r.status_code,'text':r.text,'content_type':r.headers.get('content-type')})+'\n');p.stdin.flush()
            p.stdin.close();code=p.wait(timeout=20)
        finally:
            if p.poll() is None:p.kill();p.wait(timeout=5)
    proof=json.loads((OUT/(attack_kind+'-page.json')).read_text());assert len(proof['static_resource_loads'])==20
    for item in proof['static_resource_loads']:
        file=Path('/workspace/Sim2Act/src/sim2act/web')/(item['path'].lstrip('/') or 'index.html')
        assert hashlib.sha256(file.read_bytes()).hexdigest()==item['sha256']
    (OUT/(attack_kind+'-node-exit.json')).write_text(json.dumps({'exit_code':code,'source_import':sim2act.__file__,'assets':20,'alternate_id':source['id'],'source_candidate_fingerprint':source['candidate_fingerprint'],'same_project':env[5]},indent=2)+'\n')
    assert code==0 and proof['status']=='PASS',(OUT/(attack_kind+'-node-stderr.log')).read_text()
