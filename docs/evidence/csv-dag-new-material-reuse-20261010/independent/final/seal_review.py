from pathlib import Path
import json,hashlib,subprocess
R=Path('/tmp/sim2act-dag-new-csv-independent-20261010/final');repo=Path('/workspace/Sim2Act');SHA='c9ea689a27308b94c998ced5cd0cb3fd981a5c49';PRODUCT='838f9c3208792429dfa5080670144237d8f38967'
def freeze(name):
 manifest=json.loads(Path('/tmp/sim2act-dag-new-csv-20261010/source-freeze-corrected.json').read_text());assert manifest['source_sha']==SHA;files={x['path']:x['sha256'] for x in manifest['files']};assert len(files)==373
 for p,h in files.items():assert hashlib.sha256((repo/p).read_bytes()).hexdigest()==h==hashlib.sha256(subprocess.check_output(['git','show',SHA+':'+p],cwd=repo)).hexdigest()
 src={p:h for p,h in files.items() if p.startswith('src/')};assert len(src)==70
 for p,h in src.items():assert hashlib.sha256(subprocess.check_output(['git','show',PRODUCT+':'+p],cwd=repo)).hexdigest()==h
 delta=subprocess.check_output(['git','diff','--name-only',PRODUCT+'..'+SHA],cwd=repo,text=True).splitlines();assert delta==['tests/csv_material_reuse.cjs','tests/test_csv_material_reuse.py'];assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()==SHA
 out={'source_sha':SHA,'products_execution_anchor':PRODUCT,'count':373,'products':70,'Git_worktree_author_match':True,'product70_838_match':True,'test_only_delta':delta,'files':files};(R/('source-final-'+name+'.json')).write_text(json.dumps(out,indent=2));return out
before=freeze('before')
backend_delta=json.loads((R/'BACKEND_DELTA_RESULTS.json').read_text());assert backend_delta['scenario_count']==4 and backend_delta['checks']==14
for name in ['business-v1','business-report']:assert (R/name/'response.json').exists()
firstnames=['bad-column','samekey-column','samekey-target','target-grant','source-grant','target-bytes','source-bytes','foreign-owner']
for name in firstnames:
 data=json.loads((R/('negative-'+name)/'responses.json').read_text());assert len(data)==1 and data[0]['status'] in [400,403,409,422]
ui=json.loads((R/'UI_RESULTS.json').read_text())+json.loads((R/'UI_DELTA_RESULTS.json').read_text());assert len(ui)==4 and sum(x['checks'] for x in ui)==97 and all(x['status']=='PASS' for x in ui)
for x in ui:
 out=json.loads((R/('ui-'+x['case'])/'result.json').read_text());assert len(out['checks'])==x['checks'] and out['status']=='PASS'
for p in ['source-before.json','source-delta-before.json','source-backend-after.json','source-ui-after.json','source-ui-delta-after.json']:
 files=json.loads((R/p).read_text())['files'];assert {k:v for k,v in files.items() if k.startswith('src/')}=={k:v for k,v in before['files'].items() if k.startswith('src/')}
summary={'verdict':'LIMITED_PASS','source_sha':SHA,'execution_product_source_sha':PRODUCT,'non_doc373_final_Git_worktree_author_match':True,'product70_all_execution_checkpoints_identical838':True,'test_only_final_delta':before['test_only_delta'],'backend_scenarios':14,'backend_checks':64,'backend_completed_first_phase':{'scenarios':10,'checks':50,'evidence':'initial-frozen-settings-backend.log, business response.json and first8 negative responses/database-evidence'},'backend_resume_only':{'scenarios':4,'checks':14,'evidence':'BACKEND_DELTA_RESULTS.json'},'actual_API_denials':18,'all_rejected_API_entireDB_zero_writes':True,'HTTP_UI_scenarios':4,'HTTP_UI_checks':97,'total_scenarios':18,'total_checks':161,'UI_cases':ui,'independent_CSV_oracle':{'source_count':2,'target_count':3,'target_net':'7.000','target_units':'9','source_csv':'RAW in common.py','target_csv':'TARGET in backend.py','oracle':'csv.DictReader + Python Decimal, not author40/17 data'},'initial_guard_and_harness_faults_preserved':['initial-freeze Git/worktree before guard rejected changed author test, zero APIs','initial-list-shape wrongly treated manifest files list as dict, zero APIs','initial-registration-order source graph correctly rejects grant-added stale authorization403','initial-frozen-settings assigning immutable Settings before budget API'], 'unverified':['PG','native/Win11/Edge','full373 author matrix','all source retirement/old-file independence','crossproject dynamic attack','complete manual-lock and worker-fence dynamic matrix'],'limits':{'PROJECT':'PENDING/BLOCKED_PARTIAL','semantic':'UNKNOWN','owner':'PENDING','overall':'NOT_ACCEPTED','historical_timeouts':'OPEN','LIVE':0,'actual_models':0},'repo_refs_PG_CI_writes':0}
(R/'FINAL_REVIEW.json').write_text(json.dumps(summary,indent=2))
(R/'FINAL_REVIEW.md').write_text('''LIMITED_PASS — 最终c9ea689a27308b94c998ced5cd0cb3fd981a5c49；产品执行锚点838f9c3208792429dfa5080670144237d8f38967，两者70src全字节相同。最终373非doc文件与Git、worktree、作者corrected清单精确匹配。作者在独审期间只修两测试文件，旧838/bfb373不能声称贯穿不变；所有独立执行checkpoint的70src确实未变，最终373前后另行精确核对。未采用作者40/17 oracle或作者通过次数。

自主14 SQLite/API场景64检查及4真实HTTP/jsdom页97检查，共18场景161检查。原始CSV为2行小数/负数，目标为不同rid/hash/列名的3行CSV，独立Decimal算net7.000和units9。两/三步均经新target实际Run→新Release→新Instance，并重开Store执行未见units列，结果5字段/count严格整数/目标rid与实际hash正确；冷GET零全库写入，旧Release/Instance/AppRun逐row不变，principals/grants/app_drafts/resources不扩大。

18次拒绝API：非数值列、同key换列及另target、目标runtime或来源runtime撤权、两端真实bytes变但hash未变、foreignowner、当前预算降为max_tools2；以及缺origin seal、联合删origin pair+剥两plan marker并重签、两origin binding共同自签sourcehash。后三项普通plan GET、material GET和enqueue均409，所有拒绝全DB零写。保留确定性PREFIX门，实际重构源/目标来源证明，不由重签hash单独自证。

4页面读取真实冻结HTML/全部JS并核SHA：open同target ABA迟到app GET不paint新generation、零旧plan GET/POST；5种validJSON重签错误key/owner/plan cap/anchor/digest在receipt缓存前被拒，保留UNKNOWN原body/key且同键恢复实际接受；lost actualaccepted→retry403不释放、禁用换target，第三次同body恢复；合法accepted proposal延迟→source-target-source ABA时先保存原intent receipt、零旧GET/paint，之后known恢复只GET。每页6秒等待、Node90秒预算原样，无runtime errors，DB不新执行Run/Release/Instance。browser renderer仅jsdom，不代签native/真实Edge/Win11。

两次初始freeze/manifest shape错误、注册Grant顺序使已派生source graph正确403、frozen Settings赋值错误四种harness故障完整保留。预算错误后只执行未到API的budget及剩余3origin负例；未重复已通过10场景。页面先3例75后补合法lateaccepted1例22，不重跑前三。没有实际产品BLOCK。

未独立PG、native、全部373作者测试矩阵、完整worker旧fence/终态rollback/手工锁及crossproject动态攻击；未改变旧source live-read/退休语义，故不是完整AT10固定旧文件独立性。PROJECT PENDING/BLOCKED_PARTIAL、semantic UNKNOWN/owner PENDING、overall NOT_ACCEPTED，两个历史OPEN和HTTP200其他入口限制仍保留；LIVE0、真实模型0。未改共享repo/tests/refs、未碰PG/remote/CI或spawn。
''')
after=freeze('after');assert after['files']==before['files']
files=[]
for p in sorted(R.rglob('*')):
 if p.is_file() and p.name!='COPY_WHITELIST.json' and '__pycache__' not in p.parts:
  files.append({'path':str(p.relative_to(R)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(R/'COPY_WHITELIST.json').write_text(json.dumps({'artifact_root':str(R),'source_sha':SHA,'product_source_sha':PRODUCT,'scope':'Independent boundedSQLite/API/HTTP-jsdom only; all guard/harness failures retained','count':len(files),'files':files},indent=2));print(json.dumps({'verdict':'LIMITED_PASS','scenarios':18,'checks':161,'white_count':len(files),'root':str(R)},indent=2))
