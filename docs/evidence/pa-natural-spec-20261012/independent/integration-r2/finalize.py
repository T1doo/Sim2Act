from pathlib import Path
import os,json,hashlib,subprocess,ast,xml.etree.ElementTree as ET
p=Path(__file__).resolve().parent;repo=Path('/workspace/Sim2Act-pa-provider')
def sha(f):return hashlib.sha256(f.read_bytes()).hexdigest()
def dump(n,x):q=p/n;q.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n');return sha(q)
def xml(n):
 root=ET.parse(p/n);rows=[]
 for x in root.iter('testcase'):
  if not x.get('name'):continue
  state='ERROR' if x.find('error') is not None else 'FAIL' if x.find('failure') is not None else 'SKIP' if x.find('skipped') is not None else 'PASS'
  rows.append({'classname':x.get('classname'),'name':x.get('name'),'state':state,'seconds':float(x.get('time','0'))})
 assert len(rows)==len({(r['classname'],r['name']) for r in rows})
 return {'xml':n,'sha256':sha(p/n),'unique':len(rows),'counts':{s:sum(r['state']==s for r in rows) for s in ['PASS','FAIL','ERROR','SKIP']},'nodes':rows,'suite_attributes':next(root.iter('testsuite')).attrib}
selected=xml('selected.xml');extra=xml('extra.xml');assert selected['unique']==36 and extra['unique']==2
combined=selected['nodes']+extra['nodes'];assert len(combined)==len({(r['classname'],r['name']) for r in combined})==38
expected=set(json.loads((p/'collection-exit.json').read_text())['nodes']);actual={x['classname'].replace('.','/')+'.py::'+x['name'] for x in selected['nodes']};assert actual==expected
entries={}
for foldername in ['src','tests']:
 for folder,dirs,files in os.walk(repo/foldername,followlinks=False):
  dirs[:]=sorted(d for d in dirs if d!='__pycache__')
  for n in dirs+sorted(files):
   f=Path(folder)/n
   if f.is_symlink():entries[f.relative_to(repo).as_posix()]={'type':'symlink','target':os.readlink(f)}
  for n in sorted(files):
   f=Path(folder)/n
   if f.is_file() and not f.is_symlink() and not n.endswith('.pyc'):entries[f.relative_to(repo).as_posix()]={'type':'file','bytes':f.stat().st_size,'sha256':sha(f)}
f=repo/'pyproject.toml';entries['pyproject.toml']={'type':'file','bytes':f.stat().st_size,'sha256':sha(f)}
before=json.loads((p/'source-before.json').read_text());head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip();branch=subprocess.check_output(['git','branch','--show-current'],cwd=repo,text=True).strip()
after={'head':head,'branch':branch,'entries':len(entries),'scope':before['scope'],'files_and_links':dict(sorted(entries.items()))};dump('source-after.json',after)
diffs=[k for k in sorted(set(entries)|set(before['files_and_links'])) if entries.get(k)!=before['files_and_links'].get(k)]
# Exact qualification calculation, independent of calling known().
source=(repo/'src/sim2act/text_continuations.py').read_bytes();tree=ast.parse(source)
def constant(t,n):return ast.literal_eval(next(x.value for x in t.body if isinstance(x,ast.Assign) and any(isinstance(y,ast.Name) and y.id==n for y in x.targets)))
pin=constant(tree,'QUALIFICATION_HASH');proofraw=(repo/'src/sim2act/text_software_qualification.json').read_bytes();proof=json.loads(proofraw)
rawmap={f.name:sha(f) for f in (repo/'src/sim2act').glob('*.py') if f.name!='config.py'};norm=dict(rawmap);literal=('QUALIFICATION_HASH = "'+pin+'"').encode();assert source.count(literal)==1;norm['text_continuations.py']=hashlib.sha256(source.replace(literal,('QUALIFICATION_HASH = "'+'0'*64+'"').encode())).hexdigest()
oldtree=ast.parse(subprocess.check_output(['git','show','82717272e61c2fa174ad8772e54cd9e9eb947c49:src/sim2act/text_continuations.py'],cwd=repo));anchor=(repo/'src/sim2act/text_software_anchors.json').read_bytes();oldanchor=subprocess.check_output(['git','show','82717272e61c2fa174ad8772e54cd9e9eb947c49:src/sim2act/text_software_anchors.json'],cwd=repo)
q={'implementation_files':len(rawmap),'qualification_sha256':hashlib.sha256(proofraw).hexdigest(),'sole_pin':pin,'exact_map_match':norm==proof['files'],'baseline':proof['review_baseline'],'candidate':proof['review_candidate'],'anchor_bytes_unchanged':anchor==oldanchor,'ANCHOR_HASH_unchanged':constant(tree,'ANCHOR_HASH')==constant(oldtree,'ANCHOR_HASH'),'CHANGED_unchanged':constant(tree,'CHANGED')==constant(oldtree,'CHANGED'),'original_sources':proof['sources'],'actual_raw_map':rawmap,'normalized_exact_map':norm};assert q['implementation_files']==73 and q['qualification_sha256']==pin and q['exact_map_match'] and q['anchor_bytes_unchanged'] and q['CHANGED_unchanged'] and q['ANCHOR_HASH_unchanged'];dump('qualification-static.json',q)
ui=[]
for d in sorted((p/'selected-fixtures').iterdir()):
 if d.is_symlink() or not d.is_dir() or not (d/'results.json').is_file():continue
 f=d/'results.json';v=json.loads(f.read_text());m=[]
 for key,want in v.get('loaded_source_sha256',{}).items():
  rel='src/sim2act/web/'+key.split('?')[0].removeprefix('/').removeprefix('static/');row=entries.get(rel)
  if row is None or row['sha256']!=want:m.append({'asset':key,'reported':want,'frozen':row})
 ui.append({'scenario':v['scenario'],'status':v['status'],'checks':len(v['checks']),'assets':len(v['loaded_source_sha256']),'asset_mismatches':m,'raw_file':str(f),'raw_sha256':sha(f),'labels':v['checks']})
extras=[]
for d in sorted((p/'extra-fixtures').iterdir()):
 if d.is_symlink() or not d.is_dir() or not (d/'queue-cas-proof.json').is_file():continue
 f=d/'queue-cas-proof.json';v=json.loads(f.read_text());extras.append({'file':str(f),'sha256':sha(f),'mode':v['mode'],'calibration_cells':len(v['calibration']['evaluated']),'product_private_cells':len(v['product']['evaluated']),'product_blocked':len(v['product']['blocked']),'durable':v['durable'],'actual_injection_timing':'before_cursor_execute of AppRun UPDATE, after header read and before AppRun/Run writes; raw injected_after_app_update label is imprecise and preserved','rejection':v.get('rejection')})
authorcmd=Path('/workspace/pa-natural-spec-runtime-evidence-20261012/author/final-r2-command.json');authorargs=json.loads(authorcmd.read_text())['args'];scopes=[x for x in authorargs if x.startswith('tests/')];overlap=sorted(n for n in expected if any(n==s or n.startswith(s+'::') for s in scopes));assert len(overlap)==34
active=[]
for line in subprocess.check_output(['ps','-eo','pid,ppid,args'],text=True).splitlines()[1:]:
 a=line.strip().split(None,2)
 if len(a)==3 and str(p) in a[2] and any(k in a[2] for k in ['-m pytest','node tests/','run_selected.py','run_extra.py']):active.append({'pid':int(a[0]),'ppid':int(a[1]),'args':a[2]})
old=Path('/workspace/pa-natural-spec-runtime-evidence-20261012/independent/final');olds={'report_sha256':sha(old/'FINAL_REVIEW.md'),'manifest_sha256':sha(old/'manifest.json'),'unchanged':sha(old/'FINAL_REVIEW.md')=='fbdeb56a402892e5f41e32cd2f6e1c835c5d7af820bbbb5dba767303c29d08ed' and sha(old/'manifest.json')=='61d01922f4051611736a8b275d2ae83fb9d89f6ab5bb38d471b335c6a3c78a04'}
r={'head':head,'branch':branch,'selected':selected,'extra':extra,'unique':len(combined),'counts':{s:sum(x['state']==s for x in combined) for s in ['PASS','FAIL','ERROR','SKIP']},'selected_exit':json.loads((p/'selected-exit.json').read_text()),'extra_exit':json.loads((p/'extra-exit.json').read_text()),'source':{'before_sha256':sha(p/'source-before.json'),'after_sha256':sha(p/'source-after.json'),'entries':len(entries),'differences':diffs,'head_unchanged':head==before['head'],'branch_unchanged':branch==before['branch']},'ui':ui,'independent_probes':extras,'author_overlap':{'basis':'scope membership in actual saved current author command; no inference of author current test outcome','command_sha256':sha(authorcmd),'shared_selected_nodes':len(overlap),'shared_nodes':overlap,'selected_not_author':sorted(expected-set(overlap)),'extra_independent_nodes':2},'old827_sealed_report':olds,'own_active_test_processes':active}
dump('review-result.json',r)
assert r['counts']=={'PASS':38,'FAIL':0,'ERROR':0,'SKIP':0} and not diffs and not active and olds['unchanged'] and len(ui)==5 and len(extras)==2
assert all(x['status']=='PASS' and not x['asset_mismatches'] for x in ui)
print(json.dumps({'unique':r['unique'],'counts':r['counts'],'source':r['source'],'own_active':len(active),'UI':[{k:x[k] for k in ['scenario','checks','assets','status']} for x in ui],'qualification_pin':pin,'old_sealed_unchanged':olds['unchanged']}))
