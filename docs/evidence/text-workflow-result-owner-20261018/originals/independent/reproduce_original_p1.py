"""Bounded storage/control-flow reproduction; no Worker or complete Run qualification."""
import importlib.util
import json
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import insert, select

from sim2act.contracts import Limits
from sim2act.db import (
    Store, fingerprint, internal_app_runs, internal_instance_data, internal_instances,
    internal_releases, internal_run_bindings, natural_owner_records, new_id, runs,
)

HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location(
    "sim2act.owner_acceptance_before_fix", HERE / "owner_acceptance_before_fix.py")
owner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(owner)
store = Store("sqlite:///" + str(HERE / "original-p1-fixture-qualified.db"), test_only=True)
store.initialize()
user = store.user("synthetic reviewer", "synthetic-review-only")
pid = store.project(user, "synthetic P1 control-flow")
iid, aid, app, rid, release, runtime = [new_id(x) for x in
    ["iinstance", "iapprun", "app", "run", "irelease", "appruntime"]]
with store.tx() as c:
    c.execute(insert(internal_releases).values(id=release, project_id=pid,
        principal_id=user, approval_id=new_id("iapproval"), fingerprint="0" * 64,
        snapshot={"draft": {"candidate": {"namespace": "closed-text-four-step.v1"}}}))
    c.execute(insert(internal_instances).values(id=iid, principal_id=user, project_id=pid,
        source_app_id=app, runtime_id=runtime, release_id=release, revision=1,
        data_version=1, history=[]))
    c.execute(insert(internal_app_runs).values(id=aid, instance_id=iid, release_id=release,
        principal_id=user, request_key="synthetic-four-step", fingerprint="0" * 64,
        input={}, status="SUCCEEDED", result_version=1))
    c.execute(insert(internal_run_bindings).values(run_id=rid, app_run_id=aid,
        snapshot={}, fingerprint="0" * 64))
    c.execute(insert(runs).values(id=rid, principal_id=user, project_id=pid,
        runtime_id=runtime, status="SUCCEEDED", request_key="internal:" + aid,
        resource_refs=[], context={}, result={}))
    body = {"command": "PREPARE", "request_key": "four-prepare", "expected_sequence": 0,
        "expected_contract_fingerprint": fingerprint({"version": "owner.text-four-step.v1"})}
    first = owner.natural_append(c, user, pid, iid, rid, [], body, "PENDING",
        contract={"version": "owner.text-four-step.v1"}, expires_at=9999999999)

limits = Limits(max_requests=1, max_tools=4, max_repairs=0,
    max_total_tokens=1, max_output_tokens=1, run_seconds=60)
with patch.object(owner, "natural_context", side_effect=AssertionError("must not reach private context")) as blocked:
    old = owner.natural_submit(store, user, iid, rid, limits, body)
    stop = owner.natural_submit(store, user, iid, rid, limits, {
        "command": "CANCEL", "request_key": "wrong-family-stop", "expected_sequence": 1,
        "target_id": first["id"], "target_fingerprint": first["fingerprint"],
        "reason": "Synthetic old natural endpoint family confusion"})
    context_calls = blocked.call_count
with store.tx() as c:
    rows = [dict(x) for x in c.execute(select(natural_owner_records)).mappings()]
    typed = len(c.execute(select(internal_instance_data)).all())
result = {"qualification": "BOUNDED_STORAGE_CONTROL_FLOW_ONLY_NOT_ACTUAL_WORKER",
    "old_key_returned_four_step_record": old == first,
    "old_natural_submit_appended_cancel": stop["status"] == "CANCELLED",
    "natural_context_calls": context_calls, "owner_rows": rows,
    "typed_result_rows": typed, "model_requests": 0}
assert result["old_key_returned_four_step_record"]
assert result["old_natural_submit_appended_cancel"]
assert context_calls == 0
(HERE / "original-p1-result.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({k: v for k, v in result.items() if k != "owner_rows"}, indent=2))
