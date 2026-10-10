import json,subprocess,time,os
from pathlib import Path
root=Path('/tmp/sim2act-report-dag-type-fix-20261010');sock=root/'pg-socket';sock.mkdir(exist_ok=True)
args=['docker','run','--pull=never','-d','--name','sim2act-report-dag-type-fix-20261010','--label','sim2act.owner=report-dag-type-fix-20261010','--network','none','-v',str(sock)+':/var/run/postgresql','-e','POSTGRES_HOST_AUTH_METHOD=trust','-e','POSTGRES_DB=report_type_fixture','postgres:17.9','-c','listen_addresses=']
p=subprocess.run(args,text=True,capture_output=True);(root/'pg-start.json').write_text(json.dumps({'argv':args,'exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr},indent=2)+'\n');assert p.returncode==0
cid=p.stdout.strip();(root/'pg-cid').write_text(cid+'\n');deadline=time.monotonic()+45
while True:
    logs=subprocess.check_output(['docker','logs',cid],stderr=subprocess.STDOUT,text=True);(root/'pg-startup.log').write_text(logs)
    info=json.loads(subprocess.check_output(['docker','inspect',cid],text=True))[0]
    assert info['Config']['Labels']['sim2act.owner']=='report-dag-type-fix-20261010' and info['HostConfig']['NetworkMode']=='none' and not info['HostConfig']['PortBindings']
    if 'PostgreSQL init process complete; ready for start up.' in logs:
        ready=subprocess.run(['docker','exec',cid,'psql','-U','postgres','-d','report_type_fixture','-At','-c','SELECT current_database(),version()'],capture_output=True,text=True)
        if ready.returncode==0:
            (root/'pg-ready.json').write_text(json.dumps({'container_id':cid,'owner':'report-dag-type-fix-20261010','network':'none','published_ports':0,'SQL_exit':0,'SQL_result':ready.stdout.strip(),'volumes':info['Mounts']},indent=2)+'\n');break
    assert time.monotonic()<deadline,'PG final server did not become ready';time.sleep(.2)
q="SELECT (SELECT count(*) FROM pg_namespace WHERE nspname LIKE 'test_%'),(SELECT count(*) FROM pg_roles WHERE rolname LIKE 'test_app_%'),(SELECT count(*) FROM information_schema.tables WHERE table_schema='public');"
r=subprocess.run(['docker','exec',cid,'psql','-U','postgres','-d','report_type_fixture','-At','-c',q],capture_output=True,text=True);assert r.returncode==0 and r.stdout.strip()=='0|0|0'
(root/'pg-before.json').write_text(json.dumps({'container_id':cid,'counts':r.stdout.strip()},indent=2)+'\n');print('Final PG server ready; schema/role/public 0|0|0')
