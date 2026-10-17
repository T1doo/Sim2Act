from pathlib import Path
import hashlib,json,sqlite3,xml.etree.ElementTree as ET
p=Path(__file__).parent;provenance=json.loads((p/'export-provenance.json').read_text());source=provenance['source'];s=ET.parse(p/'junit.xml').getroot().find('testsuite');rc=int((p/'pytest.exit-code').read_text());before=json.loads((p/'source-before.json').read_text());after=json.loads((p/'source-after.json').read_text());assert before['files']==after['files']and after['all_match_frozen_git']
setup=source.startswith('54567147');assert(rc==4 and s.get('errors')=='1')if setup else(rc==1 and s.get('failures')=='5'and s.get('errors')=='0')
cases={}
for f in sorted((p/'data').glob('*/result.json')):
 if f.parent.is_symlink():continue
 r=json.loads(f.read_text());d=json.loads((f.parent/'database-proof.json').read_text());assert r['status']=='FAIL'and d['worker_runs']==0
 conn=sqlite3.connect('file:'+str(f.parent/'fixture.db')+'?mode=ro',uri=True);counts={name:conn.execute(f'SELECT count(*) FROM {name}').fetchone()[0]for name in['operations','attempts','reservations','resources']};counts['run_status']=dict(conn.execute('SELECT status,count(*) FROM runs GROUP BY status'));conn.close();assert counts['operations']==counts['attempts']==counts['reservations']==0 and counts['resources']==1
 cases[d['case']]={'directory':str(f.parent.relative_to(p)),'error':r['error'],'checks_before_failure':len(r['checks']),'api':len(r['requests']),'post':sum(q['method']=='POST'for q in r['requests']),'assets':len(r['assets']),'worker_executions':0,'model_requests':0,'final_SQL_readonly_observation':counts,'observation_summary':[{k:v for k,v in o.items()if k!='proof'}for o in r.get('observations',[])]}
excluded={'raw-manifest.json','raw-SHA256SUMS','independent-proof.json','independent-review.md'}
files=sorted(f for f in p.rglob('*')if f.is_file()and not f.is_symlink()and f.relative_to(p).parts[0]!='snapshot'and f.name not in excluded)
manifest={str(f.relative_to(p)):{'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'bytes':f.stat().st_size}for f in files};(p/'raw-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');(p/'raw-SHA256SUMS').write_text(''.join(f"{v['sha256']}  {k}\n"for k,v in manifest.items()))
proof={'source':source,'returncode':rc,'junit':s.attrib,'classification':'COLLECTION_ERROR_NO_PRODUCT_CASE_EXECUTED'if setup else'EXPECTED_REAL_PRODUCT_RED_5','cases':cases,'input_file_count':len(before['files']),'before_after_identical_to_git_blob':True,'execution_input_classification':'snapshot/src, snapshot/tests, pyproject and the exact same-Git import fixture are reproducible inputs, not new runtime evidence. source-before/after record every Git blob/SHA256; snapshot copies excluded from raw-manifest and archive denominator. Dependency node_modules symlink is read-only use only.',
'initial_collection_failure':'545 exported exactly requested src/tests/pyproject; import chain rows→goal_text_applications→bounded_agent_apps required a Git independent-gold.json absent from that export.0product scenarios; original failure unchanged. New authorized2c530 export includes just that same-Git fixture; no rerun545 or workspace-source fallback.'if setup else'545 collection error was retained separately;2c530 five cases executed once from its own source export including the single required same-Git import JSON. No active working tree code or historical bundle used.',
'limits':['Actual served JS/authenticated ASGI on synthetic SQLite/JSDOM;0model and0tool execution in red cases. Pending/UNKNOWN real confirmation did persist QUEUED, not unaccepted/no-effect Run state.','No native browser/PG/real model/CI or old matrix. No fixes or test retries in this directory.'],
'raw_manifest_files':len(manifest),'raw_manifest_sha256':hashlib.sha256((p/'raw-manifest.json').read_bytes()).hexdigest()}
(p/'independent-proof.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
if setup:body=f'Git源`{source}`独立导出首轮RC4，JUnit{s.get("time")}s，collection error1、产品场景执行0。缺少测试导入链所需的同Git `docs/evidence/bounded-agent-offline-20261006/independent-gold.json`；不是产品红，也不是访问拒绝。572个输入文件导出及前后Git字节校验均完成，日志/XML/命令/RC原件保留。没有在此源自动重试；新增授权2c530五例在另一个目录执行。'
else:body=f'Git源`{source}`独立五红实际RC1，5 FAIL / 0 ERROR / 0 SKIP，JUnit{s.get("time")}s。未确认返回勾选无fresh GET且按钮仍禁用；pending真实confirm200后旧view未换；UNKNOWN返回可见恢复按钮仍0新请求；项目/账号重开继承旧checked。均为真实UI断言失败，非harness错误。5个任务0Worker领取执行/0Operation/0attempt/0reservation；pending与UNKNOWN的原确认已真实接受为QUEUED，其余WAITING_APPROVAL。共193产品API/110served资产，五DB、完整请求响应pageJSON、status观察及stderr原样保留。573个导出输入文件前后与Git一致。'
body+='\n\n快照仅从指定commit的Git对象导出；node_modules仅作为只读依赖使用，未编辑工作区。snapshot源码/测试为可重建输入，原件计数排除复制输入树，全部Git/SHA256保留于source-before/after。运行输出、DB、请求JSON、日志/XML等全部列入raw-manifest；没有重建缺失执行原件。合成SQLite/实际ASGI/servedJS/JSDOM，不代表native/Windows、PG、真实模型或CI。目录封存后停止写入。\n'
(p/'independent-review.md').write_text(body)
for name,v in manifest.items():
 data=(p/name).read_bytes();assert len(data)==v['bytes']and hashlib.sha256(data).hexdigest()==v['sha256']
for name in['independent-review.md','independent-proof.json','raw-manifest.json','raw-SHA256SUMS','source-after.json','junit.xml']:
 data=(p/name).read_bytes();print(hashlib.sha256(data).hexdigest(),name)
print('RAW',len(manifest),'TOTAL_OUTPUT_FILES',len(manifest)+4,'REPRODUCIBLE_INPUTS_EXCLUDED',len(before['files']),'READY_IMMUTABLE')
