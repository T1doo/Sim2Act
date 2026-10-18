"""Read already recorded synthetic outputs only; no product or model reexecution."""
import hashlib
import json
from pathlib import Path

root=Path('/workspace/production-trial-stages-20261018')
path=root/'run-8-chain/actual-tmp/actual-prefix0/actual-pa-stages.json'
raw=path.read_bytes(); value=json.loads(raw)
source=value['results']['source'];cold=value['results']['cold']
review=cold['owner_review']
assert review['content_access'] is True and review['owner_acceptance']=='PENDING'
assert review['run_id']==review['current']['run_id']==cold['run_id']
assert review['current']['material']['content']==cold['result']['result']['checklist']['source_content']
assert source['owner_review']['run_id']==source['run_id']
assert source['owner_review']['content_access'] is False
assert source['owner_review']['owner_acceptance']=='PENDING'
assert source['owner_review']['invalidation_reason']=='VERSION_CONFLICT'
assert all(b['snapshot']['response']['sha256']!=b['snapshot']['response']['canonical_sha256']
           for b in value['bodies'] if b['kind']=='pa_trial_response_body.v1')
proof=dict(input=str(path),sha256=hashlib.sha256(raw).hexdigest(),
    post_execution_output_only=True,additional_model_or_product_calls=0,
    current_cold_run_owner_entrance='CONTENT_ACCESS_TRUE_PENDING_EXACT_SAME_RUN_AND_B_MATERIAL',
    prior_source_owner_entrance='PENDING_HISTORY_CONTENT_REFUSED_AFTER_NEWER_RESULT',
    raw_canonical_distinct_all_seven=True)
(root/'closed-output-audit.json').write_text(json.dumps(proof,indent=2)+'\n')
print(json.dumps(proof))
