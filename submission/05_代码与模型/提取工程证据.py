"""Read the frozen local record; export only explicitly allowlisted evidence fields.
No model request, database start, or credential access is performed.
"""
from pathlib import Path
from datetime import datetime, timezone
from decimal import Decimal
import json, hashlib, csv, shutil, re

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'docs/evidence/r0-convergence-20261105/managed-pa-stage-count-21b33dc4-run6-local-writer-check.json'
OUT=ROOT/'submission/05_代码与模型/工程证据_21b33dc4_v02';OUT.mkdir(exist_ok=True)
d=json.loads(SOURCE.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(name,obj):
    text=json.dumps(obj,ensure_ascii=False,indent=2)
    assert not re.search(r'\bsk-[A-Za-z0-9]{15,}',text)
    assert 'Bearer ' not in text
    (OUT/name).write_text(text,encoding='utf-8')
def pick(obj,names):return {k:obj[k] for k in names if k in obj}
def utc(n):return datetime.fromtimestamp(n,timezone.utc).isoformat(timespec='milliseconds')
event_fields={'attempt_id','index','fence','operation_id','tool_ref','source_ref','step_id','status','error','result_version','artifact_resource','report_fingerprint','candidate_fingerprint','response_fingerprint','usage_fingerprint','raw_fingerprint','namespace','app_run_id','instance_id','release_id','input_fingerprint','request_model','mode','created_at','parameters_fingerprint','reserved_tokens','reservation_fingerprint','archive_fingerprint','reception_fingerprint','attempt_fingerprint','application_generation','goal_source'}
events={}
event_fields.update({'family','body_fingerprint','decoded_sha256','canonical_sha256','byte_count','complete','omission'})
for stage,key in [('generate','run'),('source','source'),('cold','cold')]:
    events[stage]=[dict(id=e['id'],run_id=e['run_id'],created_at=e['created_at'],kind=e['kind'],data=pick(e['data'],event_fields)) for e in d[key]['events']]
    # Preserve body hash metadata but never the private body or model reasoning.
slots=[]
for i,slot in enumerate(d['accounting']['ledger']['slots'],1):
    identity=pick(slot['identity'],['stage','run_id','attempt_id','runtime_id','version','fence','wire_sha256','wire_bytes'])
    slots.append(dict(index=i,identity=identity,reserved_at=slot['reserved_at'],attempted=slot['attempted'],accepted=slot['accepted'],settlement=pick(slot['settlement'],['outcome','response_sha256','response_ascii_bytes','prompt_tokens','completion_tokens','total_tokens'])))
candidate=pick(d['draft']['candidate'],['namespace','manifest','actions','spec_recipe','source_hash','goal','model_sample_check','goal_application'])
# These payloads are structured public sample specifications, not hidden reasoning.
dump('候选应用规格.json',candidate)
snapshot=dict(source_commit=d['source_commit'],source_record_sha256=sha(SOURCE),model_alias=d['preparation']['contract']['model'],model_alias_ledger=d['accounting']['ledger']['scope']['model'],approval_snapshot=pick(d['approval'],['status','live_allowed','formal_publication_enabled','actual_model_requests','contract_fingerprint','approval_fingerprint']),approval_time=pick(d['approval']['approval'],['approved_at','expires_at','contract_fingerprint']),accounting_flags=pick(d['accounting'],['live_allowed','dispatch_authorized','real_source_verified']),request_slots=slots,events=events,application=pick(d['app'],['id','name','namespace','formal_publication_enabled']),release=pick(d['release'],['id','namespace','formal_publication_enabled','fingerprint']),instance=pick(d['instance'],['id','source_app_id','runtime_id','release_id','revision','data_version','namespace','formal_publication_enabled']),runs={},source_cold_read=d['source_cold_read'])
for label in ['source','cold']:
    snapshot['runs'][label]=pick(d[label],['id','app_run_id','instance_id','release_id','status','result_version','semantic_status','owner_acceptance','citation_status','semantic_goal_acceptance','namespace','formal_publication_enabled'])
    snapshot['runs'][label]['steps']=d[label]['steps']
    snapshot['runs'][label]['known_effects']=[pick(e,['instance_id','version','run_id','release_id','schema_version','fingerprint']) for e in d[label]['known_effects']]
snapshot['generation_status']=d['run']['status']
dump('冻结记录_脱敏字段.json',snapshot)

request_rows=[]
for slot in slots:
    ident=slot['identity'];rec=slot['settlement'];ev=events[ident['stage']]
    matching=[e for e in ev if e['data'].get('attempt_id')==ident['attempt_id']]
    received=next(e for e in matching if e['kind'] in ['GA_RECEIVED','NS_RECEIVED'])
    request_rows.append(dict(request=slot['index'],stage=ident['stage'],run_id=ident['run_id'],attempt_id=ident['attempt_id'],model_alias=snapshot['model_alias'],ledger_reserved_unix=slot['reserved_at'],ledger_reserved_utc=utc(slot['reserved_at']),received_event_unix=received['created_at'],received_event_utc=utc(received['created_at']),prompt_tokens=rec['prompt_tokens'],completion_tokens=rec['completion_tokens'],total_tokens=rec['total_tokens'],outcome=rec['outcome'],wire_sha256=ident['wire_sha256'],response_sha256=rec['response_sha256']))
with (OUT/'逐次模型用量.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(request_rows[0]));w.writeheader();w.writerows(request_rows)
timings=[]
for stage,ev in events.items():
    accepted=next(e for e in ev if e['kind']=='ACCEPTED')
    end=next(e for e in reversed(ev) if e['kind']=='STATE')
    delta=Decimal(str(end['created_at']))-Decimal(str(accepted['created_at']))
    timings.append(dict(stage=stage,run_id=accepted['run_id'],start_event_id=accepted['id'],end_event_id=end['id'],accepted_unix=accepted['created_at'],terminal_unix=end['created_at'],accepted_utc=utc(accepted['created_at']),terminal_utc=utc(end['created_at']),seconds=str(delta),terminal_status=end['data']['status'],definition='同一运行ACCEPTED事件至终态STATE事件，包含排队、等待、模型与工具处理，不是纯模型网络延迟。'))
dump('阶段耗时定义与明细.json',timings)
existing=ROOT/'deliverables/Sim2Act_书生规则审阅复用_20261106'
for name in ['原材料.txt','新材料.txt','原材料_清单.json','新材料_清单.json','原材料_成果.md','新材料_成果.md','verification.json']:shutil.copy2(existing/name,OUT/name)
totals={k:sum(r[k] for r in request_rows) for k in ['prompt_tokens','completion_tokens','total_tokens']}
assert totals['total_tokens']==17336 and totals['prompt_tokens']+totals['completion_tokens']==17336
assert len(request_rows)==5
assert [r['total_tokens'] for r in request_rows]==[2672,6514,6127,1016,1007]
dump('主张与证据索引.json',dict(source_commit=d['source_commit'],request_count=5,totals=totals,claim_sources={'model_alias':'冻结记录_脱敏字段.json / model_alias + model_alias_ledger','five_requests_and_tokens':'冻结记录_脱敏字段.json / request_slots，逐次模型用量.csv','stage_elapsed':'冻结记录_脱敏字段.json / events，阶段耗时定义与明细.json','candidate_structure':'候选应用规格.json','instance_and_result_versions':'冻结记录_脱敏字段.json / instance + runs','citation_slices':'原材料_清单.json，新材料_清单.json'},not_claimed=['三次生成请求不等于三次错误修订','未包含完整供应商原始请求与响应正文，不提供供应商侧独立签名证明','批准与账本快照的live_allowed等原值保留，历史证据不构成新的执行授权','该内部工程链不等于正式发布、中文多格式申报、P-B、native或R0已验收']))
lines=['# 冻结工程证据补充包','','本包仅从已有冻结记录按字段白名单导出，没有新模型调用、数据库启动或业务重跑。脱敏后保留模型别名、逐次用量、候选规格、事件时间、步骤回执及结果归属。','','## 五次记录的用量','','| 次序 | 阶段 | 输入tokens | 输出tokens | 总tokens |','| --- | --- | ---: | ---: | ---: |']
for r in request_rows:lines.append(f'| {r["request"]} | {r["stage"]} | {r["prompt_tokens"]} | {r["completion_tokens"]} | {r["total_tokens"]} |')
lines+=['',f'合计：{totals["prompt_tokens"]} + {totals["completion_tokens"]} = {totals["total_tokens"]} tokens。','','## 时间的统计口径','','| 阶段 | 终态 | ACCEPTED至STATE秒数 |','| --- | --- | ---: |']
for t in timings:lines.append(f'| {t["stage"]} | {t["terminal_status"]} | {t["seconds"]} |')
lines+=['','上述耗时含排队与工具检查，来自事件墙钟差。不是纯模型延迟，也不是性能基准。两份输入为90和94字节的录制样例，不能据此宣称中文四文件场景的低成本或秒级性能。','','## 生成过程能证明什么','','三次generate请求之间出现材料读取回执、规格检查回执、最终候选验证事件。保存的候选包含read → model_all → verify → save步骤及字段来源。当前导出的事件没有GA_DIAGNOSTIC；不能把三次调用直接讲成三次错误修复，也不补造模型隐藏思维链。','','生成运行终态为PARTIAL、草案验证为预览范围，后续保存到INTERNAL_ENGINEERING_ONLY的限定应用版本。两次实例执行SUCCEEDED，引用核验PASS，语义验收NOT_RUN、人工签收PENDING。保留原始formal_publication_enabled=false及live_allowed/dispatch_authorized等快照值，不将内部链等同正式发布资格，也不把历史记录用作新授权。','','## 独立核对','','运行同目录verify_evidence.py，无需模型密钥或数据库。它从脱敏原始字段重新计算请求数、用量及事件耗时，核对同实例/同应用发布关系、两次结果版本、六条原文引用与文件哈希。该检查验证随包记录一致性，不重跑产品，不证明记录来自供应商的独立签名。','','完整源记录仍留项目内受控位置；包内不含密钥、配额主体、账号标识、endpoint、review token、local-installation、数据库或本机进程路径。']
(OUT/'README.md').write_text('\n'.join(lines),encoding='utf-8')
print(json.dumps(dict(requests=5,totals=totals,timings=[{'stage':t['stage'],'seconds':t['seconds']} for t in timings]),ensure_ascii=True))
