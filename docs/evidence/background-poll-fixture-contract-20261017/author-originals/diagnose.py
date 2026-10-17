from pathlib import Path
from datetime import datetime, timezone
import hashlib,json,os,subprocess
repo=Path('/workspace/Sim2Act');root=Path('/workspace/background-poll-fixture-fix-evidence-20261017');root.mkdir(exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
raw=Path('/workspace/project-create-selection-evidence-20261017')
files=['focused-background/command-4.log','focused-background/junit.xml','focused-background/data/test_background_poll_synthesiz0/failure.json','focused-background/data/test_background_poll_synthesiz0/driver.log','background-delivered-base/failure.json','background-delivered-base/driver.log','background-delivered-base/terminal.json','background-delivered-base/delivered-app.js','focused-checks.json','source-final.json']
protected=[]
for name in files:
 p=raw/name;b=p.read_bytes();dest=root/'old-failures'/name;dest.parent.mkdir(parents=True,exist_ok=True);assert not dest.exists();dest.write_bytes(b);protected.append({'original':str(p),'sha256':sha(b),'bytes':len(b),'copy':str(dest)})
(root/'protected-original-failures.json').write_text(json.dumps(protected,indent=2)+'\n')
original=(repo/'tests/background_poll.cjs').read_text();(root/'original-driver.cjs').write_text(original)
s=original.replace("checks=[];let dom", "checks=[],requestTimeline=[],phaseTimeline=[];const origin=process.hrtime.bigint(),ms=()=>Number(process.hrtime.bigint()-origin)/1e6;let scene=0;let dom")
s=s.replace("web=path.join(__dirname,'../src/sim2act/web')", "web='/workspace/Sim2Act/src/sim2act/web'")
s=s.replace("requests=[];gate=null;", "requests=[];gate=null;scene++;")
s=s.replace("record={path:url,method,body:","record={scene,started_ms:ms(),path:url,method,body:")
s=s.replace("requests.push(record);let body;", "requests.push(record);requestTimeline.push(record);let body;try{")
s=s.replace("return {ok:true,status:200,json:async()=>body};};", "record.response=body;record.completed_ms=ms();return {ok:true,status:200,json:async()=>body};}catch(error){record.error=error.message;record.completed_ms=ms();throw error;}};")
s=s.replace("function arm(phase){gate=", "function arm(phase){phaseTimeline.push({event:'arm',scene,phase,ms:ms()});gate=")
s=s.replace("assert(gate.used,'phase reached');", "phaseTimeline.push({event:'gate-check',scene,phase,used:gate.used,ms:ms(),health:$('health').textContent,error:$('error').textContent,latch:w.eval('backgroundRefreshInFlight'),requests:requests.length});assert(gate.used,'phase reached');")
s=s.replace("status:'PASS',checks,source_sha256:", "status:'PASS',checks,requestTimeline,phaseTimeline,source_sha256:")
s=s.replace("status:'FAIL',checks,error:e.message", "status:'FAIL',checks,requestTimeline,phaseTimeline,error:e.message")
(root/'diagnostic-driver.cjs').write_text(s)
base='17b8b8cff345c96885dfb18dd52f4ae1a6b54454';current='2aacbb207aec5d00d199c5ac20e5660bcfba2e0b';reports=[]
for label,ref in [('base',base),('current',current)]:
 d=root/('diagnostic-original-'+label);d.mkdir();p=d/'app.js';b=subprocess.check_output(['git','-c','core.fsmonitor=false','show',ref+':src/sim2act/web/app.js'],cwd=repo);p.write_bytes(b)
 cmd=['node',str(root/'diagnostic-driver.cjs'),str(d),str(p)];out=subprocess.run(cmd,capture_output=True,text=True,env={**os.environ,'NODE_PATH':str(repo/'scripts/engineering-ci/node_modules')},timeout=30);(d/'driver.log').write_text(out.stdout+out.stderr)
 r=json.loads((d/'failure.json').read_text());reports.append({'label':label,'source':ref,'app_sha256':sha(b),'argv':cmd,'rc':out.returncode,'checks':r['checks'],'trace_origin':'NEW instrumented reconstruction, not missing historical timestamps','requestTimeline':r['requestTimeline'],'phaseTimeline':r['phaseTimeline']})
# Only one healthy tick in these diagnostic variants; no matrix/recovery paths execute.
start=s.index('(async()=>{try{');one=s[:start]+"""(async()=>{try{await setup();await tick();fs.writeFileSync(path.join(root,'one-tick.json'),JSON.stringify({kind:'DIAGNOSTIC_ONLY',health:$('health').textContent,error:$('error').textContent,latch:w.eval('backgroundRefreshInFlight'),requestTimeline,phaseTimeline},null,2));}finally{dom?.window.close();}})();\n"""
for label,routefix in [('health-only',False),('health-and-catalog',True)]:
 d=root/('diagnostic-'+label);d.mkdir();variant=one.replace("api:'up',worker:'up'","api:'UP',worker:'UP'")
 if routefix:variant=variant.replace("url==='/api/apps'||","url==='/api/apps?metadata_only=true'||")
 p=d/'driver.cjs';p.write_text(variant);cmd=['node',str(p),str(d),str(root/'diagnostic-original-current/app.js')];out=subprocess.run(cmd,capture_output=True,text=True,env={**os.environ,'NODE_PATH':str(repo/'scripts/engineering-ci/node_modules')},timeout=30);(d/'driver.log').write_text(out.stdout+out.stderr);r=json.loads((d/'one-tick.json').read_text());reports.append({'label':label,'source':current,'argv':cmd,'rc':out.returncode,**r})
for row in protected:assert sha(Path(row['original']).read_bytes())==row['sha256']
(root/'diagnosis.json').write_text(json.dumps({'utc':datetime.now(timezone.utc).isoformat(),'original_driver_sha256':sha(original.encode()),'original_historical_request_timestamps':'NOT_RECORDED; never fabricate. New traces explicitly labelled.','reports':reports,'old_originals_unchanged':True},indent=2)+'\n')
print(json.dumps([{'label':r['label'],'rc':r['rc'],'checks':len(r.get('checks',[])),'error':r.get('error'),'requests':[a['path'] for a in r['requestTimeline']]} for r in reports],indent=2))
