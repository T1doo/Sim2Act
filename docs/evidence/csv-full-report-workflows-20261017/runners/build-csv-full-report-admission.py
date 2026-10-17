import json,hashlib
from pathlib import Path
from xml.etree import ElementTree as E
out=Path('/workspace/csv-full-report-evidence-20261017')
base='4a4a228f09203e08103904e3afdd04b12708a98b';refine='436c49cb8c2ac04489fd9dfd4baaf09bffea0298'
def cases(path):
 return {c.attrib['classname']+'::'+c.attrib['name']:{'status':'FAIL' if c.find('failure') is not None else 'ERROR' if c.find('error') is not None else 'SKIP' if c.find('skipped') is not None else 'PASS','seconds':float(c.attrib.get('time',0))}for c in E.parse(path).getroot().iter('testcase')}
a=cases(out/'author22.xml');b=cases(out/'author-refine2.xml');assert len(a)==22 and len(b)==2
admitted={k:{**v,'sha':base,'junit':'author22.xml'}for k,v in a.items()if v['status']=='PASS'}
for k,v in b.items():assert v['status']=='PASS';admitted[k]={**v,'sha':refine,'junit':'author-refine2.xml'}
assert len(admitted)==22
pages=[]
for case,index in [('deliver',0),('lost',1),('misbound',0),('navigation',3),('revoked-source',4)]:
 root=Path('/tmp/csv-full-report-author-'+('436c49cb' if case=='misbound'else'4a4a228f')+'-20261017')
 p=root/f'test_visible_complete_report_d{index}'/'page-result.json';v=json.loads(p.read_text());assert v['status']=='PASS' and v['case']==case
 replies=[r for r in v['requests']if isinstance(r.get('status'),int)];hist={}
 for r in replies:hist[str(r['status'])]=hist.get(str(r['status']),0)+1
 pages.append(dict(case=case,path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),checks=len(v['checks']),issued_requests=len(v['requests']),actual_replies=len(replies),status_counts=hist,assets=len(v['assets']),diagnostics=v.get('diagnostics'),models=v.get('real_model_requests')))
result=dict(implementation_sha=base,test_refinement_sha=refine,author_original={'PASS':20,'FAIL':1,'SKIP':1},author_supplement={'PASS':2,'FAIL':0,'SKIP':0},author_admitted_unique=22,author_executions=24,admitted_nodes=admitted,new_page_cases=pages,new_page_totals={'cases':len(pages),'checks':sum(p['checks']for p in pages),'actual_replies':sum(p['actual_replies']for p in pages),'issued_requests':sum(p['issued_requests']for p in pages),'assets':sum(p['assets']for p in pages)},frozen_scope='20 original PASS at implementation SHA +2 supplement PASS at test-only refinement SHA; NOT an all22 run at final HEAD',independent='pending final supplement verdict; initial21PASS1FAIL preserved')
(out/'admission.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in result.items()if k not in('admitted_nodes','new_page_cases')},ensure_ascii=False,indent=2))
