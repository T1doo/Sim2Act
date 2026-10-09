from pathlib import Path
import subprocess,json
root=Path('/tmp/sim2act-report-edit-locks-20261009')
assert (root/'pg-final.exit').read_text().strip()=='0'
container_id='21bfb8444f4d75d9e24a4fbaccc5fd514fce87df6a29a7382df32b96b9b2ed3c'
def run(args):return subprocess.run(args,capture_output=True,text=True,check=True)
data=json.loads(run(['docker','inspect',container_id]).stdout)[0]
assert data['Id']==container_id and data['Config']['Labels']['sim2act.owner']=='report-edit-locks-20261009'
assert data['HostConfig']['NetworkMode']=='none' and not data['HostConfig']['PortBindings']
volumes=[m['Name'] for m in data['Mounts'] if m['Type']=='volume']
sql="SELECT json_build_object('test_schemas',(SELECT count(*) FROM pg_namespace WHERE nspname LIKE 'test_%'),'test_roles',(SELECT count(*) FROM pg_roles WHERE rolname LIKE 'test_app_%'),'public_tables',(SELECT count(*) FROM information_schema.tables WHERE table_schema='public'));"
clean=json.loads(run(['docker','exec',container_id,'psql','-U','postgres','-d','report_locks_fixture','-t','-A','-c',sql]).stdout)
assert clean=={'test_schemas':0,'test_roles':0,'public_tables':0},clean
service=run(['docker','logs',container_id])
(root/'pg-service.log').write_text(service.stdout+service.stderr)
run(['docker','stop',container_id]);run(['docker','rm','-v',container_id])
removed=subprocess.run(['docker','inspect',container_id],capture_output=True,text=True).returncode!=0
volume_removed={v:subprocess.run(['docker','volume','inspect',v],capture_output=True,text=True).returncode!=0 for v in volumes}
assert removed and all(volume_removed.values())
proof={'container_id':container_id,'owner':'report-edit-locks-20261009','network':'none','port_bindings':{},'after_tests':clean,'pre_test_count_measured':False,'container_removed':removed,'owned_anonymous_volumes_removed':volume_removed,'scope':'Only this newly created fixture container and its anonymous data volume; retained image, dependencies, archives and logs'}
(root/'pg-cleanup.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(proof,indent=2))
