from pathlib import Path
import hashlib,json,xml.etree.ElementTree as ET
p=Path(__file__).parent; source='5575446ae124ae4a4954b1f5670ef9175b000029'
suite=ET.parse(p/'junit.xml').getroot().find('testsuite')
assert suite is not None and suite.get('tests')=='3' and all(suite.get(k)=='0' for k in ['errors','failures','skipped'])
assert (p/'pytest.exit-code').read_text().strip()=='0'
before=json.loads((p/'source-before.json').read_text());after=json.loads((p/'source-after.json').read_text())
assert before['head']==after['head']==source and before['files']==after['files'] and before['all_match_frozen'] and after['all_match_frozen']
cases={}
for f in sorted((p/'data').glob('*/result.json')):
 if f.parent.is_symlink():continue
 r=json.loads(f.read_text());d=json.loads((f.parent/'database-proof.json').read_text())
 assert r['status']=='PASS' and (f.parent/'node.stderr').stat().st_size==0
 captures=[]
 for c in sorted(f.parent.glob('captured-*.md')):
  data=c.read_bytes();assert data==d['proof']['artifact']['content'].encode()
  captures.append({'path':str(c.relative_to(p)),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
 assert len(captures)==len(r['blobs']) and all(v['revoked'] for v in r['blobs'])
 cases[r['case']]={'directory':str(f.parent.relative_to(p)),'checks':len(r['checks']),'product_api_requests':len(r['requests']),
 'get':sum(q['method']=='GET' for q in r['requests']),'post':sum(q['method']=='POST' for q in r['requests']),
 'served_assets':len(r['assets']),'cold_mock_workers':d['worker_runs'],'synthetic_model_requests':d['synthetic_model_requests'],
 'real_model_requests':d['real_model_requests'],'actual_fixture_revocations':d['actual_fixture_revocations'],
 'readonly_48_table_checkpoints':d['readonly_checks'],'executed_run_id':d['proof']['run']['id'],
 'executed_run_status':d['proof']['run']['status'],'fixture_other_queued_run_id':d['proof']['setup_other_run'],
 'independent_oracle':d['proof']['independent_oracle'],'verified_tools':[v['tool_ref']for v in d['proof']['operations']],
 'artifact_id':d['proof']['artifact']['id'],'artifact_content_sha256':d['proof']['artifact']['hash'],
 'captured_blob_files':captures,'blobs':r['blobs'],'anchors':r['anchors'],
 'controlled_response_mutations':[{'request_index':i,'path':q['path'],'description':q['controlled_delivery']}for i,q in enumerate(r['requests'])if 'controlled_delivery'in q],
 'actual_product_403':[{'request_index':i,'path':q['path']}for i,q in enumerate(r['requests'])if q.get('status')==403]}
excluded={'raw-manifest.json','raw-SHA256SUMS','independent-proof.json','independent-review.md'}
files=sorted(f for f in p.rglob('*') if f.is_file() and not f.is_symlink() and f.name not in excluded)
manifest={str(f.relative_to(p)):{'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'bytes':f.stat().st_size}for f in files}
(p/'raw-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
(p/'raw-SHA256SUMS').write_text(''.join(f"{v['sha256']}  {k}\n" for k,v in manifest.items()))
proof={'source':source,'terminal_returncode':0,'junit':suite.attrib,'cases':cases,
 'independent_repeats_author_same_three_nodes':True,'additional_unique_nodes':0,
 'source_file_count':len(before['files']),'before_after_equal_and_all_match_frozen_git':True,'src_selected_tests_diff_empty':True,
 'total_checks':sum(c['checks']for c in cases.values()),'total_product_api_requests':sum(c['product_api_requests']for c in cases.values()),
 'total_product_get':sum(c['get']for c in cases.values()),'total_visible_run_post':sum(c['post']for c in cases.values()),
 'total_cold_scripted_mock_workers':3,'total_synthetic_model_requests':12,'total_real_model_requests':0,
 'fixture_only_excluded_from_product_request_counts':'Per case: one same-name MD decoy saved before baseline and one separate 0-material QUEUED otherRun POST after Worker; revocation case one actual Grant-revoke fixture API action. Artifact derived read Grants retain original save_text policy.',
 'static_review':{'blockers':[],'same_run_background_redraw':'Scope uses explicit user generation; same-view Map and global Set preserve preview/lock through showRun(id,false), new DOM duplicate adds no request, completion unlocks it.',
 'binding':'VERIFIED receipt and same-op known_effect artifact.save_text status/resource/hash; fresh Run rebind then exact project/id/md/hash and UTF-8 SHA256.',
 'fences':'Connection/project selection/workspace/user Run selection/activeRun and current view checked after every await including digest; stale responses do not Blob.',
 'denial':'Actual revoked artifact is refused at fresh Run GET403 through authorize_receipts; clearRunDetail erases protected view, detached callback sends nothing. No claim of a second resource GET403.',
 'safe_render_and_cleanup':'Answer and preview textContent; fresh-download Blob with finally anchor removal/URL revoke; all four captured URLs revoked.'},
 'limits':['Synthetic SQLite with actual ASGI and all served JS; JSDOM events/Node Blob capture are not native browser.',
 'PARTIAL and goal NOT_RUN remain; Decimal4.00/count2 plus MD byte oracle is deterministic engineering evidence, not general semantic acceptance.',
 'One content mismatch is a controlled post-GET200 response mutation, not database corruption; four navigation gates hold real authorized GET200 delivery.',
 'Prior baseline0a59 and author68ba runs were not independently executed or reclassified by this run.',
 'Earlier material-picker zero/eight Runs remain accepted QUEUED without execution; this slice executes only one-material Runs, plus fixture queued otherRuns.',
 'No real model, PG, Windows/native browser, remote CI, other modules, or old recovery matrices executed.'],
 'raw_manifest_files':len(manifest),'raw_manifest_sha256':hashlib.sha256((p/'raw-manifest.json').read_bytes()).hexdigest(),
 'manifest_scope':'All regular original files including databases/full request-response JSON/captured MD/log/XML/source snapshots/command and tooling/pytest-cache; no reconstructed responses or static-byte source copies.'}
(p/'independent-proof.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
review=f'''冻结源 `{source}` 独立准入通过。仅运行 `tests/test_ordinary_run_results.py` 原3参数一次，RC0，3 PASS / 0 FAIL / 0 ERROR / 0 SKIP，JUnit {suite.get('time')}s（deliver8.242/navigation8.853/revocation6.188）。重复作者同3节点，额外唯一0。117份tracked src/相关测试文件before/after与冻结Git逐字相同、差异为空。

三例分别22/15/11检查、46/129/38产品API请求，共48检查、213请求（210GET/3可见Run POST），每例21份served资产由pytest核对SHA。每例执行1冷Scripted Mock Worker、4合成模型请求、0真实请求；合计3 Worker/12合成/0真实。真实注册read→aggregate→save三操作均VERIFIED，Run PARTIAL/目标NOT_RUN。独立Decimal核对4.00/count2；同名MD诱饵未被误用。

answer与MD直接按纯文本显示，无img/script执行。每次成果操作fresh Run→exact resource→UTF-8 SHA；deliver验证同Run后台重画共享preview及pending锁，新DOM重复click不加请求、结束后新DOM解锁。一次受控GET200响应内容修改被digest拒绝，未创建Blob。navigation四次Run/工作区/项目/身份往返均丢弃迟到真实GET200字节，再次当前下载成功。

共4份实际Blob MD原件（deliver3/navigation1），各109字节、SHA256 `40f053712cd1c69ee7ba21c147d002b809b04cdb53101d509efd1513ceeba209`，含CRLF/emoji/markup，与真实保存内容逐字节相同；4 URL全已revoke。revocation通过fixture真实撤销artifact Grant，下一fresh Run GET实际403，清answer/原文/controls/raw；detached回调不再发请求。未将其称为resource GET403或第二次可见点击。

每例另有fixture保存同名MD及POST建立1个0材料QUEUED otherRun，用于导航；这些不在driver的3个可见POST分母。工具成果派生resource.read Grant沿原save_text政策。每例48表只读checkpoint通过，撤权例除明确Grant变更外其他表保持。上一片0/8材料Run仅202/QUEUED未执行的边界不由本片扩大。0a59红例及68ba作者早轮本次未独跑，不改签、不覆盖其原件。

范围为合成SQLite、实际ASGI/served JS、JSDOM/Node Blob；确定性工程oracle不代表通用语义。PG、Windows/native browser、真实模型/场景、远端CI及外围矩阵均NOT_RUN。{len(manifest)}份raw逐件SHA/size及完整覆盖已验证；本目录封存后停止写入。
'''
(p/'independent-review.md').write_text(review)
for name,value in manifest.items():
 data=(p/name).read_bytes();assert len(data)==value['bytes']and hashlib.sha256(data).hexdigest()==value['sha256']
assert set(manifest)=={str(f.relative_to(p))for f in p.rglob('*')if f.is_file()and not f.is_symlink()and f.name not in excluded}
for name in ['independent-review.md','independent-proof.json','raw-manifest.json','raw-SHA256SUMS','source-before.json','source-after.json','junit.xml','pytest.log','command.txt','run-independent.py','package-evidence.py']:
 data=(p/name).read_bytes();print(hashlib.sha256(data).hexdigest(),len(data),name)
print('RAW_FILES',len(manifest),'ALL_REGULAR_FILES',len(manifest)+4,'READY_IMMUTABLE')
