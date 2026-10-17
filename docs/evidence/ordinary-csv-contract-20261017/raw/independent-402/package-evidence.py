from pathlib import Path
import hashlib,json,xml.etree.ElementTree as ET
p=Path(__file__).parent;source='402f3eb5f80be73ddc57d4bb6123fdd6157726e0'
suite=ET.parse(p/'junit.xml').getroot().find('testsuite');assert suite.get('tests')=='3'and all(suite.get(k)=='0'for k in['failures','errors','skipped']);assert(p/'pytest.exit-code').read_text().strip()=='0'
b=json.loads((p/'source-before.json').read_text());a=json.loads((p/'source-after.json').read_text());assert b['head']==a['head']==source and b['files']==a['files']and a['all_match_frozen']
delta=json.loads((p/'source-delta-from-599.json').read_text());assert delta['all_tracked_changed_paths']==['src/sim2act/web/ordinary-csv.js','tests/ordinary_csv_report.cjs']
cases={}
for f in sorted((p/'data').glob('*/result.json')):
 if f.parent.is_symlink():continue
 r=json.loads(f.read_text());d=json.loads((f.parent/'database-proof.json').read_text());assert r['status']=='PASS'and(f.parent/'node.stderr').stat().st_size==0
 capture=f.parent/'captured-report.md';data=capture.read_bytes();assert data==d['proof']['artifact']['content'].encode()and hashlib.sha256(data).hexdigest()==d['proof']['artifact']['hash']
 assert d['worker_runs']==1 and d['model_requests']==d['real_model_requests']==0
 before=d['proof']['before'];actual=d['proof']['actual'];assert before['status']=='WAITING_APPROVAL'and actual['status']=='SUCCEEDED'
 cases[r['case']]={'directory':str(f.parent.relative_to(p)),'checks':len(r['checks']),'api':len(r['requests']),'get':sum(q['method']=='GET'for q in r['requests']),'post':sum(q['method']=='POST'for q in r['requests']),'served_assets':len(r['assets']),'cold_NoModel_workers':1,'model_requests':0,'real_model_requests':0,'run':actual['id'],'before_status':before['status'],'after_status':actual['status'],'scoped_goal_acceptance':actual['result']['goal_acceptance'],'general_semantics':actual['result']['task_acceptance']['general_semantic_acceptance'],'owner_acceptance':actual['result']['task_acceptance']['owner_acceptance'],'actual_operations':len(actual['result']['receipts']),'captured_report':{'path':str(capture.relative_to(p)),'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)},'controlled_reply_losses':[{'index':i,'path':q['path'],'description':q['controlled_delivery']}for i,q in enumerate(r['requests'])if'controlled_delivery'in q]}
excluded={'raw-manifest.json','raw-SHA256SUMS','independent-proof.json','independent-review.md'}
files=sorted(f for f in p.rglob('*')if f.is_file()and not f.is_symlink()and f.name not in excluded)
manifest={str(f.relative_to(p)):{'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'bytes':f.stat().st_size}for f in files};(p/'raw-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');(p/'raw-SHA256SUMS').write_text(''.join(f"{v['sha256']}  {k}\n"for k,v in manifest.items()))
proof={'source':source,'returncode':0,'junit':suite.attrib,'admission':'PASS_LIMITED_PROSPECTIVE_STRUCTURED_CSV_REPORT','cases':cases,'checks':sum(c['checks']for c in cases.values()),'product_api':sum(c['api']for c in cases.values()),'get':sum(c['get']for c in cases.values()),'post':sum(c['post']for c in cases.values()),'served_assets':66,'cold_NoModel_worker_executions':3,'model_requests':0,'real_model_requests':0,'source_file_count':len(a['files']),'before_after_identical_to_frozen_git':True,'delta_from599':delta,
'previous_execution':{'source':'599052cbadae21b4a7ba8738fb889ea970c11e84','tests':28,'passed':28,'junit_seconds':'76.911','raw_directory':'/tmp/ordinary-csv-report-independent-599052cb-20261017','manifest_sha256':'2a17267ba1e4843664f1ba7f11a3c2d23d68157477ccc1aa73b89c5fe28fc882','status':'Kept prevalidation with display BLOCK; 25 other nodes are not re-signed as402. Only the3 affected pages repeated at402. Total selected unique28, not31.'},
'static_review':{'blockers':[],'closed':'Paired missing fingerprints no longer equal into PASS: both sides64hex plus exact checker version; two in-memory checks per page, no changed server response.',
'original_scope':'Explicit source/column/rules/full MD frozen before confirmation. Existing dispatch/Worker/ledger with stable call IDs, current budgets and min deadline, heartbeat/fences and independent integer-scaled oracle; no new executor.kind/ref or Grant policy.',
'authority':'Server checker verifies every intent/receipt/effect and readback on finalize/inspect. UI predicate is projection. Existing fixed checker/global Limits remain unchanged.'},
'limits':['Actual ASGI/SQLite and full served JS/JSDOM, not native browser;22actual served assets per page SHA-checked by Python.',
'One Run and three operations per final page. Lost case deliberately drops real accepted prepare and confirmation responses; manual exact-key replay produces no new Run or extra artifact.',
'Navigation case tests project away/back during held confirmation. Do not claim it dynamically covers every new-controller identity/workspace timing path.',
'Each page captures actual saved730-byteMD after waiting URL revoke; new pageJSON contains no separate Blob URL metadata array. Save creates original derived read Grants.',
'599 API scope tampering includes explicit synthetic persisted mutations, not real user-edit flows; original25 unrelated nodes executed only599. Related4 pages there did load the old JS version, and are not claimed rerun402.',
'All acceptance stays limited to explicitly selected structured CSV/report contract; general semanticsNOT_RUN, ownerPENDING, publication closed, old arbitrary ordinary Runs not retrofitted.',
'No PG, Windows/native, real model, remote CI/deployment or old recovery matrix run.'],
'raw_manifest_files':len(manifest),'raw_manifest_sha256':hashlib.sha256((p/'raw-manifest.json').read_bytes()).hexdigest()}
(p/'independent-proof.json').write_text(json.dumps(proof,indent=2,ensure_ascii=False)+'\n')
review=f'''最终执行源 `{source}` 独立有限准入通过。仅重跑受影响的新页面3参数一次，RC0，3 PASS / 0 FAIL / 0 ERROR / 0 SKIP，JUnit {suite.get('time')}s（5.985/5.663/4.959）。125份tracked src/相关测试before/after与402 Git逐字一致。全tracked提交diff599→402严格只有新UI谓词一行和新页面driver两纯负断言，其余文件字节相同。

最终deliver/lost/navigation为13/16/15检查，共44；实际产品API36/38/52，共126（118GET/8POST：正常准备+确认各2，lost原键重放共4）。66份served资产逐SHA验证。3例各1冷NoModel Worker、一个成功Run/三VERIFIED工具、一个完整MD成果；实际模型请求0。确认前WAITING_APPROVAL、零Operation/新增成果，明确另行确认后才执行。任意自然语言Goal草稿保留；同源后台refresh保留显式列，重复确认不增POST，丢失真实接受响应后精确原body/key恢复，项目往返的迟到确认不劫持选择。

最终每例新增两条内存克隆负断言，拒绝双侧缺失合同fp或checker；不是服务响应篡改或新的模型调用。服务端仍逐项验同Run实际intent/receipt/local_effect、独立count/Decimal及完整MD回读，结果仅PASS_CSV_REPORT_CONTRACT，general NOT_RUN/人工PENDING/发布关闭。3份实际捕获MD各730字节，逐字节等于各自真实保存内容和hash；driver等待URL revoke后才取字节，JSON没有单独URL对象列表，不伪造该元数据。

前源599独立28 PASS/76.911s作为带展示BLOCK的预验证原件原样保留，manifest SHA256 `2a17267ba1e4843664f1ba7f11a3c2d23d68157477ccc1aa73b89c5fe28fc882`。其中19新API+4普通成果回归+2原fixed合计25节点未在402重跑，保留实际599执行源，不改签；三页面复跑不增加唯一节点，选择范围仍28，不能统计31唯一。599中旧普通4例仍16合成Mock请求，原fixed2仍各1 MockTransport；本最终新3例0模型，分列不混称NoModel。

不新增executor.kind/ref或Grant政策，保存仍按原工具派生read Grant；旧fixed checker/global Limits和普通自然任务NOT_RUN保持。范围为合成SQLite、实际ASGI/servedJS、JSDOM/Node Blob；新导航例仅实际验证项目时序，不冒称全部身份/工作区组合。PG/native/Windows/真实模型语义/远端CI及旧矩阵未执行。{len(manifest)}份raw（完整命令RC/XML/log、3DB/pageJSON/SQLproof/捕获MD、Git before/after/delta及工具/cache）逐件SHA/size与覆盖校验通过；本目录停止写入。
'''
(p/'independent-review.md').write_text(review)
for name,v in manifest.items():
 data=(p/name).read_bytes();assert len(data)==v['bytes']and hashlib.sha256(data).hexdigest()==v['sha256']
assert set(manifest)=={str(f.relative_to(p))for f in p.rglob('*')if f.is_file()and not f.is_symlink()and f.name not in excluded}
for name in['independent-review.md','independent-proof.json','raw-manifest.json','raw-SHA256SUMS','source-after.json','source-delta-from-599.json','junit.xml','pytest.log','command.txt']:
 data=(p/name).read_bytes();print(hashlib.sha256(data).hexdigest(),len(data),name)
print('RAW',len(manifest),'ALL_FILES',len(manifest)+4,'READY_IMMUTABLE')
