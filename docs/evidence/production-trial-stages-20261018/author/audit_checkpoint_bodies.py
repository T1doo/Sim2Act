"""Pure-file raw/canonical verification after the incomplete closed execution."""
import base64,hashlib,json
from pathlib import Path
root=Path('/workspace/production-trial-stages-20261018')
p=root/'closed-checkpoint-facts.json';data=p.read_bytes();v=json.loads(data)
rows=[r for r in v['archives'] if r['kind']=='pa_trial_response_body.v1']
checks=[]
for row in rows:
 b=row['snapshot']['response'];raw=base64.b64decode(b['body_b64'],validate=True)
 canonical=json.dumps(json.loads(raw),ensure_ascii=True,allow_nan=False,separators=(',',':')).encode('ascii')
 assert hashlib.sha256(raw).hexdigest()==b['sha256']
 assert hashlib.sha256(canonical).hexdigest()==b['canonical_sha256']
 assert b['sha256']!=b['canonical_sha256']
 checks.append(dict(attempt_id=b['attempt_id'],raw_bytes=len(raw),canonical_bytes=len(canonical),raw_sha256=b['sha256'],canonical_sha256=b['canonical_sha256']))
assert len(checks)==7
value=dict(status='SEVEN_RAW_CANONICAL_FACTS_VALID_NOT_BUSINESS_ACCEPTANCE',
 input_sha256=hashlib.sha256(data).hexdigest(),checks=checks,
 sqlite_or_product_or_model_calls=0,owner_result_and_rejection_node_qualification='NOT_RUN')
(root/'closed-checkpoint-body-audit.json').write_text(json.dumps(value,indent=2)+'\n')
print('Seven captured response raw/canonical bytes verified; no business qualification claimed')
