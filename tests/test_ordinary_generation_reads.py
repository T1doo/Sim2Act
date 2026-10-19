"""An actual ordinary mock generation keeps complete proof and live Grant guards."""

import copy
import json
import time
from types import SimpleNamespace

import pytest
import test_natural_spec_apps as apps
from sqlalchemy import select, update

from sim2act import db
from sim2act import goal_applications as generation
from sim2act import pb_natural_specs as source
from sim2act.contracts import Limits
from sim2act.db import attempts, grants, runs
from sim2act.errors import DomainError


def test_actual_generation_reuse_requires_absent_binding_and_keeps_write_expiry_guards(env, monkeypatch, tmp_path):
    data = apps.setup(env)
    rid, _, sent = apps.generate(data, style="ordered")
    assert len(sent) == 3
    store = data[0]
    limits = Limits(**{key: getattr(data[1], key) for key in Limits.model_fields})
    actual_proof = generation._verified_candidate
    full_proofs = []

    def counted(*args, **kwargs):
        full_proofs.append(rid)
        return actual_proof(*args, **kwargs)

    monkeypatch.setattr(generation, "_verified_candidate", counted)

    class RollbackFixture(Exception):
        pass

    with pytest.raises(RollbackFixture), store.tx() as connection:
        job = connection.execute(select(runs).where(runs.c.id == rid)).mappings().one()
        assert generation.source_scope_gate(store, connection, rid)
        assert generation._ordinary_generation_reads(store, connection, rid)
        row = connection.execute(select(attempts).where(attempts.c.run_id == rid)).mappings().first()
        original_parameters = copy.deepcopy(row["parameters"])
        # An explicit null is a present binding, not an ordinary missing key.
        connection.execute(update(attempts).where(attempts.c.id == row["id"])
                           .values(parameters={**original_parameters, "pa_trial_binding": None}))
        assert not generation._ordinary_generation_reads(store, connection, rid)
        connection.execute(update(attempts).where(attempts.c.id == row["id"])
                           .values(parameters=original_parameters))
        with source._source_reads(store, connection):
            first = generation.verified_candidate(store, connection, job, limits)
            assert len(full_proofs) == 1
            first["caller_mutation"] = True
            second = generation.verified_candidate(store, connection, job, limits)
            assert "caller_mutation" not in second and len(full_proofs) == 1
            connection.execute(update(attempts).where(attempts.c.id == row["id"])
                               .values(status="RESERVED"))
            assert "pb_source_reads" not in connection.info
            with pytest.raises(DomainError):
                generation.verified_candidate(store, connection, job, limits)
            assert len(full_proofs) in (1, 2)  # Original scope or full history may reject first.
        raise RollbackFixture  # Restore only this test's intentionally damaged history.

    clock = [time.time()]
    monkeypatch.setattr(db, "time", SimpleNamespace(time=lambda: clock[0]))
    with store.tx() as connection:
        job = connection.execute(select(runs).where(runs.c.id == rid)).mappings().one()
        updated = connection.execute(update(grants).where(grants.c.project_id == data[4],
            grants.c.resource_id == data[5], grants.c.revoked.is_(False))
            .values(expires_at=clock[0] + 1))
        assert updated.rowcount > 0
        with source._source_reads(store, connection):
            prior_proofs = len(full_proofs)
            generation.verified_candidate(store, connection, job, limits)
            assert len(full_proofs) == prior_proofs + 1
            epoch = connection.info["source_proof_write_epoch"]
            clock[0] += 2  # Actual Grant expiry, with no intervening DB write.
            with pytest.raises(DomainError) as refused:
                generation.verified_candidate(store, connection, job, limits)
            assert refused.value.code == "GRANT_REVOKED"
            assert len(full_proofs) == prior_proofs + 1 and connection.info["source_proof_write_epoch"] == epoch
            assert not connection.info["pb_source_reads"].results
    (tmp_path / "ordinary-proof-reuse.json").write_text(json.dumps(dict(
        actual_mock_generation_requests=len(sent), full_proofs=len(full_proofs),
        second_read_reused_complete_proof=True, caller_mutation_isolated=True,
        present_null_not_ordinary=True, write_invalidated_and_damage_refused=True,
        expiry_without_write_refused=True, real_model_requests=0), indent=2))
