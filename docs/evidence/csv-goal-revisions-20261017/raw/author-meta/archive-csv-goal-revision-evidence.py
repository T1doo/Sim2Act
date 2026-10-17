from pathlib import Path
import gzip,hashlib,json,re,subprocess
root=Path('/workspace/Sim2Act')
out=root/'docs/evidence/csv-goal-revisions-20261017'
manifest=[]
def add(source,relative):
    source=Path(source)
    if not source.is_file() or source.is_symlink(): return
    data=source.read_bytes(); sha=hashlib.sha256(data).hexdigest()
    packed=source.suffix in {'.db','.sqlite','.sqlite3'} or len(data)>1048576
    target=out/(str(relative)+('.gz' if packed else ''))
    target.parent.mkdir(parents=True,exist_ok=True)
    payload=gzip.compress(data,mtime=0) if packed else data
    if target.exists() and target.read_bytes()!=payload: raise RuntimeError('Archive collision: '+str(target))
    target.write_bytes(payload)
    if hashlib.sha256(source.read_bytes()).hexdigest()!=sha: raise RuntimeError('Mutable original: '+str(source))
    assert (gzip.decompress(target.read_bytes()) if packed else target.read_bytes())==data
    manifest.append(dict(original=str(source),archive=str(target.relative_to(out)),encoding='gzip' if packed else 'identity',bytes=len(data),sha256=sha,stored_sha256=hashlib.sha256(payload).hexdigest()))
meta=Path('/workspace/csv-goal-revision-evidence-20261017')
for p in sorted(meta.rglob('*')):
    add(p,Path('raw/author-meta')/p.relative_to(meta))
for name in ('run-csv-goal-revision-author.py','run-csv-goal-revision-refined-deliver.py','archive-csv-goal-revision-evidence.py','verify-csv-goal-revision-delivery.py'):
    add(Path('/workspace')/name,Path('raw/author-meta')/name)
patterns=('test_same_app_actual_check','test_adopt_without_drift','test_checked_proposal_rejec','test_check_role_pins','test_revoked_new_goal_material','test_visible_same_goal_revisio')
parent=Path('/tmp/pytest-of-agent')
for batch in sorted(parent.glob('pytest-*')):
    if batch.is_symlink() or not re.fullmatch('pytest-[0-9]+',batch.name) or int(batch.name[7:])<11: continue
    for case in sorted(batch.iterdir()):
        if case.is_symlink() or not case.is_dir() or not case.name.startswith(patterns): continue
        for p in sorted(case.rglob('*')):
            add(p,Path('raw/author-development')/batch.name/case.name/p.relative_to(case))
for name in ('csv-goal-revision-author-b1b1b215-20261017','csv-goal-revision-author-refined-deliver-20261017'):
    batch=Path('/tmp')/name
    if not batch.exists(): continue
    for p in sorted(batch.rglob('*')):
        add(p,Path('raw/author')/batch.name/p.relative_to(batch))
# Independent sealed originals are copied only from the agent's final explicit
# manifest, never by recursively copying its checkout, dependency link or cache.
ind_meta=Path('/workspace/csv-goal-revision-evidence-20261017/independent-originals.json')
if ind_meta.exists():
    for item in json.loads(ind_meta.read_text()):
        source=Path(item['original'])
        assert hashlib.sha256(source.read_bytes()).hexdigest()==item['sha256']
        add(source,Path('raw/independent')/item['relative'])
out.mkdir(parents=True,exist_ok=True)
(out/'originals-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(originals=len(manifest),sqlite_copies=sum(x['original'].endswith('.db') for x in manifest),stored_bytes=sum((out/x['archive']).stat().st_size for x in manifest)),indent=2))
