import json, os, subprocess
from pathlib import Path
import pytest
from test_registered_text_extraction import prepared, make_app, request as extraction_request

OUT=Path('/tmp/pb-text-extraction-review-20261011')
@pytest.mark.parametrize('poison_kind',['wrong-existing-app','candidate-fp','wrong-other-key-app'])
def test_keyed_receipt_requires_exact_actual_candidate(env,tmp_path,poison_kind):
    data, aid, _, instance, run, target, resource, _=prepared(env)
    if poison_kind=='wrong-other-key-app':
        _,other_body=extraction_request(data,data[7] if len(data)>7 else f"/api/internal/instances/{instance['id']}/runs/{run['id']}",target)
        other_body.update(name='Extracted visible text',request_key='other-independent-original-key')
        other_reply=data[2].post(f"/api/internal/instances/{instance['id']}/runs/{run['id']}/extract",json=other_body)
        assert other_reply.status_code==201,other_reply.text
        third=other_reply.json()['id'];other_fp=other_reply.json()['candidate_fingerprint']
    else:
        third=make_app(data,'third-unrelated-authorized');other_fp=None
    prefix=os.environ.get('PB_PROBE_PREFIX','keyed-receipt-red-v3-')+poison_kind
    info=tmp_path/'info.json'
    info.write_text(json.dumps({'project':data[4],'source':aid,'instance':instance['id'],'run':run['id'],'target':target,'resource':resource,'scenario':'lost','poison_kind':poison_kind,'poison_app':third,'poison_fingerprint':other_fp,'output':str(OUT/(prefix+'.json'))}))
    p=subprocess.Popen(['node',str(OUT/'keyed_receipt_poison_v2.cjs'),str(info)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env={**os.environ,'NODE_PATH':'/workspace/node-tools/node_modules'})
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
