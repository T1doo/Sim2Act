"""Pure offline component tests, not a new Mock/admission window.

Five archived exchanges supply bytes. Complete rows and fixed model types are
synthetic. Issuer wiring uses an exact uninitialized CGR with a lifecycle double
and a stubbed producer/full-check, never a completed original graph/DB proof.
"""

import base64
import copy
import hashlib
import json
from pathlib import Path
from threading import Event, get_ident
from types import SimpleNamespace

import pytest
from sqlalchemy.engine import RowMapping
from sqlalchemy.engine.result import SimpleResultMetaData

from sim2act import cold_accounted as owned
from sim2act import natural_source_archives as archive
from sim2act import natural_spec_runtime as runtime
from sim2act import pa_trial_dispatch as dispatch
from sim2act import pb_natural_specs as pb
from sim2act import production_trial_policy as policy
from sim2act import production_trial_sender as sender
from sim2act._cold_accounted_values import _Bounds, _equal, _freeze, _node
from sim2act.contracts import strict_json
from sim2act.db import attempts, fingerprint, runs
from sim2act.errors import DomainError
from sim2act.goal_applications import response_archive
from sim2act.model import normalize_usage
from sim2act.spec_production import ProductionTrialBinding

REPO = Path(runtime.__file__).resolve().parents[2]
WIRE = REPO / "docs/evidence/g0-monitored-third-20261021/RUN/mock-exchanges.jsonl"
# Explicit test limits ONLY, never a product default/admission qualification.
LIMITS = _Bounds(20000, 50000, 128, 4 * 1024 * 1024, 8 * 1024 * 1024)


def sha(body):
    return hashlib.sha256(body).hexdigest()


def native_row(value, hidden=None):
    keys = list(value)
    data = tuple(value[k] for k in keys)
    index = {k: i for i, k in enumerate(keys)}
    if hidden is not None:
        index["hidden_alias"] = len(data)
        data += (hidden,)
    return RowMapping(SimpleResultMetaData(keys), None, index, data)


def family(role):
    records = [json.loads(line) for line in WIRE.read_text().splitlines()]
    indexes = range(3) if role == "generate" else range(3, 5)
    rid = "run_" + ("1" if role == "generate" else "2") * 32
    run = dict.fromkeys(runs.c.keys())
    run.update(
        id=rid,
        project_id="project",
        principal_id="user",
        runtime_id="runtime",
        goal="offline",
        resource_refs=[],
        status="SUCCEEDED",
        request_key="offline",
        fingerprint="a" * 64,
        created_at=1.0,
        fence=1,
        version=1,
        cancel_intent=False,
        context={"retained": ["all", {"columns": True}]},
        result={},
        error=None,
    )
    actual, chains, ns = [], [], []
    for i in indexes:
        record = records[i]
        assert record["classification"] == "SYNTHETIC_MOCK_TRANSPORT_NOT_REAL_HTTP"
        wire, payload = (base64.b64decode(record[k]) for k in ("request_b64", "response_b64"))
        parsed = strict_json(payload, 32768)
        original, canonical = response_archive(parsed)
        usage = normalize_usage(parsed)
        aid = "attempt_" + f"{i + 1:032x}"
        identity = policy.ReservationIdentity(
            requirements_fingerprint="a" * 64,
            approval_fingerprint="b" * 64,
            stage=role,
            stage_fingerprint="c" * 64,
            run_id=rid,
            runtime_id="runtime",
            version=1,
            fence=1,
            worker_id="worker",
            account_id="offline-account",
            quota_subject="offline-quota",
            attempt_id=aid,
            wire_sha256=sha(wire),
            wire_bytes=len(wire),
        )
        outcome = policy.Outcome(
            outcome="RECEIVED",
            response_sha256=canonical["sha256"],
            response_ascii_bytes=canonical["bytes"],
            **usage["tokens"],
        )
        slot = policy.Slot(
            identity=identity,
            reserved_at=100.0 + 60 * i,
            attempted=True,
            settlement=outcome,
            accepted=True,
        )
        capture = sender.Capture(
            raw_sha256=sha(payload),
            raw_bytes=len(payload),
            body_b64=base64.b64encode(payload).decode("ascii"),
            complete=True,
            received_response=True,
            omission="NONE",
            canonical_sha256=canonical["sha256"],
            canonical_ascii_bytes=canonical["bytes"],
            response_verdict="VALID_PROTOCOL",
            outcome=outcome,
        )
        row = dict.fromkeys(attempts.c.keys())
        envelope = strict_json(wire, 32768)
        row.update(
            id=aid,
            run_id=rid,
            created_at=float(i + 1),
            mode="MOCK",
            request_model=envelope["model"],
            response_model=envelope["model"],
            status="RECEIVED" if role == "generate" else "VERIFIED",
            usage=usage,
            reserved_tokens=100,
            parameters={
                "natural_spec_wire": dict(
                    sha256=sha(wire), bytes=len(wire), characters=len(wire.decode("utf8"))
                )
            },
            response=dict(received_raw=original, raw_evidence=canonical),
            elapsed=0.01,
        )
        actual.append(native_row(row))
        checked = native_row(copy.deepcopy(row))
        chains.append((slot, capture, parsed, checked, wire, payload))
        if role == "source":
            request = archive._body(run, aid, wire, True, None, archive.REQUEST)
            response = archive._body(run, aid, payload, True, canonical["sha256"], archive.RESPONSE)
            ns.append((aid, request, wire, response, payload))
    return native_row(run), actual, tuple(chains), tuple(ns)


def producer_raw(facts):
    run, actual, chains, ns = facts
    return dict(
        run=dict(run),
        actual=tuple(dict(a) for a in actual),
        chains=tuple(
            (s.model_dump(), c.model_dump(), p, dict(a), w, b) for s, c, p, a, w, b in chains
        ),
        ns_reads=tuple((aid, q.model_dump(), w, r.model_dump(), b) for aid, q, w, r, b in ns),
    )


@pytest.fixture
def lifecycle(monkeypatch):
    def check(graph, store, connection):
        graph.events.append("full-guard")
        owned._frame(graph)
        if graph.inputs:
            assert runtime._cold_graph_bytes(graph.inputs) == graph.test_pin

    def producer(graph, store, connection, binding, state, cursor, rid, role):
        graph.events.append("producer")
        assert graph.facts[0]["id"] == rid
        graph.inputs["cold-trial:accounted-" + role] = copy.deepcopy(producer_raw(graph.facts))
        graph.test_pin = runtime._cold_graph_bytes(graph.inputs)
        return graph.facts

    monkeypatch.setattr(runtime._ColdGraphRead, "check", check)
    monkeypatch.setattr(dispatch, "_graph_stage_accounted", producer)

    def make(facts, mode="offline", bounds=LIMITS):
        # Accurate lifecycle double, NOT a valid original CGR or DB transaction.
        graph = object.__new__(runtime._ColdGraphRead)
        graph.events, graph.inputs, graph.facts = [], {}, facts
        graph.active, graph.phase, graph.thread = True, "pre", get_ident()
        graph.worker = SimpleNamespace(stop=Event(), goal_planner_transport=None)
        graph.store = SimpleNamespace(test_only=True, sqlite=True)
        graph.transaction, graph.scope = object(), [object()]
        graph.nonce, graph.epoch, graph.changes = graph.scope[0], 0, 0
        graph.driver = SimpleNamespace(total_changes=0, in_transaction=True)
        graph.connection = SimpleNamespace(
            closed=False,
            info={},
            get_transaction=lambda: graph.transaction,
            in_transaction=lambda: True,
            connection=SimpleNamespace(driver_connection=graph.driver),
        )
        graph.token = pb._SourceReads(
            graph.store, graph.connection, graph.transaction, graph.driver, 0, get_ident()
        )
        graph.connection.info["pb_source_reads"] = graph.token
        graph.binding = object.__new__(ProductionTrialBinding)
        object.__setattr__(
            graph.binding,
            "contract",
            SimpleNamespace(model="intern-s2", caps=SimpleNamespace(max_output_tokens=32768)),
        )
        scope = owned._AccountedScope(graph, bounds, owned._Context("intern-s2", 32768, mode))
        return scope, graph

    return make


def issued(lifecycle, role="source", mode="offline", facts=None):
    facts = family(role) if facts is None else facts
    scope, graph = lifecycle(facts, mode)
    handle = scope.issue(role, None, None, facts[0]["id"])
    return scope.read(handle, role), scope, graph, facts


def controller(facts):
    for _actual, chain in zip(facts[1], facts[2], strict=True):
        chain[0].settlement.__dict__["response_sha256"] = sha(chain[5])
        chain[1].outcome.__dict__["response_sha256"] = sha(chain[5])
        chain[1].__dict__["provenance"] = "SPEC_PRODUCTION_CONTROLLER"
    actual = []
    chains = []
    for a, chain in zip(facts[1], facts[2], strict=True):
        actual.append(native_row(dict(a, mode="LIVE")))
        s, c, p, checked, w, b = chain
        chains.append((s, c, p, native_row(dict(checked, mode="LIVE")), w, b))
    for _aid, q, _w, r, _b in facts[3]:
        q.__dict__["provenance"] = r.__dict__["provenance"] = "SPEC_PRODUCTION_CONTROLLER"
    return facts[0], actual, tuple(chains), facts[3]


def ledger(facts):
    scope = policy.evidence.EvidenceRequirements(
        principal_id="user_" + "1" * 32,
        project_id="proj_" + "1" * 32,
        runtime_id="runtime_" + "1" * 32,
        trial_key="offline",
        approval_key="offline",
        contract_fingerprint="a" * 64,
        software_fingerprint="b" * 64,
        authorization_fingerprint="c" * 64,
        quota_subject="offline-quota",
        expires_at=1000.0,
    )
    return policy.Ledger(
        scope=scope, account_id="offline-account", slots=tuple(c[0] for c in facts[2])
    )


def resolved(facts):
    proofs = []
    for _s, c, _p, a, w, b in facts[2]:
        proofs.append(
            dict(
                attempt_id=a["id"],
                request_sha256=sha(w),
                request_bytes=len(w),
                decoded_body_sha256=sha(b),
                decoded_body_bytes=len(b),
                canonical_ascii_sha256=c.canonical_sha256,
                canonical_ascii_bytes=c.canonical_ascii_bytes,
            )
        )
    return archive.ResolvedSourceArchive(
        dict(
            source_run_id=facts[0]["id"],
            attempts=proofs,
            verification="SPEC_PRODUCTION_CONTROLLER_ARCHIVE",
            live_allowed=False,
        ),
        tuple(c[4] for c in facts[2]),
        tuple(c[5] for c in facts[2]),
    )


def legacy_source(facts, index, production):
    s, c, p, a, w, b = facts[2][index]
    aid, q, _, r, _ = facts[3][index]
    slot = dict(
        reservation=dict(
            request_key=aid, wire_sha256=s.identity.wire_sha256, wire_bytes=s.identity.wire_bytes
        ),
        accepted=s.accepted,
        settlement=s.settlement.model_dump(),
    )
    contract = SimpleNamespace(model="intern-s2", caps=SimpleNamespace(max_output_tokens=32768))
    return contract, a, slot, q, w, r, b, production


def rejects(call, *args):
    with pytest.raises(DomainError) as error:
        call(*args)
    return error.value.code


def test_issuer_order_registration_original_pin_and_no_runtime_callers(lifecycle, monkeypatch):
    facts = family("generate")
    scope, g = lifecycle(facts)
    original = owned._capture

    def observed(*args):
        assert not scope._issued
        g.events.append("copy")
        return original(*args)

    monkeypatch.setattr(owned, "_capture", observed)
    handle = scope.issue("generate", None, None, facts[0]["id"])
    assert [e for e in g.events if e != "full-guard"] == ["producer", "copy"]
    p, copied = g.events.index("producer"), g.events.index("copy")
    assert g.events[p - 1] == g.events[copied - 1] == g.events[copied + 1] == "full-guard"
    assert scope.read(handle, "generate").run.id == facts[0]["id"]
    # Different but self-consistent third model after producer must NOT issue.
    scope, g = lifecycle(family("generate"))

    def changed(facts, *args):
        facts[2][2][1].__dict__["complete"] = False
        return original(facts, *args)

    monkeypatch.setattr(owned, "_capture", changed)
    assert (
        rejects(lambda: scope.issue("generate", None, None, g.facts[0]["id"])) == "VERSION_CONFLICT"
    )
    assert not scope._active and not scope._issued
    for path in (REPO / "src/sim2act").glob("*.py"):
        if path.name not in ("cold_accounted.py", "_cold_accounted_values.py"):
            assert "_scope_for_graph(" not in path.read_text()
        if path.name not in (
            "cold_accounted.py",
            "_cold_accounted_values.py",
            "natural_source_archives.py",
            "pa_trial_dispatch.py",
            "natural_live_admission.py",
            "natural_spec_runtime.py",
            "_cold_accounted_native.py",
        ):
            assert "import cold_accounted" not in path.read_text()
            assert "from .cold_accounted" not in path.read_text()


@pytest.mark.parametrize(
    "change",
    [
        "closed",
        "scope",
        "transaction",
        "source_token",
        "write_epoch",
        "write_count",
        "raw_commit",
        "phase",
        "binding",
        "thread",
        "schema",
    ],
)
def test_handles_and_existing_views_refuse_changed_lifecycle(lifecycle, monkeypatch, change):
    f, scope, g, _ = issued(lifecycle)
    record = f.chains[1].slot.identity
    if change == "closed":
        scope.close()
    elif change == "scope":
        g.scope[0] = object()
    elif change == "transaction":
        g.transaction = object()
    elif change == "source_token":
        g.connection.info["pb_source_reads"] = object()
    elif change == "write_epoch":
        g.connection.info["source_proof_write_epoch"] = 1
    elif change == "write_count":
        g.driver.total_changes = 1
    elif change == "raw_commit":
        g.driver.in_transaction = False
    elif change == "phase":
        g.phase = "post"
    elif change == "binding":
        g.binding = object()
    elif change == "thread":
        g.thread += 1
    else:
        monkeypatch.setattr(owned, "_SCHEMA", "different-schema")
    assert rejects(lambda: scope.read(f.handle, "source")) == "VERSION_CONFLICT"
    assert rejects(lambda: record.attempt_id) == "VERSION_CONFLICT"


def test_forged_cross_scope_role_post_and_frozen_accessors(lifecycle):
    f, scope, g, _ = issued(lifecycle)
    other, _, _, _ = issued(lifecycle)
    for handle, role in (
        (owned._Handle(), "source"),
        (other.handle, "source"),
        (f.handle, "generate"),
    ):
        assert rejects(scope.read, handle, role) == "VERSION_CONFLICT"
    with pytest.raises((AttributeError, TypeError)):
        f.run._node = _node(_freeze({}, LIMITS))
    with pytest.raises(TypeError):
        bool(f.chains[0].slot == f.chains[0].slot)
    with pytest.raises(TypeError):
        bool(f.run._node != f.run._node)
    forged = owned._Record(f, _node(_freeze({"id": "fake"}, LIMITS)), "run")
    assert rejects(lambda: forged.id) == "VERSION_CONFLICT"
    g.phase = "post"
    assert rejects(lambda: owned._scope_for_graph(g, LIMITS)) == "VERSION_CONFLICT"


def test_domain_equality_different_nodes_aliases_order_and_exact_types(lifecycle):
    left = family("generate")
    right = family("generate")
    shared = {"n": [1, True, 1.0, None]}
    left[1][0]["parameters"]["extra"] = [shared, shared]
    left[2][0][3]["parameters"]["extra"] = [shared, shared]
    right[1][0]["parameters"]["extra"] = [copy.deepcopy(shared), copy.deepcopy(shared)]
    right[2][0][3]["parameters"]["extra"] = [copy.deepcopy(shared), copy.deepcopy(shared)]
    a, *_ = issued(lifecycle, "generate", facts=left)
    b, *_ = issued(lifecycle, "generate", facts=right)
    assert owned._same(a.actual[0], b.actual[0])
    assert owned._same(a.actual[0], a.chains[0].checked)
    for x, y in ((1, True), (1, 1.0), ([1], (1,)), ({"x": 1}, {"x": True})):
        assert not _equal(_node(_freeze(x, LIMITS)), _node(_freeze(y, LIMITS)))
    assert _equal(
        _node(_freeze({"a": 1, "b": [2]}, LIMITS)), _node(_freeze({"b": [2], "a": 1}, LIMITS))
    )
    v = {"x": 0}
    for _ in range(35):
        v = [v, v]
    assert _equal(_node(_freeze(v, LIMITS)), _node(_freeze(copy.deepcopy(v), LIMITS)))


@pytest.mark.parametrize("role", ["generate", "source"])
def test_all_aids_stage_usage_and_post_issue_source_isolation(lifecycle, role):
    f, scope, g, facts = issued(lifecycle, role)
    for i, chain in enumerate(facts[2]):
        dispatch._stage_usage_from_facts(facts[1][i], role, chain[0], chain[2], chain[3])
        owned._stage_usage(f, chain[3]["id"])
        before = f.chains[i].capture.raw_sha256
        chain[1].__dict__["raw_sha256"] = "e" * 64
        assert f.chains[i].capture.raw_sha256 == before
    # Private digest never appears in the old capture/business identity hash.
    for i, chain in enumerate(facts[2]):
        assert f.chains[i].slot.identity.wire_sha256 == sha(chain[4])
        assert fingerprint(sender._capture_request(chain[0].identity)) == fingerprint(
            dict(
                namespace=sender.CAPTURE,
                identity={
                    key: getattr(f.chains[i].slot.identity, key)
                    for key in owned._FIELDS["identity"]
                },
            )
        )


@pytest.mark.parametrize(
    "usage",
    [
        None,
        {},
        {"prompt_tokens": 2},
        {"prompt_tokens": True, "completion_tokens": 2, "total_tokens": 3},
        {"prompt_tokens": 1, "completion_tokens": 2.0, "total_tokens": 3},
        {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 99},
    ],
)
def test_unknown_partial_none_usage_matches_original_normalization(lifecycle, usage):
    facts = family("generate")
    facts[2][2][2]["usage"] = usage
    normalized = normalize_usage(facts[2][2][2])
    facts[1][2]["usage"].clear()
    facts[1][2]["usage"].update(normalized)
    facts[2][2][3]["usage"].clear()
    facts[2][2][3]["usage"].update(normalized)
    f, *_ = issued(lifecycle, "generate", facts=facts)
    assert owned._usage(f.chains[2].parsed) == normalized
    assert rejects(lambda: owned._stage_usage(f, facts[1][2]["id"])) == "VERSION_CONFLICT"
    assert (
        rejects(
            lambda: dispatch._stage_usage_from_facts(
                facts[1][2], "generate", facts[2][2][0], facts[2][2][2], facts[2][2][3]
            )
        )
        == "VERSION_CONFLICT"
    )


@pytest.mark.parametrize("mode", ["offline", "controller"])
def test_source_row_exchange_original_bytes_both_provenance_modes(lifecycle, mode):
    facts = family("source")
    if mode == "controller":
        facts = controller(facts)
    f, *_ = issued(lifecycle, mode=mode, facts=facts)
    for i, a in enumerate(facts[1]):
        args = legacy_source(facts, i, mode == "controller")
        archive._source_row_from_facts(args[0], args[1], args[2], args[-1])
        owned._source_row(f, a["id"])
        expected = archive._source_exchange_from_facts(*args)
        got = owned._source_exchange(f, a["id"])
        assert (got.status, got.bytes, got.sha256) == tuple(
            expected[k] for k in ("status", "bytes", "sha256")
        )
        assert sha(args[6]) != expected["sha256"]  # Raw received != canonical.
        assert fingerprint(facts[3][i][1].model_dump()) == fingerprint(
            {key: getattr(f.ns_reads[i].request, key) for key in owned._FIELDS["body"]}
        )


def test_entire_archive_chain_against_extracted_original(lifecycle):
    facts = controller(family("source"))
    state = ledger(facts)
    result = resolved(facts)
    f, _, g, _ = issued(lifecycle, mode="controller", facts=facts)
    dispatch._archive_chain_from_facts(g.binding, state, result, facts)
    owned._archive_chain(f, state, result)
    for field in (
        "attempt_id",
        "request_sha256",
        "request_bytes",
        "decoded_body_sha256",
        "decoded_body_bytes",
        "canonical_ascii_sha256",
        "canonical_ascii_bytes",
    ):
        receipt = copy.deepcopy(result.public_receipt)
        value = receipt["attempts"][1][field]
        receipt["attempts"][1][field] = value + 1 if type(value) is int else "f" * 64
        changed = archive.ResolvedSourceArchive(
            receipt, result.request_bodies, result.response_bodies
        )
        assert (
            rejects(dispatch._archive_chain_from_facts, g.binding, state, changed, facts)
            == "VERSION_CONFLICT"
        )
        assert rejects(owned._archive_chain, f, state, changed) == "VERSION_CONFLICT"
    for changed in (
        archive.ResolvedSourceArchive(
            result.public_receipt, tuple(reversed(result.request_bodies)), result.response_bodies
        ),
        archive.ResolvedSourceArchive(
            result.public_receipt, result.request_bodies, tuple(reversed(result.response_bodies))
        ),
    ):
        assert (
            rejects(dispatch._archive_chain_from_facts, g.binding, state, changed, facts)
            == "VERSION_CONFLICT"
        )
        assert rejects(owned._archive_chain, f, state, changed) == "VERSION_CONFLICT"
    state.__dict__["halted"] = True
    assert rejects(lambda: owned._archive_chain(f, state, result)) == "VERSION_CONFLICT"


@pytest.mark.parametrize("change", ["duplicate", "swap", "wrong-run", "third-checked", "ns-aid"])
def test_issuer_rejects_entire_family_association_errors(lifecycle, change):
    role = "generate" if change == "third-checked" else "source"
    facts = family(role)
    if change == "duplicate":
        facts = (facts[0], [facts[1][0], facts[1][0]], facts[2], facts[3])
    elif change == "swap":
        facts = (facts[0], facts[1], tuple(reversed(facts[2])), facts[3])
    elif change == "wrong-run":
        facts[2][1][0].identity.__dict__["run_id"] = "run_" + "f" * 32
    elif change == "third-checked":
        facts[2][2][3]["parameters"]["unexpected"] = "extra"
    else:
        ns = list(facts[3])
        ns[1] = (ns[0][0], *ns[1][1:])
        facts = (facts[0], facts[1], facts[2], tuple(ns))
    scope, g = lifecycle(facts)
    assert rejects(lambda: scope.issue(role, None, None, facts[0]["id"])) == "VERSION_CONFLICT"
    assert not scope._issued


def test_foreign_leaf_and_key_callbacks_never_execute(lifecycle):
    called = []

    class Foreign:
        def __getattribute__(self, name):
            called.append(name)
            raise AssertionError

        def __eq__(self, other):
            called.append("eq")
            raise AssertionError

        def __str__(self):
            called.append("str")
            raise AssertionError

        def __reduce__(self):
            called.append("reduce")
            raise AssertionError

    foreign = Foreign()
    for leaf, args in (
        (owned._stage_usage, (foreign, "aid")),
        (owned._source_row, (foreign, "aid")),
        (owned._source_exchange, (foreign, "aid")),
        (owned._archive_chain, (foreign, None, None)),
        (owned._same, (foreign, foreign)),
    ):
        assert rejects(leaf, *args) == "VERSION_CONFLICT"
    f, *_ = issued(lifecycle)
    assert rejects(lambda: f.run[foreign]) == "VERSION_CONFLICT"
    facts = family("generate")
    facts[2][2][0].identity.__dict__["worker_id"] = foreign
    assert rejects(lambda: owned._fixed(policy.Slot, facts[2][2][0], "slot")) == "VERSION_CONFLICT"
    assert called == []


def test_explicit_bounds_and_retained_hidden_storage_surrogates(lifecycle):
    facts = family("generate")
    hidden = {"retained": ["\ud800"]}
    facts = (native_row(dict(facts[0]), hidden), *facts[1:])
    f, scope, g, _ = issued(lifecycle, "generate", facts=facts)
    packet = scope._issued[f.handle][1]
    hidden["retained"].append(1)
    assert scope._issued[f.handle][1] is packet
    scope2, g2 = lifecycle(facts)
    h = scope2.issue("generate", None, None, facts[0]["id"])
    assert scope2._issued[h][1].digest != packet.digest
    for field in ("nodes", "edges", "depth", "leaf_bytes", "encoded_bytes"):
        scope, g = lifecycle(facts, bounds=LIMITS._replace(**{field: 1}))
        assert rejects(scope.issue, "generate", None, None, facts[0]["id"]) == "VERSION_CONFLICT"
        assert not scope._issued


def test_fixed_accessors_cover_every_current_model_and_row_field():
    models = {
        "slot": policy.Slot,
        "identity": policy.ReservationIdentity,
        "outcome": policy.Outcome,
        "capture": sender.Capture,
        "body": archive.BodyArchive,
    }
    for name, model in models.items():
        assert set(owned._FIELDS[name]) == set(model.model_fields)
    assert set(owned._FIELDS["run"]) == set(runs.c.keys())
    assert set(owned._FIELDS["attempt"]) == set(attempts.c.keys())
    facts = family("generate")
    facts[2][2][1].__dict__["extra"] = True
    assert (
        rejects(
            lambda: owned._capture(
                facts, "generate", owned._Context("intern-s2", 32768, "offline"), LIMITS
            )
        )
        == "VERSION_CONFLICT"
    )


def test_nullable_row_usage_response_reject_without_attribute_error(lifecycle):
    for column in ("usage", "response"):
        facts = family("source")
        actual = []
        chains = []
        for a, (s, c, p, checked, w, b) in zip(facts[1], facts[2], strict=True):
            actual.append(native_row(dict(dict(a), **{column: None})))
            chains.append((s, c, p, native_row(dict(dict(checked), **{column: None})), w, b))
        facts = facts[0], actual, tuple(chains), facts[3]
        f, *_ = issued(lifecycle, facts=facts)
        if column == "usage":
            assert rejects(owned._stage_usage, f, actual[1]["id"]) == "VERSION_CONFLICT"
        else:
            assert rejects(owned._source_exchange, f, actual[1]["id"]) == "VERSION_CONFLICT"
        args = legacy_source(facts, 1, False)
        assert rejects(archive._source_exchange_from_facts, *args) == "VERSION_CONFLICT"


def test_multibyte_wire_preserves_distinct_character_and_byte_counts(lifecycle):
    facts = family("source")
    index = 1
    s, c, p, a, w, b = facts[2][index]
    envelope = strict_json(w, 32768)
    envelope["messages"][0]["content"] = "离线Unicode输入"
    wire = json.dumps(envelope, ensure_ascii=False, separators=(",", ":")).encode("utf8")
    assert len(wire) != len(wire.decode("utf8"))
    s.identity.__dict__.update(wire_sha256=sha(wire), wire_bytes=len(wire))
    spec = dict(sha256=sha(wire), bytes=len(wire), characters=len(wire.decode("utf8")))
    facts[1][index]["parameters"]["natural_spec_wire"] = spec
    a["parameters"]["natural_spec_wire"] = copy.deepcopy(spec)
    chains = list(facts[2])
    chains[index] = (s, c, p, a, wire, b)
    reads = list(facts[3])
    aid, _, _, response, _ = reads[index]
    reads[index] = (
        aid,
        archive._body(facts[0], aid, wire, True, None, archive.REQUEST),
        wire,
        response,
        b,
    )
    facts = facts[0], facts[1], tuple(chains), tuple(reads)
    f, *_ = issued(lifecycle, facts=facts)
    old = archive._source_exchange_from_facts(*legacy_source(facts, index, False))
    assert owned._source_exchange(f, aid).sha256 == old["sha256"]


def test_external_ledger_full_slot_and_strict_receipt_scalar_contract(lifecycle):
    facts = controller(family("source"))
    state = ledger(facts)
    result = resolved(facts)
    f, _, g, _ = issued(lifecycle, mode="controller", facts=facts)
    # Same aid/bytes, but a full Slot value differs: SHA-only joins would miss it.
    state.slots[1].__dict__["reserved_at"] += 1.0
    assert (
        rejects(lambda: dispatch._archive_chain_from_facts(g.binding, state, result, facts))
        == "VERSION_CONFLICT"
    )
    assert rejects(lambda: owned._archive_chain(f, state, result)) == "VERSION_CONFLICT"
    state = ledger(facts)
    receipt = copy.deepcopy(result.public_receipt)
    receipt["attempts"][1]["request_bytes"] = float(receipt["attempts"][1]["request_bytes"])
    changed = archive.ResolvedSourceArchive(receipt, result.request_bodies, result.response_bodies)
    # Deliberate stricter comparison OUTSIDE the producer's exact-int receipt
    # domain; do not claim equal behavior on all invalid Python values.
    dispatch._archive_chain_from_facts(g.binding, state, changed, facts)
    assert rejects(owned._archive_chain, f, state, changed) == "VERSION_CONFLICT"


def test_forged_wrapper_nested_fields_refuse_foreign_callbacks(lifecycle):
    called = []

    class Foreign:
        def __getattribute__(self, name):
            called.append(name)
            raise AssertionError

        def __eq__(self, other):
            called.append("eq")
            raise AssertionError

        def __hash__(self):
            called.append("hash")
            raise AssertionError

    foreign = Foreign()
    f, *_ = issued(lifecycle)
    node = f.run._node
    assert rejects(type(node), node.packet, foreign) == "VERSION_CONFLICT"
    for value in (
        owned._Value(f, foreign),
        owned._Value(foreign, node),
        owned._Record(f, node, foreign),
    ):
        assert rejects(owned._same, value, value) == "VERSION_CONFLICT"
    for forged in (
        owned._Family(foreign, f.handle, "source"),
        owned._Family(f.scope, f.handle, foreign),
        owned._Family(f.scope, foreign, "source"),
    ):
        assert rejects(owned._stage_usage, forged, "aid") == "VERSION_CONFLICT"
        assert rejects(owned._source_exchange, forged, "aid") == "VERSION_CONFLICT"
    assert called == []


def test_producer_failure_invalidates_prior_handles_without_registering(lifecycle, monkeypatch):
    f, scope, g, _ = issued(lifecycle)

    class Boundary(BaseException):
        pass

    def fail(*args):
        raise Boundary

    monkeypatch.setattr(dispatch, "_graph_stage_accounted", fail)
    with pytest.raises(Boundary):
        scope.issue("generate", None, None, "run_" + "f" * 32)
    assert not scope._active and not scope._issued
    assert rejects(lambda: f.run.id) == "VERSION_CONFLICT"


def test_native_candidate_has_no_default_runtime_activation():
    import inspect

    from sim2act import natural_spec_runtime
    assert inspect.signature(natural_spec_runtime._ColdTrialGraph).parameters[
        '_accounted_candidate'].default is None
