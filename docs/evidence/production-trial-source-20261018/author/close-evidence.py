import hashlib
import json
import os
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

root = Path('/workspace/production-trial-source-20261018')
run = root/'run-1'
repo = Path('/workspace/Sim2Act')
assert not (root/'sealed-manifest.json').exists()
execution = json.loads((run/'execution.json').read_text())
assert execution['source_commit']=='ab838215af13c04281bbad441fd75b9a97839890' and execution['exit_code']==0
assert not execution['input_drift'] and not execution['helper_drift']
assert execution['input_count']==707 and execution['production_count']==138
before = json.loads((run/'inputs-before.json').read_text())
assert before==json.loads((run/'inputs-after.json').read_text())
assert json.loads((run/'helpers-before.json').read_text())==json.loads((run/'helpers-after.json').read_text())
assert subprocess.check_output(['git','-c','core.fsmonitor=false','status','--porcelain'],cwd=repo)==b''
for name,item in before['inputs'].items():
    raw=(repo/name).read_bytes()
    assert len(raw)==item['bytes'] and hashlib.sha256(raw).hexdigest()==item['sha256']
cases=ET.parse(run/'junit.xml').findall('.//testcase')
suite=ET.parse(run/'junit.xml').find('.//testsuite')
assert len(cases)==len({(c.attrib['classname'],c.attrib['name']) for c in cases})==9
assert all(len(c)==0 for c in cases)
assert suite.attrib['failures']==suite.attrib['errors']==suite.attrib['skipped']=='0'
guard=json.loads((run/'offline-guard.json').read_text())
assert guard['attempts']==[] and guard['pytest_exitstatus']==0
assert guard['adapter_methods'].count('request_serialized_captured')==3
assert guard['adapter_methods'].count('_request_serialized')==guard['adapter_methods'].count('_deadline_request')==3
tmp=run/'actual-tmp'
states=[]; rejected=[]; databases=[]
for directory,dirs,files in os.walk(tmp,followlinks=False):
    dirs[:]=[d for d in dirs if not (Path(directory)/d).is_symlink() and d!='__pycache__']
    for name in files:
        path=Path(directory)/name
        if path.is_symlink(): continue
        if name=='source-state.json': states.append(json.loads(path.read_text()))
        if name=='source-rejection.json': rejected.append((path,json.loads(path.read_text())))
        if name.endswith('.db'):
            raw=path.read_bytes();databases.append(dict(path=str(path.relative_to(root)),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
assert len(states)==len(databases)==9
assert sum(s['mock_handler_calls'] for s in states)==3
assert all(s['real_provider_calls']==0 and s['protected_other_54_tables_strict_equal'] for s in states)
assert len(rejected)==6 and {r['case'] for _,r in rejected}=={'missing','wrong_account','cross_project','expired','revoked','inconsistent'}
for path,item in rejected:
    assert item['handler_calls']==0 and item['all_55_tables_strict_equal']
    if item['case']=='missing':
        assert item['resolution']['raw_sha256'] is None
    else:
        raw=(path.parent/'raw-synthetic-source.json').read_bytes()
        assert hashlib.sha256(raw).hexdigest()==item['resolution']['raw_sha256']
    if item['case']=='cross_project':
        assert item['sql_observer_positive_payload_reads']>0 and item['foreign_source_payload_reads']==0
    if item['case']=='inconsistent':
        assert item['one_corrupt_mirror']['resolution']['reason']=='SOURCE_INTEGRITY'
        assert item['one_corrupt_mirror']['resolution']['source']['decision']=='UNKNOWN'
        assert item['one_corrupt_mirror']['all_55_tables_strict_equal'] and item['one_corrupt_mirror']['no_auto_repair']
normal=json.loads((tmp/'test_owned_raw_source_contract0/source-to-sender.json').read_text())
raw=(tmp/'test_owned_raw_source_contract0/raw-synthetic-source.json').read_bytes()
assert hashlib.sha256(raw).hexdigest()==normal['raw_sha256']==normal['resolution']['raw_sha256']
assert normal['source_reads_for_send']==4 and len(normal['trace'])==7
assert [x['step'] for x in normal['trace']]==['source_load','reserve','source_load','record_attempt','source_load','source_load','settle']
assert normal['source_missing_duplicate_lookup_calls']==0 and normal['complete_history_55_tables_strict_equal']
assert normal['receipt']['journal']['ledger']['slots'][0]['accepted']
late=json.loads((tmp/'test_source_revoked_after_guar0/source-late-revocation.json').read_text())
slot=late['receipt']['journal']['ledger']['slots'][0]
assert slot['settlement']['total_tokens']==8 and not slot['accepted'] and late['receipt']['journal']['ledger']['halted']
assert late['same_original_key_handler_calls']==1 and late['recovery_55_tables_strict_equal']
boundary=json.loads((tmp/'test_new_entry_stays_offline_a0/source-boundary.json').read_text())
assert boundary['default_error']['code']=='LIVE_BLOCKED' and boundary['source_permission_error_propagated']['code']=='PERMISSION_DENIED'
assert boundary['refusals_handler_calls']==0 and boundary['new_entry_refusals_55_tables_strict_equal']
assert boundary['original_data_entry_mock_handler_calls']==1
importers=[]
for path in (repo/'src/sim2act').glob('*.py'):
    if path.name!='production_trial_source.py' and 'import production_trial_source' in path.read_text() or path.name!='production_trial_source.py' and 'from .production_trial_source import' in path.read_text():
        importers.append(str(path.relative_to(repo)))
assert importers==['src/sim2act/production_trial_sender.py']
closure=dict(source_commit=execution['source_commit'],baseline=execution['baseline'],unique_nodes=9,executions=9,passed=9,failed=0,
    junit_seconds=float(suite.attrib['time']),outer_seconds=execution['elapsed_seconds'],inputs=707,production_inputs=138,
    input_drift=False,helper_drift=False,changed_baseline_inputs=['src/sim2act/production_trial_sender.py'],unchanged_baseline_inputs=704,unchanged_baseline_production=136,
    source_production_importers=importers,old_19_12_8_nodes_rerun=0,synthetic_adapter_calls=3,mock_handler_calls=3,real_provider_calls=0,
    source_path_mock_handler_calls=2,original_data_entry_compatibility_mock_calls=1,source_reloads_for_one_exchange=4,
    rejected_cases={item['case']:item['resolution']['source']['decision'] for _,item in rejected},
    normal_raw_source_sha256=normal['raw_sha256'],normal_raw_source_bytes=len(raw),
    late_source_revocation='one guard-passed Mock IO, known body/usage8 retained, current revoked source denies acceptance/halt; no resend',
    source_contract='only fixed explicitly synthetic test-only SQLite evidence contract, no real source producer; no caller source/ALLOW/callback parameter in new sender entry',
    scope='UNINSTALLED; issuer/hash/pairs are not provenance or fee facts; unavailable evidence_fingerprint zero sentinel never usable',
    physical_fixture_databases=databases,database_copies=0,subprocess_crash_windows_run=0,
    row_evidence='actual strict full55-table assertions for all six refusal windows, corrupt mirror and original-key repeats; fixture teardown compares all54 other tables including runs/events and non-new rows; no full-row exports or independent DB reconstruction',
    final_fixture_limitations='normal test removes source pair deliberately; inconsistent test leaves one corrupt source fingerprint to prove UNKNOWN/no auto repair; do not claim all final source fixtures valid',
    parent_guard='socket.connect/connect_ex, real HTTPTransport and Settings.from_env blocked; exact existing InternModel/MockTransport observed, no child processes in this slice',
    not_run=['real account/identity/entitlement/enforcement/revocation/fees/provider/model/semantics','source producer or LIVE/source/sender registration','full generation/source/cold/UI chain','PostgreSQL','Windows/native','remote CI','old 19/12/8 matrices or cancelled window'])
(root/'closure.json').write_text(json.dumps(closure,indent=2)+'\n')
(root/'close-evidence.py').write_bytes(Path(__file__).read_bytes())
manifest={}
for directory,dirs,files in os.walk(root,followlinks=False):
    dirs[:]=[d for d in dirs if not (Path(directory)/d).is_symlink() and d!='__pycache__']
    for name in files:
        path=Path(directory)/name
        if path.is_symlink() or path.suffix in ('.db','.pyc') or name=='sealed-manifest.json':continue
        data=path.read_bytes();manifest[str(path.relative_to(root))]=dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
sealed=dict(scope='SEALED author design/source/first qualification; all nonDB regular files except this manifest, bytecode and symlink aliases; stop writes after seal',files=manifest,files_excluding_manifest=len(manifest),bytes_excluding_manifest=sum(x['bytes'] for x in manifest.values()))
data=(json.dumps(sealed,indent=2)+'\n').encode()
(root/'sealed-manifest.json').write_bytes(data)
print(json.dumps(dict(source_commit=execution['source_commit'],unique_nodes=9,executions=9,pass_count=9,junit_seconds=closure['junit_seconds'],outer_seconds=closure['outer_seconds'],non_db_files=len(manifest),non_db_bytes=sealed['bytes_excluding_manifest'],manifest_bytes=len(data),manifest_sha256=hashlib.sha256(data).hexdigest(),fixture_databases=len(databases),real_provider_calls=0)))
