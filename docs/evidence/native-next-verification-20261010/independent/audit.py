import pathlib,json,hashlib,re,datetime,decimal,xml.etree.ElementTree as ET,subprocess
R=pathlib.Path('/tmp/sim2act-native-next-plan-independent-20261010');REPO=pathlib.Path('/workspace/Sim2Act');PUB=REPO/'docs/evidence/native-next-verification-20261010';PRIVATE=pathlib.Path('/tmp/sim2act-native-prerequisites-20261010');NATIVE=json.loads((REPO/'docs/evidence/native-engineering-prerequisites-20261010/native-9002/result.json').read_text());M=json.loads((PUB/'measurements.json').read_text());remaining=json.loads((PUB/'remaining11.json').read_text());sha='9002bf958f79972e576e831ebdf5e0d90fc44ea5'
expected=[t['nodeid'] for t in NATIVE['target_results'] if not t['status'].startswith('PASS')];assert remaining==expected==M['remaining'] and len(remaining)==len(set(remaining))==11
passed=[t['nodeid'] for t in NATIVE['target_results'] if t['status'].startswith('PASS')];assert len(passed)==15
local={}
for name in ['sqlite26.xml','pg26.xml']:
 path=PRIVATE/name;public=REPO/'docs/evidence/native-engineering-prerequisites-20261010/author'/name;assert path.read_bytes()==public.read_bytes();cases=list(ET.parse(path).getroot().iter('testcase'));times={c.attrib['classname'].replace('.','/')+'.py::'+c.attrib['name']:decimal.Decimal(c.attrib['time']) for c in cases};assert len(times)==26 and set(times)==set(remaining+passed);target={node:times[node] for node in remaining};actualsum=sum(target.values());actualmax=max(target.values());passsum=sum(times[node] for node in passed)
 assert actualsum==decimal.Decimal(str(M['local'][name]['remaining11_sum'])) and passsum==decimal.Decimal(str(M['local'][name]['passed15_sum']));assert target=={p:decimal.Decimal(str(t)) for p,t in M['local'][name]['per_remaining'].items()}
 assert actualmax==decimal.Decimal('18.65' if name=='sqlite26.xml' else '32.241');local[name]={'remaining_sum':str(actualsum),'remaining_max':str(actualmax),'passed15_sum':str(passsum),'source_xml_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
starts=[]
for line in (PRIVATE/'ci-9002-full.log').read_bytes().decode('utf-8').splitlines():
 if 'SIM2ACT_CI_DIAGNOSTIC ' in line:
  d=json.loads(line.split('SIM2ACT_CI_DIAGNOSTIC ',1)[1])
  if d['event']=='node_start':starts.append(d)
assert len(starts)==592 and len({d['nodeid'] for d in starts})==592
spans=[]
for i,d in enumerate(starts[:-1]):
 if d['nodeid'] in passed:
  delta=datetime.datetime.fromisoformat(starts[i+1]['utc'])-datetime.datetime.fromisoformat(d['utc']);micro=(delta.days*86400+delta.seconds)*1000000+delta.microseconds;span=decimal.Decimal(micro)/1000000;assert span>0;spans.append({'nodeid':d['nodeid'],'start':d['utc'],'next_nodeid':starts[i+1]['nodeid'],'next_start':starts[i+1]['utc'],'seconds':str(span)})
assert len(spans)==15;total=sum(decimal.Decimal(s['seconds']) for s in spans);maximum=max(decimal.Decimal(s['seconds']) for s in spans);assert total==decimal.Decimal(str(M['native_completed15_next_start_spans_sum']))==decimal.Decimal('73.889275') and maximum==decimal.Decimal(str(M['native_completed15_next_start_spans_max']))==decimal.Decimal('9.444151')
assert M['native_full_collected']==NATIVE['summary']['collected']==2234 and M['native_complete']==591 and M['native_suite_seconds']==float(NATIVE['summary']['junit'][0]['time'])==815.798
assert M['budgets_unchanged']=={'native_job':900,'edge':240,'node':150} and 'UNKNOWN' in M['native_remaining_cost']
plan=(REPO/'docs/F2/NativeNextVerification20261010.md').read_text();test=(REPO/'scripts/Test.ps1').read_text();ci=(REPO/'scripts/WindowsCI.ps1').read_text();assert test.startswith("param([ValidateSet('Engineering', 'R0')] [string] $Suite = 'Engineering', [string] $CITracePath = '')") and ci.startswith("param([ValidateSet('Setup', 'Test', 'Report', 'Cleanup')] [string] $Phase)")
for text in ['DIAGNOSTIC_ONLY','max-parallel=1','交集为空且并集精确等于完整集合','900s约束究竟','端到端合同','每个隔离分片作业分别900s','未得到这一合同决策前','UNKNOWN','OPEN','NOT_ACCEPTED']:
 assert text in plan,text
manifests={}
for name in ['native-interruption-diagnostics-20261010','native-engineering-prerequisites-20261010']:
 p=REPO/'docs/evidence'/name/'PUBLISHED_MANIFEST.json';manifests[name]=hashlib.sha256(p.read_bytes()).hexdigest()
old=json.loads(pathlib.Path('/tmp/sim2act-native-final-publication-audit-20261010/FINAL_PUBLICATION_AUDIT.json').read_text());assert list(manifests.values())==[old['manifests']['observer']['manifest_sha256'],old['manifests']['prerequisites']['manifest_sha256']]
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()==sha
result={'verdict':'PLAN_MEASUREMENTS_AND_SCOPE_PASS','source_sha':sha,'remaining11_exact':True,'local_recomputed':local,'native_passed15_spans':{'sum':str(total),'max':str(maximum),'count':15,'limit':'serial start-to-next-start includes fixture/teardown and overhead; not CPU or Windows remaining-node cost'},'full_collected':2234,'suite_seconds':815.798,'contract_decision':{'required':'900 seconds end-to-end acceptance vs 900 seconds for each isolated job','existing_workflow_fact':'current single job15m=900s bounds Setup/smoke/engineering/Edge/report/cleanup together','end_to_end':'serial multiple900s jobs cannot satisfy it; equivalence/cost proof or explicit contract change required','per_isolated_job':'explicitly authorize coverage/isolation and separately report workflow wall time; existing Edge240/Node150 unchanged'},'interfaces_currently_not_implemented':True,'target_mode_diagnostic_only':True,'full_partition_exact_union_no_overlap_fresh_isolation_maxparallel1':True,'unknown_tail_cost_not_zero':True,'prior219_248_manifests_unchanged':True,'tests_CI_PG_run':0,'repo_ref_writes':0,'plan_file_sha256':hashlib.sha256(plan.encode()).hexdigest()}
(R/'native15-independent-spans.json').write_text(json.dumps(spans,indent=2));(R/'PLAN_AUDIT.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
