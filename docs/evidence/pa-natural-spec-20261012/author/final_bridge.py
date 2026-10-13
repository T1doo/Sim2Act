"""Compare source bytes and actual XML nodes across the two completed runs."""
import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REVIEW = ROOT.parent / 'independent/final'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def nodes(path):
    root = ET.parse(path).getroot()
    result = {}
    for case in root.findall('.//testcase'):
        key = case.attrib['classname'].replace('.', '/') + '.py::' + case.attrib['name']
        status = ('FAIL' if case.find('failure') is not None else 'ERROR' if case.find('error') is not None
                  else 'SKIP' if case.find('skipped') is not None else 'PASS')
        assert key not in result, key
        result[key] = status
    return result

author = json.loads((ROOT / 'final-source-after.json').read_text())
independent = json.loads((REVIEW / 'source-after.json').read_text())
review_files = {key: value['sha256'] for key, value in independent['files_and_links'].items()}
assert author['head'] == independent['head'] == '82717272e61c2fa174ad8772e54cd9e9eb947c49'
assert author['files'] == review_files and len(review_files) == 434
an = nodes(ROOT / 'final.xml')
sn = nodes(REVIEW / 'selected.xml')
en = nodes(REVIEW / 'extra.xml')
gn = nodes(REVIEW / 'extra-graph.xml')
assert not set(sn) & set(en) and not (set(sn) | set(en)) & set(gn)
all_review = {**sn, **en, **gn}
value = dict(frozen_head=author['head'], source_entries=434, source_differences=0,
             author_after_sha256=sha(ROOT / 'final-source-after.json'),
             independent_after_sha256=sha(REVIEW / 'source-after.json'),
             author_unique=len(an), independent_unique=len(all_review),
             overlapping_nodeids=sorted(set(an) & set(all_review)),
             independent_only_nodeids=sorted(set(all_review) - set(an)),
             author_xml_sha256=sha(ROOT / 'final.xml'),
             independent_xml_sha256={p:sha(REVIEW / p) for p in ['selected.xml','extra.xml','extra-graph.xml']},
             counts_are_separate='Never add review passes to the author denominator; some different node IDs also cover related behaviour.')
(ROOT / 'author-independent-source-bridge.json').write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')
print(json.dumps({k:v for k,v in value.items() if k not in ['overlapping_nodeids','independent_xml_sha256']},indent=2))
print('actual_overlap',len(value['overlapping_nodeids']))
