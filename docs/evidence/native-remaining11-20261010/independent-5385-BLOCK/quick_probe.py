import pathlib,json,runpy,hashlib,sys,subprocess,os,copy,contextlib
R=pathlib.Path('/tmp/sim2act-native-remaining11-independent-5385-20261010');REPO=pathlib.Path('/workspace/Sim2Act');PLUGIN=REPO/'scripts/native_pytest_diagnostics.py';a=runpy.run_path(str(PLUGIN));nodes=a['remaining11_nodes']();rec=a['Recorder'](R/'actual-Recorder.jsonl',nodes)
with (R/'Recorder-stdout.log').open('w') as stream,contextlib.redirect_stdout(stream):
 rec.pytest_sessionstart(None);rec.emit('full_collection',nodes=nodes+['extra-test']);rec.emit('selection',scope='DIAGNOSTIC_ONLY_REMAINING11',full_count=12,full_nodes_sha256=hashlib.sha256(json.dumps(nodes+['extra-test']).encode()).hexdigest(),required_nodes=nodes,deselected_count=1);rec.emit('collection',nodes=nodes)
 for node in nodes:
  rec.emit('node_start',nodeid=node)
  for phase in ['setup','call','teardown']:rec.emit('node_report',nodeid=node,phase=phase,outcome='passed')
  rec.emit('node_finish',nodeid=node)
 rec.pytest_sessionfinish(None,0)
base=[json.loads(l) for l in (R/'actual-Recorder.jsonl').read_text().splitlines()];results=[]
for name in ['valid','foreignstart','foreignfinish','wrongrequestevent','extranonrequestedsession']:
 records=copy.deepcopy(base)
 if name=='foreignstart':next(r for r in records if r['event']=='node_start')['nodeid']='foreign-node'
 if name=='foreignfinish':next(r for r in records if r['event']=='node_finish')['nodeid']='foreign-node'
 if name=='wrongrequestevent':records[0]['event']='unexpected_header'
 if name=='extranonrequestedsession':records.insert(4,dict(event='session_start',pid=records[0]['pid']))
 p=R/(name+'.jsonl');p.write_text(''.join(json.dumps(r)+'\n' for r in records));s=a['summarize'](p);env={**os.environ};env.pop('GITHUB_STEP_SUMMARY',None);o=subprocess.run([sys.executable,str(PLUGIN),'--report',str(p),'--junit',str(R/'missing.xml')],env=env,capture_output=True,text=True);(R/(name+'-Report.log')).write_text(o.stdout+o.stderr);(R/(name+'-summary.json')).write_text(json.dumps(s,indent=2));results.append({'case':name,'Report_exit':o.returncode,'selection_verified':s['selection_verified'],'required_targets_complete':s['required_targets_complete'],'expected_accept':name=='valid','pass':(o.returncode==0)==(name=='valid')})
(R/'quick-results.json').write_text(json.dumps(results,indent=2));print(json.dumps(results,indent=2))
