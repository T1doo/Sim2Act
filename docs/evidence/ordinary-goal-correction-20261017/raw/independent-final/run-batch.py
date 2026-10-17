import datetime,hashlib,json,os,subprocess,sys,time,xml.etree.ElementTree as ET
from pathlib import Path
root=Path(__file__).parent;batch=root/sys.argv[1];spec=json.loads((batch/'commands.json').read_text());env=dict(os.environ);env.update(spec['env'])
for key in spec['unset']:env.pop(key,None)
start=time.time();started=datetime.datetime.now(datetime.timezone.utc).isoformat()
with (batch/'pytest.log').open('w') as log:p=subprocess.run(spec['command'],cwd=spec['cwd'],env=env,stdout=log,stderr=subprocess.STDOUT)
ended=datetime.datetime.now(datetime.timezone.utc).isoformat()
(batch/'terminal.json').write_text(json.dumps(dict(returncode=p.returncode,started_at=started,ended_at=ended,wall_seconds=time.time()-start,attempts=1),indent=2)+'\n')
before=json.loads((batch/'source-before.json').read_text());records=[]
for item in before['inputs']:
 data=(Path(spec['cwd'])/item['path']).read_bytes();records.append(dict(path=item['path'],git_blob=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest(),sha256=hashlib.sha256(data).hexdigest(),size=len(data)))
unchanged=records==before['inputs']
(batch/'source-after.json').write_text(json.dumps(dict(source_sha=before['source_sha'],input_count=len(records),inputs=records,identical_to_before=unchanged),indent=2)+'\n')
if (batch/'junit.xml').exists():
 suites=ET.parse(batch/'junit.xml').getroot();nodes=[dict(classname=x.get('classname'),name=x.get('name'),seconds=x.get('time'),failure=x.find('failure') is not None,error=x.find('error') is not None,skipped=x.find('skipped') is not None) for x in suites.iter('testcase')];(batch/'collected.json').write_text(json.dumps(dict(source_sha=before['source_sha'],from_original_junit=True,nodes=nodes,count=len(nodes),expected=spec['expected_unique_nodes']),indent=2)+'\n')
print(json.dumps(dict(batch=sys.argv[1],returncode=p.returncode,inputs_unchanged=unchanged,input_count=len(records))))
raise SystemExit(p.returncode)
