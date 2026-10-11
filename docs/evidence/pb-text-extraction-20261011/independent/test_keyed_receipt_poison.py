import json, os, subprocess
from pathlib import Path
import pytest
from test_registered_text_extraction import prepared, make_app

OUT=Path('/tmp/pb-text-extraction-review-20261011')
@pytest.mark.parametrize('poison_kind',['wrong-existing-app','candidate-fp'])
def test_keyed_receipt_requires_exact_actual_candidate(env,tmp_path,poison_kind):
    data, aid, _, instance, run, target, resource, _=prepared(env)
    third=make_app(data,'third-unrelated-authorized')
    prefix='keyed-receipt-red-'+poison_kind
    info=tmp_path/'info.json'
    info.write_text(json.dumps({'project':data[4],'source':aid,'instance':instance['id'],'run':run['id'],'target':target,'resource':resource,'scenario':'lost','poison_kind':poison_kind,'poison_app':third,'output':str(OUT/(prefix+'.json'))}))
    p=subprocess.Popen(['node',str(OUT/'keyed_receipt_poison.cjs'),str(info)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env={**os.environ,'NODE_PATH':'/workspace/node-tools/node_modules'})
    worker_calls=0
    try:
        for line in p.stdout:
            request=json.loads(line)
            if request.get('done'):break
            if request.get('command')=='worker':
                worker_calls+=1
                raise AssertionError('Unexpected cold Worker; poison guard must be evaluated before running a candidate')
            response=data[2].request(request['method'],request['path'],json=request.get('body'),headers=request.get('headers'))
            answer={'id':request['id'],'status':response.status_code,'text':response.text,'content_type':response.headers.get('content-type')}
            p.stdin.write(json.dumps(answer)+'\n');p.stdin.flush()
        p.stdin.close();error=p.stderr.read();code=p.wait(timeout=20)
        (OUT/(prefix+'.log')).write_text(error)
        (OUT/(prefix+'-process.json')).write_text(json.dumps({'exit_code':code,'worker_calls':worker_calls,'scope':'Actual API and HTTP assets; only keyed receipt response substituted in JSDOM fetch; no native browser or real provider'},indent=2)+'\n')
        assert code==0,error
    finally:
        if p.poll() is None:p.kill();p.wait(timeout=10)
