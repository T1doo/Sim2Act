import datetime,json,sys
from pathlib import Path
sys.path.insert(0,'/workspace/Sim2Act/tests')
from local_record_control_assertions import assert_control_changes

def test_closed_original_snapshot_oracle():
    original=Path('/workspace/local-record-controls-20261018')
    case=original/'pytest-temp/test_local_record_page_explici0'
    execution=json.loads((original/'execution.json').read_text())
    bounds=tuple(datetime.datetime.fromisoformat(execution[key]).timestamp() for key in ['started_at','ended_at'])
    before=json.loads((case/'database-before-page.json').read_text())
    after=json.loads((case/'database-after-page.json').read_text())
    info=json.loads((case/'info.json').read_text())
    proof=assert_control_changes(before,after,info['seed_run'],time_bounds=bounds)
    proof.update(classification='PURE_CLOSED_JSON_ORACLE_NO_PRODUCT_DB_OR_WORKER_EXECUTION',original_pytest='FAIL_HEARTBEAT_ORACLE',original_page='PASS',probe_id_independently_captured=False,probe_identity_limit='Unique new heartbeat shape/id/time verified; original inline Worker object id was not separately recorded. Future harness captures it.',original_unclaimed_worker_assertion='Executed before original failure; no new Worker here')
    (Path(__file__).parent/'closed-snapshot-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
