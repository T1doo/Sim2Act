from pathlib import Path
import hashlib,json,os,subprocess,xml.etree.ElementTree as ET
p=Path(__file__).parent;source='aed84dfc36eb6e810760331bd72b5f9853b981d5';red_source='2c530db7c25836f5851de057771450ff632c379d'
s=ET.parse(p/'junit.xml').getroot().find('testsuite');assert s.get('tests')=='9'and all(s.get(k)=='0'for k in['failures','errors','skipped']);assert(p/'pytest.exit-code').read_text().strip()=='0'
b=json.loads((p/'source-before.json').read_text());a=json.loads((p/'source-after.json').read_text());assert b['files']==a['files']and b['head']==a['head']==source and a['all_match_frozen_git']
changed=subprocess.check_output(['git','-c','core.fsmonitor=false','diff','--name-only',red_source,source,'--','src','tests'],cwd='/workspace/Sim2Act',env={**os.environ,'GIT_OPTIONAL_LOCKS':'0'}).decode().splitlines();assert changed==['src/sim2act/web/app.js','src/sim2act/web/ordinary-csv.js']
cases={}
for f in sorted((p/'data').glob('*/result.json')):
 if f.parent.is_symlink():continue
 r=json.loads(f.read_text());d=json.loads((f.parent/'database-proof.json').read_text());assert r['status']=='PASS'and(f.parent/'node.stderr').stat().st_size==0
 new='prospective'in f.parent.name;name=r['case']if new else'ordinary-result-workspace-return';actual=d['proof']['actual']if new else d['proof']['actual_run'];artifact=d['proof']['artifact'];caps=[]
 for md in sorted(f.parent.glob('*.md')):
  data=md.read_bytes();assert data==artifact['content'].encode()and hashlib.sha256(data).hexdigest()==artifact['hash'];caps.append({'path':str(md.relative_to(p)),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
 assert len(caps)==1
 cases[name]={'directory':str(f.parent.relative_to(p)),'checks':len(r['checks']),'api':len(r['requests']),'get':sum(q['method']=='GET'for q in r['requests']),'post':sum(q['method']=='POST'for q in r['requests']),'assets':len(r['assets']),'cold_workers':1,'worker_kind':'NoModel'if new else'ScriptedMock','synthetic_model_requests':0 if new else d['synthetic_model_requests'],'real_model_requests':0,'actual_run':actual['id'],'actual_status':actual['status'],'goal_acceptance':actual['result']['goal_acceptance'],'captured_md':caps,'observations':[{k:v for k,v in o.items()if k not in['proof','actual_run','visible_result']}for o in r.get('observations',[])],'controlled_reply_loss':[{'index':i,'path':q['path'],'description':q['controlled_delivery']}for i,q in enumerate(r['requests'])if'controlled_delivery'in q]}
excluded={'raw-manifest.json','raw-SHA256SUMS','independent-proof.json','independent-review.md'}
files=sorted(f for f in p.rglob('*')if f.is_file()and not f.is_symlink()and f.name not in excluded)
manifest={str(f.relative_to(p)):{'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'bytes':f.stat().st_size}for f in files};(p/'raw-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');(p/'raw-SHA256SUMS').write_text(''.join(f"{v['sha256']}  {k}\n"for k,v in manifest.items()))
proof={'source':source,'returncode':0,'junit':s.attrib,'admission':'PASS_LIMITED_CONFIRMATION_SCOPE_AND_WORKSPACE_FIX','cases':cases,'checks':149,'api':409,'get':389,'post':20,'served_assets':198,'new_pages_NoModel_cold_workers':8,'new_pages_model_requests':0,'related_ordinary_cold_scripted_workers':1,'related_ordinary_synthetic_Mock_requests':4,'real_model_requests':0,'input_file_count':len(a['files']),'input_count_explanation':'571 tracked src/tests plus pyproject.toml; only hashes retained, not copied source counted as runtime evidence.','before_after_identical_git_bytes':True,'red_green_src_tests_changed_paths':changed,'backend_and_all_test_bytes_unchanged_from_red':True,'independent_repeat_additional_unique_nodes':0,
'previous_reds':[{'source':'54567147fd8220eae05fe708196df099f00654df','directory':'/tmp/csv-report-confirm-workspace-red-independent-54567147-20261017','classification':'collection error /0product execution','manifest_sha256':'183922927f0ac474dbb5002ee24d82ee6c067abe83c550ed3cde452904d77e96'},{'source':red_source,'directory':'/tmp/csv-report-confirm-workspace-red-independent-2c530db7-20261017','classification':'actual5product failures','junit_seconds':'25.814','manifest_sha256':'eaa77e81fde27ef832c127dc59f267fccc852e923a16190a183ec5ceed74919c'}],
'static_review':{'blockers':[],'view_identity':'New workspace view object and owner/workspace gates invalidate all detached closures; ready acknowledgement resets across scope. Same Run background redraw shares current view appropriately.','fresh_ACK':'New checked acknowledgement first GETs the exact Run; checks id,WAITING_APPROVAL,Run version,unconfirmed flag,contract fp and full snapshot before enabling original atomic POST. View identity/workspace and ack generation rechecked after await.','pending_unknown':'Original body/key/state survive without automatic GET/POST on return. New unchecked view provides explicit original-Run GET; pending oldresponse cannot overwrite fresh current readback, UNKNOWN explicit retry uses exact original key.','proof_version':'Read-only proof uses run_version, avoiding collision with spec.version.','unchanged_boundary':'Backend executor/Grant/acceptance/checker untouched. No arbitrary Goal promotion or prior25 re-signing.'},
'limits':['Actual ASGI/SQLite, full served JS and JSDOM/Node Blob, not native browser.8structured scopes pass only exact prospective CSV report contract; generalNOT_RUN/ownerPENDING, publish closed.','Pending and UNKNOWN response holds/loss are explicit synthetic delivery controls after real server acceptance, not all transport/crash recovery scenarios.','8new captured730B MD plus1old109B MD bind exact resource hashes; drivers wait URL revoke. New JSON does not separately persist Blob URL arrays.','Old ordinary result case separately creates fixture queued otherRun and calls scripted Mock4 times; not a zero-model whole batch or only one total fixturePOST.','No native Windows/browser, PG, real model/semantic evaluation, CI/deployment or old fault matrix. Old59925cases retain original execution source.'],
'raw_manifest_files':len(manifest),'raw_manifest_sha256':hashlib.sha256((p/'raw-manifest.json').read_bytes()).hexdigest()}
(p/'independent-proof.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
review=f'''最终源`{source}`独立有限准入通过。仅执行8个指定CSV页面参数+已有ordinary结果workspace-return1例，共9例一次，RC0，9PASS/0FAIL/0ERROR/0SKIP，JUnit{s.get('time')}s。571份tracked src/tests加pyproject共572输入文件before/after与Git逐字相同。对真实五红2c530的src/tests差异严格仅app.js与ordinary-csv.js，后端和测试字节全不变。

149检查、409实际产品API（389GET/20POST含明确原键重放）、198served资产逐SHA核验。8新页各1冷NoModel Worker、0模型请求，均完成同Run三VERIFIED工具/完整MD；相关ordinary返回1例另1冷Scripted Worker/4合成Mock请求，保持PARTIAL/NOT_RUN，0真实模型。9份实际MD原件逐字节等于各自授权保存内容/hash：新8份各730B，旧1份109B；driver等待URL revoke后捕获。

五个真实红缺口均关闭：未确认返回的新控件先fresh GET完整原Run再使显式确认可用；pending返回新建未勾选锁定view，显式原Run GET恢复已接受QUEUED，旧迟到response不污染新回读；UNKNOWN返回由新控件用原body/key明确恢复；项目/身份往返不继承checked，旧detached控件0请求，新勾选重新鉴权核完整snapshot/version/fp。返回本身0自动GET/POST，后台重画不复活旧scope；只读proof以run_version显示原Run版。原三页直接回归及旧成果返回同时通过。

545首轮独立snapshot收集错误原件另留，产品执行0；2c530另目录真实5FAIL/25.814s，0Worker执行/0Operation/0模型（pending/UNKNOWN确认已实际接受，故为QUEUED）。这两类不混称红，不覆盖或补造缺失原件。红快照源码/测试按可重建Git输入分类，仅输入hash作为归档证据，未把数百源码复制件计作新增运行原件。

范围限定合成SQLite、实际ASGI/served JS、JSDOM/Node Blob；通用语义NOT_RUN、人工PENDING、发布关闭。无新executor/Grant/成功定义，不改fixed checker或此前59925例执行SHA。原生Windows/browser、PG、真实模型、CI及旧故障矩阵未执行。{len(manifest)}份raw逐SHA/size与覆盖核验，完整命令RC/log/XML/9DB/pageJSON/SQLproof/9MD及source hashes保留；目录封存后停止写入。
'''
(p/'independent-review.md').write_text(review)
for name,v in manifest.items():
 data=(p/name).read_bytes();assert len(data)==v['bytes']and hashlib.sha256(data).hexdigest()==v['sha256']
assert set(manifest)=={str(f.relative_to(p))for f in p.rglob('*')if f.is_file()and not f.is_symlink()and f.name not in excluded}
for name in['independent-review.md','independent-proof.json','raw-manifest.json','raw-SHA256SUMS','source-after.json','junit.xml','pytest.log','command.txt']:
 data=(p/name).read_bytes();print(hashlib.sha256(data).hexdigest(),len(data),name)
print('RAW',len(manifest),'ALL_OUTPUTS',len(manifest)+4,'READY_IMMUTABLE')
