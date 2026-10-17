from pathlib import Path
from datetime import datetime,timezone
import json,subprocess
repo=Path('/workspace/Sim2Act');raw=Path('/workspace/csv-dag-result-download-evidence-20261017');out=raw/'author';out.mkdir(exist_ok=True)
nodes=['tests/test_csv_dag_directory.py::test_saved_csv_dag_directory_actual_http[download-'+s+']' for s in ['dual','report','use','fixed']]
argv=['/workspace/sim2act-venv/bin/python','-m','pytest',*nodes,'-q','--basetemp='+str(out/'data'),'--junitxml='+str(out/'junit.xml')]
import os
env={**os.environ,'PYTHONPATH':'src','NODE_PATH':str(repo/'scripts/engineering-ci/node_modules')}
command={'utc_started':datetime.now(timezone.utc).isoformat(),'source':'3be0300b306fac0cb6f5d9e0a1521ca16814c126','argv':argv,'cwd':str(repo),'env_overrides':{'PYTHONPATH':'src','NODE_PATH':env['NODE_PATH']},'unique_nodes':4,'attempts_this_source':1}
(raw/'commands.json').write_text(json.dumps(command,indent=2)+'\n')
with (out/'pytest.log').open('w') as f:p=subprocess.run(argv,cwd=repo,env=env,stdout=f,stderr=subprocess.STDOUT)
terminal={**command,'utc_finished':datetime.now(timezone.utc).isoformat(),'rc':p.returncode}
(raw/'author-terminal.json').write_text(json.dumps(terminal,indent=2)+'\n');print(json.dumps(terminal));raise SystemExit(p.returncode)
