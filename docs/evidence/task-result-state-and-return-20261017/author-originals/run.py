from pathlib import Path
from datetime import datetime,timezone
import json,os,subprocess,sys
raw=Path(__file__).parent;label=sys.argv[1];source=subprocess.check_output(['git','-c','core.fsmonitor=false','rev-parse','HEAD'],text=True).strip();dest=raw/label;dest.mkdir()
nodes=['tests/test_ordinary_run_results.py::test_ordinary_goal_results_actual_tools_and_page[workspace-return]','tests/test_fixed_goal_status.py'] if label=='baseline' else ['tests/test_ordinary_run_results.py','tests/test_fixed_goal_status.py']
cmd=['/workspace/sim2act-venv/bin/python','-m','pytest',*nodes,'-q','--basetemp='+str(dest/'data'),'--junitxml='+str(dest/'junit.xml')]
meta={'source':source,'utc_started':datetime.now(timezone.utc).isoformat(),'argv':cmd,'attempts':1,'env_overrides':{'PYTHONPATH':'src','NODE_PATH':'/workspace/Sim2Act/scripts/engineering-ci/node_modules'}}
(raw/('commands-'+label+'.json')).write_text(json.dumps(meta,indent=2)+'\n')
with (dest/'pytest.log').open('w') as log:p=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,env={**os.environ,**meta['env_overrides']})
meta.update(utc_finished=datetime.now(timezone.utc).isoformat(),rc=p.returncode);(raw/('terminal-'+label+'.json')).write_text(json.dumps(meta,indent=2)+'\n');print(json.dumps(meta));sys.exit(p.returncode)
