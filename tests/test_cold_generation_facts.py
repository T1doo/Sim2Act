"""One actual 3-Mock Generation; strict local facts only, not a P-B trial.

No full P-B stage, source producer, approval, claim or LIVE authority is created.
The exact synthetic ProductionTrialBinding below is only a local read pin.
"""

import copy
import json
import threading
import time
from contextlib import contextmanager
from functools import partial
from types import SimpleNamespace

import httpx
import pytest
import test_natural_spec_apps as app_fixture
from fastapi.testclient import TestClient
from sqlalchemy import event, insert, select, text, update
from test_pb_live_source_contract import material
from test_spec_app_operations import snapshot

from sim2act import goal_applications as generation
from sim2act import natural_live_admission as admission
from sim2act import natural_spec_runtime as runtime
from sim2act import pa_spec_apps as spec
from sim2act import pb_natural_specs as extraction
from sim2act.api import create_app
from sim2act.config import Settings
from sim2act.contracts import Limits
from sim2act.db import (
    Store,
    app_drafts,
    attempts,
    events,
    fingerprint,
    goal_application_candidates,
    new_id,
    operations,
    runs,
)
from sim2act.errors import DomainError
from sim2act import _cold_source_image as owned_image
from sim2act.production_trial_admission import canonical_quota_subject
from sim2act.spec_production import ProductionTrialBinding
from sim2act.worker import Worker


def write(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n")


def denied(call):
    with pytest.raises(DomainError) as error:
        call()
    return error.value.code


@pytest.fixture(scope="module")
def generated(tmp_path_factory):
    out = tmp_path_factory.mktemp("cold-generation-facts")
    url = "sqlite:///" + str(out / "fixture.db")
    store = Store(url, test_only=True)
    store.initialize()
    user = store.user("Generation facts A", "synthetic-test-A")
    other = store.user("Generation facts B", "synthetic-test-B")
    settings = Settings(url, out, mode="mock")

    def forbidden(*args, **kwargs):
        pytest.fail("Generation facts tests cannot use a real HTTP transport")

    # The existing ready() helper owns the only finite MockTransport. Do not
    # import the other leaf module's autouse guard, which blocks Mock too.
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(httpx.HTTPTransport, "handle_request", forbidden)
        patch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", forbidden)
        with TestClient(create_app(store, settings)) as client:
            client.headers["Authorization"] = "Bearer synthetic-test-A"
            project = client.post("/api/projects", json=dict(name="Original Generation facts"))
            assert project.status_code == 201, project.text
            pid = project.json()["id"]
            data = app_fixture.setup((store, settings, client, user, other, pid, None))
            rid, aid, release, instance, sent = app_fixture.ready(data, style="ordered")
            assert len(sent) == 3
            with store.tx() as c:
                run = dict(c.execute(select(runs).where(runs.c.id == rid)).mappings().one())
                rows = c.execute(select(attempts).where(attempts.c.run_id == rid)
                    .order_by(attempts.c.created_at, attempts.c.id)).mappings().all()
                assert len(rows) == 3 and all(r["status"] == "RECEIVED" for r in rows)
                assert all("generation_received_raw" in r["parameters"] for r in rows)
                draft = dict(c.execute(select(app_drafts).where(app_drafts.c.id == aid)).mappings().one())
            # This uninstalled binding is not validated/approved/claimed/sent.
            # Only principal/project feed the G facet. Actual material/Goal and
            # frozen Limits still come exclusively from the real Generate Run.
            trial = admission.PBTrialContract(trial_key="synthetic-generation-pin", project_id=pid,
                principal_id=user, runtime_id=new_id("runtime"),
                quota_subject=canonical_quota_subject("synthetic-generation-account"),
                software_fingerprint="b" * 64, authorization_fingerprint="c" * 64,
                bindings=[material(1), material(2)], stage_keys=dict(generate="g", source="s", cold="c"),
                expires_at=time.time() + 3600, path="P-B", extraction_request_key="x",
                extraction_recipe=app_fixture.recipe("ordered"))
            binding = ProductionTrialBinding(trial, "synthetic-read-pin", "synthetic-generation-account")
            worker = object.__new__(Worker)
            worker.store, worker.s, worker.pa_trial = store, data[1], binding
            worker.id, worker.stop, worker.goal_planner_transport = "synthetic-generation-reader", threading.Event(), None
            worker._journal_trial_store, worker._journal_trial_binding = store, binding
            worker._journal_trial_drift = False
            full = Limits(**{k: getattr(data[1], k) for k in Limits.model_fields})
            fixture = SimpleNamespace(store=store, worker=worker, user=user, rid=rid,
                run=run, draft=draft, full=full, sent=sent, out=out,
                release=release, instance=instance)
            write(out / "generation-fixture.json", dict(run=run, attempts=[dict(r) for r in rows],
                generated_requests=sent, actual_mock_calls=3, live_authority=False,
                scope="GENERATION_ONLY_SYNTHETIC_READ_PIN_NOT_PB_TRIAL"))
            yield fixture
            data[2].close()
    store.engine.dispose()


@contextmanager
def scope(f, c):
    roles = dict(source=f.full.model_copy(deep=True), generate=None,
        platform=f.full.model_copy(deep=True), trial=f.full.model_copy(deep=True), per_use=None)
    # The None role is intentionally distinct from equal-valued explicit Limits.
    with extraction._source_reads(f.store, c):
        with runtime._cold_graph_read(f.worker, c,
                dict(generation_run=f.run), roles, "pre") as guard:
            yield guard


def strict_history(f, c, guard):
    contract, source, reader = generation._cold_generation_source(f.store, c, f.run, guard)
    history = generation._cold_history_from_source(f.store, c, f.run, contract, source, reader)
    return contract, source, reader, history


def test_complete_generation_facts_equal_public_none_and_full_limits(generated, tmp_path):
    f = generated
    before = snapshot(f.store)
    with f.store.tx() as c:
        public_history = generation._history(f.store, c, f.run)
        public_none = generation._verified_candidate(f.store, c, f.run, None)
        public_full = generation._verified_candidate(f.store, c, f.run, f.full)
        native = spec._native_audit_facts(f.store, c, f.user, f.draft)
        with scope(f, c) as guard:
            contract, source, reader, history = strict_history(f, c, guard)
            assert owned_image.compat(history) == (public_history[0], [dict(r) for r in public_history[1]])
            assert owned_image.is_kind(history,"q") and owned_image.is_kind(history[1],"l")
            assert len(history[1]) == 3
            assert [r["parameters"]["generation_index"] for r in history[1]] == [0, 1, 2]
            strict_none = generation._cold_candidate_from_history(f.store, c, f.run,
                contract, source, history, None, reader)
            strict_full = generation._cold_candidate_from_history(f.store, c, f.run,
                contract, source, history, f.full, reader)
            assert strict_none == public_none and strict_full == public_full
            assert set(reader.candidate_values) == {("NONE",), ("LIMITS", fingerprint(f.full.model_dump()))}
            assert guard.role_limits["generate"] is None
            assert reader.contract.limits.model_dump() == contract.limits.model_dump()
            assert reader.contract.application_generation.app_limits is not None
            assert reader.contract.application_generation.app_limits.model_dump() == strict_full["manifest"]["runtime_limits"]
            observed = []

            def observe(conn, cursor, statement, parameters, context, executemany):
                observed.append(statement)

            event.listen(f.store.engine, "before_cursor_execute", observe)
            try:
                strict_audit = spec._native_audit_facts(f.store, c, f.user, f.draft,
                    _graph_read=guard, _generation_reader=reader)
            finally:
                event.remove(f.store.engine, "before_cursor_execute", observe)
            assert strict_audit == native
            assert not any(s.startswith("SELECT attempts.id, attempts.run_id")
                or s.startswith("SELECT operations.id, operations.run_id") for s in observed)
            write(tmp_path / "complete-generation-facts.json", dict(history=history,
                public_none=public_none, public_full=public_full, strict_none=strict_none,
                strict_full=strict_full, native_audit=strict_audit, native_sql=observed,
                frozen_generation_limits=contract.limits.model_dump(),
                selected_app_limits=contract.application_generation.app_limits.model_dump(),
                caller_limits=f.full.model_dump(), caller_none=None))
    assert snapshot(f.store) == before and len(f.sent) == 3


def test_fixed_raw_methods_memo_once_preserve_full_lists_and_default_queries(generated, tmp_path):
    f = generated
    before = snapshot(f.store)
    with f.store.tx() as c:
        savepoint = c.begin_nested()
        try:
            first = c.execute(select(events).where(events.c.run_id == f.rid,
                events.c.kind == "GA_RECEIVED")).mappings().first()
            c.execute(insert(events).values(**{**dict(first), "id": new_id("evt")}))
            with scope(f, c) as guard:
                _, _, reader, _ = strict_history(f, c, guard)
                received = reader._anchors("GA_RECEIVED")
                assert len(received) == 4 and sum(row == first["data"] for row in received) == 2
                read, check = reader.read_operation(), reader.checker_operation()
                requests = [reader.intent(read), reader.intent(check)]
                response = reader.checker_response()
                ordered, counted = reader.ordered_attempts(), reader.counter_operations()
                assert len(reader._anchors("GA_APP_CONFIRMED")) == 1
                diagnostic = reader._anchors("GA_DIAGNOSTIC")
                assert diagnostic == []
                observed = []

                def observe(conn, cursor, statement, parameters, context, executemany):
                    observed.append(statement)

                event.listen(f.store.engine, "before_cursor_execute", observe)
                try:
                    assert reader._anchors("GA_RECEIVED") is received
                    assert reader.ordered_attempts() is ordered
                    assert reader.counter_operations() is counted
                    assert reader.read_operation() is read and reader.checker_operation() is check
                    assert reader.intent(read) is requests[0] and reader.intent(check) is requests[1]
                    assert reader.checker_response() is response
                    assert reader._anchors("GA_DIAGNOSTIC") is diagnostic
                    assert reader._anchors("GA_SPEC_CHECKED")
                finally:
                    event.remove(f.store.engine, "before_cursor_execute", observe)
                assert observed == []
                key = reader._raw_key("anchors", "GA_RECEIVED")
                assert key[:4] == tuple(f.run[k] for k in ("principal_id", "project_id", "runtime_id", "id"))
                write(tmp_path / "raw-method-memo.json", dict(keys=list(reader._raw_cache),
                    received=received, read_id=read["id"], check_id=check["id"],
                    repeated_diagnostic_sql=observed))
            default = generation._GenerationFactsReader(f.store, c, f.run)
            observed = []
            event.listen(f.store.engine, "before_cursor_execute", observe)
            try:
                assert default._anchors("GA_RECEIVED") == default._anchors("GA_RECEIVED")
            finally:
                event.remove(f.store.engine, "before_cursor_execute", observe)
            assert len(observed) == 2 and default._raw_cache == {}
        finally:
            savepoint.rollback()
    assert snapshot(f.store) == before and len(f.sent) == 3


def test_actual_wire_raw_usage_and_feedback_corruption_rejected_sticky(generated, tmp_path):
    f = generated
    before = snapshot(f.store)
    proofs = []
    for facet in ("raw-0", "wire-1", "usage-2", "checker-feedback"):
        with f.store.tx() as c:
            savepoint = c.begin_nested()
            try:
                rows = c.execute(select(attempts).where(attempts.c.run_id == f.rid)
                    .order_by(attempts.c.created_at, attempts.c.id)).mappings().all()
                if facet == "checker-feedback":
                    op = c.execute(select(operations).where(operations.c.run_id == f.rid,
                        operations.c.call_id == "ga_spec_check")).mappings().one()
                    receipt = copy.deepcopy(op["receipt"])
                    receipt["data"]["diagnostic"] = {"code": "forged-feedback"}
                    c.execute(update(operations).where(operations.c.id == op["id"]).values(receipt=receipt))
                else:
                    index = int(facet[-1])
                    row = rows[index]
                    if facet == "usage-2":
                        usage = copy.deepcopy(row["usage"])
                        usage["tokens"]["total_tokens"] += 1
                        changes = dict(usage=usage)
                    else:
                        parameters = copy.deepcopy(row["parameters"])
                        if facet == "raw-0":
                            parameters["generation_received_raw"] += " "
                        else:
                            parameters["generation_wire"] = "0" * 64
                        changes = dict(parameters=parameters)
                    c.execute(update(attempts).where(attempts.c.id == row["id"]).values(**changes))
                public_code = denied(lambda: generation._history(f.store, c, f.run))
                with pytest.raises(DomainError):
                    with scope(f, c) as guard:
                        contract, source, reader = generation._cold_generation_source(f.store, c, f.run, guard)
                        strict_code = denied(partial(generation._cold_history_from_source,
                            f.store, c, f.run, contract, source, reader))
                        assert strict_code == public_code and not guard.active
                        assert denied(reader.ordered_attempts) == "VERSION_CONFLICT"
                        proofs.append(dict(facet=facet, public_code=public_code,
                            strict_code=strict_code, sticky=not guard.active))
            finally:
                savepoint.rollback()
        assert snapshot(f.store) == before
    write(tmp_path / "history-corruption.json", proofs)
    assert len(f.sent) == 3


def test_wrong_raw_facet_input_role_and_write_reuse_poison_same_scope(generated, tmp_path):
    f = generated
    before = snapshot(f.store)
    proofs = []
    for fault in ("raw-facet", "history-copy", "bad-limits", "role-none", "write"):
        with f.store.tx() as c:
            with pytest.raises(DomainError):
                with scope(f, c) as guard:
                    contract, source, reader, history = strict_history(f, c, guard)
                    if fault == "raw-facet":
                        received = reader._raw_key("anchors", "GA_RECEIVED")
                        reserved = reader._raw_key("anchors", "GA_WIRE_RESERVED")
                        reader._raw_cache[received] = reader._raw_cache[reserved]
                        call = partial(reader._anchors, "GA_RECEIVED")
                    elif fault == "history-copy":
                        call = partial(generation._cold_candidate_from_history, f.store, c, f.run,
                            contract, source, copy.deepcopy(owned_image.compat(history)), None, reader)
                    elif fault == "bad-limits":
                        class Callback:
                            def model_dump(self):
                                pytest.fail("Foreign Limits serializer cannot execute")

                        call = partial(generation._cold_candidate_from_history, f.store, c, f.run,
                            contract, source, history, Callback(), reader)
                    elif fault == "role-none":
                        guard.role_limits["generate"] = f.full.model_copy(deep=True)
                        call = reader.ordered_attempts
                    else:
                        c.execute(text("UPDATE principals SET name=name WHERE id='absent'"))
                        call = reader.ordered_attempts
                    assert denied(call) == "VERSION_CONFLICT" and not guard.active
                    assert denied(reader.check) == "VERSION_CONFLICT"
                    proofs.append(dict(fault=fault, inactive_after_caught_error=not guard.active))
    assert snapshot(f.store) == before and len(f.sent) == 3
    write(tmp_path / "sticky-read-scope.json", proofs)


def test_default_first_errors_stay_before_private_source_and_operation_reads(generated, tmp_path):
    f = generated
    before = snapshot(f.store)
    observed = []

    def observe(conn, cursor, statement, parameters, context, executemany):
        observed.append(statement)

    with f.store.tx() as c:
        event.listen(f.store.engine, "before_cursor_execute", observe)
        try:
            bad_message = dict(role="user", content="not-a-candidate")
            code = denied(lambda: generation.parse_candidate(f.store, c, f.run, bad_message, f.full))
        finally:
            event.remove(f.store.engine, "before_cursor_execute", observe)
        assert code == "INVALID_MANIFEST" and observed == []
        savepoint = c.begin_nested()
        try:
            row = c.execute(select(attempts).where(attempts.c.run_id == f.rid)
                .order_by(attempts.c.created_at, attempts.c.id)).mappings().first()
            c.execute(update(attempts).where(attempts.c.id == row["id"]).values(parameters=[]))
            observed.clear()
            event.listen(f.store.engine, "before_cursor_execute", observe)
            try:
                with pytest.raises(DomainError, match="Invalid typed generation counters") as error:
                    generation._history(f.store, c, f.run)
            finally:
                event.remove(f.store.engine, "before_cursor_execute", observe)
            assert error.value.code == "VERSION_CONFLICT"
            assert not any(s.startswith("SELECT operations.id, operations.run_id") for s in observed)
            write(tmp_path / "default-first-errors.json", dict(invalid_message=code,
                typed_counter=error.value.public(), sql=observed))
        finally:
            savepoint.rollback()
    assert snapshot(f.store) == before and len(f.sent) == 3


def test_typed_generation_contract_drift_stops_before_next_authority_io(generated, monkeypatch, tmp_path):
    f = generated
    before = snapshot(f.store)
    observed, callbacks = [], []
    with f.store.tx() as c:
        with pytest.raises(DomainError):
            with scope(f, c) as guard:
                contract, _, reader = generation._cold_generation_source(f.store, c, f.run, guard)
                original = f.store.own_project
                number = contract.limits.max_requests

                def forbidden_dump(*args, **kwargs):
                    callbacks.append("instance-dump")
                    pytest.fail("Typed pin must use the exact FrozenRunContract class serializer")

                object.__getattribute__(contract, "__dict__")["model_dump"] = forbidden_dump
                reader.check()

                def mutate_after_project(*args, **kwargs):
                    value = original(*args, **kwargs)
                    observed.append("own_project")
                    contract.limits.max_requests = float(number)
                    assert contract.limits.max_requests == reader.source_pin["contract"]["limits"]["max_requests"]
                    assert type(contract.limits.max_requests) is float
                    return value

                def later_authority(*args, **kwargs):
                    observed.append("later-authority")
                    pytest.fail("Typed contract drift must stop before the next authority IO")

                with monkeypatch.context() as patch:
                    patch.setattr(f.store, "own_project", mutate_after_project)
                    patch.setattr(f.store, "recheck_proof_authorities", later_authority)
                    assert denied(reader.source) == "VERSION_CONFLICT"
                assert not guard.active and observed == ["own_project"] and callbacks == []
                assert denied(reader.check) == "VERSION_CONFLICT"
                write(tmp_path / "typed-contract-next-io.json", dict(observed=observed,
                    callback_calls=callbacks, actual_type=type(contract.limits.max_requests).__name__,
                    saved_type=type(reader.source_pin["contract"]["limits"]["max_requests"]).__name__,
                    sticky=not guard.active))
    assert snapshot(f.store) == before and len(f.sent) == 3


def test_original_manifest_numeric_drift_stops_after_prefix_and_confirmation_sql(generated, monkeypatch, tmp_path):
    f = generated
    before = snapshot(f.store)
    proofs = []
    for edge in ("prefix-marker", "confirmation"):
        sql_after_drift, changed, compiled = [], [], []
        with f.store.tx() as c:
            with pytest.raises(DomainError):
                with scope(f, c) as guard:
                    if edge == "confirmation":
                        contract, source, reader, history = strict_history(f, c, guard)
                        raw = generation._cold_candidate_from_history(f.store, c, f.run,
                            contract, source, history, f.full, reader)
                        prefix = spec._cold_original_origin_prefix(f.store, c, f.user, f.draft, f.full, guard)
                        marker = c.execute(select(goal_application_candidates).where(
                            goal_application_candidates.c.app_id == f.draft["id"])).mappings().one()
                        compiled.append(prefix.manifest)
                    original_compile = spec.compile_candidate

                    def observe_compile(*args, original_compile=original_compile, compiled=compiled, **kwargs):
                        value = original_compile(*args, **kwargs)
                        compiled.append(value[0])
                        return value

                    def before_sql(conn, cursor, statement, parameters, context, executemany,
                            changed=changed, sql_after_drift=sql_after_drift):
                        if changed:
                            sql_after_drift.append(statement)

                    def after_sql(conn, cursor, statement, parameters, context, executemany,
                            edge=edge, changed=changed, compiled=compiled):
                        selected = ("FROM task_extractions" in statement if edge == "prefix-marker"
                            else statement.startswith("SELECT goal_application_candidates.confirmation"))
                        if compiled and not changed and selected:
                            manifest = compiled[-1]
                            original = manifest.revision
                            manifest.revision = float(original)
                            changed.append(statement)
                            assert manifest.revision == original and type(manifest.revision) is float

                    event.listen(f.store.engine, "before_cursor_execute", before_sql)
                    event.listen(f.store.engine, "after_cursor_execute", after_sql)
                    try:
                        with monkeypatch.context() as patch:
                            if edge == "prefix-marker":
                                patch.setattr(spec, "compile_candidate", observe_compile)
                                call = partial(spec._cold_original_origin_prefix,
                                    f.store, c, f.user, f.draft, f.full, guard)
                            else:
                                call = partial(spec._cold_original_origin_from_generation,
                                    f.store, c, f.user, prefix, reader, raw, marker)
                            assert denied(call) == "VERSION_CONFLICT"
                    finally:
                        event.remove(f.store.engine, "before_cursor_execute", before_sql)
                        event.remove(f.store.engine, "after_cursor_execute", after_sql)
                    assert len(changed) == 1 and sql_after_drift == [] and not guard.active
                    if edge == "confirmation":
                        assert denied(reader.check) == "VERSION_CONFLICT"
                    proofs.append(dict(edge=edge, changed_after_sql=changed, later_sql=sql_after_drift,
                        actual_type=type(compiled[-1].revision).__name__, sticky=not guard.active))
        assert snapshot(f.store) == before
    write(tmp_path / "typed-original-manifest-next-io.json", proofs)
    assert len(f.sent) == 3


def test_original_target_strict_relay_keeps_guard_valueerror_identity(generated, monkeypatch, tmp_path):
    f = generated
    before = snapshot(f.store)
    same_error = ValueError("synthetic original relay guard error")
    completed, later_sql, later_calls = [], [], []
    with f.store.tx() as c:
        with pytest.raises(DomainError):
            with scope(f, c) as guard:
                _, _, reader = generation._cold_generation_source(f.store, c, f.run, guard)
                prefix = spec._cold_original_origin_prefix(f.store, c, f.user, f.draft, f.full, guard)
                key = "original-origin-prefix:" + f.draft["id"] + ":" + fingerprint(f.full.model_dump())
                relay = spec._ColdOriginalOriginRead(guard, prefix, reader, key, guard.inputs[key])
                spec._original_origin_checkpoint(f.store, c, f.user, relay)
                original_own, original_check = f.store.own_project, reader.check

                def owned_project(*args, **kwargs):
                    value = original_own(*args, **kwargs)
                    completed.append("owned-project")
                    return value

                def actual_reader_guard():
                    original_check()
                    if completed:
                        raise same_error

                def later_authorize(*args, **kwargs):
                    later_calls.append("authorize")
                    pytest.fail("Relay failure must stop before the next authority IO")

                def before_sql(conn, cursor, statement, parameters, context, executemany):
                    if completed:
                        later_sql.append(statement)

                event.listen(f.store.engine, "before_cursor_execute", before_sql)
                try:
                    with monkeypatch.context() as patch:
                        patch.setattr(f.store, "own_project", owned_project)
                        patch.setattr(f.store, "authorize", later_authorize)
                        patch.setattr(reader, "check", actual_reader_guard)
                        with pytest.raises(ValueError) as error:
                            spec.target(f.store, c, f.user, f.run["project_id"], "unused-after-guard",
                                _graph_read=guard, _origin_read=relay)
                        assert error.value is same_error
                finally:
                    event.remove(f.store.engine, "before_cursor_execute", before_sql)
                assert completed == ["owned-project"] and later_sql == [] and later_calls == []
                assert not guard.active and denied(reader.check) == "VERSION_CONFLICT"

                def malformed_owned_row(*args, **kwargs):
                    raise same_error

                # The same error remains mapped on the original default path;
                # even argument-binding TypeError retains its prior mapping.
                with monkeypatch.context() as patch:
                    patch.setattr(f.store, "own_project", malformed_owned_row)
                    assert denied(partial(spec.target, f.store, c, f.user,
                        f.run["project_id"], "unused-default")) == "VERSION_CONFLICT"
                    assert denied(spec.target) == "VERSION_CONFLICT"
                write(tmp_path / "original-target-guard-error-identity.json", dict(
                    same_exception_object=True, completed=completed, later_sql=later_sql,
                    later_calls=later_calls, default_error="VERSION_CONFLICT", sticky=not guard.active))
    assert snapshot(f.store) == before and len(f.sent) == 3
