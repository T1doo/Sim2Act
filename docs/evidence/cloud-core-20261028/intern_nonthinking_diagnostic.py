import hashlib,json,time,sys
from pathlib import Path
from sim2act.config import Settings
from sim2act.contracts import Limits
from sim2act.production_evidence import configured_token
from sim2act.model import InternModel
from sim2act import natural_spec_runtime as runtime,natural_specs as codec
root=Path('/workspace/Sim2Act/docs/evidence/cloud-core-20261028')
s=Settings('sqlite://',root,mode='live',live_enabled=True,token=configured_token(),max_requests=2,max_tools=4,max_repairs=0,max_total_tokens=4096,max_output_tokens=1024,run_seconds=30)
limits=Limits(**{k:getattr(s,k) for k in Limits.model_fields})
results=[]
for stage,text in [('source','Before release, verify the source. The output format remains undecided.'),('cold','Before export, verify the totals. The delivery date remains undecided.')]:
 source=dict(resource_id='non-sensitive-cloud-'+stage,content=text,format='txt',hash=hashlib.sha256(text.encode()).hexdigest())
 goal=dict(goal='Extract requirements and unresolved decisions with exact source quotations.',unresolved=['Human review of completeness'],constraints=['Do not invent facts'],acceptance_checks=['Exact citations'])
 binding=dict(draft=dict(candidate=dict(goal=goal)))
 messages=runtime.messages(binding,dict(step_id='extract_'+stage),dict(executor=dict(ref='model.spec.all')),dict(args=dict(content=text)))
 wire=json.dumps(dict(model='intern-s2',stream=False,max_tokens=1024,messages=messages,tools=[],thinking_mode=False),ensure_ascii=False,separators=(',',':')).encode()
 rec=dict(stage=stage,source=source,kind='REAL_MODEL_PRODUCT_EXTRACTOR_NOT_DB_CONTROLLER',request_sha256=hashlib.sha256(wire).hexdigest(),request_bytes=len(wire),retries=0,paid_cap=0,semantic_acceptance='NOT_RUN',owner_acceptance='PENDING')
 started=time.monotonic()
 try:
  cap=InternModel(s).request_serialized_captured(wire,lambda request:{'deadline':time.time()+30})
  rec.update(http_status=200,response_sha256=hashlib.sha256(cap.body).hexdigest(),response_bytes=len(cap.body),finish_reason=cap.parsed.get('choices',[{}])[0].get('finish_reason'),usage_observed=cap.parsed.get('usage'),thinking_mode=False)
  value,usage=runtime.parse(cap.parsed,source,'model.spec.all',limits,4096)
  report=codec.report(source,value['items'],goal)
  rec.update(status='VERIFIED_CITATIONS',http_status=200,response_sha256=hashlib.sha256(cap.body).hexdigest(),response_bytes=len(cap.body),usage=usage,output=value,report=report)
 except Exception as e:
  rec.update(status='STOPPED',error=e.public() if hasattr(e,'public') else type(e).__name__,http_status=rec.get('http_status',getattr(e,'_received_status_code',None)))
 rec['elapsed_seconds']=time.monotonic()-started
 results.append(rec)
 (root/'intern-extraction-nonthinking.json').write_text(json.dumps(dict(max_requests=2,max_output_tokens_per_request=1024,max_total_tokens=4096,results=results),ensure_ascii=False,indent=2)+'\n')
 print(stage,rec['status'],round(rec['elapsed_seconds'],3),flush=True)
 if rec['status']=='STOPPED':sys.exit(1)
