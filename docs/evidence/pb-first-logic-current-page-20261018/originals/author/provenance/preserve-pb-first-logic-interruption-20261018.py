import datetime
import hashlib
import json
import subprocess
from pathlib import Path

root=Path('/workspace/pb-first-logic-current-page-evidence-20261018')
retained=root/'interrupted-1'
assert not retained.exists()
assert json.loads((root/'second-disconnect-recovery.json').read_text())['known_owned_live_process_matches']==[]
assert 'exit_code' not in json.loads((root/'execution.json').read_text())
repo=Path('/workspace/Sim2Act')
assert subprocess.check_output(['git','-c','core.fsmonitor=false','rev-parse','HEAD'],cwd=repo,text=True).strip()=='2fa76ff2458d3b732f1c18c000a51b4e9171d87b'
assert not subprocess.check_output(['git','-c','core.fsmonitor=false','status','--porcelain=v1','--untracked-files=all'],cwd=repo,text=True)
retained.mkdir()
originals=[]
for name in ['actual-tmp','execution.json','actual.stdout','actual.stderr']:
    source=root/name
    assert source.exists(),name
    paths=sorted(source.rglob('*')) if source.is_dir() else [source]
    for path in paths:
        if path.is_file() and not path.is_symlink():
            data=path.read_bytes()
            originals.append(dict(path=str(path.relative_to(root)),bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
    source.rename(retained/name)
for row in originals:
    data=(retained/row['path']).read_bytes()
    assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256']
(retained/'retained-original-manifest.json').write_text(json.dumps(originals,indent=2)+'\n')
record=dict(time_utc=datetime.datetime.now(datetime.UTC).isoformat(),classification='INTERRUPTED_WITHOUT_EXIT_JUNIT_OR_FINALLY_AFTER_EXEC_TRANSPORT_DISCONNECT',pytest_result='UNKNOWN_NOT_COUNTED_AS_PASS_OR_ORDINARY_FAILURE',exit_code=None,junit=None,source_sha='2fa76ff2458d3b732f1c18c000a51b4e9171d87b',last_completed_http_receipt='GET /api/internal/apps/app_c08c3152bb5c2faf8e3f6fcba643fdba/instances 200; following GET original instance began without a saved response',observed_page_post_statuses=[201,202,201,200],saved_mock_counts={'generation':3,'source-original':2,'pb-original':2,'logic-check':2,'logic-use':0},saved_business_stages=3,saved_business_worker_calls=3,real_model_requests=0,original_node_pid=58345,owned_processes_observed_absent=True,transport_failure_exact='exec-server transport disconnected; failed to resume exec-server session: recovery timed out after 25s',causality='Transport disconnection, stopped evidence and absent owned processes are observed; no exit receipt proves a precise process termination cause.',retained_original_files=len(originals),retained_manifest='retained-original-manifest.json',retry='One fresh same-source bounded attempt only after observed owned process absence; do not resume/replay the interrupted partial fixture.')
(retained/'interruption-classification.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
(root/'second-disconnect-tool-output-transcript.txt').write_text('Explicit tool-output transcript; not a separately captured original stderr file.\nMonitoring exec_command: CreateProcess Rejected Failed to create unified exec process: exec-server transport disconnected; failed to resume exec-server session: recovery timed out after 25s.\nExisting session13500 poll: Unified exec process failed: exec-server transport disconnected; failed to resume exec-server session: recovery timed out after 25s.\nA bounded original-environment read probe later succeeded: cwd /workspace/Sim2Act, HEAD2fa76ff2458d3b732f1c18c000a51b4e9171d87b, git status empty. No duplicate product process was started while outcome was uncertain.\n')
print(json.dumps(record,ensure_ascii=False))
