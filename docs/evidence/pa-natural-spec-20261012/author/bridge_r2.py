"""Exact current-source and named-test comparison, with old verdict retained."""
import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REVIEW = ROOT.parent/'independent/integration-r2'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def nodes(path):
    result = {}
    for case in ET.parse(path).findall('.//testcase'):
        key = case.attrib['classname'].replace('.','/')+'.py::'+case.attrib['name']
        assert key not in result
        result[key] = ('FAIL' if case.find('failure') is not None else 'ERROR' if case.find('error') is not None
                       else 'SKIP' if case.find('skipped') is not None else 'PASS')
    return result

author = json.loads((ROOT/'final-r2-source-after.json').read_text())
review = json.loads((REVIEW/'source-after.json').read_text())
files = {key:value['sha256'] for key,value in review['files_and_links'].items()}
assert author['head'] == review['head'] == 'c28e91a5066e59c1c36e76b910515298d0d1eb28'
assert author['files'] == files and len(files) == 434
an = nodes(ROOT/'final-r2.xml')
sn = nodes(REVIEW/'selected.xml')
en = nodes(REVIEW/'extra.xml')
assert not set(sn)&set(en)
rn = {**sn,**en}
old = json.loads((ROOT/'final-source-after.json').read_text())
delta = {name:[old['files'].get(name),files.get(name)] for name in set(old['files'])|set(files)
         if old['files'].get(name)!=files.get(name)}
value = dict(frozen_head=author['head'],source_entries=434,source_differences=0,
             author_source_after_sha256=sha(ROOT/'final-r2-source-after.json'),
             independent_source_after_sha256=sha(REVIEW/'source-after.json'),
             author_unique=len(an),independent_current_unique=len(rn),
             overlapping_nodeids=sorted(set(an)&set(rn)),independent_only_nodeids=sorted(set(rn)-set(an)),
             delta_from_827=delta,unchanged_from_827=434-len(delta),
             old_verdict='Original 79-node review belongs to 827. It is preserved, not relabelled as current c28.',
             xml_sha256={str(path.relative_to(ROOT.parent)):sha(path) for path in
                         [ROOT/'final-r2.xml',REVIEW/'selected.xml',REVIEW/'extra.xml']})
(ROOT/'author-independent-source-bridge-r2.json').write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')
print(json.dumps({key:v for key,v in value.items() if key not in ['overlapping_nodeids','delta_from_827','xml_sha256']},indent=2))
print('actual_current_overlap',len(value['overlapping_nodeids']))
