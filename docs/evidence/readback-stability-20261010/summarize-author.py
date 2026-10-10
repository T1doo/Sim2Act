import json,xml.etree.ElementTree as E
from pathlib import Path
r=Path('/tmp/sim2act-read-stability-20261010');out={}
for k in ['sqlite','pg']:
 cases=list(E.parse(r/(k+'.xml')).getroot().iter('testcase'));ui=[json.loads(p.read_text()) for p in sorted((r/k).rglob('results.json'))]
 out[k]={'run':json.loads((r/(k+'-run.json')).read_text()),'collected_nodes':len(cases),'PASS':sum(c.find('skipped') is None and c.find('failure') is None and c.find('error') is None for c in cases),'SKIP':[dict(c.attrib,reason=c.find('skipped').attrib) for c in cases if c.find('skipped') is not None],'FAIL':[c.attrib for c in cases if c.find('failure') is not None or c.find('error') is not None],'UI_results':len(ui),'UI_named_checks':sum(len(d['checks']) for d in ui),'old_source_upgrade_proofs':len(list((r/k).rglob('upgrade-proof.json'))),'all_UI_status_PASS':all(d['status']=='PASS' for d in ui),'actual_models':0,'raw_waits_and_observer_unchanged':True}
 assert out[k]['collected_nodes']==59 and out[k]['run']['exit']==0 and out[k]['run']['byte_match'] and not out[k]['FAIL']
(r/'author-summary.json').write_text(json.dumps(out,indent=2)+'\n');print({k:{key:v[key] for key in ['collected_nodes','PASS','UI_results','UI_named_checks','old_source_upgrade_proofs','all_UI_status_PASS']} for k,v in out.items()})
