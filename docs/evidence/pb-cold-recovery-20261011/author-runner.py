from pathlib import Path
import subprocess,sys,json,os,hashlib,time,datetime,xml.etree.ElementTree as ET
repo=Path('/workspace/Sim2Act');os.chdir(repo);name=sys.argv[1];args=sys.argv[2:];root=repo/'docs/evidence/pb-cold-recovery-20261011'
paths=set(subprocess.check_output(['git','ls-files','--','src','tests','pyproject.toml'],text=True).splitlines())
paths.update(subprocess.check_output(['git','ls-files','--others','--exclude-standard','--','src','tests'],text=True).splitlines())
def source():return {p:hashlib.sha256((repo/p).read_bytes()).hexdigest() for p in sorted(paths) if (repo/p).is_file()}
before=source();root.joinpath(name+'-source-before.json').write_text(json.dumps(before,indent=2)+'\n')
env=os.environ.copy();env.pop('SIM2ACT_TEST_DATABASE_URL',None);env['NODE_PATH']='/workspace/node-tools/node_modules';env['SIM2ACT_PB_EVIDENCE_DIR']=str(root/(name+'-pb-pages'));env['SIM2ACT_COLD_EVIDENCE_DIR']=str(root/(name+'-cold-pages'))
cmd=['.venv/bin/python','-m','pytest',*args,'-q','--basetemp=/tmp/pb-cold-author-'+name,'--junitxml='+str(root/(name+'.xml'))]
root.joinpath(name+'-command.json').write_text(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':cmd,'cwd':str(repo),'NODE_PATH':env['NODE_PATH'],'SIM2ACT_TEST_DATABASE_URL':'UNSET','source_count':len(before)},indent=2)+'\n')
start=time.monotonic()
with root.joinpath(name+'.log').open('w') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,env=env)
after=source();root.joinpath(name+'-source-after.json').write_text(json.dumps(after,indent=2)+'\n')
changes=[p for p in before if after.get(p)!=before[p]];out={'exit':r.returncode,'wall_seconds':time.monotonic()-start,'source_count':len(before),'source_changes':changes}
if root.joinpath(name+'.xml').exists():
 nodes=ET.parse(root/(name+'.xml')).findall('.//testcase');out['named_nodes']=len([n for n in nodes if n.get('name')]);out['pass']=sum(n.get('name') is not None and n.find('failure') is None and n.find('error') is None and n.find('skipped') is None for n in nodes);out['fail']=sum(n.find('failure') is not None for n in nodes);out['error']=sum(n.find('error') is not None for n in nodes);out['skip']=sum(n.find('skipped') is not None for n in nodes)
root.joinpath(name+'-exit.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out));assert not changes,changes;sys.exit(r.returncode)
