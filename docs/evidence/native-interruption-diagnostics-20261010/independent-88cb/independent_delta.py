import pathlib,subprocess,json,hashlib,os,sys,runpy,traceback
ROOT=pathlib.Path('/tmp/sim2act-native-diagnostics-independent-88cb-20261010');REPO=pathlib.Path('/workspace/Sim2Act');SHA='88cb3c64b5dcbaf3df7183ebbf72773547585e15';OLD='d8f2101b5259be5b51d00eca527db7cf3b4c5b37';PLUGIN=REPO/'scripts/native_pytest_diagnostics.py'
def freeze(label):
 m=json.loads(pathlib.Path('/tmp/sim2act-native-diagnostics-20261010/source-freeze.json').read_text())['files'];a={p:hashlib.sha256((REPO/p).read_bytes()).hexdigest() for p in m};g={p:hashlib.sha256(subprocess.check_output(['git','show',SHA+':'+p],cwd=REPO)).hexdigest() for p in m};head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip();assert head==SHA and a==g==m;out={'sha':head,'count':len(m),'git_match':True,'worktree_match':True,'files':a};(ROOT/('source-'+label+'.json')).write_text(json.dumps(out,indent=2));return a
before=freeze('before');api=runpy.run_path(str(PLUGIN));redact=api['redact'];results=[]
cases=[
 ('original',"authorization='Basic CI_ORIGINAL_BASIC' password='first CI_ORIGINAL_SPACED'",['CI_ORIGINAL_BASIC','CI_ORIGINAL_SPACED']),
 ('escaped',r'''password="first\" CI_ESCAPED_QUOTE \\ CI_ESCAPED_SLASH"''',['CI_ESCAPED_QUOTE','CI_ESCAPED_SLASH']),
 ('unquoted',"authorization=Basic CI_UNQUOTED_BASIC tail CI_UNQUOTED_TAIL",['CI_UNQUOTED_BASIC','CI_UNQUOTED_TAIL']),
 ('multiline',"password='first CI_MULTILINE_FIRST\nsecond CI_MULTILINE_SECOND'\nordinary diagnostic survives",['CI_MULTILINE_FIRST','CI_MULTILINE_SECOND']),
 ('json',json.dumps({'api_key':'first CI_JSON_API second','secret':'CI_JSON_SECRET'}),['CI_JSON_API','CI_JSON_SECRET']),
 ('scheme',"POSTGRESQL+psycopg://ciuser:CI_UPPER_DB@127.0.0.1/db\nBearer CI_BEARER_VALUE",['CI_UPPER_DB','CI_BEARER_VALUE']),
]
# Each material is an independently authored real assertion failure, not an author test body.
fixture='import pytest\nMESSAGES='+repr([c[1] for c in cases])+'\n@pytest.mark.parametrize("index",range(len(MESSAGES)))\ndef test_material(index):\n    assert False, MESSAGES[index]\n'
(ROOT/'test_fixture.py').write_text(fixture)
env={**os.environ,'PYTHONPATH':str(REPO),'PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1','PYTHONUTF8':'1'}
for k in ['PYTEST_ADDOPTS','SIM2ACT_TEST_DATABASE_URL','GITHUB_STEP_SUMMARY']:env.pop(k,None)
cmd=[sys.executable,'-m','pytest','-q','-p','scripts.native_pytest_diagnostics','--ci-diagnostics',str(ROOT/'events.jsonl'),'--junitxml',str(ROOT/'junit.xml'),'test_fixture.py'];(ROOT/'command.json').write_text(json.dumps(cmd,indent=2));p=subprocess.run(cmd,cwd=ROOT,env=env,text=True,capture_output=True,timeout=20);(ROOT/'child.log').write_text(p.stdout+p.stderr);assert p.returncode==1
reportcmd=[sys.executable,str(PLUGIN),'--report',str(ROOT/'events.jsonl'),'--junit',str(ROOT/'junit.xml')];r=subprocess.run(reportcmd,cwd=ROOT,env={**env,'GITHUB_STEP_SUMMARY':str(ROOT/'step-summary.md')},text=True,capture_output=True,timeout=15);(ROOT/'report.log').write_text(r.stdout+r.stderr);assert r.returncode==0
channels={'JSONL':(ROOT/'events.jsonl').read_text(),'diagnostic_stdout':'\n'.join(s for s in p.stdout.splitlines() if s.startswith('SIM2ACT_CI_DIAGNOSTIC ')),'Report':r.stdout};(ROOT/'diagnostic-stdout.log').write_text(channels['diagnostic_stdout'])
for name,text,tokens in cases:
 leaks={ch:[v for v in tokens if v in body] for ch,body in channels.items()};results.append({'case':name,'channels':leaks,'all_values_synthetic':True,'pass':not any(leaks.values())})
(ROOT/'redaction-results.json').write_text(json.dumps(results,indent=2));assert all(row['pass'] for row in results),results
summary=api['summarize'](ROOT/'events.jsonl');assert len(summary['failures'])==6 and summary['suite_complete'] and summary['exitstatuses']==[1];(ROOT/'summary.json').write_text(json.dumps(summary,indent=2))
pure=[]
for name,text,tokens in cases:
 value=redact(text);pure.append({'case':name,'output':value,'pass':all(v not in value for v in tokens)})
assert all(row['pass'] for row in pure);assert redact('node failed with ordinary assertion')=='node failed with ordinary assertion';assert 'ordinary diagnostic survives' in redact(cases[3][1]);(ROOT/'pure-boundaries.json').write_text(json.dumps({'cases':pure,'ordinary_text_unchanged':True,'line_after_closed_multiline_retained':True},indent=2))
after=freeze('after');assert before==after
changed=subprocess.check_output(['git','diff','--name-only',OLD,SHA],cwd=REPO,text=True).splitlines();assert set(changed)=={'scripts/native_pytest_diagnostics.py','tests/test_native_pytest_diagnostics.py'}
bridge={p:hashlib.sha256(subprocess.check_output(['git','show',OLD+':'+p],cwd=REPO)).hexdigest()==h for p,h in before.items() if p not in changed};src={p:hashlib.sha256(subprocess.check_output(['git','show','47388f573746daa27f8d5790ca358eef91378ad5:'+p],cwd=REPO)).hexdigest()==h for p,h in before.items() if p.startswith('src/')};assert len(bridge)==358 and all(bridge.values()) and len(src)==69 and all(src.values());(ROOT/'delta-byte-bridge.json').write_text(json.dumps({'source_sha':SHA,'old_sha':OLD,'changed':changed,'unchanged_frozen_count':358,'all_unchanged_equal':True,'product_count':69,'all_product_equal_to_473':True,'before_after_match':True},indent=2));print(json.dumps({'source_sha':SHA,'scenario_count':6,'channel_assertions':18,'pure_boundary_assertions':8,'failure_summary_assertion':1,'actual_child_exit':p.returncode,'verdict':'LIMITED_PASS'}))
