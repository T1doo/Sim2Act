from pathlib import Path
import hashlib,json,xml.etree.ElementTree as ET
p=Path(__file__).parent;source='22476bd2f5bb1ce4f4e49cdd38849e5c91053819'
suite=ET.parse(p/'junit.xml').getroot().find('testsuite')
assert suite is not None and suite.get('tests')=='6' and all(suite.get(k)=='0'for k in ['errors','failures','skipped'])
assert (p/'pytest.exit-code').read_text().strip()=='0'
before=json.loads((p/'source-before.json').read_text());after=json.loads((p/'source-after.json').read_text())
assert before['head']==after['head']==source and before['files']==after['files'] and before['all_match_frozen'] and after['all_match_frozen']
cases={}
for f in sorted((p/'data').glob('*/result.json')):
 if f.parent.is_symlink():continue
 r=json.loads(f.read_text());d=json.loads((f.parent/'database-proof.json').read_text())
 assert r['status']=='PASS'and(f.parent/'node.stderr').stat().st_size==0
 name=r.get('case',r.get('kind'))
 c={'raw_directory':str(f.parent.relative_to(p)),'checks':len(r['checks']),'product_api_requests':len(r['requests']),
 'get':sum(q['method']=='GET'for q in r['requests']),'post':sum(q['method']=='POST'for q in r['requests']),
 'served_assets':len(r['assets']),'readonly_checkpoints':d['readonly_checks'],
 'actual_product_403':[{'index':i,'path':q['path']}for i,q in enumerate(r['requests'])if q.get('status')==403]}
 if 'case'in r:
  captures=[]
  for a in sorted(f.parent.glob('captured-*.md')):
   data=a.read_bytes();assert data==d['proof']['artifact']['content'].encode()
   captures.append({'path':str(a.relative_to(p)),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
  assert len(captures)==len(r['blobs'])and all(b['revoked']for b in r['blobs'])
  c.update({'family':'ordinary_three_tool_report','cold_scripted_mock_workers':d['worker_runs'],
   'synthetic_mock_model_requests':d['synthetic_model_requests'],'real_model_requests':d['real_model_requests'],
   'actual_fixture_revocations':d['actual_fixture_revocations'],'run_id':d['proof']['run']['id'],
   'run_status':d['proof']['run']['status'],'goal_acceptance':d['proof']['actual_run']['result']['goal_acceptance'],
   'fixture_other_queued_run':d['proof']['setup_other_run'],'verified_tools':[op['tool_ref']for op in d['proof']['operations']],
   'independent_oracle':d['proof']['independent_oracle'],'captured_files':captures,'blobs':r['blobs'],'anchors':r['anchors'],
   'controlled_delivery':[{'index':i,'path':q['path'],'description':q['controlled_delivery']}for i,q in enumerate(r['requests'])if 'controlled_delivery'in q]})
 else:
  w=json.loads((f.parent/'worker-proof.json').read_text());claims=sum(e['kind']=='CLAIMED'for e in w['actual_run']['events'])
  assert claims==w['normal_worker_claims']==2 and d['all_tables']==48 and d['all_rows_unchanged_by_page']
  c.update({'family':'existing_prospective_fixed_acceptance','synthetic_mocktransport_provider_requests':d['synthetic_provider_requests'],
   'normal_worker_claims_observed':claims,'real_model_requests':d['real_model_requests'],
   'actual_verified_tools':w['actual_verified_tools'],'run_id':w['actual_run']['id'],'run_status':w['actual_run']['status'],
   'goal_acceptance':w['actual_run']['result']['goal_acceptance'],'task_acceptance':w['actual_run']['result']['task_acceptance'],
   'in_memory_projection_negative_checks':2,'all_48_tables_unchanged_by_page':True})
 cases[name]=c
excluded={'raw-manifest.json','raw-SHA256SUMS','independent-proof.json','independent-review.md'}
files=sorted(f for f in p.rglob('*')if f.is_file()and not f.is_symlink()and f.name not in excluded)
manifest={str(f.relative_to(p)):{'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'bytes':f.stat().st_size}for f in files}
(p/'raw-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
(p/'raw-SHA256SUMS').write_text(''.join(f"{v['sha256']}  {k}\n"for k,v in manifest.items()))
proof={'source':source,'terminal_returncode':0,'junit':suite.attrib,'cases':cases,
 'same_six_author_nodes_repeated':True,'additional_unique_nodes_from_independent_repeat':0,
 'frozen_tracked_src_and_related_test_count':len(before['files']),'before_after_identical_to_frozen_git':True,'source_diffs_empty':True,
 'total_checks':sum(c['checks']for c in cases.values()),'total_product_api_requests':sum(c['product_api_requests']for c in cases.values()),
 'total_get':sum(c['get']for c in cases.values()),'total_visible_run_post':sum(c['post']for c in cases.values()),
 'ordinary_cold_scripted_mock_workers':4,'ordinary_synthetic_mock_model_requests':16,
 'fixed_mocktransport_provider_requests':2,'fixed_normal_worker_claims':4,'real_model_requests':0,
 'static_review':{'blockers':[],
 'not_run_cause':'Ordinary GoalSpec F1-tool-chain and Worker PARTIAL/NOT_RUN unchanged; no prospective ordinary acceptance evaluator is added or retrofitted.',
 'projection':'Both progress/summary use one predicate: original fixed version/kind/check/source IDs/hash/fingerprint, strict report scope/true/status and SUCCEEDED/PASS_FIXED_CONTRACT. Missing dual bindings and nonsingleton source rejected in memory.',
 'return':'Owner binds identity/connection/project selection/user Run generation; workspace return creates a new view and scope from cached authoritative Run, with no automatic API or reused preview. New explicit operations fresh-authorize Run/resource/hash; old pending and detached closures stay invalid.',
 'background':'Same-Run background redraw preserves original same-scope view and lock; this remains verified by ordinary deliver case.'},
 'limits':['Actual authenticated ASGI, full served JS and synthetic SQLite; JSDOM/Node Blob is not native browser.',
 'Ordinary cases each execute one selected-material report as PARTIAL/NOT_RUN; Decimal4.00/count2 is a deterministic engineering oracle, not general semantics.',
 'Ordinary fixture per case separately saves same-name MD and POSTs one zero-material QUEUED otherRun; not counted as the four visible POSTs. Artifact read Grants follow existing save_text policy; one fixture actual revoke.',
 'Fixed cases reuse existing approved OFFLINE_TEST contract and existing normal Worker twice; fixed exact synthetic goal PASS only, general NOT_RUN, owner PENDING and publication closed.',
 'Two malformed projection checks per fixed case operate only on in-memory clones, not server response mutations or database changes.',
 'Prior slice retains 3 cold workers/12 synthetic Mock requests and zero/eight input Runs accepted QUEUED, not executed. This batch has separate ordinary16 Mock plus fixed2 MockTransport, and does not alter prior counts.',
 'Baseline6c6263FAIL and candidate6236PASS not independently repeated; this batch does not modify or reconstruct earlier raw evidence.',
 'No PG, Windows/native browser, real models/semantic acceptance, remote CI, deployment or old fault/recovery matrix executed.'],
 'raw_manifest_files':len(manifest),'raw_manifest_sha256':hashlib.sha256((p/'raw-manifest.json').read_bytes()).hexdigest(),
 'manifest_scope':'All regular originals including six DB/info/result/stderr/SQL proofs, two Worker proofs, five captured MD, command/RC/XML/log/source snapshots, runner/package tools and pytest-cache metadata; symlink aliases excluded.'}
(p/'independent-proof.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
review=f'''冻结源 `{source}` 独立准入通过。仅执行指定两文件共6参数一次，RC0，6 PASS / 0 FAIL / 0 ERROR / 0 SKIP，JUnit {suite.get('time')}s。重复作者同6节点，额外唯一0。123份tracked src/相关测试文件before/after均与冻结Git逐字相同、差异为空；产品改动限UI，普通后端验收合同未改变。

普通deliver/navigation/revocation/workspace-return分别22/15/11/14检查、46/129/38/45次产品请求；固定read_preview/sum_quantity_z各8检查、13GET。共78检查、284产品API（280GET/4可见Run POST）、126served资产，由pytest逐SHA校验。普通4例各1冷Scripted Mock Worker/4合成Mock请求，合计4冷Worker/16合成/0真实；每例真实read→aggregate→save三VERIFIED操作，PARTIAL/目标NOT_RUN。固定2例各1离线MockTransport请求、同正常Worker两次领取（原件实际CLAIMED事件各2），合计2provider/4claims；每例1真实已核验工具，只旧精确固定合同PASS，general NOT_RUN、owner PENDING、发布关闭。

状态投影同时用于进度及摘要，匹配旧版本/kind/check/源ID/hash/fingerprint、严格true和完整限定scope。已补双侧缺失字段及非单元素源拒绝；每固定例两条负向断言仅操作内存克隆，没有改API交付或数据库。普通没有被回填PASS，NOT_RUN根因未被改写成模型或配置开关。

workspace-return无需轮询或重选历史Run即可立即查看；返回本身0API且不复用预览。新view/scope允许fresh Run→resource→SHA，旧detached控件0请求，旧held下载释放0Blob且不污染新预览；新的明确下载成功。原3例同时保留后台重画共享锁、四类导航迟到隔离、内容digest拒绝，以及实际artifact撤权后的fresh Run GET403清保护视图。

5份实际捕获MD各109字节，SHA256 `40f053712cd1c69ee7ba21c147d002b809b04cdb53101d509efd1513ceeba209`，与真实保存原文逐字节相同，5 URL全revoked。每普通例fixture另存同名诱饵并另POST一个0材料QUEUED otherRun，不能算入可见用户4POST或称零新增Grant；派生Grant沿既有save_text政策，实际fixture撤权1。6例各有48表只读checkpoint，固定页面全表原样。

上一片3 Worker/12合成请求及0/8材料只202/QUEUED未执行的历史保持原义；本轮普通16 Mock和固定2 MockTransport分列。baseline6c626与候选623本独审未重复或改签。范围为合成SQLite/实际ASGI及served JS/JSDOM/Node Blob；普通确定性oracle不代表语义验收。PG、Windows/native、真实模型/场景、远端CI及旧故障矩阵均NOT_RUN。{len(manifest)}份raw逐件SHA/size与完整覆盖已验证，目录封存后停止写入。
'''
(p/'independent-review.md').write_text(review)
for name,v in manifest.items():
 data=(p/name).read_bytes();assert len(data)==v['bytes']and hashlib.sha256(data).hexdigest()==v['sha256']
assert set(manifest)=={str(f.relative_to(p))for f in p.rglob('*')if f.is_file()and not f.is_symlink()and f.name not in excluded}
for name in ['independent-review.md','independent-proof.json','raw-manifest.json','raw-SHA256SUMS','source-before.json','source-after.json','junit.xml','pytest.log','command.txt','run-independent.py','package-evidence.py']:
 data=(p/name).read_bytes();print(hashlib.sha256(data).hexdigest(),len(data),name)
print('RAW_FILES',len(manifest),'ALL_REGULAR_FILES',len(manifest)+4,'READY_IMMUTABLE')
