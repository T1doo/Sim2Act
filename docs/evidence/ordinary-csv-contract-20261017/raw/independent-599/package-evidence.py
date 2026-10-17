from pathlib import Path
import hashlib,json,sqlite3,xml.etree.ElementTree as ET
p=Path(__file__).parent;source='599052cbadae21b4a7ba8738fb889ea970c11e84'
suite=ET.parse(p/'junit.xml').getroot().find('testsuite');assert suite.get('tests')=='28'and all(suite.get(k)=='0'for k in ['failures','errors','skipped']);assert(p/'pytest.exit-code').read_text().strip()=='0'
b=json.loads((p/'source-before.json').read_text());a=json.loads((p/'source-after.json').read_text());assert b['head']==a['head']==source and b['files']==a['files']and a['all_match_frozen']
pages={};dbs={}
for f in sorted((p/'data').glob('*/result.json')):
 if f.parent.is_symlink():continue
 r=json.loads(f.read_text());assert r['status']=='PASS';assert(f.parent/'node.stderr').stat().st_size==0
 captures=[]
 for c in sorted(f.parent.glob('*.md')):
  data=c.read_bytes();captures.append({'path':str(c.relative_to(p)),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
 pages[f.parent.name]={'case':r['case'],'family':'new_NoModel_page'if'prospective'in f.parent.name else'ordinary_result_regression','checks':len(r['checks']),'api':len(r['requests']),'get':sum(q['method']=='GET'for q in r['requests']),'post':sum(q['method']=='POST'for q in r['requests']),'assets':len(r['assets']),'captures':captures,'blob_metadata':r.get('blobs'),'controlled_deliveries':[{'index':i,'path':q['path'],'description':q['controlled_delivery']}for i,q in enumerate(r['requests'])if'controlled_delivery'in q]}
for f in sorted((p/'data').glob('*/fixture.db')):
 if f.parent.is_symlink():continue
 c=sqlite3.connect('file:'+str(f)+'?mode=ro',uri=True)
 counts={name:c.execute(f'SELECT count(*) FROM {name}').fetchone()[0]for name in['runs','operations','attempts','reservations','resources','local_effects']}
 counts['run_status']=dict(c.execute('SELECT status,count(*) FROM runs GROUP BY status').fetchall());counts['claimed_events']=c.execute("SELECT count(*) FROM events WHERE kind='CLAIMED'").fetchone()[0];c.close();dbs[f.parent.name]=counts
assert len(dbs)==28
excluded={'raw-manifest.json','raw-SHA256SUMS','independent-proof.json','independent-review.md'}
files=sorted(f for f in p.rglob('*')if f.is_file()and not f.is_symlink()and f.name not in excluded)
manifest={str(f.relative_to(p)):{'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'bytes':f.stat().st_size}for f in files};(p/'raw-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');(p/'raw-SHA256SUMS').write_text(''.join(f"{v['sha256']}  {k}\n"for k,v in manifest.items()))
proof={'source':source,'returncode':0,'junit':suite.attrib,'admission':'PREVALIDATION_ONLY_STATIC_DISPLAY_BLOCK','static_block':'csvReportPassed accepted paired missing contract fingerprints/checker through undefined equality. Backend checker/permissions unaffected; fixed by later402, not retested or re-signed here.',
'source_file_count':len(a['files']),'before_after_equal_frozen_git':True,'selected28':{'new_API':19,'new_page':3,'related_ordinary_result':4,'related_existing_fixed':2},'independent_repeat_extra_unique':0,'pages':pages,'post_run_sqlite_readonly_observation_not_additional_test':dbs,
'new_NoModel_execution':'10 successful structured Run executions plus one budget-tightened failed execution; 4 use cold Store (main+three pages), remaining7 use existing Store. Separately one explicit lease claim/reserve-denied test does not execute its Run and leaves fixture RUNNING. No model calls.',
'related_models':'Four prior ordinary result cases: 4 cold scripted workers/16 synthetic Mock requests; original fixed2 each one MockTransport provider request and two normal Worker claims. 0real. Not new NoModel counts.',
'limits':['Full page requests/responses saved for7 JSDOM cases, not a claim of per-request trace for all direct Python API assertions.28 final SQLite DBs and written API rejection/run artifacts retained.',
'Persisted-source/receipt/artifact/contract corruption cases directly modify synthetic DB for negative checking; not user-edit APIs or recovery evidence.',
'New pages capture three MD files after waiting URL revoke; their JSON does not separately persist URL metadata. Related driver does persist five Blob metadata entries/files.',
'Original fixed checker/global Limits and old arbitrary ordinary PARTIAL/NOT_RUN unchanged. No retrofit/general semantic or owner acceptance.',
'No native browser/Windows, PG, real model, remote CI/deployment or old fault matrix.'],
'raw_manifest_files':len(manifest),'raw_manifest_sha256':hashlib.sha256((p/'raw-manifest.json').read_bytes()).hexdigest()}
(p/'independent-proof.json').write_text(json.dumps(proof,indent=2,ensure_ascii=False)+'\n')
review=f'''执行源 `{source}`：指定28例独立一次实际28 PASS / 0 FAIL / 0 ERROR / 0 SKIP，RC0，JUnit {suite.get('time')}s。125份tracked src/相关测试前后与冻结Git字节一致。结果为保留预验证，因后续静态发现展示谓词双侧缺失字段仍可能PASS，**不作最终准入**；backend checker/权限不受此展示缺口影响。修复另在402源及新目录独立验证，本目录原件不改签。

范围：19个新API节点+3个新完整页面节点+4个普通成果回归+2个原fixed节点。新路径在已授权CSV/选列上，事前冻结完整MD与规则、另行确认，原Worker/dispatch三工具和整数缩放oracle独立核验；拒绝改变scope、越界、真实save授权撤销、取消、预算收紧、原合同/回执/成果合成DB损坏及旧Run追认，且reserve拒绝模型。新路径10个成功执行、1个收紧预算失败；其中main+3页面采用4个cold Store，其余7个既有Store执行。另一个仅显式claim/reserve拒绝的fixture Run有意未执行，不称全部Run终态。28个最终SQLite DB逐只读观察记录在proof。

新3页面分别11/14/13检查、36/38/52实际API、22served资产/页；完整准备/确认/无前置副作用/冷NoModel运行/同Run查看下载，lost例受控丢失真实接受响应后原键恢复，navigation例隔离迟到确认，未增加模型。原4成果回归62检查/258API/88资产，仍4冷Scripted Worker、16合成Mock请求；原fixed2仍各1 MockTransport+2 Worker claims，仅旧固定合同PASS。0真实模型。新3MD原件与同例实际保存文本相同，原回归5MD也保留；API主成功例另存saved-report.md。

页面JSON保存7个JSDOM用例的实际请求响应与资产SHA；不冒称全部直接Python API断言均有逐请求日志。否定场景中持久数据损坏是明确合成注入，不是用户编辑能力或恢复验收。原Grant政策不变，工具保存仍派生read Grant。普通语义NOT_RUN、人工PENDING、正式发布关闭。PG/native/Windows/真实模型/远端CI及旧矩阵均未执行。{len(manifest)}份raw逐件SHA/size及覆盖校验通过；目录封存后停止写入。
'''
(p/'independent-review.md').write_text(review)
for name,v in manifest.items():
 data=(p/name).read_bytes();assert len(data)==v['bytes']and hashlib.sha256(data).hexdigest()==v['sha256']
assert set(manifest)=={str(f.relative_to(p))for f in p.rglob('*')if f.is_file()and not f.is_symlink()and f.name not in excluded}
for name in['independent-review.md','independent-proof.json','raw-manifest.json','raw-SHA256SUMS','source-after.json','junit.xml','pytest.log']:
 data=(p/name).read_bytes();print(hashlib.sha256(data).hexdigest(),len(data),name)
print('RAW',len(manifest),'ALL_FILES',len(manifest)+4,'READY_IMMUTABLE')
