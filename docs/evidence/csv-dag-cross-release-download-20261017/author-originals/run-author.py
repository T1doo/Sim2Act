from pathlib import Path
from datetime import datetime,timezone
import json,subprocess,os
repo=Path('/workspace/Sim2Act');raw=Path('/workspace/csv-dag-cross-release-download-evidence-20261017');out=raw/'author';out.mkdir(exist_ok=True)
argv=['/workspace/sim2act-venv/bin/python','-m','pytest','tests/test_csv_dag_cross_release_download.py::test_visible_compatible_adoption_cold_old_new_downloads_and_revoke','-q','--basetemp='+str(out/'data'),'--junitxml='+str(out/'junit.xml')]
meta={'source':'a865971e73e4ce20cffec61e3bce5b71f5b0504c','utc_started':datetime.now(timezone.utc).isoformat(),'argv':argv,'env_overrides':{'PYTHONPATH':'src','NODE_PATH':str(repo/'scripts/engineering-ci/node_modules')},'attempts':1}
(raw/'commands-author.json').write_text(json.dumps(meta,indent=2)+'\n')
with (out/'pytest.log').open('w') as f:p=subprocess.run(argv,cwd=repo,env={**os.environ,**meta['env_overrides']},stdout=f,stderr=subprocess.STDOUT)
terminal={**meta,'utc_finished':datetime.now(timezone.utc).isoformat(),'rc':p.returncode};(raw/'terminal-author.json').write_text(json.dumps(terminal,indent=2)+'\n');print(json.dumps(terminal));raise SystemExit(p.returncode)
