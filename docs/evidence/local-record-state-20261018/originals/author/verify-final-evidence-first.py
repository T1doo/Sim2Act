import hashlib
import json
import subprocess
import time
import xml.etree.ElementTree as ET
from pathlib import Path

root=Path('/workspace/Sim2Act'); out=Path('/workspace/local-record-state-evidence-20261018')
before=json.loads((out/'final-inputs-before.json').read_text())
after={name:{'bytes':(root/name).stat().st_size,'sha256':hashlib.sha256((root/name).read_bytes()).hexdigest()} for name in before['inputs']}
changes={name:dict(before=value,after=after[name]) for name,value in before['inputs'].items() if value!=after[name]}
assert not changes, changes
(out/'final-inputs-after.json').write_text(json.dumps({'head':before['head'],'time_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'inputs':after,'changes':changes},indent=2))
groups={}; identities=set()
for name in ['backend-d5eadc70','ui-d5eadc70','shared-d5eadc70','shared-bounded-final']:
    tree=ET.parse(out/(name+'.xml')); suites=tree.getroot().findall('testsuite')
    entries=tree.getroot().findall('.//testcase')
    cases=[c for c in entries if 'classname' in c.attrib and 'name' in c.attrib]
    assert all(int(s.attrib.get(field,0))==0 for s in suites for field in ['failures','errors','skipped'])
    nodes=[c.attrib['classname']+'::'+c.attrib['name'] for c in cases]
    assert not (identities & set(nodes)); identities.update(nodes)
    groups[name]=dict(tests=len(cases),passed=len(cases),suite_seconds=sum(float(s.attrib['time']) for s in suites),
        completed_case_seconds=sum(float(c.attrib.get('time',0)) for c in cases),nodes=nodes,
        unattributed_case_entries=len(entries)-len(cases),
        batch_status='INTERRUPTED_AFTER_TWO_COMPLETED; PA_UI_NOT_VERIFIED' if name=='shared-d5eadc70' else 'PASS')
assert len(identities)==16, len(identities)
ui=[]
for path in sorted((out/'ui-d5eadc70').glob('*/page-result.json')):
    v=json.loads(path.read_text()); assert v['status']=='PASS'
    for a in v['static_resource_loads']:
        file=root/'src/sim2act/web'/(a['path'].lstrip('/') or 'index.html')
        assert a['status']==200 and hashlib.sha256(file.read_bytes()).hexdigest()==a['sha256']
    assert not json.loads((path.parent/'source-changes.json').read_text())
    ui.append(dict(scenario=v['scenario'],checks=len(v['checks']),http_actions=len(v['actions']),assets=len(v['static_resource_loads']),boots=v['boots']))
assert len(ui)==3
value=dict(frozen_head=before['head'],current_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
    final_unique_pytest_nodes=len(identities),groups=groups,ui=ui,inputs=len(after),input_changes=changes,
    real_model_requests=0,windows='NOT_RUN',pg='NOT_RUN',native_browser='NOT_RUN',remote_ci='NOT_RUN',real_semantics='NOT_RUN',
    historical_failures='Preserved; not included in final unique count',
    incomplete_legacy='PA full generation UI explicitly interrupted at 412.41s; NOT_VERIFIED, not included in 16 passed',
    independent_scope='Reports and short probe separately qualified')
(out/'final-qualified-summary.json').write_text(json.dumps(value,indent=2)+'\n')
print(json.dumps(value))
