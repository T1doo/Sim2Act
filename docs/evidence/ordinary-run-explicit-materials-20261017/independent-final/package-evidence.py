from pathlib import Path
import hashlib, json, xml.etree.ElementTree as ET
p=Path(__file__).parent
source='09155e6e3415acb1d53aff80248d745badd37805'
suite=ET.parse(p/'junit.xml').getroot().find('testsuite')
assert suite is not None and suite.get('tests')=='3' and all(suite.get(k)=='0' for k in ['errors','failures','skipped'])
assert (p/'pytest.exit-code').read_text().strip()=='0'
before=json.loads((p/'source-before.json').read_text());after=json.loads((p/'source-after.json').read_text())
assert before['head']==after['head']==source and before['files']==after['files'] and before['all_match_frozen'] and after['all_match_frozen']
case_proofs={}
for path in sorted((p/'data').rglob('result.json')):
 if path.is_symlink():continue
 r=json.loads(path.read_text());db=json.loads((path.parent/'database-proof.json').read_text())
 assert r['status']=='PASS' and (path.parent/'node.stderr').stat().st_size==0
 case_proofs[r['case']]={
  'relative_raw_directory':str(path.parent.relative_to(p)), 'checks':len(r['checks']),
  'api_requests':len(r['requests']), 'get':sum(q['method']=='GET' for q in r['requests']),
  'post':sum(q['method']=='POST' for q in r['requests']), 'served_assets':len(r['assets']),
  'normal_cold_mock_worker_runs':db['normal_cold_mock_worker_runs'],
  'synthetic_model_requests':db['synthetic_model_requests'],'real_model_requests':db['real_model_requests'],
  'fixture_tenth_resource_saves':db['fixture_resource_saves'], 'controlled_catalog_deliveries':r['mutations'],
  'accepted_runs':next(v['accepted_runs'] for v in db['proof'] if 'accepted_runs' in v),
 }
excluded={'raw-manifest.json','raw-SHA256SUMS','independent-proof.json','independent-review.md'}
files=sorted(x for x in p.rglob('*') if x.is_file() and not x.is_symlink() and x.name not in excluded)
manifest={str(x.relative_to(p)):{'sha256':hashlib.sha256(x.read_bytes()).hexdigest(),'bytes':x.stat().st_size} for x in files}
(p/'raw-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
(p/'raw-SHA256SUMS').write_text(''.join(f"{entry['sha256']}  {name}\n" for name,entry in manifest.items()))
proof={'source':source,'independent_command':'command.txt','terminal_returncode':0,'junit':suite.attrib,
 'same_three_author_nodes_repeated':True,'additional_unique_nodes_from_independent_run':0,
 'frozen_tracked_source_and_relevant_test_files':len(before['files']), 'before_after_files_equal':True,
 'all_selected_files_equal_frozen_git':True,'source_diffs_empty':True,
 'cases':case_proofs,'total_checks':sum(v['checks'] for v in case_proofs.values()),
 'total_product_api_requests':sum(v['api_requests'] for v in case_proofs.values()),
 'raw_manifest_files':len(manifest),'raw_manifest_sha256':hashlib.sha256((p/'raw-manifest.json').read_bytes()).hexdigest(),
 'static_review':{'original_list_failure_deselection_block':'Closed: only sending/unknown disables picker; zero is valid and nonzero requires ready.',
 'oracle_path':'API contract.snapshot.goal.resource_refs; original SQL exact Run/contract/read-intent assertions retained.',
 'scope_isolation':'Independent GoalCard selection; synchronous project/identity clear; current-only material list updates; unknown replay does not pass new draft guards.',
 'new_blockers':[]},
 'limits':['Actual served assets and authenticated ASGI with synthetic SQLite, JSDOM DOM/events; not native browser.',
 'use: exact 0/1/8 API202 and SQL snapshots; only one-material Run executed, PARTIAL and whole-goal NOT_RUN; zero/eight QUEUED.',
 'refresh: failed GET delivery cancellation checks Goal-only UI readiness, not a POST during that failed-list state.',
 'frozen: synthetic response loss after real acceptance plus one filtered catalog delivery with unchanged real permission; not actual revocation.',
 'refresh/frozen fixture each saves tenth resource by existing Save policy; do not claim no new Grants.',
 'Baseline66786 and author c7692P1F were not independently run; no independent c769 failure claimed.',
 'No PG, native Windows/browser, real models/semantic acceptance, remote CI or extra recovery matrix executed.'],
 'manifest_scope':'All regular original files including runner, packaging script and local pytest-cache metadata; no source/static byte copies or reconstructed responses.'}
(p/'independent-proof.json').write_text(json.dumps(proof,indent=2,ensure_ascii=False)+'\n')
review=f'''冻结源 `{source}` 独立复验准入通过。仅运行 `tests/test_ordinary_run_materials.py` 三参数一次，RC0，3 PASS / 0 FAIL / 0 ERROR / 0 SKIP；JUnit {suite.get('time')}s。重复作者同三节点，额外唯一节点0。117份 tracked src/相关测试文件执行前后与冻结 Git 完全一致，源码差异为空。

use/refresh/frozen 分别15/8/6条检查、53/60/35次产品API请求；共29检查、148请求（143 GET、5 POST），每例21份实际served资产均由pytest校验SHA。每例保留SQLite DB、info、完整请求响应result、空stderr、database-proof；命令、日志、XML、前后源码hash一并保留。

use 从9份材料中明确选择，实际API接受0/1/8三个Run，SQL确认各自Run refs与持久合同一致。仅1份材料的Run执行一次冷MockModel Worker，发生2次合成模型请求、0真实请求；读取意图精确绑定该材料，结果PARTIAL，整目标验收NOT_RUN。0/8两个Run仍QUEUED。9份选择保留并被UI阻止，未发送POST；GoalCard独立选材保持不变。

原静态阻断已关闭：列表未就绪时允许显式取消选择，非零仍禁新提交；refresh在真实GET200后模拟一次交付失败，验证保留ID、可取消至0，及刷新/项目ABA/身份切换隔离。frozen模拟真实已接受响应丢失，再过滤一次列表交付；原ID/原body/key保留，重复提交被阻止，恢复实际返回同一Run。列表过滤权限未改变，不是撤权。refresh/frozen各另有一次fixture保存第10份材料，沿用既有Save和Grant政策。

DOM初始化及GoalCard分离未见新增阻断；新提交读取当前显式选择，原sending/unknown恢复不受新草稿校验干扰。修复前c769作者2P1F和66786红例本独审均未执行，没有独立失败可归档。

范围是合成SQLite、实际ASGI/served JS、JSDOM事件；列表未就绪时0材料只验证UI可提交，实际0材料202在列表健康时执行。原生浏览器/Windows、PG、真实模型/场景语义、远端CI及额外恢复矩阵均NOT_RUN。原始manifest列出{len(manifest)}份文件及逐件SHA/size；本目录封存后停止写入。
'''
(p/'independent-review.md').write_text(review)
for name,entry in manifest.items():
 data=(p/name).read_bytes();assert len(data)==entry['bytes'] and hashlib.sha256(data).hexdigest()==entry['sha256']
assert set(manifest)=={str(x.relative_to(p)) for x in p.rglob('*') if x.is_file() and not x.is_symlink() and x.name not in excluded}
for name in ['independent-review.md','independent-proof.json','raw-manifest.json','raw-SHA256SUMS','source-before.json','source-after.json','junit.xml','pytest.log','command.txt','run-independent.py','package-evidence.py']:
 data=(p/name).read_bytes();print(hashlib.sha256(data).hexdigest(),len(data),name)
print('RAW_FILES',len(manifest),'ALL_REGULAR_FILES',len(manifest)+4,'READY_IMMUTABLE')
