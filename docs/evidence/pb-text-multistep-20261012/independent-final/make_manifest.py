import hashlib,json
from pathlib import Path
out=Path(__file__).parent
files={}
for p in sorted(out.rglob('*')):
    if p.is_file() and p.name!='manifest.json' and not any(x.endswith(('-fixtures','-cache')) or x=='__pycache__' for x in p.relative_to(out).parts):
        files[str(p.relative_to(out))]=hashlib.sha256(p.read_bytes()).hexdigest()
a={'classification':'LIMITED_PASS_R11_56_UNIQUE_NODES','files':files,'source_map':'ba77f3195c17bc1015ced6c15224240f8a64f54020d06fa56a324f3f85e9351a','implementation':'82a9ded4897962cb81e8e0d05a2195a3686e60bbe0032ac25316dc2d793ae4ab','history_file_count':381,'exclusions':'temporary pytest fixture SQLite/cache and __pycache__ only; manifest self omitted'}
(out/'manifest.json').write_text(json.dumps(a,indent=2)+'\n')
assert all(hashlib.sha256((out/f).read_bytes()).hexdigest()==h for f,h in files.items())
print('manifest files',len(files),'SHA256',hashlib.sha256((out/'manifest.json').read_bytes()).hexdigest());print('report SHA256',files['FINAL_REVIEW.md'])
