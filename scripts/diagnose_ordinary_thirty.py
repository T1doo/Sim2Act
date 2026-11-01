"""Manual original-30 controller diagnostic. No new authorization or clock replacement.

Run explicitly with pytest, PYTHONPATH including src/tests, and
SIM2ACT_DIAGNOSTIC_SOURCE bound to the frozen application commit.
Existing synthetic controller fixtures still apply; this is not live acceptance."""
import ast,json,sqlite3,time,traceback,os,subprocess,io,tarfile,hashlib
from contextlib import closing
from pathlib import Path
from types import SimpleNamespace

from dataclasses import replace
from conftest import env as env
from test_cold_control_full_flow import original_flow,observe_original_lease_failures as observe_original_lease_failures,no_real_http as no_real_http
from test_cold_snapshot_full_flow import snapshots
import test_pb_spec_production_controller as controller_test
from sim2act import natural_live_admission as gate
from sim2act.db import fingerprint


def require_ordinary_caps(contract):
    """Exact declared old schema for ordinary models and immutable PB Views."""
    assert gate._contract_kind(contract.caps) is gate.TrialCaps
    raw=contract.caps.model_dump()
    assert raw['lease_seconds']==30
    assert not {'settlement_seconds','settlement_protocol'} & raw.keys()
    return raw


def validate_negative_state(run, attempt, operation, internal, typed, event_rows, failure_observations):
    """Read-only budget-negative assertions, also usable on a closed saved case.

    Neither state is goal success. REJECTED_KNOWN is the original finite-budget
    handler; RECEIVED/DISPATCHED is a distinct unresolved receipt boundary.
    Prior verified READ operations do not prove this model operation settled.
    """
    failures=[row for row in failure_observations if row['run_id']==run['id']]
    assert len(failures)==1
    assert failures[0]['error']['code']=='BUDGET_EXHAUSTED'
    assert failures[0]['error']['message']=='Finite model settlement interval ended'
    assert run['status'] != 'SUCCEEDED'
    operation_id=json.loads(attempt['parameters'])['natural_spec']['operation_id']
    assert operation['id']==operation_id and operation['run_id']==run['id']==attempt['run_id']
    settled=sum(r['kind'] in ('NS_SETTLED','NS_SETTLEMENT_LEASE_RESERVED') or
        r['kind']=='SPEC_STEP_VERIFIED' and r['data'].get('operation_id')==operation_id for r in event_rows)
    response=json.loads(attempt['response']);usage=json.loads(attempt['usage'])
    received=[r for r in event_rows if r['kind']=='NS_RECEIVED']
    rejected=[r for r in event_rows if r['kind']=='NS_REJECTED']
    assert len(received)==1 and response is not None and usage['status']=='known'
    assert fingerprint(response)==received[0]['data']['response_fingerprint']
    if attempt['status']=='REJECTED_KNOWN':
        assert operation['status']=='REJECTED_KNOWN' and len(rejected)==1
        assert rejected[0]['data']['error']=='BUDGET_EXHAUSTED'
    else:
        assert attempt['status']=='RECEIVED' and operation['status']=='DISPATCHED' and not rejected
    assert (json.loads(operation['receipt']) if operation['receipt'] is not None else None) is None
    assert (json.loads(internal['output']) if internal['output'] is not None else None) is None
    assert internal['result_version'] is None and typed==0 and settled==0
    assert (json.loads(run['result']) if run['result'] is not None else None) is None
    return usage


def selected_negative_events(event_rows, attempt_id):
    # Ordinary caps never reserve any signed extended settlement interval,
    # including for a previous successfully committed model in the same Run.
    assert not any(r['kind']=='NS_SETTLEMENT_LEASE_RESERVED' for r in event_rows)
    return [r for r in event_rows if r['kind'] not in (
        'NS_RECEIVED','NS_REJECTED','NS_SETTLED')
        or r['data'].get('attempt_id')==attempt_id]


def test_original_thirty_large_goal_or_safe_budget_refusal(env,tmp_path,monkeypatch):
    source=os.environ['SIM2ACT_DIAGNOSTIC_SOURCE']
    from sim2act import natural_spec_runtime as runtime
    # Bind every tracked application resource, not merely the unchanged runtime
    # module. Native callee/build qualification remains the original product's.
    archive=subprocess.check_output(['git','archive',source,'src/sim2act'],
        cwd=os.environ.get('SIM2ACT_SOURCE_REPO','/workspace/Sim2Act'))
    base=Path(runtime.__file__).resolve().parent
    checked={}
    with tarfile.open(fileobj=io.BytesIO(archive)) as tree:
        for member in tree:
            if member.isdir():continue
            assert member.isfile() and member.name.startswith('src/sim2act/')
            relative=member.name.removeprefix('src/sim2act/')
            expected=tree.extractfile(member).read()
            assert (base/relative).read_bytes()==expected, relative
            checked[relative]=hashlib.sha256(expected).hexdigest()
    assert checked
    opened=snapshots(monkeypatch,env[1].database_url)
    original_prepare=controller_test.prepare_pb
    changes=[]
    # Restore the original helper reference before any application code runs.
    # Only choose a freshly approved old TrialCaps payload, never mutate approval.
    def ordinary_prepare(env,out):
        controller_test.prepare_pb=original_prepare
        data=controller_test.apps.setup(env)
        account='synthetic-pb-production-shape'
        subject=controller_test.admission.canonical_quota_subject(account)
        data=(data[0],replace(data[1],quota_subject=subject),*data[2:])
        data[0].initialize(quota_subject=subject)
        original,consent=controller_test.frozen(data,ttl=1800)
        contract=gate.PBTrialContract(**(original.model_dump()|dict(quota_subject=subject,
            caps=gate.TrialCaps().model_dump())),path='P-B',
            extraction_request_key='original-pb-production-extraction',
            extraction_recipe=controller_test.apps.recipe('ordered'))
        consent=consent.model_copy(update=dict(expected_contract_fingerprint=fingerprint(contract.model_dump())))
        gate.approve(data[0],data[3],contract,consent)
        changes.append({'caps':contract.caps.model_dump(),'caps_exact_type':type(contract.caps) is gate.TrialCaps,'approval_key':consent.request_key,
            'contract_fingerprint':fingerprint(contract.model_dump()),'original_approve_used':True})
        return data,SimpleNamespace(contract=contract,approval_key=consent.request_key,account_id=account)
    monkeypatch.setattr(controller_test,'prepare_pb',ordinary_prepare)
    caught=None;frame=None
    try:original_flow(env,tmp_path,monkeypatch)
    except AssertionError as error:
        caught=error;tb=error.__traceback__
        while tb:
            if tb.tb_frame.f_code is original_flow.__code__:frame=tb.tb_frame
            tb=tb.tb_next
    finally:
        # Always retain actual intervals, including an unclassified failure
        # in this diagnostic's own assertions. No business decision uses it.
        (tmp_path/'ordinary-thirty-observed.json').write_text(json.dumps(dict(
            classification='RAW_REAL_CLOCK_ORDINARY30_OBSERVATIONS_NOT_GOAL_VERDICT',
            source_commit=source, ordinary_caps=changes,
            records=[r for store in opened for r in store._local_model_snapshot_records]),indent=2)+'\n')
    assert len(changes)==1 and changes[0]['caps_exact_type'] is True
    assert changes[0]['caps']['lease_seconds']==30
    assert not {'settlement_seconds','settlement_protocol'} & changes[0]['caps'].keys()
    if caught is None:
        records=list(opened[0]._local_model_snapshot_records)
        assert len(records)==2 and all(r['outcome']=='COMMITTED' for r in records)
        assert len((tmp_path/'mock-exchanges.jsonl').read_text().splitlines())==7
        proof=json.loads((tmp_path/'pb-controller-proof.json').read_text())
        assert proof['result']['status']=='SUCCEEDED'
        (tmp_path/'ordinary-thirty-result.json').write_text(json.dumps(dict(
            status='GOAL_COMPLETED_UNDER_ORIGINAL_CONTROLLER_ASSERTIONS',source_commit=source,
            source_files=checked,ordinary_caps=changes,
            records=records,fixed_mock_requests=7,real_model_requests=0),indent=2)+'\n')
        return
    assert frame is not None
    text=Path(original_flow.__code__.co_filename).read_text()
    wanted=next(n.lineno for n in ast.walk(ast.parse(text)) if isinstance(n,ast.Assert)
        and ast.get_source_segment(text,n.test)=='result.status_code == 200 and result.json()["status"] == "SUCCEEDED"')
    last=traceback.extract_tb(caught.__traceback__)[-1]
    assert Path(last.filename)==Path(original_flow.__code__.co_filename) and last.lineno==wanted,(last,wanted)
    binding=frame.f_locals['binding'];cold=frame.f_locals['cold_id']
    require_ordinary_caps(binding.contract)
    assert len(changes)==1 and changes[0]['caps']['lease_seconds']==30
    assert 'settlement_seconds' not in changes[0]['caps']
    assert len(opened)==1
    records=list(opened[0]._local_model_snapshot_records)
    assert 1<=len(records)<=2 and records[-1]['outcome']=='ROLLED_BACK'
    assert all(r['outcome']=='COMMITTED' for r in records[:-1])
    assert 27<records[-1]['seconds']<120
    # The original controller has returned and its stores/worker have closed.
    # These are negative-case reads, not a first-success readback claim.
    db=tmp_path/'fixture.db'
    with closing(sqlite3.connect('file:'+str(db)+'?mode=ro',uri=True)) as c:
        c.row_factory=sqlite3.Row
        run=dict(c.execute('SELECT * FROM runs WHERE id=?',(cold,)).fetchone())
        all_cold_attempts=[dict(r) for r in c.execute('SELECT * FROM attempts WHERE run_id=?',(cold,))]
        target=[r for r in all_cold_attempts if r['status'] in ('RECEIVED','REJECTED_KNOWN')]
        assert len(target)==1 and len(all_cold_attempts)==len(records)
        attempt=target[0]
        operation_id=json.loads(attempt['parameters'])['natural_spec']['operation_id']
        operation=dict(c.execute('SELECT * FROM operations WHERE id=? AND run_id=?',(operation_id,cold)).fetchone())
        internal=dict(c.execute('SELECT a.* FROM internal_app_runs a JOIN internal_run_bindings b ON b.app_run_id=a.id WHERE b.run_id=?',(cold,)).fetchone())
        typed=c.execute('SELECT count(*) FROM internal_instance_data WHERE instance_id=?',(internal['instance_id'],)).fetchone()[0]
        event_rows=[dict(r) for r in c.execute('SELECT * FROM events WHERE run_id=?',(cold,))]
        for r in event_rows:r['data']=json.loads(r['data'])
        settled=sum(r['kind'] in ('NS_SETTLED','NS_SETTLEMENT_LEASE_RESERVED') or
            r['kind']=='SPEC_STEP_VERIFIED' and r['data'].get('operation_id')==operation_id for r in event_rows)
        total=c.execute('SELECT count(*) FROM attempts').fetchone()[0]
    assert run['status']!='SUCCEEDED' and run['created_at']+300>time.time()
    assert binding.contract.expires_at>time.time()
    failures=[json.loads(row) for row in (tmp_path/'failure-observations.jsonl').read_text().splitlines()]
    # A prior Cold may already be VERIFIED. Its settled event must not be
    # mistaken for this failed attempt's settlement, nor silently discarded.
    selected_events=selected_negative_events(event_rows,attempt['id'])
    usage=validate_negative_state(run, attempt, operation, internal, typed, selected_events, failures)
    expected_requests=5+len(records)
    assert total==expected_requests and len((tmp_path/'mock-exchanges.jsonl').read_text().splitlines())==expected_requests
    result={'classification':'ORIGINAL_TRIALCAPS_30_REAL_CLOCK_SQLITE_FIXED_MOCK_NEGATIVE_NOT_LIVE',
        'candidate_source':source,'source_files':checked,'status':'PASS_NEGATIVE_FAILED_ATTEMPT_NOT_COMMITTED',
        'contract_input_change_only':changes,'old_caps_not_upgraded':True,'run_id':cold,'run_status':run['status'],
        'expired_lease_wall':run['lease_until'],'run_and_trial_deadlines_still_future':True,
        'received_response_preserved':True,'known_usage':usage,'response_fingerprint_matches_received':True,'attempt_id':attempt['id'],'operation_id':operation['id'],
        'attempt_status':attempt['status'],'operation_status':operation['status'],
        'typed_results':typed,'all_run_NS_SETTLED_events':sum(r['kind']=='NS_SETTLED' for r in event_rows),
        'all_run_extended_lease_reservations':0,
        'selected_model_verified_events':sum(r['kind']=='SPEC_STEP_VERIFIED' and r['data'].get('operation_id')==operation_id for r in event_rows),'records':records,
        'failed_cold_ordinal':len(records),'prior_cold_attempts':[
            dict(id=r['id'],status=r['status']) for r in all_cold_attempts if r['id']!=attempt['id']],
        'fixed_mock_requests':expected_requests,'real_model_requests':0,'automatic_replay':False,
        'original_success_assertion_failure':{'file':str(last.filename),'line':last.lineno,'message':str(caught)}}
    (tmp_path/'ordinary-thirty-result.json').write_text(json.dumps(result,indent=2)+'\n')
