import hashlib,json,os,subprocess,time
from pathlib import Path
root=Path('/workspace/Sim2Act');out=Path('/workspace/csv-full-report-evidence-20261017');expected='4a4a228f09203e08103904e3afdd04b12708a98b'
def git(*args):return subprocess.check_output(['git','-c','core.fsmonitor=false',*args],cwd=root,text=True).strip()
def inputs():
    names=subprocess.check_output(['git','-c','core.fsmonitor=false','ls-files','-z','src','tests','schemas','pyproject.toml'],cwd=root).decode().split('\0')
    return {n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in names if n}
assert git('rev-parse','HEAD')==expected
selected=['tests/test_csv_full_report.py','tests/test_ordinary_csv_report.py::test_prospective_csv_report','tests/test_application_use.py::test_application_use_actual_http','tests/test_ordinary_csv_extraction.py::test_visible_sum_extraction_through_existing_version_directory_and_use[deliver]','tests/test_natural_spec_owner_acceptance.py::test_exact_goal_result_explicit_human_declaration[False-pa]']
before=inputs();(out/'author-source-before.json').write_text(json.dumps({'head':expected,'files':before},indent=2))
command=['/workspace/sim2act-venv/bin/python','-m','pytest',*selected,'-q','--basetemp=/tmp/csv-full-report-author-4a4a228f-20261017','--junitxml='+str(out/'author22.xml')]
started=time.time();(out/'author-command.json').write_text(json.dumps({'head':expected,'command':command,'selected':selected,'started_at':started,'test_scope':'synthetic SQLite/ASGI, NoModel new cases; existing natural MockTransport, JSDOM_NOT_NATIVE'},indent=2))
with(out/'author22.log').open('w')as stream:
    result=subprocess.run(command,cwd=root,env={**os.environ,'SIM2ACT_LIVE_ENABLED':'false'},stdout=stream,stderr=subprocess.STDOUT)
after=inputs();(out/'author-source-after.json').write_text(json.dumps({'head':git('rev-parse','HEAD'),'files':after},indent=2));(out/'author-result.json').write_text(json.dumps({'head':git('rev-parse','HEAD'),'returncode':result.returncode,'wall_seconds':time.time()-started,'source_files':len(before),'source_unchanged':before==after,'model_scope':'new NoModel; old natural MockTransport','native_browser':False,'remote_ci':False},indent=2));print((out/'author-result.json').read_text());raise SystemExit(result.returncode)
