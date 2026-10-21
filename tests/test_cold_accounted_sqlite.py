"""Real accounted producers/CGR/SQL transactions, synthetic upstream facts only."""

import hashlib
import json

import httpx
import pytest
from accounted_sqlite_fixture import seed, seed_cold, segment
from fastapi.testclient import TestClient
from sqlalchemy import func, select, update

from sim2act import cold_accounted as owned
from sim2act import natural_live_admission as gate
from sim2act import natural_source_archives as archive
from sim2act import natural_spec_runtime as runtime
from sim2act import pa_trial_dispatch as dispatch
from sim2act._cold_accounted_values import _Bounds, _Node
from sim2act.api import create_app
from sim2act.config import Settings
from sim2act.db import Store, attempts, grants, runs
from sim2act.errors import DomainError
from sim2act.model import InternModel
from sim2act.worker import Worker


@pytest.fixture(autouse=True)
def forbid_execution(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Offline SQLite integration cannot run Worker/model/transport")

    monkeypatch.setattr(Worker, "__init__", forbidden)
    monkeypatch.setattr(Worker, "once", forbidden)
    monkeypatch.setattr(InternModel, "__init__", forbidden)
    for transport in (httpx.HTTPTransport, httpx.AsyncHTTPTransport, httpx.MockTransport):
        for method in ("handle_request", "handle_async_request"):
            if hasattr(transport, method):
                monkeypatch.setattr(transport, method, forbidden)


@pytest.fixture
def sql_facts(tmp_path):
    # Do not invoke generic env: it supports externally configured PG URLs.
    # This fixture always creates its own new SQLite database before any query.
    store = Store("sqlite:///" + str(tmp_path / "accounted-isolated.db"), test_only=True)
    store.initialize()
    user = store.user("offline accounted SQLite", "synthetic-test-A")
    settings = Settings(str(store.engine.url), tmp_path, mode="mock")
    client = TestClient(create_app(store, settings))
    client.headers["Authorization"] = "Bearer synthetic-test-A"
    project = client.post("/api/projects", json={"name": "offline accounted SQLite"})
    assert project.status_code == 201
    f = None
    try:
        f = seed((store, settings, client, user, None, project.json()["id"], None))
        yield f
    finally:
        if f is not None:
            f.client.close()
        client.close()
        store.engine.dispose()


def resolve(s, **kwargs):
    f = s.f
    return archive._graph_resolve_trial_source(
        s.graph,
        f.store,
        s.c,
        f.user,
        f.contract,
        f.binding.approval_key,
        s.state,
        s.stage,
        f.proof,
        s.source,
        f.extraction,
        **kwargs,
    )


def test_real_producer_owned_handle_source_resolver_and_archive_chain(sql_facts, tmp_path):
    f = sql_facts
    with f.store.tx() as c, segment(f, c) as s:
        original = resolve(s)
        candidate = resolve(s, _accounted_test=s.bridge)
        assert candidate.public_receipt == original.public_receipt
        assert candidate.request_bodies == original.request_bodies
        assert candidate.response_bodies == original.response_bodies
        dispatch._graph_pb_archive_chain(
            s.graph, f.store, c, f.binding, s.state, candidate, s.source, _accounted_test=s.bridge
        )
        view = s.scope.read(s.handle, "source")
        assert len(view.actual) == len(view.chains) == len(view.ns_reads) == 2
        for row in view.actual:
            owned._stage_usage(view, row.id)
        record = view.actual[0]
        counts = {
            role: c.execute(
                select(func.count()).select_from(attempts).where(attempts.c.run_id == rid)
            ).scalar_one()
            for role, rid in (("generate", f.gen_id), ("source", f.source_id))
        }
        (tmp_path / "sqlite-source-result.json").write_text(
            json.dumps(
                dict(
                    synthetic_upstream_facts=True,
                    complete_cold_prepare_executed=False,
                    database=str(f.store.engine.url),
                    producer="original _graph_stage_accounted",
                    full_cgr_checks_retained=True,
                    original_authorization_queries_retained=True,
                    default_product_switch=False,
                    guard_exemptions=0,
                    counts=counts,
                    caps=f.contract.caps.model_dump(),
                    fixture_only_bounds=list(s.scope._bounds),
                    receipt=candidate.public_receipt,
                    default_and_candidate_equal=True,
                    requests=[hashlib.sha256(b).hexdigest() for b in candidate.request_bodies],
                    responses=[hashlib.sha256(b).hexdigest() for b in candidate.response_bodies],
                    execution_tripwires_installed=True,
                    worker_constructed=False,
                    new_model_exchanges=0,
                    g0_executed=False,
                    performance_qualification=False,
                ),
                ensure_ascii=False,
                indent=2,
            )
        )
    with pytest.raises(DomainError):
        _ = record.id
    with pytest.raises(DomainError):
        s.scope.read(s.handle, "source")


@pytest.mark.parametrize("field", ["reserved_at", "fence", "outcome"])
def test_complete_slot_identity_outcome_not_just_aid(sql_facts, field):
    f = sql_facts
    with f.store.tx() as c, segment(f, c) as s:
        view = s.scope.read(s.handle, "source")
        slot = s.state.slots[-1]
        aid = slot.identity.attempt_id
        owned._source_slot(view, s.state, aid)  # successful full-value control
        if field == "reserved_at":
            changed = slot.model_copy(update=dict(reserved_at=slot.reserved_at + 1))
        elif field == "fence":
            changed = slot.model_copy(
                update=dict(
                    identity=slot.identity.model_copy(update=dict(fence=slot.identity.fence + 1))
                )
            )
        else:
            changed = slot.model_copy(
                update=dict(
                    settlement=slot.settlement.model_copy(update=dict(response_sha256="f" * 64))
                )
            )
        ledger = s.state.model_copy(update=dict(slots=(*s.state.slots[:-1], changed)))
        assert changed.identity.attempt_id == aid
        with pytest.raises(DomainError):
            owned._source_slot(view, ledger, aid)
        resolved = resolve(s, _accounted_test=s.bridge)
        with pytest.raises(DomainError):
            owned._archive_chain(view, ledger, resolved)


@pytest.mark.parametrize("ending", ["commit", "rollback", "write", "raw_write"])
def test_sql_transaction_boundaries_close_records_and_handles(sql_facts, ending):
    f = sql_facts
    before = f.source_job["goal"]
    with pytest.raises(DomainError), f.store.tx() as c:
        with segment(f, c) as s:
            record = s.scope.read(s.handle, "source").run
            assert record.goal == before
            if ending in {"commit", "rollback"}:
                # A real write precedes the terminal transaction operation. The
                # old reader cannot be revived by a new transaction afterwards.
                c.execute(update(runs).where(runs.c.id == f.source_id).values(goal=ending))
                getattr(c, ending)()
            elif ending == "write":
                c.execute(update(runs).where(runs.c.id == f.source_id).values(goal=ending))
            else:
                # Bypass SQLAlchemy's epoch listener; native total_changes still
                # detects the write and rejects the held record.
                c.connection.driver_connection.execute(
                    "UPDATE runs SET goal=? WHERE id=?", (ending, f.source_id)
                )
            with pytest.raises(DomainError):
                _ = record.id
            with pytest.raises(DomainError):
                s.scope.read(s.handle, "source")
            assert not s.scope._active and s.scope._issued == {}
    with f.store.tx() as c:
        current = c.execute(select(runs.c.goal).where(runs.c.id == f.source_id)).scalar_one()
        assert current == ("commit" if ending == "commit" else before)


@pytest.mark.parametrize(
    "change", ["settings", "worker", "binding", "model", "max_tokens", "stop", "transport"]
)
def test_same_identity_mutable_frontier_remains_fresh(sql_facts, change):
    f = sql_facts
    with pytest.raises(DomainError), f.store.tx() as c, segment(f, c) as s:
        record = s.scope.read(s.handle, "source").run
        if change == "settings":
            object.__setattr__(f.settings, "run_seconds", f.settings.run_seconds - 1)
        elif change == "worker":
            f.worker.id += "-changed"
        elif change == "binding":
            object.__setattr__(f.binding, "approval_key", "changed-key")
        elif change == "model":
            object.__setattr__(f.contract, "model", "changed-model")
        elif change == "max_tokens":
            object.__setattr__(f.contract.caps, "max_output_tokens", 1)
        elif change == "stop":
            f.worker.stop.set()
        else:
            f.worker.goal_planner_transport = httpx.MockTransport(
                lambda r: pytest.fail("must never send")
            )
        with pytest.raises(DomainError):
            _ = record.id
        with pytest.raises(DomainError):
            s.scope.read(s.handle, "source")
        assert not s.scope._active and s.scope._issued == {}
        # Scope-only stop refusal does not invalidate the original CGR; cause
        # one explicit refusal so the outer test consistently rolls back.
        raise DomainError("VERSION_CONFLICT", "Expected offline fixture drift")


def test_pre_post_foreign_scope_closed_scope_and_no_opaque_transport(sql_facts):
    f = sql_facts
    with f.store.tx() as c, segment(f, c) as s:
        record = s.scope.read(s.handle, "source").run
        with segment(f, c, "post") as post:
            with pytest.raises(DomainError):
                owned._scope_for_graph(post.graph, _Bounds(1, 1, 1, 1, 1))
            with pytest.raises(DomainError):
                s.bridge.family(post.graph)
        # Valid pre scope survives a foreign/post refusal.
        assert record.id == f.source_id
        transport = httpx.MockTransport(lambda r: pytest.fail("must never send"))
        f.worker.goal_planner_transport = transport
        # Even a fresh CGR cannot admit mutable transport content. Its handler
        # may change in place without changing transport identity.
        from sim2act import natural_spec_runtime as runtime

        roles = dict.fromkeys(("source", "generate", "platform", "trial", "per_use"))
        with runtime._cold_graph_read(f.worker, c, {"transport-refusal": True}, roles, "pre") as g:
            with pytest.raises(DomainError):
                owned._scope_for_graph(g, _Bounds(1, 1, 1, 1, 1))
            transport.handler = lambda r: pytest.fail("changed handler must never send")
            with pytest.raises(DomainError):
                owned._scope_for_graph(g, _Bounds(1, 1, 1, 1, 1))
        f.worker.goal_planner_transport = None
        s.scope.close()
        with pytest.raises(DomainError):
            _ = record.id
        with pytest.raises(DomainError):
            s.scope.read(s.handle, "source")


def test_original_authorization_rechecks_after_sql_revoke(sql_facts):
    f = sql_facts
    with f.store.tx() as c:
        c.execute(
            update(grants)
            .where(
                grants.c.principal_id == f.bound["draft"]["runtime_id"],
                grants.c.tool_ref == "resource.read",
            )
            .values(revoked=True)
        )
    # A fresh scope cannot mistake an unchanged runtime/Run identity for an
    # existing authority. Original Source producer's job scope refuses it.
    with pytest.raises(DomainError) as denied, f.store.tx() as c, segment(f, c):
        pytest.fail("revoked Source authority reached the owned issuer")
    assert denied.value.code == "GRANT_REVOKED"


def test_complete_prewrite_single_producers_and_owned_consumers(sql_facts, monkeypatch):
    f = sql_facts
    with f.store.tx() as c, segment(f, c) as old:
        baseline = resolve(old)
        old_authority, _ = gate._graph_stage_current(
            old.graph, f.store, c, f.user, f.contract, "source", old.stage
        )
    counts = []
    original = dispatch._graph_stage_accounted

    def once(*args, **kwargs):
        counts.append(args[7])
        return original(*args, **kwargs)

    def no_legacy_issue(*args, **kwargs):
        pytest.fail("Complete prewrite must issue at original producer completion exactly once")

    monkeypatch.setattr(dispatch, "_graph_stage_accounted", once)
    monkeypatch.setattr(owned._AccountedScope, "issue", no_legacy_issue)

    class Sentinel:
        def __getattr__(self, name):
            pytest.fail("Prewrite cannot access a transport method/handler: " + name)

    f.worker.goal_planner_transport = Sentinel()
    with f.store.tx() as c, segment(f, c, prewrite=True) as s:
        assert counts == ["source", "generate"]
        assert s.source.scope is s.generated.scope is s.scope
        assert s.mode.inputs["cold-trial:accounted-source"] is s.source
        assert s.mode.inputs["cold-trial:accounted-generate"] is s.generated
        assert s.mode.complete["source"] is s.source
        assert s.mode.complete["generated"] is s.generated
        with pytest.raises(TypeError):
            s.mode.complete["generation"]["run"] = s.source.run
        assert s.stage[6] is s.generated
        assert s.stage[0]._family is s.source
        assert s.stage[4]._family is s.generated
        for family, count in ((s.source, 2), (s.generated, 3)):
            assert len(family.actual) == count
            for row in family.actual:
                owned._stage_usage(family, row.id)
        current, job = gate._graph_stage_current(
            s.graph, f.store, c, f.user, f.contract, "source", s.stage, _owned=s.mode
        )
        assert current == old_authority
        assert job._family is s.source
        candidate = resolve(s, _owned=s.mode)
        assert candidate == baseline
        dispatch._graph_pb_archive_chain(
            s.graph, f.store, c, f.binding, s.state, candidate, s.source, _owned=s.mode
        )
        assert counts == ["source", "generate"]
        # Runtime accounted field consumer returns the family, never dump/thaw.
        graph = object.__new__(runtime._ColdTrialGraph)
        graph.guard, graph.accounted_prewrite = s.graph, s.mode
        assert graph._accounted_fields(s.source) is s.source
        assert graph._accounted_fields(s.generated) is s.generated
        s.mode.assert_current()


def test_complete_prewrite_cold_context_and_runtime_typed_frontier(sql_facts):
    f = sql_facts
    seed_cold(f)
    with f.store.tx() as c, segment(f, c) as old:
        expected, _, _, _ = gate._graph_run_context(
            old.graph,
            f.store,
            c,
            f.user,
            f.contract,
            f.binding.approval_key,
            "cold",
            f.cold_job["id"],
            1,
            1,
            old.cold_stage,
        )
    with f.store.tx() as c, segment(f, c, prewrite=True) as s:
        phase, _ = gate._graph_stage_current(
            s.graph, f.store, c, f.user, f.contract, "cold", s.cold_stage, _owned=s.mode
        )
        assert phase == f.cold_phase.authority
        approval, current, actual, _ = gate._graph_run_context(
            s.graph,
            f.store,
            c,
            f.user,
            f.contract,
            f.binding.approval_key,
            "cold",
            f.cold_job["id"],
            1,
            1,
            s.cold_stage,
            _owned=s.mode,
        )
        assert approval == expected and current == phase and actual["id"] == f.cold_job["id"]
        assert s.cold_stage[6] is s.stage[6] is s.generated
        assert s.cold_stage[7] is s.mode.complete["source"] is s.source
        # Real runtime typed/base/check methods; upstream native origin remains
        # explicitly synthetic, so trial/platform/audit nodes are not fabricated.
        graph = object.__new__(runtime._ColdTrialGraph)
        graph.__dict__.update(
            worker=f.worker,
            c=c,
            guard=s.graph,
            accounted_prewrite=s.mode,
            platform=None,
            trial=None,
            audit_seed=None,
            journal=(s.state, s.cursor, 10),
            source_accounted=s.source,
            generate_accounted=s.generated,
            cold_stage_facts=s.cold_stage,
            source_stage_facts=s.stage,
            sealed_fields=s.mode.complete,
            source_proof=f.proof,
            original=f.contract,
            live_source=None,
            context_record=None,
            authority_record=None,
            authority_fields=None,
            phase="COMPLETE",
        )
        graph.check()
        for key, role in (
            ("cold-trial:accounted-source", "source"),
            ("cold-trial:accounted-generate", "generate"),
        ):
            assert type(s.graph.inputs[key]) is dict  # legacy oracle namespace
            assert s.mode.inputs[key].role == role  # private logical namespace
        assert type(s.graph.inputs["cold-trial:complete"]["generated"]) is dict
        with pytest.raises(DomainError):
            runtime._cold_graph_bytes(dict(forbidden_family=s.generated))


@pytest.mark.parametrize(
    "damage", ["settings", "model", "max_tokens", "binding", "stop", "write", "legacy_content"]
)
def test_complete_prewrite_dynamic_and_content_refusals(sql_facts, damage):
    f = sql_facts
    with pytest.raises(DomainError), f.store.tx() as c, segment(f, c, prewrite=True) as s:
        record = s.generated.actual[2]
        aid = record.id
        if damage == "settings":
            object.__setattr__(f.settings, "run_seconds", f.settings.run_seconds - 1)
        elif damage == "model":
            object.__setattr__(f.contract, "model", "changed")
        elif damage == "max_tokens":
            object.__setattr__(f.contract.caps, "max_output_tokens", 1)
        elif damage == "binding":
            object.__setattr__(f.binding, "approval_key", "changed")
        elif damage == "stop":
            f.worker.stop.set()
        elif damage == "write":
            c.execute(update(runs).where(runs.c.id == f.source_id).values(goal="changed"))
        else:
            s.graph.inputs["cold-trial:accounted-generate"]["actual"][2]["parameters"][
                "max_tokens"
            ] = 0
            # Owned content stays immutable; the original full oracle still
            # rejects legacy witness drift before any consumer/action boundary.
            assert record.id == aid and record.parameters["max_tokens"] > 0
        with pytest.raises(DomainError):
            s.mode.assert_current()
        with pytest.raises(DomainError):
            _ = record.id
        assert not s.mode.active and not s.mode.inputs and not s.scope._issued
        raise DomainError("VERSION_CONFLICT", "Expected prewrite refusal")


@pytest.mark.parametrize("damage", ["lease", "fence", "cancel"])
def test_complete_prewrite_fresh_actual_run_refuses(sql_facts, damage):
    f = sql_facts
    seed_cold(f)
    values = (
        dict(lease_until=0.0)
        if damage == "lease"
        else dict(fence=2)
        if damage == "fence"
        else dict(cancel_intent=True)
    )
    with f.store.tx() as c:
        c.execute(update(runs).where(runs.c.id == f.cold_job["id"]).values(**values))
    with pytest.raises(DomainError), f.store.tx() as c, segment(f, c, prewrite=True) as s:
        gate._graph_run_context(
            s.graph,
            f.store,
            c,
            f.user,
            f.contract,
            f.binding.approval_key,
            "cold",
            f.cold_job["id"],
            1,
            1,
            s.cold_stage,
            _owned=s.mode,
        )


def test_complete_prewrite_duplicate_role_clears_scope(sql_facts):
    f = sql_facts
    with pytest.raises(DomainError), f.store.tx() as c, segment(f, c, prewrite=True) as s:
        record = s.source.run
        with pytest.raises(DomainError):
            dispatch._graph_stage_accounted(
                s.graph,
                f.store,
                c,
                f.binding,
                s.state,
                s.cursor,
                f.source_id,
                "source",
                _owned=s.mode,
            )
        with pytest.raises(DomainError):
            _ = record.id
        assert not s.mode.active and not s.scope._issued


@pytest.mark.parametrize("point", ["chain", "final_guard"])
def test_complete_prewrite_producer_failure_immediately_clears_scope(sql_facts, monkeypatch, point):
    f, observed = sql_facts, []
    original_producer = dispatch._graph_stage_accounted
    original_chain = dispatch._graph_journal_chain
    original_add, original_check = runtime._ColdGraphRead.add, runtime._ColdGraphRead.check
    failed = {"armed": False}

    def chain(*args, **kwargs):
        value = original_chain(*args, **kwargs)
        if point == "chain" and args[4]["id"] == f.gen_id:
            raise DomainError("VERSION_CONFLICT", "Injected failure after real complete chain")
        return value

    def add(graph, name, value):
        original_add(graph, name, value)
        if point == "final_guard" and name == "cold-trial:accounted-generate":
            failed["armed"] = True

    def check(graph, store, c):
        original_check(graph, store, c)
        if failed["armed"]:
            failed["armed"] = False
            raise DomainError("VERSION_CONFLICT", "Injected original last guard failure")

    def producer(*args, **kwargs):
        try:
            return original_producer(*args, **kwargs)
        except DomainError:
            mode = kwargs["_owned"]
            # Inspect BEFORE ExitStack closes the mode; the producer itself
            # must immediately revoke the already-issued Source sibling.
            observed.append((mode.active, bool(mode.scope._issued), bool(mode.inputs)))
            raise

    monkeypatch.setattr(dispatch, "_graph_journal_chain", chain)
    monkeypatch.setattr(dispatch, "_graph_stage_accounted", producer)
    monkeypatch.setattr(runtime._ColdGraphRead, "add", add)
    monkeypatch.setattr(runtime._ColdGraphRead, "check", check)
    with pytest.raises(DomainError), f.store.tx() as c, segment(f, c, prewrite=True):
        pytest.fail("Failed Generate cannot reach any prewrite consumer")
    assert observed == [(False, False, False)]


@pytest.mark.parametrize("ending", ["commit", "rollback"])
def test_complete_prewrite_transaction_end_revokes_both_families(sql_facts, ending):
    f = sql_facts
    with pytest.raises(DomainError), f.store.tx() as c, segment(f, c, prewrite=True) as s:
        source, generated = s.source.run, s.generated.actual[2]
        getattr(c, ending)()
        with pytest.raises(DomainError):
            _ = source.id
        with pytest.raises(DomainError):
            _ = generated.id
        assert not s.mode.active and not s.mode.inputs and not s.scope._issued


def test_complete_prewrite_closed_scope_and_post_refusal(sql_facts):
    f = sql_facts
    with f.store.tx() as c, segment(f, c, prewrite=True) as s:
        record = s.generated.actual[2]
        with segment(f, c, "post") as post:
            with pytest.raises(DomainError):
                owned._OwnedPrewriteMode(post.graph, s.scope._bounds)
        assert record.id
    with pytest.raises(DomainError):
        _ = record.id


def test_complete_prewrite_logical_run_exact_views_have_no_callbacks(sql_facts):
    f, callbacks = sql_facts, []

    class Probe:
        def __eq__(self, other):
            callbacks.append("eq")
            return True

        def __getattr__(self, name):
            callbacks.append("getattr")
            return None

    with f.store.tx() as c, segment(f, c, prewrite=True) as s:
        original = s.generated.run
        check = s.mode._OwnedPrewriteMode__assert_generation_run
        check(original)
        bad_node = object.__new__(_Node)
        object.__setattr__(bad_node, "packet", original._node.packet)
        object.__setattr__(bad_node, "ref", Probe())
        candidates = (
            owned._Record(s.generated, original._node, Probe()),
            owned._Record(s.generated, Probe(), "run"),
            owned._Record(s.generated, bad_node, "run"),
            s.source.run,
        )
        for value in candidates:
            with pytest.raises(DomainError):
                check(value)
            with pytest.raises(DomainError):
                s.mode.assert_run("generate", value)
        assert callbacks == []
        check(original)
