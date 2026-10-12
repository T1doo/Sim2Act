from pathlib import Path
import xml.etree.ElementTree as ET,json,hashlib
base=Path('/tmp/pa-spec-checklist-author-20261012')
ind=Path('/tmp/pa-spec-checklist-independent-20261012/dynamic-final-a396-20261012')
def junit(path):
    root=ET.parse(path).getroot();out={}
    for case in root.iter('testcase'):
        key=case.attrib.get('classname','')+'::'+case.attrib.get('name','')
        if not case.attrib.get('classname'):continue
        verdict='FAIL' if case.find('failure') is not None else 'ERROR' if case.find('error') is not None else 'SKIP' if case.find('skipped') is not None else 'PASS'
        assert key not in out,key
        out[key]=verdict
    return dict(entries=out,counts={v:list(out.values()).count(v) for v in ['PASS','FAIL','ERROR','SKIP']})
author=junit(base/'final-r4.xml')
independent={}
for path in [ind/'extra.xml',ind.parent/'dynamic-final-a396-r2-20261012'/'selected.xml']:
    group=junit(path);independent[str(path.relative_to(ind.parent))]=group
flat={}
for group in independent.values():
    for key,value in group['entries'].items():
        assert key not in flat,key
        flat[key]=value
ui=[]
for path in sorted((base/'final-r4-fixtures').rglob('results.json')):
    if 'test_spec_page_actual' not in str(path):continue
    result=json.loads(path.read_text())
    ui.append(dict(path=str(path.relative_to(base)),status=result.get('status'),checks=len(result.get('checks',[])),assets=len(result.get('loaded_source_sha256',{})),sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
result=dict(author=author,independent_groups=independent,independent_unique={v:list(flat.values()).count(v) for v in ['PASS','FAIL','ERROR','SKIP']},author_independent_overlap=sorted(set(flat)&set(author['entries'])),independent_extra=sorted(set(flat)-set(author['entries'])),page_results=ui)
(base/'final-aggregate.json').write_text(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ['author','independent_groups','author_independent_overlap','independent_extra']},indent=2));print('author',author['counts'],'independent groups',{k:v['counts'] for k,v in independent.items()},'overlap',len(result['author_independent_overlap']),'extra',len(result['independent_extra']))
