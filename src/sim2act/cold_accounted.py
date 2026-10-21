"""Uninstalled accounted-family component; no guard exemption or send authority.

Only the private graph bridge can issue after the ORIGINAL producer succeeds.
Only explicit additive SQLite test branches import this module. Bounds must be supplied explicitly;
their product-scale derivation and whole-consumer migration remain prerequisites
for installation. There is no fallback, post mode, thaw, or digest-as-permission.
"""

from dataclasses import dataclass
from threading import get_ident

from sqlalchemy.engine import RowMapping

from . import natural_live_admission as gate
from . import natural_source_archives as archive
from . import production_trial_policy as policy
from . import production_trial_sender as sender
from ._cold_accounted_values import _Bounds, _equal, _freeze, _Node, _node, _Rejected
from .contracts import strict_json
from .goal_applications import response_archive
from .model import normalize_usage

_SCHEMA = "accounted-family.pre.v1"
_FIELDS = {
    "run": (
        "id",
        "project_id",
        "principal_id",
        "runtime_id",
        "goal",
        "resource_refs",
        "status",
        "request_key",
        "fingerprint",
        "created_at",
        "lease_until",
        "fence",
        "worker_id",
        "context",
        "result",
        "error",
        "cancel_intent",
        "version",
    ),
    "attempt": (
        "id",
        "run_id",
        "created_at",
        "mode",
        "request_model",
        "response_model",
        "status",
        "usage",
        "reserved_tokens",
        "parameters",
        "response",
        "error",
        "elapsed",
    ),
    "slot": ("identity", "reserved_at", "attempted", "settlement", "accepted"),
    "identity": (
        "requirements_fingerprint",
        "approval_fingerprint",
        "stage",
        "stage_fingerprint",
        "run_id",
        "runtime_id",
        "version",
        "fence",
        "worker_id",
        "account_id",
        "quota_subject",
        "attempt_id",
        "wire_sha256",
        "wire_bytes",
    ),
    "outcome": (
        "outcome",
        "response_sha256",
        "response_ascii_bytes",
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
    ),
    "capture": (
        "provenance",
        "raw_sha256",
        "raw_bytes",
        "body_b64",
        "complete",
        "received_response",
        "omission",
        "canonical_sha256",
        "canonical_ascii_bytes",
        "response_verdict",
        "outcome",
    ),
    "body": (
        "version",
        "run_id",
        "attempt_id",
        "principal_id",
        "project_id",
        "runtime_id",
        "phase",
        "provenance",
        "byte_count",
        "sha256",
        "received_complete",
        "extent",
        "omission",
        "body_b64",
        "canonical_sha256",
    ),
}
_NESTED = {
    ("slot", "identity"): "identity",
    ("slot", "settlement"): "outcome",
    ("capture", "outcome"): "outcome",
}
_TOKENS = ("prompt_tokens", "completion_tokens", "total_tokens")


@dataclass(frozen=True, slots=True)
class _Context:
    model: str
    max_output_tokens: int
    mode: str  # Explicit controller/offline provenance, never inferred from rows.

    def __post_init__(self):
        if not (
            type(self.model) is str
            and self.model
            and type(self.max_output_tokens) is int
            and self.max_output_tokens > 0
            and type(self.mode) is str
            and self.mode in ("controller", "offline")
        ):
            raise _Rejected("exact trusted leaf context required")


def _frame(graph):
    """Cheap lifecycle witness only. Original full guards remain at boundaries."""
    from .natural_spec_runtime import _ColdGraphRead
    from .pb_natural_specs import _source_reads_current

    gate.require(
        type(graph) is _ColdGraphRead
        and graph.active
        and graph.phase == "pre"
        and type(graph.scope) is list
        and len(graph.scope) == 1
        and graph.scope[0] is graph.nonce
        and not graph.connection.closed
        and graph.connection.get_transaction() is graph.transaction
        and graph.thread == get_ident()
        and graph.connection.info.get("pb_source_reads") is graph.token
        and type(graph.epoch) is int
        and graph.connection.info.get("source_proof_write_epoch", 0) == graph.epoch
        and graph.connection.connection.driver_connection is graph.driver
        and graph.driver.in_transaction is True
        and _source_reads_current(graph.store, graph.connection, graph.token)
        and type(graph.driver.total_changes) is int
        and graph.driver.total_changes == graph.changes,
        "Accounted scope lifecycle changed",
    )
    return (
        graph,
        graph.store,
        graph.connection,
        graph.transaction,
        graph.scope,
        graph.nonce,
        graph.token,
        graph.binding,
        graph.driver,
        graph.phase,
        graph.epoch,
        graph.driver.total_changes,
        graph.thread,
        _SCHEMA,
    )


def _same_frame(left, right):
    return all(a is b for a, b in zip(left[:9], right[:9], strict=True)) and all(
        type(a) is type(b) and a == b for a, b in zip(left[9:], right[9:], strict=True)
    )


class _Handle:
    __slots__ = ()


class _AccountedScope:
    """Private issuance registry, never a new production permission boundary."""

    def __init__(self, graph, bounds, context):
        gate.require(
            type(bounds) is _Bounds
            and type(context) is _Context
            and all(type(v) is int and v > 0 for v in bounds)
        )
        self._graph, self._bounds, self._context = graph, bounds, context
        self._active, self._issued, self._roles = True, {}, set()
        self._full_check()
        self._frame = _frame(graph)

    def _full_check(self):
        from .natural_spec_runtime import _ColdGraphRead

        gate.require(type(self._graph) is _ColdGraphRead)
        _ColdGraphRead.check(self._graph, self._graph.store, self._graph.connection)

    def _current(self):
        try:
            # This uninstalled bridge has no guard exemption. In particular an
            # unchanged binding/settings identity is not a freshness witness.
            self._full_check()
            gate.require(not self._graph.worker.stop.is_set(), "Accounted reader stopped")
            gate.require(
                self._active and _same_frame(self._frame, _frame(self._graph)),
                "Accounted scope changed",
            )
        except BaseException:
            self.close()
            raise

    def close(self):
        self._active = False
        self._issued.clear()
        self._roles.clear()

    def issue(self, role, state, cursor, run_id):
        """Original full producer -> owned copy -> original guard -> register.

        Accepts no Packet/digest or caller assertion that verification happened.
        Current runtime never calls this bridge; all old pins stay installed.
        """
        from .pa_trial_dispatch import _graph_stage_accounted

        try:
            self._current()
            gate.require(
                type(role) is str
                and role in ("source", "generate")
                and role not in self._roles
                and type(run_id) is str
            )
            self._full_check()
            facts = _graph_stage_accounted(
                self._graph,
                self._graph.store,
                self._graph.connection,
                self._graph.binding,
                state,
                cursor,
                run_id,
                role,
            )
            self._current()
            data = _capture(facts, role, self._context, self._bounds)
            # The original producer pinned its complete business-value shape.
            # Copying a self-consistent but changed returned model is not enough.
            expected = _freeze(self._graph.inputs["cold-trial:accounted-" + role], self._bounds)
            gate.require(
                _equal(_node(data).get("value"), _node(expected)),
                "Owned accounted copy differs from original complete producer proof",
            )
            self._full_check()
            self._current()
            handle = _Handle()
            self._issued[handle] = role, data
            self._roles.add(role)
            result = _Family(self, handle, role)
            _associations(result)  # Entire 3/2-aid relation, never first-aid only.
            return handle
        except BaseException:
            self.close()
            raise

    def read(self, handle, role):
        self._current()
        gate.require(
            type(handle) is _Handle
            and type(role) is str
            and handle in self._issued
            and self._issued[handle][0] == role,
            "Unissued or wrong-role accounted handle",
        )
        return _Family(self, handle, role)


def _scope_for_graph(graph, bounds):
    """Explicit, uninstalled pre/SQLite bridge. No default production budget."""
    from .natural_spec_runtime import _ColdGraphRead

    gate.require(
        type(graph) is _ColdGraphRead
        and graph.phase == "pre"
        and graph.store.test_only
        and graph.store.sqlite
        # Offline SQL integration has no transport. Do not silently admit an
        # opaque mutable transport whose content the old CGR does not pin.
        and graph.worker.goal_planner_transport is None
    )
    _ColdGraphRead.check(graph, graph.store, graph.connection)
    contract = graph.binding.contract
    context = _Context(contract.model, contract.caps.max_output_tokens, "controller")
    result = _AccountedScope(graph, bounds, context)
    _ColdGraphRead.check(graph, graph.store, graph.connection)
    return result


@dataclass(frozen=True, slots=True, eq=False)
class _SourceTestBridge:
    """Explicit additive integration only; never skips an original predicate."""

    scope: _AccountedScope
    handle: _Handle

    def family(self, graph):
        gate.require(
            type(self.scope) is _AccountedScope
            and self.scope._graph is graph
            and graph.store.test_only
            and graph.store.sqlite
            and graph.phase == "pre"
            and graph.worker.goal_planner_transport is None
        )
        family = self.scope.read(self.handle, "source")
        context = self.scope._context
        contract = graph.binding.contract
        gate.require(
            context.mode == "controller"
            and type(contract.model) is str
            and context.model == contract.model
            and type(contract.caps.max_output_tokens) is int
            and context.max_output_tokens == contract.caps.max_output_tokens
        )
        return family


def _source_test_family(bridge, graph):
    gate.require(type(bridge) is _SourceTestBridge)
    return bridge.family(graph)


def _source_slot(family, state, aid):
    """Join all Slot/Identity/Outcome fields, including non-aid fields."""
    gate.require(type(state) is policy.Ledger)
    _, chain, _ = _source_parts(family, aid)
    slots = tuple(s for s in state.slots if s.identity.attempt_id == aid)
    gate.require(len(slots) == 1 and slots[0].identity.stage == "source")
    raw = gate._trial_typed_storage(policy.Slot, slots[0])
    gate._trial_typed_values([(policy.Slot, slots[0], raw)])
    gate.require(_same_native(chain.slot, raw), "Complete Source slot differs")


def _fixed(expected, value, schema):
    actual = gate._trial_typed_storage(expected, value)
    raw = expected.model_dump(value, warnings=False)
    gate._trial_typed_values([(expected, value, raw)])
    gate.require(
        set(raw) == set(_FIELDS[schema]) and gate._trial_typed_equal(actual, raw),
        "Complete accounted fixed record required",
    )
    return raw


def _capture(facts, role, context, bounds):
    from .natural_spec_runtime import _cold_graph_row_storage

    gate.require(type(facts) is tuple and len(facts) == 4)
    run, actual, chains, ns_reads = facts
    count = 3 if role == "generate" else 2
    gate.require(
        type(actual) in (list, tuple)
        and type(chains) in (list, tuple)
        and type(ns_reads) in (list, tuple)
        and len(actual) == len(chains) == count
        and len(ns_reads) == (2 if role == "source" else 0)
    )
    sidecars = []

    def row(value, schema, label):
        if type(value) is RowMapping:
            keys, data, index = _cold_graph_row_storage(value)
            names = tuple(str(k) for k in keys)
            gate.require(len(names) == len(set(names)), "Duplicate accounted row keys")
            sidecars.append((label, (keys, data, index)))
            value = {str(k): data[index[str(k)]] for k in keys}
        else:
            gate.require(type(value) is dict and all(type(k) is str for k in value))
            value = dict(value)
        gate.require(set(value) == set(_FIELDS[schema]), "Complete accounted row columns required")
        return value

    copied_run = row(run, "run", ("run",))
    copied_actual = tuple(row(a, "attempt", ("actual", i)) for i, a in enumerate(actual))
    copied_chains = []
    for i, chain in enumerate(chains):
        gate.require(type(chain) is tuple and len(chain) == 6)
        slot, capture, parsed, checked, wire, payload = chain
        gate.require(type(wire) is bytes and type(payload) is bytes)
        copied_chains.append(
            (
                _fixed(policy.Slot, slot, "slot"),
                _fixed(sender.Capture, capture, "capture"),
                parsed,
                row(checked, "attempt", ("checked", i)),
                wire,
                payload,
            )
        )
    copied_ns = []
    for read in ns_reads:
        gate.require(type(read) is tuple and len(read) == 5)
        aid, request, wire, response, payload = read
        gate.require(type(aid) is str and type(wire) is bytes and type(payload) is bytes)
        copied_ns.append(
            (
                aid,
                _fixed(archive.BodyArchive, request, "body"),
                wire,
                _fixed(archive.BodyArchive, response, "body"),
                payload,
            )
        )
    return _freeze(
        dict(
            schema=_SCHEMA,
            role=role,
            phase="pre",
            mode=context.mode,
            value=dict(
                run=copied_run,
                actual=copied_actual,
                chains=tuple(copied_chains),
                ns_reads=tuple(copied_ns),
            ),
            row_storage=tuple(sidecars),
        ),
        bounds,
    )


@dataclass(frozen=True, slots=True, eq=False)
class _Value:
    _family: "_Family"
    _node: _Node

    def __eq__(self, other):
        raise TypeError("Use explicit domain comparison, not record/view equality")

    def _check(self):
        gate.require(
            type(self._family) is _Family and type(self._node) is _Node,
            "Exact issued family and node required",
        )
        if type(self) is _Record:
            gate.require(
                type(self._schema) is str and self._schema in _FIELDS,
                "Exact fixed record schema required",
            )
        packet = self._family._root().packet
        gate.require(
            self._node.packet is packet
            and type(self._node.ref) is int
            and 0 <= self._node.ref < len(packet.nodes),
            "Accounted view is not from its issued packet",
        )

    def __getitem__(self, key):
        self._check()
        if self._node.tag == "dict":
            node = self._node.get(key)
        else:
            gate.require(type(key) is int)
            node = self._node.sequence()[key]
        return _read(self._family, node)

    def __len__(self):
        self._check()
        return len(self._node.items() if self._node.tag == "dict" else self._node.sequence())


@dataclass(frozen=True, slots=True, eq=False)
class _Record(_Value):
    _schema: str

    def __getattr__(self, name):
        self._check()
        gate.require(
            type(self._schema) is str and self._schema in _FIELDS,
            "Exact fixed record schema required",
        )
        gate.require(
            type(name) is str and name in _FIELDS[self._schema], "Unknown fixed accounted field"
        )
        node = self._node.get(name)
        nested = _NESTED.get((self._schema, name))
        if nested is not None and node.tag != "none":
            return _Record(self._family, node, nested)
        return _read(self._family, node)


def _read(family, node):
    return _Value(family, node) if node.tag in ("dict", "tuple", "list") else node.scalar()


@dataclass(frozen=True, slots=True, eq=False)
class _Chain:
    slot: _Record
    capture: _Record
    parsed: _Value
    checked: _Record
    wire: bytes
    payload: bytes


@dataclass(frozen=True, slots=True, eq=False)
class _NSRead:
    aid: str
    request: _Record
    wire: bytes
    response: _Record
    payload: bytes


@dataclass(frozen=True, slots=True, eq=False)
class _Family:
    scope: _AccountedScope
    handle: _Handle
    role: str

    def _root(self):
        gate.require(type(self.scope) is _AccountedScope and type(self.role) is str)
        self.scope._current()
        gate.require(
            type(self.handle) is _Handle
            and self.handle in self.scope._issued
            and self.scope._issued[self.handle][0] == self.role,
            "Unissued accounted family",
        )
        return _node(self.scope._issued[self.handle][1]).get("value")

    @property
    def run(self):
        return _Record(self, self._root().get("run"), "run")

    @property
    def actual(self):
        return tuple(_Record(self, n, "attempt") for n in self._root().get("actual").sequence())

    @property
    def chains(self):
        result = []
        for n in self._root().get("chains").sequence():
            s, c, p, a, w, b = n.sequence()
            result.append(
                _Chain(
                    _Record(self, s, "slot"),
                    _Record(self, c, "capture"),
                    _Value(self, p),
                    _Record(self, a, "attempt"),
                    w.scalar(),
                    b.scalar(),
                )
            )
        return tuple(result)

    @property
    def ns_reads(self):
        result = []
        for n in self._root().get("ns_reads").sequence():
            aid, q, w, r, b = n.sequence()
            result.append(
                _NSRead(
                    aid.scalar(),
                    _Record(self, q, "body"),
                    w.scalar(),
                    _Record(self, r, "body"),
                    b.scalar(),
                )
            )
        return tuple(result)


def _same(left, right):
    gate.require(type(left) in (_Value, _Record) and type(right) in (_Value, _Record))
    left._check()
    right._check()
    return _equal(left._node, right._node)


def _same_native(value, native):
    if type(value) not in (_Value, _Record):
        return False
    value._check()
    return _equal(value._node, _node(_freeze(native, value._family.scope._bounds)))


def _scalar_same(left, right):
    gate.require(
        type(left) in (str, bytes, int, bool, float, type(None))
        and type(right) in (str, bytes, int, bool, float, type(None))
    )
    return type(left) is type(right) and left == right


def _one(values, aid, field="id"):
    gate.require(type(aid) is str)
    found = tuple(v for v in values if getattr(v, field) == aid)
    gate.require(len(found) == 1, "Exact accounted aid relation required")
    return found[0]


def _associations(family):
    run, actual, chains, reads = family.run, family.actual, family.chains, family.ns_reads
    gate.require(len({a.id for a in actual}) == len(actual))
    for index, (a, chain) in enumerate(zip(actual, chains, strict=True)):
        identity = chain.slot.identity
        gate.require(
            type(a.id) is str
            and a.run_id == run.id
            and _same(a, chain.checked)
            and identity.stage == family.role
            and identity.run_id == run.id
            and identity.attempt_id == a.id
            and identity.runtime_id == run.runtime_id
        )
        if family.role == "source":
            read = reads[index]
            gate.require(
                read.aid == a.id and read.wire == chain.wire and read.payload == chain.payload
            )
            for body in (read.request, read.response):
                gate.require(
                    body.run_id == run.id
                    and body.attempt_id == a.id
                    and body.principal_id == run.principal_id
                    and body.project_id == run.project_id
                    and body.runtime_id == run.runtime_id
                )


def _usage(parsed):
    """Same normalize_usage rules, reading owned data without thawing it."""
    parsed._check()
    if parsed._node.tag != "dict":
        usage = None
    else:
        usage = dict(parsed._node.items()).get("usage")
    fields = dict(usage.items()) if usage is not None and usage.tag == "dict" else {}
    known = {
        k: fields[k].scalar()
        for k in _TOKENS
        if k in fields and fields[k].tag == "int" and fields[k].scalar() >= 0
    }
    complete = (
        len(known) == 3
        and known["total_tokens"] == known["prompt_tokens"] + known["completion_tokens"]
    )
    return dict(
        status="known" if complete else "partial" if known else "unknown", tokens=known or None
    )


def _stage_usage(family, aid):
    gate.require(type(family) is _Family)
    actual = _one(family.actual, aid)
    chain = tuple(c for c in family.chains if c.checked.id == aid)
    gate.require(len(chain) == 1)
    chain = chain[0]
    usage = _usage(chain.parsed)
    gate.require(
        _same(chain.checked, actual)
        and actual.status == ("RECEIVED" if family.role == "generate" else "VERIFIED")
        and _same_native(actual.usage, usage)
        and usage["status"] == "known"
        and chain.slot.settlement is not None
        and all(
            type(getattr(chain.slot.settlement, k)) is int
            and getattr(chain.slot.settlement, k) == usage["tokens"][k]
            for k in _TOKENS
        )
    )


def _source_parts(family, aid):
    gate.require(type(family) is _Family)
    gate.require(family.role == "source")
    actual = _one(family.actual, aid)
    reads = tuple(r for r in family.ns_reads if r.aid == aid)
    chains = tuple(c for c in family.chains if c.checked.id == aid)
    gate.require(len(reads) == len(chains) == 1)
    return actual, chains[0], reads[0]


def _source_row(family, aid):
    row, chain, _ = _source_parts(family, aid)
    ctx = family.scope._context
    gate.require(
        row.mode == ("LIVE" if ctx.mode == "controller" else "MOCK")
        and row.status == "VERIFIED"
        and row.request_model == row.response_model == ctx.model
        and chain.slot.accepted is True
        and chain.slot.settlement is not None
    )


@dataclass(frozen=True, slots=True)
class _Canonical:
    status: str
    bytes: int
    sha256: str


def _source_exchange(family, aid):
    row, chain, read = _source_parts(family, aid)
    request, response, wire, received = read.request, read.response, read.wire, read.payload
    raw = strict_json(received, archive.MAX_BODY_BYTES)
    original, canonical = response_archive(raw)
    usage = normalize_usage(raw)
    envelope = strict_json(wire, archive.MAX_BODY_BYTES)
    ctx, identity, outcome = family.scope._context, chain.slot.identity, chain.slot.settlement
    gate.require(
        type(envelope) is dict
        and envelope.get("model") == ctx.model
        and envelope.get("stream") is False
        and type(envelope.get("max_tokens")) is int
        and 0 < envelope["max_tokens"] <= ctx.max_output_tokens
        and _same_native(
            row.parameters["natural_spec_wire"],
            dict(sha256=request.sha256, bytes=len(wire), characters=len(wire.decode("utf-8"))),
        )
        and identity.wire_sha256 == request.sha256
        and _scalar_same(identity.wire_bytes, len(wire))
        and original is not None
        and _same_native(row.response, dict(received_raw=original, raw_evidence=canonical))
        and response.canonical_sha256 == canonical["sha256"]
        and _same_native(row.usage, usage)
        and usage["status"] == "known"
        and outcome is not None
        and outcome.response_sha256
        == (response.sha256 if ctx.mode == "controller" else canonical["sha256"])
        and _scalar_same(outcome.response_ascii_bytes, canonical["bytes"])
        and all(
            type(getattr(outcome, k)) is int and getattr(outcome, k) == usage["tokens"][k]
            for k in _TOKENS
        )
    )
    return _Canonical(**canonical)


def _archive_chain(family, state, resolved):
    """Owned family plus fresh detached snapshots of still-protected old roots.

    Caller retains original ledger/resolve typed guards, current DB authorization
    and byte/archive producers. Snapshotting these arguments issues no permit.
    """
    gate.require(type(family) is _Family)
    family._root()
    gate.require(
        family.role == "source"
        and family.scope._context.mode == "controller"
        and type(resolved) is archive.ResolvedSourceArchive
    )
    state_raw = gate._trial_typed_storage(policy.Ledger, state)
    gate._trial_typed_values([(policy.Ledger, state, state_raw)])
    bound = family.scope._bounds
    ledger = _node(_freeze(state_raw, bound))
    root = _node(
        _freeze(
            dict(
                receipt=resolved.public_receipt,
                requests=resolved.request_bodies,
                responses=resolved.response_bodies,
            ),
            bound,
        )
    )
    receipt = root.get("receipt")
    slots = tuple(
        n
        for n in ledger.get("slots").sequence()
        if n.get("identity").get("stage").scalar() == "source"
    )
    proofs = receipt.get("attempts").sequence()
    gate.require(
        ledger.get("halted").scalar() is False
        and len(slots) == len(proofs) == len(family.chains) == len(family.ns_reads) == 2
        and receipt.get("verification").scalar() == "SPEC_PRODUCTION_CONTROLLER_ARCHIVE"
        and receipt.get("live_allowed").scalar() is False
        and receipt.get("source_run_id").scalar() == family.run.id
    )
    for index, (slot, proof) in enumerate(zip(slots, proofs, strict=True)):
        aid = proof.get("attempt_id").scalar()
        row, chain, _ = _source_parts(family, aid)
        identity, capture = chain.slot.identity, chain.capture
        gate.require(
            _equal(chain.slot._node, slot)
            and any(_same(chain.checked, a) for a in family.actual)
            and row.run_id == identity.run_id == family.run.id
            and identity.attempt_id == aid
            and _scalar_same(identity.wire_sha256, proof.get("request_sha256").scalar())
            and _scalar_same(identity.wire_bytes, proof.get("request_bytes").scalar())
            and _scalar_same(capture.raw_sha256, proof.get("decoded_body_sha256").scalar())
            and _scalar_same(capture.raw_bytes, proof.get("decoded_body_bytes").scalar())
            and _scalar_same(capture.canonical_sha256, proof.get("canonical_ascii_sha256").scalar())
            and _scalar_same(
                capture.canonical_ascii_bytes, proof.get("canonical_ascii_bytes").scalar()
            )
            and root.get("requests").sequence()[index].scalar() == chain.wire
            and root.get("responses").sequence()[index].scalar() == chain.payload
        )
