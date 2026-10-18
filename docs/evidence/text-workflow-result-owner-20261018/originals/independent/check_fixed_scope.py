"""Short family-scope regression on the original synthetic control-flow database."""
import json
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import event, select

from sim2act import owner_acceptance as owner
from sim2act.contracts import Limits
from sim2act.db import Store, fingerprint, internal_instances, natural_owner_records
from sim2act.errors import DomainError

HERE = Path(__file__).parent
store = Store("sqlite:///" + str(HERE / "original-p1-fixture-qualified.db"), test_only=True)
limits = Limits(max_requests=1, max_tools=4, max_repairs=0,
    max_total_tokens=1, max_output_tokens=1, run_seconds=60)
with store.tx() as c:
    instance = dict(c.execute(select(internal_instances)).mappings().one())
    before = [dict(r) for r in c.execute(select(natural_owner_records)).mappings()]
first, last = before
user, iid, rid = instance["principal_id"], instance["id"], first["run_id"]
original = first["payload"]["request"]
stop = {"command": "CANCEL", "request_key": "fixed-cross-family-stop", "expected_sequence": 2,
    "target_id": last["id"], "target_fingerprint": last["fingerprint"], "reason": "Synthetic scope check"}
traces, outcomes = [], []

def trace(conn, cursor, statement, parameters, context, many):
    traces.append({"sql": statement, "parameters": parameters})

event.listen(store.engine, "before_cursor_execute", trace)
with patch.object(owner, "natural_context", side_effect=AssertionError("must not reach private context")) as blocked:
    for name, call in [
        ("original_key", lambda: owner.natural_submit(store, user, iid, rid, limits, original)),
        ("stop", lambda: owner.natural_submit(store, user, iid, rid, limits, stop)),
        ("read_metadata", lambda: owner.natural_read(store, user, iid, rid, limits, original["request_key"])),
    ]:
        start = len(traces)
        try:
            call()
        except DomainError as error:
            outcomes.append({"operation": name, "error": error.code,
                "sql_start": start, "sql_end": len(traces)})
        else:
            raise AssertionError(name + " accepted a four-step Run at the natural-spec route")
    context_calls = blocked.call_count
event.remove(store.engine, "before_cursor_execute", trace)
with store.tx() as c:
    after = [dict(r) for r in c.execute(select(natural_owner_records)).mappings()]
assert all(item["error"] == "UNSUPPORTED_CAPABILITY" for item in outcomes)
assert not any("natural_owner" in item["sql"] for item in traces)
assert fingerprint(before) == fingerprint(after)
assert context_calls == 0
result = {"qualification": "BOUNDED_STORAGE_CONTROL_FLOW_ONLY_NOT_ACTUAL_WORKER",
    "outcomes": outcomes, "owner_tables_queried": False,
    "owner_rows_unchanged": True, "natural_context_calls": context_calls,
    "source_sha256": __import__("hashlib").sha256(Path(owner.__file__).read_bytes()).hexdigest(),
    "traces": traces}
(HERE / ("fixed-scope-result-" + result["source_sha256"][:12] + ".json")).write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({k: v for k, v in result.items() if k != "traces"}, indent=2))
