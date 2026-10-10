import json,subprocess,hashlib
from pathlib import Path
r=Path('/tmp/sim2act-dag-new-csv-20261010');cid=(r/'pg-cid').read_text().strip();info=json.loads(subprocess.check_output(['docker','inspect',cid],text=True))[0]
assert info['Config']['Labels']['sim2act.owner']=='dag-new-csv-20261010' and info['HostConfig']['NetworkMode']=='none' and not info['HostConfig']['PortBindings']
q="SELECT (SELECT count(*) FROM pg_namespace WHERE nspname LIKE 'test_%'),(SELECT count(*) FROM pg_roles WHERE rolname LIKE 'test_app_%'),(SELECT count(*) FROM information_schema.tables WHERE table_schema='public');"
counts=subprocess.check_output(['docker','exec',cid,'psql','-U','postgres','-d','material_reuse_fixture','-At','-c',q],text=True).strip();(r/'pg-after.json').write_text(json.dumps(dict(container_id=cid,counts=counts),indent=2)+'\n');assert counts=='0|0|0','preserve container for diagnosis instead of dropping unknown state'
logs=subprocess.check_output(['docker','logs',cid],stderr=subprocess.STDOUT);(r/'pg-server.log').write_bytes(logs)
vol=[m['Name'] for m in info['Mounts'] if m['Type']=='volume'];subprocess.run(['docker','stop','-t','5',cid],check=True,capture_output=True);(r/'pg-server-shutdown.log').write_bytes(subprocess.check_output(['docker','logs',cid],stderr=subprocess.STDOUT));subprocess.run(['docker','rm','-v',cid],check=True,capture_output=True)
absent=subprocess.run(['docker','inspect',cid],capture_output=True).returncode!=0;removed={v:subprocess.run(['docker','volume','inspect',v],capture_output=True).returncode!=0 for v in vol};assert absent and all(removed.values())
(r/'pg-cleanup.json').write_text(json.dumps(dict(container_id=cid,owner='dag-new-csv-20261010',network='none',published_ports=0,counts=counts,container_absent=absent,owned_anonymous_volumes_removed=removed,server_log_sha256=hashlib.sha256(logs).hexdigest()),indent=2)+'\n');print('owned fixture cleaned, no unknown state')
