"""Local draft contract and full-wire MOCK shape sizing; never calls a model."""
import copy
import hashlib
import json
from pathlib import Path
import httpx
from sim2act.tools import definitions
from oracle import parse,render,validate,Rejected

out=Path(__file__).resolve().parent
repo=out.parents[2]
source=repo/'docs/sources/V5/平台产品设计.md'
lines=source.read_text().splitlines()
selected='\n'.join(lines[449:458])
rid='res_'+'c'*32
keys=['release_instance_preview','version_and_dynamic_authorization','compatible_upgrade_rollback','rollback_boundaries']
obligations=[['immutable_release','instance_owns_data_and_runs','new_release_preserves_data','preview_test_namespace','no_production_write'],['bind_validated_dependencies','pointer_version_compare','run_pins_release','dynamic_authorization_each_action'],['compatible_upgrade_only','reject_breaking_delete_type_migration','rollback_checks_current_data'],['release_rollback_not_data_rollback','release_rollback_not_external_compensation','backup_migration_compensation_separate_evidence']]
gold={'contract_version':1,'source':{'resource_ref':rid,'document_id':'v5-platform-product','document_version':1,'document_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'selection_sha256':hashlib.sha256(selected.encode()).hexdigest(),'line_start':450,'line_end':458},'rules':[{'rule_key':k,'line_start':n,'line_end':n,'quote':lines[n-1],'obligations':v} for k,n,v in zip(keys,[452,454,456,458],obligations,strict=True)]}
contract={'kind':'DEVELOPER_DRAFT_OFFLINE_CONTRACT','gold_owner_acceptance':'PENDING','product_action':'NOT_IMPLEMENTED','input':{'format':'md','selection_utf8_bytes':len(selected.encode()),'selection_lines':9,'local_source':'docs/sources/V5/平台产品设计.md','external_transmission':'NOT_AUTHORIZED_FOR_THIS_FUTURE_TASK'},'gold':gold}
(out/'contract.json').write_text(json.dumps(contract,indent=2,ensure_ascii=False)+'\n')
valid={'checklist':gold,'markdown':render(gold)}
assert validate(valid,contract)
negative=[]
for fault in ['wrong_resource','wrong_document','wrong_version','bool_version','wrong_document_hash','wrong_selection_hash','wrong_selection_start','extra_source_field','missing_rule','duplicate_rule','reordered_rules','unknown_rule','wrong_quote','wrong_span','bool_span','missing_obligation','extra_obligation','invented_quote','extra_rule_field','extra_envelope_field','wrong_markdown','script_markdown','old_answer_cache','empty_rules','wrong_contract_version']:
    v=copy.deepcopy(valid);s=v['checklist']['source'];rr=v['checklist']['rules']
    if fault=='wrong_resource':s['resource_ref']='res_'+'d'*32
    elif fault=='wrong_document':s['document_id']='another-spec'
    elif fault=='wrong_version':s['document_version']=2
    elif fault=='bool_version':s['document_version']=True
    elif fault=='wrong_document_hash':s['document_sha256']='0'*64
    elif fault=='wrong_selection_hash':s['selection_sha256']='0'*64
    elif fault=='wrong_selection_start':s['line_start']=449
    elif fault=='extra_source_field':s['path']='/tmp/forbidden'
    elif fault=='missing_rule':rr.pop()
    elif fault=='duplicate_rule':rr[1]=copy.deepcopy(rr[0])
    elif fault=='reordered_rules':rr.reverse()
    elif fault=='unknown_rule':rr[0]['rule_key']='unregistered'
    elif fault=='wrong_quote':rr[0]['quote']='发布可以删除实例数据'
    elif fault=='wrong_span':rr[0]['line_start']=454
    elif fault=='bool_span':rr[0]['line_start']=True
    elif fault=='missing_obligation':rr[0]['obligations'].pop()
    elif fault=='extra_obligation':rr[0]['obligations'].append('allow_production_write')
    elif fault=='invented_quote':rr[0]['quote']+=' 自动批准权限。'
    elif fault=='extra_rule_field':rr[0]['url']='https://example.invalid'
    elif fault=='extra_envelope_field':v['script']='arbitrary generated code'
    elif fault=='wrong_markdown':v['markdown']='unrelated'
    elif fault=='script_markdown':v['markdown']+='<script>bad()</script>'
    elif fault=='old_answer_cache':v={'checklist':{'answer':'42'},'markdown':'42'}
    elif fault=='empty_rules':v['checklist']['rules']=[]
    else:v['checklist']['contract_version']=2
    try:validate(v,contract)
    except Rejected:negative.append({'fault':fault,'status':'REJECTED'})
    else:raise AssertionError(fault)
for fault,raw in [('duplicate_json_key','{"checklist":{},"checklist":{},"markdown":""}'),('invalid_json','not JSON'),('oversized_json','x'*16001)]:
    try:validate(parse(raw),contract)
    except Rejected:negative.append({'fault':fault,'status':'REJECTED'})
    else:raise AssertionError(fault)

# This is fully disclosed MOCK public shape sizing; never InternModel/Client/send.
# Includes unchanged actual system message and registered full tool definitions.
previous=json.loads((repo/'docs/evidence/AT02-dual-live-20261006/results.json').read_text())
system=previous['final_trace']['runs'][0]['context']['messages'][0]
goal='从已授权选段提取规范检查清单，先读取资料，再用artifact.save_text保存checklist JSON（contract_version/source/rules），消费保存反馈后报告成果ref。每条rule仅含rule_key/line_start/line_end/逐字quote/obligations，覆盖所有规范段，不添加规则或外发。source精确绑定：'+json.dumps(gold['source'],ensure_ascii=False)+'。允许类别：'+json.dumps(keys)+'；允许义务标识词汇（自行依据原文分组，不提供gold映射）：'+json.dumps([x for v in obligations for x in v])+ '。Markdown由受信任确定性模板从校验JSON渲染，不由模型重复生成。'
messages=[system,{'role':'user','content':json.dumps({'goal':goal,'resource_refs':[rid]},ensure_ascii=False)}]
shapes=[]
def shape():
    body={'model':'intern-s2','messages':messages,'tools':definitions(),'stream':False,'max_tokens':1024}
    wire=httpx.Request('POST','https://example.invalid',json=body).content
    shapes.append({'round':len(shapes)+1,'kind':'MOCK exact draft full serialization, not actual model output','characters':len(wire.decode()),'utf8_bytes':len(wire),'sha256':hashlib.sha256(wire).hexdigest(),'roles':[m['role'] for m in messages],'max_tokens':1024,'conservative_worker_envelope':len(json.dumps({'messages':messages,'tools':definitions()},ensure_ascii=False).encode())+1024})
shape()
messages.extend([{'role':'assistant','content':'','tool_calls':[{'id':'mock-read-call','type':'function','function':{'name':'resource.read','arguments':json.dumps({'resource_id':rid})}}]},{'role':'tool','tool_call_id':'mock-read-call','content':json.dumps({'operation_id':'op_'+'e'*32,'status':'VERIFIED','data':{'resource_id':rid,'content':selected,'hash':gold['source']['selection_sha256'],'format':'md'},'artifact_refs':[],'receipt_ref':'op_'+'e'*32,'check_results':[{'check':'receipt.readback.v1','status':'PASS'}],'usage_ref':None,'error':None},ensure_ascii=False)}])
shape()
artifact=json.dumps(gold,ensure_ascii=False,separators=(',',':'))
messages.extend([{'role':'assistant','content':'','tool_calls':[{'id':'mock-save-call','type':'function','function':{'name':'artifact.save_text','arguments':json.dumps({'text':artifact},ensure_ascii=False)}}]},{'role':'tool','tool_call_id':'mock-save-call','content':json.dumps({'operation_id':'op_'+'f'*32,'status':'VERIFIED','data':{'resource_id':'res_'+'f'*32,'hash':hashlib.sha256(artifact.encode()).hexdigest()},'artifact_refs':['res_'+'f'*32],'receipt_ref':'op_'+'f'*32,'check_results':[{'check':'receipt.readback.v1','status':'PASS'}],'usage_ref':None,'error':None},ensure_ascii=False)}])
shape()
assert len(artifact)<=8000
result={'status':'PASS_OFFLINE_DRAFT_CONTRACT_ONLY','external_model_requests':0,'owner_semantic_gold_acceptance':'PENDING','product_feature':'NOT_IMPLEMENTED','positive_gold':'PASS','negative_cases':negative,'selection_utf8_bytes':len(selected.encode()),'model_artifact_format':'checklist JSON only; Markdown deterministic derived view, not a second saved artifact','artifact_characters':len(artifact),'artifact_utf8_bytes':len(artifact.encode()),'minimum_success_chain_requests':3,'model_identity':'NOT_TESTED_MOCK_SHAPES_ONLY','draft_wire_shapes':shapes,'reserved_envelope_sum':sum(x['conservative_worker_envelope'] for x in shapes),'actual_token_usage':'NOT_APPLICABLE_NO_CALL','limitations':['Gold is developer draft, not independently owner-approved.','Shape uses prebuilt gold and synthetic receipts only, no model extraction or actual save.','Later model content/callIDs/output can be longer; actual send must independently check the full body.','Scope is one source task, not P-A/P-B candidate generation, cold application execution or publish.']}
(out/'offline-results.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
print(json.dumps({'positive':'PASS','negative_cases':len(negative),'requests_sent':0,'minimum_future_requests':3,'wire_characters':[x['characters'] for x in shapes],'wire_utf8_bytes':[x['utf8_bytes'] for x in shapes],'reserved_envelope_sum':result['reserved_envelope_sum'],'artifact_characters':len(artifact)}))
