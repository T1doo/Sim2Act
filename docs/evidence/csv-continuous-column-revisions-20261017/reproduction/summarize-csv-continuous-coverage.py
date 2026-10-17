import json,re,xml.etree.ElementTree as ET
from pathlib import Path
raw=Path('/workspace/csv-continuous-column-evidence-20261017')
d74='d74f2fed55b6067e5d3c34ca6e4348b92e75f48a';b589='b589809375c89b4d93617d91c780a1e0f7f704e2'
batches=[('author-d74-regressions',d74,raw/'author-d74-regressions/junit.xml'),('independent-d74-api',d74,Path('/tmp/f2-csv-continuous-d74f-independent/junit.xml')),('independent-d74-pages',d74,Path('/tmp/csv-column-independent-d74f2fed-20261017/junit.xml')),('author-b589-byte-verified-upgrade-candidate',b589,raw/'author-upgrade-candidate/junit.xml'),('author-b589-old-pages',b589,raw/'author-b589-old-pages/junit.xml'),('independent-b589-upgrade-and-receipt',b589,Path('/tmp/csv-upgrade-independent-b5898093-20261017/junit.xml')),('independent-b589-next-and-navigation',b589,Path('/tmp/csv-continuous-independent-b5898093-g3l0xk_b/evidence/junit.xml'))]
def cases(path):
 return [dict(id=x.attrib['classname'].split('.')[-1]+'::'+x.attrib['name'],seconds=x.attrib['time'],failure=[z.text for z in x.findall('failure')],error=[z.text for z in x.findall('error')],skip=bool(x.findall('skipped'))) for x in ET.parse(path).iter('testcase')]
results=[]
for name,sha,path in batches:
 c=cases(path);assert c and not any(x['failure'] or x['error'] or x['skip'] for x in c),(name,c)
 results.append(dict(name=name,source_sha=sha,junit=str(path),calls=len(c),passes=len(c),cases=c))
allcases=[x for r in results for x in r['cases']];unique={x['id'] for x in allcases}
expected=set()
for line in (raw/'final-collection.log').read_text().splitlines():
 if line.startswith('tests/') and '::' in line:
  module,name=line.split('::',1);expected.add(Path(module).stem+'::'+name)
assert len(expected)==32 and unique==expected,(expected-unique,unique-expected)
assert len(allcases)==39
wip=[]
for name in ('dev-first','dev-second','dev-api','dev-browser','dev-negative'):
 c=cases(raw/(name+'.xml'));wip.append(dict(name=name,source='unfrozen development WIP; not final frozen-batch claims',junit=str(raw/(name+'.xml')),calls=len(c),passes=sum(not(x['failure'] or x['error'] or x['skip']) for x in c),failures=sum(bool(x['failure'] or x['error']) for x in c),cases=c))
assert sum(x['calls'] for x in wip)==10 and sum(x['failures'] for x in wip)==2
bysha={sha:dict(calls=sum(r['calls'] for r in results if r['source_sha']==sha),unique_cases=len({c['id'] for r in results if r['source_sha']==sha for c in r['cases']})) for sha in (d74,b589)}
report=dict(status='PASS_BOUNDED',formal_calls=39,formal_passes=39,formal_failures=0,formal_skips=0,unique_test_ids=32,by_sha=bysha,batches=results,development_calls=10,development_passes=8,development_failures=2,development=wip,all_unique_ids=sorted(unique),limitations=['32 is the union of documented source batches, not a claim of one final-SHA full run.','same-navigation uses current registry at d74; at b589 it additionally verifies synthetic prior registry, actual stale409 and lost derive201 recovery.','No real model, Windows, PG, native browser, remote CI, deployment or real semantic acceptance.','Actual ce3 binary upgrade and v3-to-v4/spec8 chain not run.'])
(raw/'coverage-summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in report.items() if k not in ('batches','development','all_unique_ids')},indent=2))
