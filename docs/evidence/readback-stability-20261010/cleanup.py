from pathlib import Path
import json,subprocess
r=Path('/tmp/sim2act-read-stability-20261010')
assert json.loads((r/'pg-run.json').read_text())['exit']==0
cid=(r/'pg-cid').read_text().strip();assert len(cid)==64
info=json.loads(subprocess.check_output(['docker','inspect',cid],text=True))[0]
assert info['Id']==cid and info['Config']['Labels']['sim2act.owner']=='read-stability-20261010'
assert info['HostConfig']['NetworkMode']=='none' and not info['HostConfig']['PortBindings']
volumes=[m['Name'] for m in info['Mounts'] if m['Type']=='volume']
expected=[m['Name'] for m in json.loads((r/'pg-ready.json').read_text())['volumes'] if m['Type']=='volume']
assert volumes==expected and len(volumes)==1
q="SELECT (SELECT count(*) FROM pg_namespace WHERE nspname LIKE 'test_%'),(SELECT count(*) FROM pg_roles WHERE rolname LIKE 'test_app_%'),(SELECT count(*) FROM information_schema.tables WHERE table_schema='public');"
p=subprocess.run(['docker','exec',cid,'psql','-U','postgres','-d','read_stability_fixture','-At','-c',q],capture_output=True,text=True)
(r/'pg-after.json').write_text(json.dumps(dict(container_id=cid,exit=p.returncode,counts=p.stdout.strip()),indent=2)+'\n')
assert p.returncode==0 and p.stdout.strip()=='0|0|0'
steps=[]
for args in (['docker','stop',cid], ['docker','rm','-v',cid]):
    p=subprocess.run(args,capture_output=True,text=True)
    steps.append(dict(argv=args,exit=p.returncode,stdout=p.stdout,stderr=p.stderr));assert p.returncode==0
    if args[1]=='stop':
        logs=subprocess.check_output(['docker','logs',cid],stderr=subprocess.STDOUT,text=True)
        (r/'pg-server-final.log').write_text(logs)
        (r/'pg-shutdown.log').write_text(''.join(line+'\n' for line in logs.splitlines() if any(x in line for x in ['shutdown request','shutting down','database system is shut down'])))
p=subprocess.run(['docker','inspect',cid],capture_output=True,text=True);assert p.returncode!=0
remaining=[]
for v in volumes:
    p=subprocess.run(['docker','volume','inspect',v],capture_output=True,text=True);assert p.returncode!=0
    remaining.append(dict(volume=v,absent=True))
(r/'pg-cleanup.json').write_text(json.dumps(dict(container_id=cid,owner='read-stability-20261010',schema_role_public='0|0|0',steps=steps,container_absent=True,volumes=remaining,unrelated_resources_modified=False,shutdown_log_export='only shutdown messages; full server log retained privately'),indent=2)+'\n')
print('Owned container and volume removed normally; schemas/roles/public 0|0|0')
