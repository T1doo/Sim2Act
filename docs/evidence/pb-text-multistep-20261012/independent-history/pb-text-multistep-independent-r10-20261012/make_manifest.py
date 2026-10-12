import hashlib,json
from pathlib import Path
out=Path(__file__).parent
files={}
for p in sorted(out.rglob('*')):
    parts=p.relative_to(out).parts
    if p.is_file() and p.name!='manifest.json' and not any(x.endswith(('-fixtures','-cache')) or x=='__pycache__' for x in parts):
        files[str(p.relative_to(out))]=hashlib.sha256(p.read_bytes()).hexdigest()
a={'classification':'LIMITED_PASS_54_UNIQUE_FINAL_NODES_RAW_55_WITH_ONE_RETAINED_FIXTURE_FAILURE','files':files,'source_map':'8315e4f02df120c2b066c12e58dd2299e5dbbe52062d8b53fcfd4514512253fa','implementation':'ccf4ffd41ff45ccf5d46d12ebb659c1ea930b9f75dd45922ec84781806d0c70a','history_count':len(json.loads((out/'history-manifest.json').read_text())),'exclusions':'temporary pytest SQLite fixture/cache and __pycache__ only; manifest self omitted'}
(out/'manifest.json').write_text(json.dumps(a,indent=2)+'\n')
assert all(hashlib.sha256((out/f).read_bytes()).hexdigest()==h for f,h in files.items())
print('manifest',len(files),hashlib.sha256((out/'manifest.json').read_bytes()).hexdigest());print('FINAL_REVIEW',files['FINAL_REVIEW.md'])
