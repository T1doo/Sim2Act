from pathlib import Path
import os,json,hashlib,subprocess,xml.etree.ElementTree as ET
root=Path(__file__).resolve().parent
repo=Path('/workspace/Sim2Act-pa-provider')
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def entries(base, names=None):
 values={}
 dirs=names or ['src','tests']
 for name in dirs:
  start=base/name
  for folder,ds,fs in os.walk(start,followlinks=False):
   ds[:]=sorted(d for d in ds if d!='__pycache__')
   for n in ds+sorted(fs):
    p=Path(folder)/n
    if p.is_symlink():values[p.relative_to(base).as_posix()]={'type':'symlink','target':os.readlink(p)}
   for n in sorted(fs):
    p=Path(folder)/n
    if not p.is_symlink() and p.is_file() and not n.endswith('.pyc'):
     values[p.relative_to(base).as_posix()]={'type':'file','bytes':p.stat().st_size,'sha256':sha(p)}
 if names is None:
  p=base/'pyproject.toml';values['pyproject.toml']={'type':'file','bytes':p.stat().st_size,'sha256':sha(p)}
 return dict(sorted(values.items()))
def dump(name,obj):
 p=root/name;p.write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n');return sha(p)
def junit(p):
 tree=ET.parse(p);items=[]
 for e in tree.iter('testcase'):
  if not e.get('name'):continue
  state='ERROR' if e.find('error') is not None else 'FAIL' if e.find('failure') is not None else 'SKIP' if e.find('skipped') is not None else 'PASS'
  items.append(dict(classname=e.get('classname'),name=e.get('name'),state=state,seconds=float(e.get('time','0'))))
 ids=[(x['classname'],x['name']) for x in items];assert len(ids)==len(set(ids))
 return {'named_unique':len(items),'counts':{s:sum(x['state']==s for x in items) for s in ['PASS','FAIL','ERROR','SKIP']},'nodes':items,'xml_sha256':sha(p)}
selected=junit(root/'selected.xml');extra=junit(root/'extra.xml');extra_graph=junit(root/'extra-graph.xml')
combined=selected['nodes']+extra['nodes']+extra_graph['nodes'];assert len(combined)==len({(x['classname'],x['name']) for x in combined})
before=json.loads((root/'source-before.json').read_text());after=entries(repo)
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip();branch=subprocess.check_output(['git','branch','--show-current'],cwd=repo,text=True).strip()
diffs=[{'path':k,'before':before['files_and_links'].get(k),'after':after.get(k)} for k in sorted(set(after)|set(before['files_and_links'])) if after.get(k)!=before['files_and_links'].get(k)]
aftersha=dump('source-after.json',{'head':head,'branch':branch,'entries':len(after),'scope':before['scope'],'files_and_links':after})
ui=[]
for d in sorted((root/'selected-fixtures').iterdir()):
 if d.is_symlink() or not d.is_dir():continue
 p=d/'results.json'
 if not p.is_file():continue
 value=json.loads(p.read_text());hashes=value.get('loaded_source_sha256',{})
 mismatches=[]
 for key,want in hashes.items():
  key=key.split('?')[0]
  rel='src/sim2act/web/'+key.removeprefix('/').removeprefix('static/')
  expected=before['files_and_links'].get(rel)
  if expected is None or expected['sha256']!=want:mismatches.append({'asset':key,'reported':want,'frozen':expected})
 ui.append({'file':str(p),'sha256':sha(p),'scenario':value.get('scenario'),'status':value.get('status'),'checks':len(value.get('checks',[])),'check_labels':value.get('checks',[]),'assets':len(hashes),'asset_hashes':hashes,'asset_mismatches':mismatches,'posts':sum(r.get('method')=='POST' for r in value.get('requests',[])),'browser':value.get('browser'),'api':value.get('api')})
processes=[]
for line in subprocess.check_output(['ps','-eo','pid,ppid,args'],text=True).splitlines()[1:]:
 cols=line.strip().split(None,2)
 if len(cols)==3 and str(root) in cols[2] and any(x in cols[2] for x in ('-m pytest','node tests/','run_selected.py','run_extra.py','run_extra_graph.py')):
  processes.append({'pid':int(cols[0]),'ppid':int(cols[1]),'args':cols[2]})
result={'selected':selected,'extra':extra,'extra_graph':extra_graph,'combined_unique':len(combined),'combined_counts':{s:sum(x['state']==s for x in combined) for s in ['PASS','FAIL','ERROR','SKIP']},'selected_exit':json.loads((root/'selected-exit.json').read_text()),'extra_exit':json.loads((root/'extra-exit.json').read_text()),'extra_graph_exit':json.loads((root/'extra-graph-exit.json').read_text()),'source':{'before_sha256':sha(root/'source-before.json'),'after_sha256':aftersha,'entries_before':before['entries'],'entries_after':len(after),'head_before':before['head'],'head_after':head,'branch_before':before['branch'],'branch_after':branch,'differences':diffs},'ui':ui,'own_active_processes':processes,'overlap':json.loads((root/'author-overlap.json').read_text())}
dump('final-result.json',result)
print(json.dumps({'combined_unique':result['combined_unique'],'counts':result['combined_counts'],'source_entries':len(after),'source_differences':len(diffs),'own_active_processes':len(processes),'ui':[{k:x[k] for k in ['scenario','status','checks','assets']} for x in ui]}))
