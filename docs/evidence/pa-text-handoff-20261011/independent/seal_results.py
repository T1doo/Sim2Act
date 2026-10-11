import json,hashlib,subprocess,xml.etree.ElementTree as ET
from pathlib import Path
out=Path('/tmp/pa-text-handoff-review-20261011')
before=json.loads((out/'final-source-before.json').read_text())
after={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in before}
(out/'final-source-after.json').write_text(json.dumps(after,indent=2))
assert before==after,'Source changed during independent checks'
parent=Path('docs/evidence/pa-text-handoff-20261011/source-manifest.json')
full_before=json.loads(parent.read_text())['files']
full_after={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in full_before}
assert full_before==full_after,'Parent freeze manifest no longer matches'
(out/'complete-source-verification.json').write_text(json.dumps({'scope':'Independent verification of parent freeze manifest; own test before/after 14 paths separately recorded','parent_manifest':str(parent),'tracked_paths':len(full_before),'unchanged':True,'files':full_after},indent=2))
counts={}
for key,file in [('raw','raw-first.xml'),('backend','backend-final.xml'),('http_ui','http-ui-first.xml')]:
    tests=ET.parse(out/file).findall('.//testcase')
    counts[key]={'tests':len(tests),'failures':sum(t.find('failure') is not None for t in tests),'errors':sum(t.find('error') is not None for t in tests),'skips':sum(t.find('skipped') is not None for t in tests)}
    assert counts[key]['failures']==counts[key]['errors']==counts[key]['skips']==0
ui=[]
for p in sorted((out/'http-ui-first').glob('*.json')):
    data=json.loads(p.read_text());assert data['status']=='PASS' and data['api']=='IPC_IN_PROCESS_HTTP'
    assert all(full_after['src/sim2act/web/'+name]==digest for name,digest in data['loaded_source_sha256'].items())
    assert all(item['visible'] and item['enabled'] for item in data['user_actions'])
    ui.append({'scenario':data['scenario'],'checks':len(data['checks']),'visible_dom_actions':len(data['user_actions']),'post_generation_count':sum(r['method']=='POST' and r['path'].endswith('/application-runs') for r in data['requests']),'post_confirmation_count':sum(r['method']=='POST' and r['path'].endswith('/confirm-application-candidate') for r in data['requests'])})
assert len(ui)==13
assert all(item['post_generation_count']==item['post_confirmation_count']==1 for item in ui)
controlled=json.loads((out/'handoff-first.json').read_text())
assert controlled['status']=='PASS' and len(controlled['results'])==14
assert all(full_after['src/sim2act/web/'+name]==digest for name,digest in controlled['loaded_source_sha256'].items())
legacy=json.loads((out/'legacy-actual-sealed.json').read_text());assert legacy['status']=='PASS'
result={'status':'PASS','scope':'Three repairs: visible exact-app handoff; protected complete received JSON; acceptance-id poisoning keyed recovery','pytest':counts,'pytest_total':sum(v['tests'] for v in counts.values()),'controlled_not_http':{'tests':14,'status':'PASS','artifact':'handoff-first.json'},'actual_previous_sealed_sqlite_read':legacy,'http_ui_scenarios':ui,'http_ui_checks':sum(v['checks'] for v in ui),'http_ui_visible_actions':sum(v['visible_dom_actions'] for v in ui),'own_before_after_source_paths':len(before),'source_unchanged':True,'parent_freeze_independently_verified_paths':len(full_before),'source_sha256':after,'live_requests':0,'not_run':['Actual model/provider or paid calls','Semantic goal acceptance','Native browser/layout/OS or Windows','PostgreSQL','Deployment or push','Full P-A/P-B product acceptance'],'retained_exploratory_failure':{'log':'legacy-actual.log','source':'/tmp/pa-independent-review-20261011/root-temp/test_goal_feedback_repair_rele0/fixture.db','actual_status':409,'explanation':'Pre-seal earlier record lacks GA_APP_CONFIRMED and Run context repairs is 0 despite actual diagnostic; current independent proof rejects it. No migration/backfill claim. Actual prior sealed record separately passed.'},'unresolved_product_defects':[],'blockers':[],'repo_head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()}
(out/'final-review.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
report=f'''独立终审 PASS。限定于本轮三项修复，没有未解决产品缺陷或执行阻塞。

实际 pytest {result['pytest_total']} PASS / 0 FAIL / 0 SKIP：backend39（作者13＋独立adversarial26），raw21（作者14＋本轮独立7），实际 IPC/进程内 HTTP＋实际CSS可见原生DOM点击13。

受控响应、实际产品DOM另14 PASS；这一组明确为 CONTROLLED_NOT_HTTP，不混同上述13条实际HTTP链。HTTP13共{result['http_ui_checks']}检查、{result['http_ui_visible_actions']}次可见且启用的DOM动作。每条链都只有1次生成POST和1次确认POST；原key恢复仅GET。

核验：确认与丢回执恢复可见准确app/状态/term焦点；迟到nav A→B→A/目标编辑/新目标/另选app/slow app与internal GET不误跳或抢焦点，保留未保存目标。POST合法错误ID/对象ID/异常字段不可晋升RunID，原keyGET恢复。正常/RECEIVED拒绝/修订原始JSON canonical ASCII≤32768在protected Attempt参数完整保存，独立GA_RECEIVED raw sha锚阻止只改额外字段并重签metadata。两个阶段超界仅bytes/sha/OMITTED_OVERSIZE，无opaque内容，无新增执行/候选。未知未收到response不造raw且resume不重发。旧已封版实际SQLite backup只读回读app200，Attempt未补造数据，原dbSHA不变。

保全说明：先选更早未封版root-temp记录回读409的 exploratory assertion FAIL 保留于legacy-actual.log。其来源缺GA_APP_CONFIRMED，repair计数0；属于先前缺证据记录被拒绝，不是本轮raw兼容回归。改选上一轮已封版seal-temp真实记录另行PASS，证据legacy-actual-sealed.json，未改写旧证据。

本代理14个受审src/driver文件测试前后SHA一致；独立核对父冻结manifest {len(full_before)} tracked paths全部仍一致，HTTP/controlled全部加载文件哈希匹配。
goal_applications.py {after['src/sim2act/goal_applications.py']}
app.js {after['src/sim2act/web/app.js']}
goal-application.js {after['src/sim2act/web/goal-application.js']}
全部SHA见final-source-before.json/final-source-after.json、complete-source-verification.json与final-review.json。

LIVE=0。真实模型/付费、语义接受、native browser布局/Windows/PG、部署或push、完整P-A/P-B均NOT_RUN。独审未改repo，只写本/tmp目录。
'''
(out/'FINAL_REVIEW.txt').write_text(report)
print(json.dumps({'status':'PASS','pytest_total':result['pytest_total'],'controlled':14,'actual_old_sealed_sqlite':'PASS','http_ui_checks':result['http_ui_checks'],'http_ui_visible_actions':result['http_ui_visible_actions'],'hash_unchanged':True,'goal_applications_sha256':after['src/sim2act/goal_applications.py'],'app_js_sha256':after['src/sim2act/web/app.js'],'goal_application_js_sha256':after['src/sim2act/web/goal-application.js']},indent=2))
