import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import xml.etree.ElementTree as ET

repo = Path('/workspace/Sim2Act')
root = Path('/tmp/sim2act-condition-groups-20261009')
evidence = repo / 'docs/evidence/bounded-condition-groups-20261009'
evidence.mkdir(exist_ok=True)
sha = subprocess.check_output(['git', 'rev-parse', '79b119b'], cwd=repo, text=True).strip()
files = json.loads((root / 'source-freeze.json').read_text())['files']
final = {name: hashlib.sha256((repo / name).read_bytes()).hexdigest() for name in files}
changed = [name for name in files if files[name] != final[name]]
assert changed == sorted(changed)
assert set(changed) == {'src/sim2act/web/csv-dag.js', 'tests/condition_groups_ui.cjs', 'tests/test_condition_groups_ui.py'}
(evidence / 'final-source-freeze.json').write_text(json.dumps({'source_sha':sha,'base_sha':'8c572154ff72ac61a506fb9313cb631996e76df7','previous_source_sha':'eeb368ccb338429637f271bf57bdb2781245b976','changed_files':changed,'files':final},indent=2)+'\n')
summary = {}
for name in ['sqlite-frozen','pg-frozen','sqlite-final-ui-v2','pg-final-ui']:
    if not (root / (name+'.xml')).exists():
        continue
    for ext in ['log','xml','exit']:
        shutil.copy2(root / (name+'.'+ext), evidence / (name+'.'+ext))
    suite = ET.parse(root / (name+'.xml')).getroot().find('testsuite')
    summary[name] = dict(suite.attrib)
    page_checks = 0
    proofs = []
    for file in (root / name).rglob('*'):
        if file.is_symlink() or not file.is_file() or file.name not in ['results.json','driver.log','upgrade-proof.json']:
            continue
        dest = evidence / name / file.relative_to(root / name)
        dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(file,dest)
        if file.name == 'results.json':
            data = json.loads(file.read_text())
            assert data['status'] == 'PASS'
            expected = files if name.endswith('frozen') else final
            for loaded,digest in data['loaded_source_sha256'].items():
                assert digest == expected['src/sim2act/web/'+loaded]
            page_checks += len(data['checks'])
            proofs.append({'case':str(file.parent.name),'checks':len(data['checks']),'loaded_source_sha256':data['loaded_source_sha256']})
    summary[name]['page_cases'] = len(proofs)
    summary[name]['driver_checks'] = page_checks
    summary[name]['source_sha'] = 'eeb368ccb338429637f271bf57bdb2781245b976' if name.endswith('frozen') else sha
    (evidence / (name+'-source-verification.json')).write_text(json.dumps(proofs,indent=2)+'\n')
history = evidence / 'development-history'
history.mkdir(exist_ok=True)
for name in ['sqlite-final-ui']:
    for ext in ['log','xml','exit']:
        shutil.copy2(root / (name+'.'+ext),history / (name+'.'+ext))
    for file in (root / name).rglob('*'):
        if file.is_file() and not file.is_symlink() and file.name in ['results.json','driver.log','failure.json']:
            dest=history / name / file.relative_to(root / name)
            dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(file,dest)
(evidence / 'test-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
