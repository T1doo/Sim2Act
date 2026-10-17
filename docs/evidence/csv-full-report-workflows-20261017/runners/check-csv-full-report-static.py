import json,subprocess,time
from pathlib import Path
root=Path('/workspace/Sim2Act');out=Path('/workspace/csv-full-report-evidence-20261017')
commands=[['/workspace/sim2act-venv/bin/ruff','check','src/sim2act/csv_full_report.py','src/sim2act/ordinary_csv.py','src/sim2act/api.py','src/sim2act/db.py','src/sim2act/goal_applications.py','tests/test_csv_full_report.py'],['/workspace/sim2act-venv/bin/python','-m','mypy','src/sim2act/csv_full_report.py','--follow-imports=silent']]+[['node','--check',p]for p in ['src/sim2act/web/app.js','src/sim2act/web/use.js','src/sim2act/web/csv-full-report.js','tests/csv_full_report.cjs']]+[['git','-c','core.fsmonitor=false','diff','--check']]
results=[]
for command in commands:
 started=time.monotonic();r=subprocess.run(command,cwd=root,capture_output=True,text=True);results.append(dict(command=command,returncode=r.returncode,seconds=time.monotonic()-started,stdout=r.stdout,stderr=r.stderr));assert r.returncode==0,r.stdout+r.stderr
(out/'final-static-checks.json').write_text(json.dumps({'head':'436c49cb8c2ac04489fd9dfd4baaf09bffea0298','results':results},indent=2));print('7 static commands PASS; mypy scope only new module')
