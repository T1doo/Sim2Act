"""Actual65 successful source AppRuns; no fabricated Run/journal or limit override."""
from pathlib import Path
import datetime
import json
import time

from sqlalchemy import select
from test_registered_text_extraction import prepared, snapshot
from test_persistent_app_runs import NoModel

from sim2act.db import attempts, internal_app_runs, internal_instance_data, internal_run_bindings, operations, runs
from sim2act.db import registered_extraction_requests as journal
from sim2act.worker import Worker

OUT = Path(__file__).parent

def test_project64_sources_budget_is_enforced_before65th_prepare(env):
    started = time.monotonic()
    values = prepared(env)
    data, source, release, instance, first_run, target, resource, first_url = values
    store, settings, client, user, project, *_ = data
    worker = Worker(store, settings, NoModel())
    project_url = f'/api/projects/{project}/registered-text-requests'
    records = []
    stage = 'SETUP'
    report = {'classification':'ACTUAL_SQLITE_AUTHENTICATED_HTTP_NORMAL_WORKER_65_SUCCEEDED_APPRUNS_SAME_INSTANCE','source_app':source,'instance':instance['id'],'project':project,'target_app':target,'target_resource':resource,'scope':'Synthetic upstream fixture only; repeated literal Worker must use NoModel. No DB row insertion/update, fake Run/journal, runtime limit overrides, new grant, or provider calls by this script.','records':records}
    existing_actions = []
    report['existing_source_actions_at_cap'] = existing_actions
    final_prepare = None
    index64 = None
    index65 = None
    try:
        for number in range(1, 66):
            stage = f'APP_RUN_{number}'
            if number == 1:
                actual = first_run
                queued = None
            else:
                queued_response = client.post(
                    f"/api/internal/instances/{instance['id']}/runs",
                    json={'expected_revision':instance['revision'],'expected_release_fingerprint':release['fingerprint'],'input':{'term':'Beta'},'request_key':f'independent-budget-run-{number:03d}'},
                )
                queued = {'status':queued_response.status_code,'body':queued_response.json()}
                assert queued_response.status_code == 202, queued_response.text
                assert worker.once(), 'Normal Worker did not claim a queued AppRun'
                read_response = client.get(f"/api/internal/instances/{instance['id']}/runs/{queued['body']['run_id']}")
                assert read_response.status_code == 200, read_response.text
                actual = read_response.json()
            record = {'number':number,'queued':queued,'run_id':actual['id'],'status':actual['status'],'result_version':actual['result_version'],'result':actual['result']}
            records.append(record)
            assert actual['status'] == 'SUCCEEDED', actual
            assert actual['result_version'] == number
            with store.tx() as c:
                record['attempts'] = [dict(r) for r in c.execute(select(attempts).where(attempts.c.run_id==actual['id'])).mappings()]
                record['operations'] = [dict(r) for r in c.execute(select(operations).where(operations.c.run_id==actual['id'])).mappings()]
                bound = dict(c.execute(select(internal_run_bindings).where(internal_run_bindings.c.run_id==actual['id'])).mappings().one())
                record['binding'] = bound
                record['app_run'] = dict(c.execute(select(internal_app_runs).where(internal_app_runs.c.id==bound['app_run_id'])).mappings().one())
                typed = [dict(r) for r in c.execute(select(internal_instance_data).where(internal_instance_data.c.run_id==bound['app_run_id'])).mappings()]
                record['typed_records'] = typed
            assert record['attempts'] == [], 'Literal AppRun unexpectedly called a provider'
            assert record['app_run']['status'] == 'SUCCEEDED'
            assert record['app_run']['instance_id'] == instance['id']
            assert len(record['typed_records']) == 1
            assert len(record['operations']) == 1 and record['operations'][0]['status'] == 'VERIFIED'
            url = f"/api/internal/instances/{instance['id']}/runs/{actual['id']}"
            stage = f'OPTIONS_{number}'
            options = client.get(url+'/extraction-options')
            assert options.status_code == 200, options.text
            value = options.json()
            selected = next(t for t in value['targets'] if t['id']==target)
            body = {'expected_proof_fingerprint':value['source_proof_fingerprint'],'target_app_id':target,'expected_target_draft_fingerprint':selected['fingerprint'],'name':f'Explicit first request for source {number}','request_key':f'independent-budget-original-{number:03d}','expected_latest_key':None,'expected_latest_candidate_fingerprint':None}
            record['options'] = value
            record['prepare_request'] = body
            with store.tx() as c:
                journal_before = [dict(r) for r in c.execute(select(journal)).mappings()]
            all_tables_before = snapshot(store) if number == 65 else None
            stage = f'PREPARE_{number}'
            reply = client.post(url+'/extraction-requests',json=body)
            record['prepare_response'] = {'status':reply.status_code,'body':reply.json()}
            with store.tx() as c:
                journal_after = [dict(r) for r in c.execute(select(journal)).mappings()]
            record['journal_count_before'] = len(journal_before)
            record['journal_count_after'] = len(journal_after)
            record['journal_unchanged'] = journal_before==journal_after
            if number == 65:
                record['all_tables_unchanged'] = all_tables_before == snapshot(store)
            if number < 65:
                assert reply.status_code == 201, reply.text
                assert reply.json()['sequence']==1 and reply.json()['state']=='PREPARED'
                assert len(journal_after)==number
            else:
                final_prepare = reply
            if number in (64,65):
                index = client.get(project_url)
                record['project_index'] = {'status':index.status_code,'body':index.json(),'cache_control':index.headers.get('cache-control')}
                if number == 64:
                    index64 = index
                    assert index.status_code==200 and len(index.json()['items'])==64, index.text
                    # Full project source budget must still permit stopping an existing
                    # source and a new explicit key in that same source history.
                    first_meta = records[0]['prepare_response']['body']
                    close_request = {'request_key':first_meta['request_key'],'expected_latest_key':first_meta['request_key'],'expected_request_fingerprint':first_meta['request_fingerprint']}
                    stopped = client.post(first_url+'/extraction-request-close',json=close_request)
                    existing_actions.append({'action':'CLOSE_EXISTING_AT64','request':close_request,'status':stopped.status_code,'body':stopped.json()})
                    assert stopped.status_code==200 and stopped.json()['state']=='CLOSED'
                    next_body = {**records[0]['prepare_request'],'request_key':'independent-budget-existing-next-key','name':'Explicit new key on existing source at cap','expected_latest_key':first_meta['request_key']}
                    same = client.post(first_url+'/extraction-requests',json=next_body)
                    existing_actions.append({'action':'PREPARE_EXISTING_NEW_KEY_AT64','request':next_body,'status':same.status_code,'body':same.json()})
                    assert same.status_code==201 and same.json()['sequence']==2
                    still = client.get(project_url)
                    existing_actions.append({'action':'INDEX_STILL64','status':still.status_code,'body':still.json()})
                    assert still.status_code==200 and len(still.json()['items'])==64
                else:
                    index65 = index
        stage = 'FINAL_BUDGET_ASSERTION'
        report['succeeded_source_runs'] = len(records)
        report['distinct_run_ids'] = len({r['run_id'] for r in records})
        report['source64_index_status'] = index64.status_code
        report['source65_prepare_status'] = final_prepare.status_code
        report['source65_index_status'] = index65.status_code
        report['source65_index_body'] = index65.json()
        assert final_prepare.status_code==400 and final_prepare.json()['error']['code']=='BUDGET_EXHAUSTED' and records[-1]['journal_unchanged'] and records[-1]['all_tables_unchanged'], '65th actual successful source was allowed to persist; expected budget rejection before write to keep cold project discovery available'
        assert index65.status_code==200 and len(index65.json()['items'])==64
    finally:
        report.update(stage=stage, elapsed_seconds=round(time.monotonic()-started,3), finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
        with store.tx() as c:
            report['final_journal_metadata'] = [dict(r) for r in c.execute(select(*(column for column in journal.c if column.name!='request'))).mappings()]
            report['source_successful_app_run_count'] = len(list(c.execute(select(internal_app_runs.c.id).where(internal_app_runs.c.instance_id==instance['id'],internal_app_runs.c.status=='SUCCEEDED')).scalars()))
        path=OUT/'actual65-budget-proof.json'
        assert not path.exists()
        path.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
