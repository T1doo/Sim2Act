import datetime,hashlib,json,os,subprocess,time
from pathlib import Path
root=Path(__file__).parent
spec=json.loads((root/'commands.json').read_text()); env=dict(os.environ);env.update(spec['env'])
for key in spec['unset']:env.pop(key,None)
start=time.time();started=datetime.datetime.now(datetime.timezone.utc).isoformat()
with (root/'pytest.log').open('w') as log:
 p=subprocess.run(spec['command'],cwd=spec['cwd'],env=env,stdout=log,stderr=subprocess.STDOUT)
ended=datetime.datetime.now(datetime.timezone.utc).isoformat()
(root/'terminal.json').write_text(json.dumps(dict(returncode=p.returncode,started_at=started,ended_at=ended,wall_seconds=time.time()-start,attempts=1),indent=2)+'\n')
before=json.loads((root/'source-before.json').read_text()); records=[]
for item in before['inputs']:
 data=(Path(spec['cwd'])/item['path']).read_bytes();records.append(dict(path=item['path'],git_blob=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest(),sha256=hashlib.sha256(data).hexdigest(),size=len(data)))
(root/'source-after.json').write_text(json.dumps(dict(source_sha=before['source_sha'],inputs=records,input_count=len(records),identical_to_before=records==before['inputs']),indent=2)+'\n')
print(json.dumps(dict(returncode=p.returncode,input_count=len(records),inputs_unchanged=records==before['inputs'])))
raise SystemExit(p.returncode)
