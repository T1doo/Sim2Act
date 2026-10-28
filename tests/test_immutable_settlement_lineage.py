"""Full original synthetic lineage replay; no saved Run is resumed/executed.

The archived accepted B2 DB is copied into a fresh private temporary database.
Only public bound, pure candidate compilation, and deliberate SQL fault edits
run. No Worker/model/transport, lease renewal, or old approval is reused.
"""

import gzip
from pathlib import Path

import pytest
from sqlalchemy import select, update

from sim2act import natural_specs as natural
from sim2act import pa_spec_apps as spec
from sim2act import pb_natural_specs as pb
from sim2act._immutable_settlement import ContentPlan
from sim2act.contracts import Limits
from sim2act.db import Store, grants, resources, runs
from sim2act.errors import DomainError

ARCHIVE = Path(__file__).resolve().parents[1] / (
    "docs/evidence/cloud-frontier-structure-20261028/originals/fixture.db.gz"
)


@pytest.fixture
def lineage(tmp_path):
    path = tmp_path / "owned-plan-private-lineage.db"
    path.write_bytes(gzip.decompress(ARCHIVE.read_bytes()))
    store = Store("sqlite:///" + str(path), test_only=True)
    other = Store("sqlite:///" + str(path), test_only=True)
    limits = Limits(
        max_requests=4,
        max_tools=4,
        max_repairs=1,
        max_total_tokens=64000,
        max_output_tokens=1024,
        run_seconds=300,
    )
    try:
        with store.tx() as c, pb._source_reads(store, c):
            jobs = c.execute(select(runs)).mappings().all()
            job = dict(
                next(
                    row
                    for row in reversed(jobs)
                    if row["context"].get("spec_family") == natural.VERSION
                )
            )
            binding = spec.bound(store, c, job["principal_id"], job, limits)
        plan = ContentPlan.compile(
            dict(
                candidate=binding["draft"]["candidate"],
                platform=limits.model_dump(),
                call=dict(wire=b"synthetic plan fixture"),
            )
        )
        yield store, other, job, limits, binding, plan
    finally:
        store.engine.dispose()
        other.engine.dispose()


def test_complete_nonzero_binding_reconstructs_in_new_transaction(lineage):
    store, other, job, limits, original, plan = lineage
    with other.tx() as c, pb._source_reads(other, c):
        current = plan.read_current(other, c, job["principal_id"], job, limits)
        assert current == original
        assert current is not original
        assert current["draft"]["candidate"] is not original["draft"]["candidate"]
    assert not hasattr(plan, "graph") and not hasattr(plan, "permission")


def test_external_committed_source_change_rejected_by_fresh_full_binding(lineage):
    store, other, job, limits, binding, plan = lineage
    with other.tx() as c:
        result = c.execute(
            update(resources)
            .where(resources.c.id == binding["source"]["resource_id"])
            .values(content="changed by independent connection")
        )
        assert result.rowcount == 1
    with pytest.raises(DomainError):
        with store.tx() as c, pb._source_reads(store, c):
            plan.read_current(store, c, job["principal_id"], job, limits)


def test_external_revocation_rechecked_not_inherited_from_plan(lineage):
    store, other, job, limits, binding, plan = lineage
    with other.tx() as c:
        result = c.execute(
            update(grants)
            .where(grants.c.resource_id == binding["source"]["resource_id"])
            .values(revoked=True)
        )
        assert result.rowcount > 0
    with pytest.raises(DomainError):
        with store.tx() as c, pb._source_reads(store, c):
            plan.read_current(store, c, job["principal_id"], job, limits)


def test_rejected_dependency_edit_rolls_back_and_plan_is_still_only_data(lineage):
    store, other, job, limits, binding, plan = lineage
    with pytest.raises(DomainError):
        with store.tx() as c, pb._source_reads(store, c):
            c.execute(
                update(resources)
                .where(resources.c.id == binding["source"]["resource_id"])
                .values(content="uncommitted bad edit")
            )
            # Writes invalidate the old read scope. Start the original fresh one.
            with pb._source_reads(store, c):
                plan.read_current(store, c, job["principal_id"], job, limits)
    with other.tx() as c, pb._source_reads(other, c):
        assert plan.read_current(other, c, job["principal_id"], job, limits) == binding
