"""Same-call origin proof reuse retains the original authorization boundaries."""
import json

import pytest
import test_natural_spec_apps as apps
from sqlalchemy import select, update
from test_spec_production_controller import no_real_http as no_real_http

from sim2act import app_jobs
from sim2act import pa_spec_apps as spec
from sim2act.contracts import Limits
from sim2act.db import attempts, fingerprint, grants
from sim2act.errors import DomainError


def test_running_original_source_reuses_only_exact_read_release_origin(env, tmp_path, monkeypatch):
    data = apps.setup(env)
    _, _, release, instance, generated = apps.ready(data, style="ordered")
    store, _, client, user, project, resource = data[:6]
    source = apps.enqueue(data, release, instance)
    job = store.claim("original-source-binding-regression", 30)
    assert job["id"] == source
    limits = Limits(**{k: getattr(data[1], k) for k in Limits.model_fields})
    original, origins = spec.verify_origin, []

    def verified(*args, **kwargs):
        value = original(*args, **kwargs)
        origins.append(args[3]["id"])
        return value

    monkeypatch.setattr(spec, "verify_origin", verified)
    with store.tx() as c:
        optimized = spec.bound(store, c, user, job, limits)
    optimized_count = len(origins)
    assert optimized_count == 1

    # Full original fallback uses the same immutable inputs and Limits. No
    # binding or authority survives this earlier transaction.
    origins.clear()
    load = app_jobs.load_binding

    def without_local_origin(*args, **kwargs):
        return load(*args, **{k: v for k, v in kwargs.items() if k != "_origin_out"})

    with monkeypatch.context() as patch:
        patch.setattr(app_jobs, "load_binding", without_local_origin)
        with store.tx() as c:
            complete = spec.bound(store, c, user, job, limits)
    assert len(origins) > optimized_count and fingerprint(complete) == fingerprint(optimized)
    fallback_count = len(origins)

    def revoke_after_full_release(*args, **kwargs):
        value = load(*args, **kwargs)
        args[1].execute(update(grants).where(grants.c.principal_id == user,
            grants.c.project_id == project, grants.c.resource_id == resource).values(revoked=True))
        return value

    monkeypatch.setattr(app_jobs, "load_binding", revoke_after_full_release)
    with pytest.raises(DomainError) as denied:
        with store.tx() as c:
            spec.bound(store, c, user, job, limits)
    assert denied.value.code in {"VERSION_CONFLICT", "GRANT_REVOKED"}
    with store.tx() as c:
        assert all(not row for row in c.execute(select(grants.c.revoked).where(
            grants.c.principal_id == user, grants.c.project_id == project,
            grants.c.resource_id == resource)).scalars())
        assert not c.execute(select(attempts.c.id).where(attempts.c.run_id == source)).first()
    assert len(generated) == 3
    (tmp_path / "same-call-origin-proof.json").write_text(json.dumps(dict(
        real_models=0, generation_mock_exchanges=3, source_mock_exchanges=0,
        optimized_full_origins=optimized_count, fallback_full_origins=fallback_count,
        binding_fingerprint=fingerprint(optimized), full_fallback_identical=True,
        actual_midcall_grant_revoke_refused=denied.value.code,
        revoked_transaction_rolled_back=True, source_attempts=0), indent=2))
    client.close()
