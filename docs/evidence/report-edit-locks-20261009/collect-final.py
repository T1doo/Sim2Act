from pathlib import Path
import shutil,json,xml.etree.ElementTree as ET,hashlib
r=Path('/tmp/sim2act-report-edit-locks-20261009');dst=Path('docs/evidence/report-edit-locks-20261009')
freeze=json.loads((r/'source-freeze-final.json').read_text());summary={'source_sha':freeze['source_sha'],'source_files':len(freeze['files']),'source_bytes_unchanged':True,'LIVE':0,'backends':{}}
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==v for p,v in freeze['files'].items())
for kind in ('sqlite','pg'):
 assert (r/(kind+'-final.exit')).read_text().strip()=='0'
 suite=ET.parse(r/(kind+'-final.xml')).getroot().find('testsuite')
 info={k:int(suite.get(k)) for k in ('tests','failures','errors','skipped')};info['passed']=info['tests']-info['failures']-info['errors']-info['skipped'];info['pytest_seconds']=float(suite.get('time'));info['run']=json.loads((r/(kind+'-final-run.json')).read_text());info['skips']=[{'name':tc.get('name'),'reason':tc.find('skipped').get('message')} for tc in suite.findall('testcase') if tc.find('skipped') is not None];info['pages']=[];info['upgrades']=[]
 for p in (r/(kind+'-final')).iterdir():
  if not p.is_dir() or p.is_symlink():continue
  if (p/'results.json').exists():
   proof=json.loads((p/'results.json').read_text());assert proof['status']=='PASS'
   hashes=proof.get('loaded_source_sha256',proof.get('hashes',{}))
   assert hashes and all(hashlib.sha256((Path('src/sim2act/web')/name).read_bytes()).hexdigest()==v for name,v in hashes.items())
   info['pages'].append({'directory':p.name,'checks':len(proof['checks']),'hashes_matched_final':True,'loaded_files':len(hashes)})
  if (p/'upgrade-proof.json').exists():info['upgrades'].append({'directory':p.name,'proof':'upgrade-proof.json'})
  for filename in ('results.json','info.json','driver.log','child.log','upgrade-proof.json','old-source-proof.json','old-report-lock-proof.json'):
   source=p/filename
   if source.exists():
    target=dst/kind/p.name;target.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target/filename)
 for suffix in ('.log','.xml','.exit','-command.json','-run.json'):
  source=r/(kind+'-final'+suffix);shutil.copy2(source,dst/source.name)
 info['page_cases']=len(info['pages']);info['page_checks']=sum(p['checks'] for p in info['pages']);info['upgrade_cases']=len(info['upgrades']);assert info['tests']==85 and info['page_cases']==10 and info['page_checks']==178 and info['upgrade_cases']==3
 summary['backends'][kind]=info
(dst/'test-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({k:{f:v[f] for f in ('passed','skipped','page_cases','page_checks','upgrade_cases','pytest_seconds')} for k,v in summary['backends'].items()},indent=2))
