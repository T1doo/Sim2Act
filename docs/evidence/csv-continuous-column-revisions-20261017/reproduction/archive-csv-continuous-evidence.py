import gzip,hashlib,json
from pathlib import Path
repo=Path('/workspace/Sim2Act');raw=Path('/workspace/csv-continuous-column-evidence-20261017');dest=repo/'docs/evidence/csv-continuous-column-revisions-20261017'
assert not dest.exists();dest.mkdir(parents=True)
roots=[
 ('author-originals',raw),
 ('author-d74-regression-data',Path('/tmp/csv-continuous-author-d74-regressions-20261017')),
 ('author-b589-old-page-data',Path('/tmp/csv-continuous-author-b589-old-pages-20261017')),
 ('author-b589-upgrade-data',Path('/tmp/csv-continuous-upgrade-page-data-20261017')),
 ('development-first-data',Path('/tmp/csv-continuous-dev-first-20261017')),
 ('development-second-data',Path('/tmp/csv-continuous-dev-second-20261017')),
 ('development-api-data',Path('/tmp/csv-continuous-dev-api-20261017')),
 ('development-browser-data',Path('/tmp/csv-continuous-dev-browser-20261017')),
 ('development-negative-data',Path('/tmp/csv-continuous-dev-negative-20261017')),
 ('existing-wip-upgrade-probe',Path('/tmp/csv-continuous-upgrade-probe-20261017')),
 ('independent-d74-api',Path('/tmp/f2-csv-continuous-d74f-independent')),
 ('independent-d74-pages',Path('/tmp/csv-column-independent-d74f2fed-20261017')),
 ('independent-b589-upgrade',Path('/tmp/csv-upgrade-independent-b5898093-20261017')),
 ('independent-b589-next-navigation',Path('/tmp/csv-continuous-independent-b5898093-g3l0xk_b/evidence')),
 ('design-oracles',Path('/tmp/f2-csv-continuation-design')),
 ('design-browser',Path('/tmp/csv-column-revision-page-design-20261017')),
 ('contract-wip',Path('/tmp/f2-csv-continuous-ce3-wip-review')),
 ('contract-cache-wip',Path('/tmp/f2-csv-continuous-cache-wip-review')),
 ('contract-design',Path('/tmp/f2-csv-continuous-ce3-contract-design.md')),
 ('contract-design',Path('/tmp/f2-csv-continuous-ce3-contract-design.json')),
]
scripts=['run-csv-continuous-regressions.py','run-csv-b589-old-pages.py','prepare-csv-upgrade-candidate.py','draft-csv-upgrade-fix.py','freeze-csv-upgrade-isolated.py','verify-csv-upgrade-candidate.py','probe-csv-continuous-upgrade.py','summarize-csv-continuous-coverage.py','verify-csv-continuous-source.py','archive-csv-continuous-evidence.py']
roots += [('reproduction',Path('/workspace')/name) for name in scripts]
manifest=[];excluded=[]
def sha(b):return hashlib.sha256(b).hexdigest()
for prefix,root in roots:
 assert root.exists(),root
 paths=[root] if root.is_file() else sorted(root.rglob('*'))
 for p in paths:
  rel=Path(p.name) if root.is_file() else p.relative_to(root)
  if not p.is_file() or p.is_symlink() or any(x in rel.parts for x in ('snapshot','__pycache__','.pytest_cache','node_modules','.git')):continue
  data=p.read_bytes()
  if p.name.endswith(('.tar.gz','.tar')):
   excluded.append(dict(original=str(p),reason='redundant container; all unique raw payloads retained separately',bytes=len(data),sha256=sha(data)));continue
  compressed=p.suffix in ('.db','.sqlite','.sqlite3','.log','.xml') or len(data)>1024*1024
  name=prefix+'/'+str(rel)+('.gz' if compressed else '')
  target=dest/name;assert not target.exists(),target;target.parent.mkdir(parents=True,exist_ok=True)
  stored=gzip.compress(data,mtime=0) if compressed else data;target.write_bytes(stored)
  manifest.append(dict(original=str(p),saved=name,bytes=len(data),sha256=sha(data),encoding='gzip' if compressed else 'identity',stored_sha256=sha(stored)))
for x in manifest:
 data=(dest/x['saved']).read_bytes();assert sha(data)==x['stored_sha256']
 if x['encoding']=='gzip':data=gzip.decompress(data)
 assert len(data)==x['bytes'] and sha(data)==x['sha256']
(dest/'ORIGINALS.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
report=dict(original_files=len(manifest),sqlite_copies=sum(Path(x['original']).suffix in ('.db','.sqlite','.sqlite3') for x in manifest),original_bytes=sum(x['bytes'] for x in manifest),stored_bytes=sum((dest/x['saved']).stat().st_size for x in manifest),all_decoded_originals_verified=True,excluded_redundant_containers=excluded)
(dest/'archive-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False,indent=2))
