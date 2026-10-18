"""Regression for the independent natural Run family marker, no Worker qualification."""
import copy
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import event, select, update

from sim2act import owner_acceptance as owner
from sim2act.contracts import Limits
from sim2act.db import Store, fingerprint, internal_instances, internal_releases, natural_owner_records
from sim2act.errors import DomainError
from sim2act.natural_specs import VERSION

HERE = Path(__file__).parent
store = Store("sqlite:///" + str(HERE / "original-p1-fixture-qualified.db"), test_only=True)
limits = Limits(max_requests=1, max_tools=4, max_repairs=0,
    max_total_tokens=1, max_output_tokens=1, run_seconds=60)
with store.tx() as c:
    instance = dict(c.execute(select(internal_instances)).mappings().one())
    release = dict(c.execute(select(internal_releases)).mappings().one())
    before = [dict(x) for x in c.execute(select(natural_owner_records)).mappings()]
    row = before[0]
    mutated = copy.deepcopy(release["snapshot"])
    mutated["draft"]["candidate"]["namespace"] = VERSION
    c.execute(update(internal_releases).where(internal_releases.c.id == release["id"]).values(snapshot=mutated))
traces, error = [], None
def trace(conn, cursor, statement, parameters, context, many):
    traces.append({"sql": statement, "parameters": parameters})
event.listen(store.engine, "before_cursor_execute", trace)
try:
    with patch.object(owner, "natural_context", side_effect=AssertionError("must not reach private context")) as blocked:
        try:
            owner.natural_submit(store, instance["principal_id"], instance["id"],
                row["run_id"], limits, row["payload"]["request"])
        except DomainError as rejected:
            error = rejected.code
        context_calls = blocked.call_count
finally:
    event.remove(store.engine, "before_cursor_execute", trace)
    with store.tx() as c:
        c.execute(update(internal_releases).where(internal_releases.c.id == release["id"]).values(snapshot=release["snapshot"]))
with store.tx() as c:
    after = [dict(x) for x in c.execute(select(natural_owner_records)).mappings()]
assert error == "VERSION_CONFLICT"
assert not any("natural_owner" in item["sql"] for item in traces)
assert context_calls == 0 and fingerprint(before) == fingerprint(after)
result = {"qualification": "BOUNDED_STORAGE_CONTROL_FLOW_ONLY_NOT_ACTUAL_WORKER",
    "error": error, "owner_tables_queried": False, "owner_rows_unchanged": True,
    "natural_context_calls": context_calls, "synthetic_release_restored": True,
    "source_sha256": hashlib.sha256(Path(owner.__file__).read_bytes()).hexdigest(), "traces": traces}
(HERE / ("fixed-namespace-result-" + result["source_sha256"][:12] + ".json")).write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({k: v for k, v in result.items() if k != "traces"}, indent=2))
