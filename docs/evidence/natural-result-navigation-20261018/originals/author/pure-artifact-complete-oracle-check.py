import json,sys
from pathlib import Path
sys.path.insert(0,'tests')
from test_natural_result_navigation_ui import completed_delta,queued_delta
b=Path('/workspace/natural-result-navigation-evidence-20261018');p=b/'actual-final-tmp/test_same_pb_instance_navigate0';read=lambda n:json.loads((p/n).read_text());a=read('v2-before-page.json');z=read('final-rows.json');info=read('info.json');w=read('business-workers.json')[-1];rid=w['run_id'];key=next(r['request_key'] for r in z['internal_app_runs'] if r not in a['internal_app_runs']);queued_delta(a,read('v2-before-worker.json'),info,rid,key);out=completed_delta(a,z,info,rid,key,w,read('stage-wires.json')['pb-v2'][0]);print(json.dumps(dict(classification='PURE_ARTIFACT_NO_PRODUCT_HTTP_WORKER_MODEL_DB',status='PASS',result_version=out['typed']['version'],queue_journal=6,completed_journal=10)))
