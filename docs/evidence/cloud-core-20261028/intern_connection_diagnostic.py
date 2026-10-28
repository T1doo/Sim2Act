import hashlib,json,time,sys
from pathlib import Path
from sim2act.config import Settings
from sim2act.production_evidence import configured_token,FREE_SERVICE_POLICY
from sim2act.model import InternModel,returned_model_identity,require_returned_model,parse_response,normalize_usage
out=Path('/workspace/Sim2Act/docs/evidence/cloud-core-20261028/intern-current.json')
start=time.monotonic()
s=Settings('sqlite://',Path('/workspace/scratch'),mode='live',live_enabled=True,token=configured_token(),max_requests=1,max_tools=1,max_repairs=0,max_total_tokens=2048,max_output_tokens=1024,run_seconds=30)
wire=json.dumps(dict(model='intern-s2',stream=False,max_tokens=1024,messages=[dict(role='user',content='Reply with exactly SIM2ACT_READY and no other text.')],tools=[]),separators=(',',':')).encode()
report=dict(endpoint=InternModel.ENDPOINT,model=s.model,request_limit=1,retries=0,paid_cap=0,fee_basis=FREE_SERVICE_POLICY,request_sha256=hashlib.sha256(wire).hexdigest(),request_bytes=len(wire),started_at=time.time())
try:
 cap=InternModel(s).request_serialized_captured(wire,lambda request:{'deadline':time.time()+30})
 raw=cap.parsed
 identity=returned_model_identity('intern-s2',raw.get('model'))
 require_returned_model(identity)
 assistant,calls=parse_response(raw)
 usage=normalize_usage(raw)
 report.update(http_status=200,identity=identity,assistant=assistant,tool_calls=len(calls),usage=usage,response_sha256=hashlib.sha256(cap.body).hexdigest(),response_bytes=len(cap.body),output_check=assistant['content'].strip()=='SIM2ACT_READY',status='RECEIVED')
except Exception as e:
 report.update(status='STOPPED',error_type=type(e).__name__,error=e.public() if hasattr(e,'public') else 'details suppressed',http_status=getattr(e,'_received_status_code',None))
report['elapsed_seconds']=time.monotonic()-start
out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
sys.exit(0 if report['status']=='RECEIVED' and report['output_check'] else 1)
