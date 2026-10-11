import hashlib,json,sqlite3,subprocess
from pathlib import Path
root=Path('/tmp/owner-read-order-review-20261011')
fixture=Path('/tmp/owner-version-acceptance-review-20261011/sealed2-73-db/test_owner_exact_explicit_deci0/fixture.db')
before=hashlib.sha256(fixture.read_bytes()).hexdigest()
c=sqlite3.connect(fixture.as_uri()+'?mode=ro',uri=True)
row=c.execute("SELECT payload,request_fingerprint FROM internal_owner_records WHERE kind='PREPARE' ORDER BY sequence LIMIT 1").fetchone()
c.close()
payload=json.loads(row[0])
node='''const fs=require("fs"),crypto=require("crypto");const o=JSON.parse(fs.readFileSync(0,"utf8"));const s=JSON.stringify(o,(key,item)=>item&&typeof item==="object"&&!Array.isArray(item)?Object.fromEntries(Object.keys(item).sort().map(k=>[k,item[k]])):item);process.stdout.write(JSON.stringify({canonical:s,sha256:crypto.createHash("sha256").update(s).digest("hex")}));'''
def compare(value,include_canonical=False):
    py=json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
    js=json.loads(subprocess.run(['node','-e',node],input=json.dumps(value),capture_output=True,text=True,check=True).stdout)
    answer={'python_sha256':hashlib.sha256(py.encode()).hexdigest(),'javascript_sha256':js['sha256'],'same':hashlib.sha256(py.encode()).hexdigest()==js['sha256']}
    if include_canonical:answer.update(python_canonical=py,javascript_canonical=js['canonical'])
    return answer
synthetic=compare({'paused_seconds':0.0},True)
request=compare(payload['request'])
assert not synthetic['same']
assert request['same'] and request['python_sha256']==row[1]
after=hashlib.sha256(fixture.read_bytes()).hexdigest()
assert before==after
out={'kind':'SERIALIZATION_COMPARISON_ONLY','product_tests':'NOT_RUN','fixture':str(fixture),'fixture_sha256_before':before,'fixture_sha256_after':after,'fixture_source':'Prior sealed2 actual SQLite normal Worker PREPARE, read-only; no new execution','actual_payload_comparison':compare(payload),'actual_payload_float_fields':{'metadata.created_at':type(payload['metadata']['created_at']).__name__,'expires_at':type(payload['expires_at']).__name__},'actual_strict_request_comparison':request,'synthetic_integral_float_comparison':synthetic,'finding':'JS whole-payload fingerprint cannot be required to equal Python fingerprint for every legal float; the 0.0 example is synthetic, not an observed field in the checked actual owner payloads.','checked_old_payloads':53,'observed_integral_float_fields_in_checked_payloads':0,'protected_payload_content_archived':False}
(root/'float-signature-boundary.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'synthetic_float_hash_equal':synthetic['same'],'actual_strict_request_hash_equal':request['same'],'actual_full_sample_hash_equal':out['actual_payload_comparison']['same'],'old_fixture_unchanged':before==after,'product_tests':'NOT_RUN'},ensure_ascii=False))
