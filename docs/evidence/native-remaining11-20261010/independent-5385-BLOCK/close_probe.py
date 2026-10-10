import pathlib,json,subprocess,hashlib,sys,runpy,os,copy,ast
R=pathlib.Path('/tmp/sim2act-native-remaining11-independent-5385-20261010');REPO=pathlib.Path('/workspace/Sim2Act');SHA='5385ac9293737cca8ed5dfeec990b760b240bf63';OLD='d49aab3e8023b3bf47a7f66577e557d2874c24ae';PLUGIN=REPO/'scripts/native_pytest_diagnostics.py';a=runpy.run_path(str(PLUGIN));nodes=a['remaining11_nodes']();manifest=json.loads(pathlib.Path('/tmp/sim2act-native-remaining11-20261010/source-freeze.json').read_text())['files']
def freeze(label):
 actual={p:hashlib.sha256((REPO/p).read_bytes()).hexdigest() for p in manifest};git={p:hashlib.sha256(subprocess.check_output(['git','show',SHA+':'+p],cwd=REPO)).hexdigest() for p in manifest};assert len(actual)==363 and actual==git==manifest and subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()==SHA;(R/('source-'+label+'.json')).write_text(json.dumps({'source_sha':SHA,'count':363,'all_match':True,'files':actual},indent=2));return actual
before=freeze('before');base=[json.loads(line) for line in (R/'actual-Recorder.jsonl').read_text().splitlines()];results=[];env={**os.environ};env.pop('GITHUB_STEP_SUMMARY',None)
for name in ['missingselection','missingfull','wronghash','wrongcount','skip','interrupt','partialtail','wrongscope','foreignpid','duplicatephase','extranodephase','outoforder']:
 records=copy.deepcopy(base)
 if name=='missingselection':records=[r for r in records if r['event']!='selection']
 if name=='missingfull':records=[r for r in records if r['event']!='full_collection']
 if name=='wronghash':next(r for r in records if r['event']=='selection')['full_nodes_sha256']='0'*64
 if name=='wrongcount':next(r for r in records if r['event']=='selection')['full_count']=22234
 if name=='skip':next(r for r in records if r['event']=='node_report')['outcome']='skipped'
 if name=='interrupt':records[-1]['exitstatus']=2
 if name=='wrongscope':next(r for r in records if r['event']=='selection')['scope']='FULL_ENGINEERING'
 if name=='foreignpid':records[5]['pid']+=1
 if name=='duplicatephase':records.insert(-1,copy.deepcopy(next(r for r in records if r['event']=='node_report')))
 if name=='extranodephase':extra=copy.deepcopy(next(r for r in records if r['event']=='node_report'));extra['nodeid']='foreign-node';records.insert(-1,extra)
 if name=='outoforder':i=next(i for i,r in enumerate(records) if r['event']=='node_start');j=next(i for i,r in enumerate(records) if r['event']=='node_finish');records[i],records[j]=records[j],records[i]
 p=R/(name+'.jsonl');p.write_text(''.join(json.dumps(r)+'\n' for r in records)+('{"event":' if name=='partialtail' else ''));o=subprocess.run([sys.executable,str(PLUGIN),'--report',str(p),'--junit',str(R/'missing.xml')],env=env,capture_output=True,text=True);(R/(name+'-Report.log')).write_text(o.stdout+o.stderr);s=a['summarize'](p);(R/(name+'-summary.json')).write_text(json.dumps(s,indent=2));results.append({'case':name,'actual_Report_exit':o.returncode,'complete':s['required_targets_complete'],'scope':s['scope'],'pass':o.returncode!=0})
after=freeze('after');assert before==after;changed=subprocess.check_output(['git','diff','--name-only',OLD,SHA],cwd=REPO,text=True).splitlines();assert set(changed)=={'scripts/native_pytest_diagnostics.py','tests/test_native_pytest_diagnostics.py'}
for p,h in before.items():
 if p not in changed:assert hashlib.sha256(subprocess.check_output(['git','show',OLD+':'+p],cwd=REPO)).hexdigest()==h
src={p:h for p,h in before.items() if p.startswith('src/')};assert len(src)==69
for p,h in src.items():assert hashlib.sha256(subprocess.check_output(['git','show','47388f573746daa27f8d5790ca358eef91378ad5:'+p],cwd=REPO)).hexdigest()==h
oldsource=subprocess.check_output(['git','show',OLD+':scripts/native_pytest_diagnostics.py'],cwd=REPO,text=True);oldfuncs={n.name:ast.dump(n,include_attributes=False) for n in ast.parse(oldsource).body if isinstance(n,(ast.ClassDef,ast.FunctionDef))};newfuncs={n.name:ast.dump(n,include_attributes=False) for n in ast.parse(PLUGIN.read_text()).body if isinstance(n,(ast.ClassDef,ast.FunctionDef))};assert {k:v for k,v in oldfuncs.items() if k!='summarize'}=={k:v for k,v in newfuncs.items() if k!='summarize'};(R/'byte-bridge.json').write_text(json.dumps({'SHA':SHA,'old':OLD,'unchanged_frozen_count':361,'products_same473':69,'only_summarize_AST_changes':True,'before_after_match':True},indent=2));(R/'close-results.json').write_text(json.dumps(results,indent=2));print(json.dumps({'correctly_refused':sum(r['pass'] for r in results),'still_false_pass':sum(not r['pass'] for r in results),'363match':True,'361unchanged':True}))
