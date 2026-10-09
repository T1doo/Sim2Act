from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import xml.etree.ElementTree as ET

repo=Path('/workspace/Sim2Act')
root=Path('/tmp/sim2act-condition-groups-integration-20261009')
dest=repo/'docs/evidence/bounded-condition-groups-integration-20261009'
dest.mkdir(exist_ok=True)
baseline=json.loads((root/'baseline-verification.json').read_text())
assert all(hashlib.sha256((repo/name).read_bytes()).hexdigest()==digest for name,digest in baseline['files'].items())
for name in ['baseline-verification.json','fast-forward.log','ruff.log','mypy.log','product-diff-check.log','pg-container.json','pg-ready.log','collect_evidence.py']:
    shutil.copy2(root/name,dest/name)
summary={}
for backend in ['sqlite','pg']:
    if not (root/(backend+'.exit')).exists():continue
    assert (root/(backend+'.exit')).read_text().strip()=='0'
    for ext in ['log','xml','exit']:
        shutil.copy2(root/(backend+'.'+ext),dest/(backend+'.'+ext))
    suite=ET.parse(root/(backend+'.xml')).getroot().find('testsuite')
    assert suite.attrib['tests']=='13'
    assert all(suite.attrib[k]=='0' for k in ['errors','failures','skipped'])
    page_proofs=[]
    upgrades=[]
    for file in (root/backend).rglob('*'):
        if file.is_symlink() or not file.is_file() or file.name not in ['results.json','driver.log','upgrade-proof.json']:
            continue
        target=dest/backend/file.relative_to(root/backend)
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(file,target)
        if file.name=='results.json':
            data=json.loads(file.read_text())
            assert data['status']=='PASS'
            assert all(digest==baseline['files']['src/sim2act/web/'+name] for name,digest in data['loaded_source_sha256'].items())
            if file.parent.name.startswith('test_actual_group_controls'):
                assert len(data['checks'])==24
                assert 'four-leaf group disables add at its exact bound' in data['checks']
                assert 'removing a leaf restores bounded add control' in data['checks']
            page_proofs.append({'case':file.parent.name,'checks':len(data['checks']),'loaded_source_sha256':data['loaded_source_sha256']})
        elif file.name=='upgrade-proof.json':
            data=json.loads(file.read_text())
            assert data['old_json_storage_bytes_preserved'] is True
            assert data['no_migration'] is True
            upgrades.append({'case':file.parent.name,'archive_sha':data['archive_sha'],'old_module_sha256':data['old_module_sha256'],'old_json_storage_bytes_preserved':True,'no_migration':True})
    assert len(page_proofs)==11 and sum(p['checks'] for p in page_proofs)==199
    assert len(upgrades)==2
    assert {u['archive_sha'] for u in upgrades}=={'5a5543c902fbb78dd91c28c98386af51fb24dd67','1b65e94ebd81c1e31091b3078b8223328b726294'}
    result={**suite.attrib,'pass':13,'page_cases':11,'driver_checks':199,'four_leaf_add_remove_page_cases':3,'actual_old_source_upgrades':upgrades,'execution_head':'f540194b334f6ccce06b7548e7a0d36636d6fbc1','source_freeze':'79b119b616a20d9347b5677c0d58fbbbe18127c8','product_freeze':'f4bf46355e009617775c056540fc45fcc4512a77','attribution':'Author integration HTTP/jsdom/Worker and upgrade regression; not independent PG or native acceptance.'}
    summary[backend]=result
    (dest/(backend+'-page-source-verification.json')).write_text(json.dumps(page_proofs,indent=2)+'\n')
(dest/'test-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
