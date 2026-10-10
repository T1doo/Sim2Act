import pathlib,json,hashlib,subprocess,sys,os,runpy,copy,contextlib,ast,types
R=pathlib.Path('/tmp/sim2act-native-remaining11-independent-180a-20261010');REPO=pathlib.Path('/workspace/Sim2Act');SHA='180a4710405b9c06d1e7cc7213b3ffd073d05567';OLD='5385ac9293737cca8ed5dfeec990b760b240bf63';PLUGIN=REPO/'scripts/native_pytest_diagnostics.py';a=runpy.run_path(str(PLUGIN));m=json.loads(pathlib.Path('/tmp/sim2act-native-remaining11-20261010/source-freeze.json').read_text())['files']
def freeze(label):
 actual={p:hashlib.sha256((REPO/p).read_bytes()).hexdigest() for p in m};git={p:hashlib.sha256(subprocess.check_output(['git','show',SHA+':'+p],cwd=REPO)).hexdigest() for p in m};assert len(actual)==363 and actual==git==m and subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()==SHA;(R/('source-'+label+'.json')).write_text(json.dumps({'source_sha':SHA,'count':363,'all_match':True,'files':actual},indent=2));return actual
before=freeze('before');nodes=a['remaining11_nodes']();rec=a['Recorder'](R/'Recorder-hook-trace.jsonl',nodes);items=[types.SimpleNamespace(nodeid=n) for n in ['ordinary-extra-node']+list(reversed(nodes))];deselected=[];cfg=types.SimpleNamespace(hook=types.SimpleNamespace(pytest_deselected=lambda items:deselected.extend(items)));session=types.SimpleNamespace(items=items)
# Exercise the actual Recorder lifecycle hooks with bounded synthetic reports.
with (R/'Recorder-hook-stdout.log').open('w') as s,contextlib.redirect_stdout(s):
 rec.pytest_sessionstart(session);rec.pytest_collection_modifyitems(session,cfg,items);rec.pytest_collection_finish(session)
 for item in session.items:
  rec.pytest_runtest_logstart(item.nodeid,('own-material.py',0,item.nodeid))
  for phase in ['setup','call','teardown']:rec.pytest_runtest_logreport(types.SimpleNamespace(nodeid=item.nodeid,when=phase,outcome='passed',failed=False,duration=0.001))
  rec.pytest_runtest_logfinish(item.nodeid,None)
 rec.pytest_sessionfinish(session,0)
assert [i.nodeid for i in session.items]==nodes and [i.nodeid for i in deselected]==['ordinary-extra-node'];base=[json.loads(line) for line in (R/'Recorder-hook-trace.jsonl').read_text().splitlines()];assert sum(r['event']=='node_report' for r in base)==33 and sum(r['event']=='node_finish' for r in base)==11
results=[];env={**os.environ};env.pop('GITHUB_STEP_SUMMARY',None)
names=['valid','missingselection','missingfull','wronghash','wrongcount','foreignstart','foreignfinish','wrongrequestevent','extranonrequestedsession','extranodephase','outoforder','wholeforeign11','skip','interrupt','partialtail','foreignpid','wrongscope']
for name in names:
 rs=copy.deepcopy(base)
 if name=='missingselection':rs=[r for r in rs if r['event']!='selection']
 if name=='missingfull':rs=[r for r in rs if r['event']!='full_collection']
 if name=='wronghash':next(r for r in rs if r['event']=='selection')['full_nodes_sha256']='0'*64
 if name=='wrongcount':next(r for r in rs if r['event']=='selection')['full_count']=22234
 if name=='foreignstart':next(r for r in rs if r['event']=='node_start')['nodeid']='foreign-node'
 if name=='foreignfinish':next(r for r in rs if r['event']=='node_finish')['nodeid']='foreign-node'
 if name=='wrongrequestevent':rs[0]['event']='unexpected_header'
 if name=='extranonrequestedsession':rs.insert(4,dict(event='session_start',pid=rs[0]['pid']))
 if name=='extranodephase':extra=copy.deepcopy(next(r for r in rs if r['event']=='node_report'));extra['nodeid']='foreign-node';rs.insert(-1,extra)
 if name=='outoforder':i=next(i for i,r in enumerate(rs) if r['event']=='node_start');j=next(i for i,r in enumerate(rs) if r['event']=='node_finish');rs[i],rs[j]=rs[j],rs[i]
 if name=='wholeforeign11':
  replacements={n:'foreign-'+str(i) for i,n in enumerate(nodes)}
  for r in rs:
   if 'nodeid' in r:r['nodeid']=replacements.get(r['nodeid'],r['nodeid'])
   for key in ['nodes','required_nodes']:
    if key in r:r[key]=[replacements.get(n,n) for n in r[key]]
  full=next(r for r in rs if r['event']=='full_collection')['nodes'];next(r for r in rs if r['event']=='selection')['full_nodes_sha256']=hashlib.sha256(json.dumps(full).encode()).hexdigest();next(r for r in rs if r['event']=='collection_summary')['nodes_sha256']=hashlib.sha256(json.dumps([replacements[n] for n in nodes]).encode()).hexdigest()
 if name=='skip':next(r for r in rs if r['event']=='node_report' and r['phase']=='call')['outcome']='skipped'
 if name=='interrupt':rs[-1]['exitstatus']=2
 if name=='foreignpid':rs[5]['pid']+=1
 if name=='wrongscope':next(r for r in rs if r['event']=='selection')['scope']='FULL_ENGINEERING'
 folder=R/name;folder.mkdir();p=folder/'events.jsonl';p.write_text(''.join(json.dumps(r)+'\n' for r in rs)+('{"event":' if name=='partialtail' else ''));summary=a['summarize'](p);(folder/'summary.json').write_text(json.dumps(summary,indent=2));o=subprocess.run([sys.executable,str(PLUGIN),'--report',str(p),'--junit',str(folder/'absent.xml')],env={**env,'GITHUB_STEP_SUMMARY':str(folder/'step-summary.md')},capture_output=True,text=True);(folder/'Report.log').write_text(o.stdout+o.stderr);expected=name=='valid';good=(o.returncode==0)==expected and summary['required_targets_complete']==expected;assert good,(name,o.returncode,summary);assert summary['scope']=='DIAGNOSTIC_ONLY_REMAINING11';results.append({'case':name,'status':'PASS','Report_exit':o.returncode,'required_complete':summary['required_targets_complete'],'selection_verified':summary['selection_verified'],'expected_accept':expected})
# Limited regression sensitivity: known two freezes actually false-pass their own old attack types.
for version,case in [('d49aab3e8023b3bf47a7f66577e557d2874c24ae','missingselection'),('5385ac9293737cca8ed5dfeec990b760b240bf63','foreignstart')]:
 path=R/('old-'+version[:4]+'.py');path.write_bytes(subprocess.check_output(['git','show',version+':scripts/native_pytest_diagnostics.py'],cwd=REPO));o=subprocess.run([sys.executable,str(path),'--report',str(R/case/'events.jsonl'),'--junit',str(R/'absent.xml')],env=env,capture_output=True,text=True);(R/('old-'+version[:4]+'-sensitivity.log')).write_text(o.stdout+o.stderr);assert o.returncode==0 and '"required_targets_complete": true' in o.stdout
# The older5385 does not load manifest in summarize; copy no source/manifest and keep this sensitivity bounded.
after=freeze('after');assert after==before;changed=subprocess.check_output(['git','diff','--name-only',OLD,SHA],cwd=REPO,text=True).splitlines();assert set(changed)=={'scripts/native_pytest_diagnostics.py','tests/test_native_pytest_diagnostics.py'}
for p,h in before.items():
 if p not in changed:assert hashlib.sha256(subprocess.check_output(['git','show',OLD+':'+p],cwd=REPO)).hexdigest()==h
src={p:h for p,h in before.items() if p.startswith('src/')};assert len(src)==69
for p,h in src.items():assert hashlib.sha256(subprocess.check_output(['git','show','47388f573746daa27f8d5790ca358eef91378ad5:'+p],cwd=REPO)).hexdigest()==h
oldsrc=subprocess.check_output(['git','show',OLD+':scripts/native_pytest_diagnostics.py'],cwd=REPO,text=True);functions=lambda t:{n.name:ast.dump(n,include_attributes=False) for n in ast.parse(t).body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name!='summarize'};assert functions(oldsrc)==functions(PLUGIN.read_text());(R/'byte-bridge.json').write_text(json.dumps({'source_sha':SHA,'base':OLD,'unchanged_frozen':361,'products_same473':69,'other_diagnostic_AST_identical':True,'363before_after_match':True},indent=2));(R/'results.json').write_text(json.dumps({'source_sha':SHA,'Report_cases':results,'Report_case_count':17,'old_sensitivity_checks':2,'Recorder_hook_selection_checks':3,'native_execution':False,'target11_test_execution':False},indent=2));print(json.dumps({'source_sha':SHA,'verdict':'LIMITED_PASS','Report_cases':17,'old_sensitivity':2,'Recorder_positive_hooks':3,'363match':True,'361bytebridge':True}))
