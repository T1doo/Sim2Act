import hashlib,json,shutil,subprocess,xml.etree.ElementTree as ET
from pathlib import Path
from collections import Counter
root=Path('/workspace/Sim2Act-bounded-product-candidate');dest=root/'docs/evidence/natural-activation-20261007';dest.mkdir(exist_ok=True)
sha=lambda data:hashlib.sha256(data).hexdigest()
def copy_folder(source,target):
    target.mkdir(parents=True,exist_ok=True)
    for p in source.iterdir():
        if p.is_file():
            if p.name=='source.patch':
                data=p.read_bytes()
                (target/'source-patch.json').write_text(json.dumps({'original_name':p.name,'original_sha256':sha(data),'encoding':'utf-8 JSON string','patch':data.decode()},ensure_ascii=False,indent=2)+'\n')
            else:shutil.copyfile(p,target/p.name)
copy_folder(Path('/tmp/natural-activation-evidence'),dest/'module-fd92')
copy_folder(Path('/tmp/natural-activation-independent/c51eb29'),dest/'independent-c51')
for name in ('design-review.json','root-6ed-pre-review.json'):
    shutil.copyfile(Path('/tmp/natural-activation-independent')/name,dest/name)
for source,name in [(Path('/tmp/natural-activation-root/final'),'pre-drain-c51'),(Path('/tmp/natural-activation-root/final-9406'),'final-9406')]:copy_folder(source,dest/name)
copy_folder(Path('/tmp/natural-activation-root'),dest/'root-development')
# exclude runner archives accidentally copied at top: they are safe source, not private DBs.
for stage in ('pre-drain-c51','final-9406'):
    p=dest/stage
    nodes=json.loads((p/'collection.json').read_text());cases=list(ET.parse(p/'junit.xml').iter('testcase'))
    actual=[c.attrib['classname'].replace('.','/')+'.py::'+c.attrib['name'] for c in cases]
    assert Counter(nodes)==Counter(actual), (stage,set(nodes)^set(actual))
    assert json.loads((p/'source-before.json').read_text())['files']==json.loads((p/'source-after.json').read_text())['files']
# verify all original module artifact hashes including lossless JSON-wrapped patch
expected=json.loads((dest/'module-fd92/artifact-hashes.json').read_text())
for name,expected_hash in expected.items():
    if name=='source.patch':data=json.loads((dest/'module-fd92/source-patch.json').read_text())['patch'].encode()
    else:data=(dest/'module-fd92'/name).read_bytes()
    assert sha(data)==expected_hash,(name,expected_hash)
expected=json.loads((dest/'independent-c51/artifact-hashes.json').read_text())
for name,expected_hash in expected.items():assert sha((dest/'independent-c51'/name).read_bytes())==expected_hash,name
latest=json.loads((dest/'final-9406/source-before.json').read_text());assert latest['head']==subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
for name,expected_hash in latest['files'].items():
    assert sha((root/name).read_bytes())==expected_hash
    assert sha(subprocess.check_output(['git','show',latest['head']+':'+name],cwd=root))==expected_hash
# original full DOM + drain outputs from the owned final pytest fixture tree, no DB exports
fixture=Path('/tmp/pytest-of-agent/pytest-601');ui=dest/'final-9406/ui';ui.mkdir(exist_ok=True)
for glob in ('test_natural_goal_actual_http_*','test_natural_ui_owned_page_dra*'):
    for p in fixture.glob(glob):
        if p.is_symlink():continue
        result=p/('results.json' if 'actual_http' in p.name else 'result.json')
        if result.exists():shutil.copyfile(result,ui/(p.name+'.json'))
assert len(list(ui.glob('*.json')))==9
summary={'execution_source':latest['head'],'collection':304,'pass':303,'skip':1,'fail':0,'seconds':98.59,'source_files':len(latest['files']),'source_before_after_git_equal':True,'junit_collection_multiset_equal':True,'module_own_source':'fd92c4e8c133666a997cd26b5bf73b8841a4b69a','module_own':{'pass':37,'skip':0,'seconds':7.24},'independent_execution_source':'c51eb294c93dcb07fac85b459067680c91a91356','independent_actual_unique':19,'independent_product10_bytes_equal_final':True,'external_model_calls':0,'production_activation':'DEFAULT_DISABLED_LIVE_ID_EMPTY','pg_concurrency':'NOT_RUN_NO_OWNED_ENDPOINT','protected_native':'BLOCKED_EXISTING_SUID_OWNERSHIP','full_windows_ci':'NOT_RUN_EXISTING_NO_GO_900','ui_outputs':9,'preserved_failures':'module WIP syntax/import; first HTTP status assumptions; root expiry empty JSON; mypy type findings retained in log/documentation','safe_export':'No real token/DSN/Authorization/private database exported; source.patch losslessly wrapped as JSON string, original SHA verified.'}
(dest/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary))
