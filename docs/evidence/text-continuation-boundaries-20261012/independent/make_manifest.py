import hashlib,json
from pathlib import Path
out=Path(__file__).parent
files={}
for p in sorted(out.rglob('*')):
    rel=p.relative_to(out)
    if p.is_file() and p.name!='manifest.json' and not any(part.endswith(('-fixtures','-cache')) or part=='__pycache__' for part in rel.parts):
        files[str(rel)]=hashlib.sha256(p.read_bytes()).hexdigest()
manifest={'classification':'LIMITED_PASS_112_UNIQUE_NODES','files':files,'source_map':'973918a69af80c30b19436f09519e25f09dbf581892cdf24a3db7b2d9e49ef04','implementation':'7bc662bb1483693e96edf916d2177ad51f246e0cbde7a50d943675d8c9ec852d','qualification':'410 frozen src/tests plus pyproject checked before/after; exact exit0/JUnit/logs; no source writes','exclusions':'temporary pytest fixture DB/cache and __pycache__ only; manifest self omitted','history_manifest_files':len(json.loads((out/'history-manifest.json').read_text()))}
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('manifest files',len(files),'sha256',hashlib.sha256((out/'manifest.json').read_bytes()).hexdigest())
print('FINAL_REVIEW sha256',files['FINAL_REVIEW.md'])
assert all(hashlib.sha256((out/p).read_bytes()).hexdigest()==h for p,h in files.items())
