"""Single-field corruption check; restores the known synthetic release in finally."""
import copy
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import select, update

from sim2act import owner_acceptance as owner
from sim2act.contracts import Limits
from sim2act.db import Store, internal_instances, internal_releases, natural_owner_records
from sim2act.natural_specs import VERSION

HERE = Path(__file__).parent
store = Store("sqlite:///" + str(HERE / "original-p1-fixture-qualified.db"), test_only=True)
limits = Limits(max_requests=1, max_tools=4, max_repairs=0,
    max_total_tokens=1, max_output_tokens=1, run_seconds=60)
with store.tx() as c:
    instance = dict(c.execute(select(internal_instances)).mappings().one())
    release = dict(c.execute(select(internal_releases)).mappings().one())
    row = dict(c.execute(select(natural_owner_records).order_by(natural_owner_records.c.sequence)).mappings().first())
    mutated = copy.deepcopy(release["snapshot"])
    mutated["draft"]["candidate"]["namespace"] = VERSION
    c.execute(update(internal_releases).where(internal_releases.c.id == release["id"]).values(snapshot=mutated))
try:
    with patch.object(owner, "natural_context", side_effect=AssertionError("private context should not be reached")) as blocked:
        result = owner.natural_submit(store, instance["principal_id"], instance["id"],
            row["run_id"], limits, row["payload"]["request"])
        assert result["id"] == row["id"]
        context_calls = blocked.call_count
finally:
    with store.tx() as c:
        c.execute(update(internal_releases).where(internal_releases.c.id == release["id"]).values(snapshot=release["snapshot"]))
result = {"qualification": "BOUNDED_STORAGE_CONTROL_FLOW_ONLY_NOT_ACTUAL_WORKER",
    "fault": "Only release snapshot draft candidate namespace changed; no independent natural Run seal exists",
    "old_key_accepted_under_spoofed_namespace": True,
    "natural_context_calls": context_calls, "synthetic_release_restored": True,
    "source_sha256": hashlib.sha256(Path(owner.__file__).read_bytes()).hexdigest()}
(HERE / "namespace-only-p2-result.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
