import hashlib,json,os,subprocess,time
from pathlib import Path
root=Path('/workspace/Sim2Act');out=Path('/workspace/csv-full-report-evidence-20261017');expected='436c49cb8c2ac04489fd9dfd4baaf09bffea0298'
def git(*args):return subprocess.check_output(['git','-c','core.fsmonitor=false',*args],cwd=root,text=True).strip()
def inputs():
    names=subprocess.check_output(['git','-c','core.fsmonitor=false','ls-files','-z','src','tests','schemas','pyproject.toml'],cwd=root).decode().split('\0')
    return {n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in names if n}
assert git('rev-parse','HEAD')==expected
selected=['tests/test_csv_full_report.py::test_visible_complete_report_directory_and_new_run[misbound]','tests/test_application_use.py::test_application_use_actual_http']
before=inputs();(out/'author-refine-source-before.json').write_text(json.dumps({'head':expected,'files':before},indent=2))
command=['/workspace/sim2act-venv/bin/python','-m','pytest',*selected,'-q','--basetemp=/tmp/csv-full-report-author-436c49cb-20261017','--junitxml='+str(out/'author-refine2.xml')]
started=time.time();(out/'author-refine-command.json').write_text(json.dumps({'head':expected,'command':command,'selected':selected,'started_at':started,'test_scope':'synthetic SQLite/ASGI, NoModel new cases; existing natural MockTransport, JSDOM_NOT_NATIVE'},indent=2))
with(out/'author-refine2.log').open('w')as stream:
    result=subprocess.run(command,cwd=root,env={**os.environ,'SIM2ACT_LIVE_ENABLED':'false','NODE_PATH':'/workspace/Sim2Act/scripts/engineering-ci/node_modules'},stdout=stream,stderr=subprocess.STDOUT)
after=inputs();(out/'author-refine-source-after.json').write_text(json.dumps({'head':git('rev-parse','HEAD'),'files':after},indent=2));(out/'author-refine-result.json').write_text(json.dumps({'head':git('rev-parse','HEAD'),'returncode':result.returncode,'wall_seconds':time.time()-started,'source_files':len(before),'source_unchanged':before==after,'model_scope':'new NoModel; old natural MockTransport','native_browser':False,'remote_ci':False},indent=2));print((out/'author-refine-result.json').read_text());raise SystemExit(result.returncode)
