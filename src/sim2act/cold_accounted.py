"""Uninstalled accounted-family component; no guard exemption or send authority.

Only the private graph bridge can issue after the ORIGINAL producer succeeds.
Only explicit additive SQLite test branches import this module. Bounds must be supplied explicitly;
their product-scale derivation and whole-consumer migration remain prerequisites
for installation. There is no fallback, post mode, thaw, or digest-as-permission.
"""

from contextlib import contextmanager
from dataclasses import dataclass
from threading import get_ident
from types import MappingProxyType
from typing import Any

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
        self._prewrite_mode = None
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
            if self._prewrite_mode is None:
                self._full_check()
            else:
                self._prewrite_mode._dynamic()
            gate.require(not self._graph.worker.stop.is_set(), "Accounted reader stopped")
            gate.require(
                self._active and _same_frame(self._frame, _frame(self._graph)),
                "Accounted scope changed",
            )
        except BaseException:
            if self._prewrite_mode is None:
                self.close()
            else:
                self._prewrite_mode.close()
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
                self._prewrite_mode is None, "Prewrite issuance belongs to producer completion"
            )
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
        # Historical additive-fixture restriction only. The complete prewrite
        # mode below instead proves transport non-use and accepts nonempty ones.
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


class _LegacyOracle:
    """Assertion-only sidecar. No business values, rows or tuples are returned.

    This is deliberately NOT an alternate consumer source. Legacy full pins and
    typed checks remain as a comparison until the whole closure is reviewed.
    """

    def __init__(self, graph):
        self.__graph, self.__facts = graph, {}

    def remember(self, role, completed):
        gate.require(role not in self.__facts)
        self.__facts[role] = completed

    def clear(self):
        self.__facts.clear()

    def assert_current(self):
        models: list[tuple[type, object, dict]] = []
        for role, facts in self.__facts.items():
            gate._graph_trial_accounted_models_from_raw(
                models, facts, self.__graph.inputs["cold-trial:accounted-" + role]
            )
        gate._trial_typed_values(models)

    def assert_run(self, role, value):
        gate.require(_same_native(value, dict(self.__facts[role][0])))

    def assert_stage(self, facts):
        # Reconstruct only the OLD comparison tuple from retained original
        # objects, never thaw owned values and never expose the tuple to callers.
        prior = list(facts)
        if type(prior[0]) is _Record:
            self.assert_run("source", prior[0])
            prior[0] = self.__facts["source"][0]
        self.assert_run("generate", prior[4])
        prior[4] = self.__facts["generate"][0]
        prior[6] = self.__facts["generate"]
        if prior[7] is not None:
            prior[7] = self.__facts["source"]
        gate._graph_trial_stage_raw_from_raw(
            tuple(prior), self.__graph.inputs["cold-trial:complete"]
        )

    def pin_complete(self, fields):
        prior = dict(fields)
        prior["generation"] = dict(fields["generation"], run=dict(self.__facts["generate"][0]))
        for role, key in (("source", "source"), ("generate", "generated")):
            prior[key] = self.__graph.inputs["cold-trial:accounted-" + role]
        self.__graph.add("cold-trial:complete", prior)

    def assert_archive(self, binding, state, resolved):
        from .pa_trial_dispatch import _archive_chain_from_facts

        _archive_chain_from_facts(
            binding,
            state,
            resolved,
            self.__facts["source"],
            _guard=lambda: self.__graph.check(self.__graph.store, self.__graph.connection),
        )


class _OwnedPrewriteMode:
    """Explicit internal prewrite mode, never a production bounds qualification.

    Private logical inputs/complete contain families. They never enter the old
    pickle/raw/pre/post/origin/software fingerprint namespace. That namespace
    remains intact as a full-scan oracle, not a source of consumer values.
    """

    def __init__(self, graph, bounds):
        from .natural_spec_runtime import _ColdGraphRead

        gate.require(
            type(graph) is _ColdGraphRead
            and graph.phase == "pre"
            and graph.store.test_only
            and graph.store.sqlite
        )
        _ColdGraphRead.check(graph, graph.store, graph.connection)
        self.graph, self.active = graph, True
        b = graph.binding
        self.__binding_header = (b.approval_key, b.account_id, b.version, b.contract_fingerprint)
        self.__inputs: dict[str, Any] = {}
        self.__families: dict[str, _Family] = {}
        self.__pending = None
        self.inputs = MappingProxyType(self.__inputs)
        self.complete = None
        self.__oracle = _LegacyOracle(graph)
        contract = graph.binding.contract
        self.scope = _AccountedScope(
            graph, bounds, _Context(contract.model, contract.caps.max_output_tokens, "controller")
        )
        self.scope._prewrite_mode = self

    def _dynamic(self):
        g, w, ctx = self.graph, self.graph.worker, self.scope._context
        gate.require(self.active and self.scope._active and self.scope._prewrite_mode is self)
        _frame(g)
        gate.require(
            w.store is g.store
            and g.store.engine is g.engine
            and w.s is g.settings
            and vars(w.s) == g.settings_values
            and w.pa_trial is g.binding
            and w.stop is g.stop
            and not w.stop.is_set()
            and w.id == g.worker_id
            and w.goal_planner_transport is g.transport
            and getattr(w, "_journal_trial_store", None) is g.store
            and getattr(w, "_journal_trial_binding", None) is g.binding
            and getattr(w, "_journal_trial_drift", None) is False
            and (
                g.binding.approval_key,
                g.binding.account_id,
                g.binding.version,
                g.binding.contract_fingerprint,
            )
            == self.__binding_header
            and type(g.binding.contract.model) is str
            and g.binding.contract.model == ctx.model
            and type(g.binding.contract.caps.max_output_tokens) is int
            and g.binding.contract.caps.max_output_tokens == ctx.max_output_tokens,
            "Prewrite dynamic frontier changed",
        )

    def assert_current(self):
        try:
            self._dynamic()
            self.__assert_links()
            self.scope._full_check()  # Existing whole legacy scan, still retained.
            self.__oracle.assert_current()
            self.scope._full_check()
        except BaseException:
            self.close()
            raise

    def __assert_links(self):
        for role, family in self.__families.items():
            gate.require(
                self.__inputs["cold-trial:accounted-" + role] is family
                and family.scope is self.scope
                and family.role == role
                and family.handle in self.scope._issued
            )
        if self.complete is not None:
            gate.require(
                self.__inputs["cold-trial:complete"] is self.complete
                and self.complete["source"] is self.__families["source"]
                and self.complete["generated"] is self.__families["generate"]
            )
            self.__assert_generation_run(self.complete["generation"]["run"])

    def __assert_generation_run(self, record):
        family = self.__families["generate"]
        packet = self.scope._issued[family.handle][1]
        gate.require(
            type(record) is _Record
            and record._family is family
            and type(record._schema) is str
            and record._schema == "run"
            and type(record._node) is _Node
            and type(record._node.ref) is int
            and record._node.packet is packet
            and record._node.ref == _node(packet).get("value").get("run").ref,
            "Logical generation Run must be the issued Generate record",
        )

    def close(self):
        self.active = False
        self.scope.close()
        self.__oracle.clear()
        self.__inputs.clear()
        self.__families.clear()
        self.__pending = None
        self.complete = None

    def _begin(self, graph, role):
        try:
            self.assert_current()
            gate.require(
                graph is self.graph
                and type(role) is str
                and role in ("source", "generate")
                and role not in self.__families
                and self.__pending is None
            )
            self.__pending = role
        except BaseException:
            self.close()
            raise

    def _completed(self, graph, role, completed):
        """Called ONLY after the original producer's final full guard succeeds."""
        try:
            gate.require(
                graph is self.graph and role == self.__pending and role not in self.__families
            )
            self.assert_current()
            packet = _capture(completed, role, self.scope._context, self.scope._bounds)
            expected = _freeze(graph.inputs["cold-trial:accounted-" + role], self.scope._bounds)
            gate.require(_equal(_node(packet).get("value"), _node(expected)))
            self.scope._full_check()
            handle = _Handle()
            self.scope._issued[handle] = role, packet
            self.scope._roles.add(role)
            family = _Family(self.scope, handle, role)
            _associations(family)
            self.__oracle.remember(role, completed)
            self.__families[role] = family
            self.__inputs["cold-trial:accounted-" + role] = family
            self.__pending = None
            self.assert_current()
            return family
        except BaseException:
            self.close()
            raise

    def assert_family(self, graph, family, role):
        self.assert_current()
        gate.require(
            graph is self.graph
            and type(family) is _Family
            and family is self.__families.get(role)
            and family.scope is self.scope
            and self.inputs["cold-trial:accounted-" + role] is family
        )
        family._root()

    def assert_run(self, role, record):
        family = self.__families[role]
        self.assert_family(self.graph, family, role)
        gate.require(
            type(record) is _Record
            and record._family is family
            and type(record._schema) is str
            and record._schema == "run"
            and _same(record, family.run)
        )
        self.__oracle.assert_run(role, record)

    def assert_upstream_run(self, role, native):
        self.assert_current()
        gate.require(
            _same_native(self.__families[role].run, dict(gate._trial_pure_mapping(native))),
            "Accounted/upstream complete Run differs",
        )

    def seal(self, fields):
        self.assert_current()
        gate.require(
            self.complete is None
            and type(fields) is dict
            and fields["source"] is self.__families["source"]
            and fields["generated"] is self.__families["generate"]
        )
        self.__assert_generation_run(fields["generation"]["run"])
        self.complete = MappingProxyType(
            dict(fields, generation=MappingProxyType(dict(fields["generation"])))
        )
        self.__inputs["cold-trial:complete"] = self.complete

    def pin_legacy_complete(self, fields):
        """Oracle-only raw assembly; its value never crosses this method."""
        gate.require(fields is self.complete)
        self.__oracle.pin_complete(fields)
        self.assert_current()

    def assert_archive(self, binding, state, resolved):
        self.assert_current()
        self.__oracle.assert_archive(binding, state, resolved)
        self.assert_current()

    def assert_stage(self, facts):
        self.assert_current()
        gate.require(type(facts) in (tuple, list) and len(facts) == 9 and self.complete is not None)
        job, bound, raw, metadata, gen, _, generated, source, extraction = facts
        self.assert_family(self.graph, generated, "generate")
        self.assert_run("generate", gen)
        full = self.complete
        if full is None:
            raise _Rejected("Complete prewrite manifest required")
        gate.require(
            raw is full["generation"]["raw"] and metadata is full["generation"]["metadata"]
        )
        if bound is full["source_binding"]:
            gate.require(source is None and extraction is None)
            self.assert_run("source", job)
        else:
            gate.require(
                bound is full["binding"] and job is full["cold_job"] and extraction is not None
            )
            self.assert_family(self.graph, source, "source")
            draft, _, target, goal = extraction
            gate.require(
                draft is full["extraction"]["draft"]
                and target is full["extraction"]["target"]
                and goal is full["extraction"]["goal"]
            )
        self.__oracle.assert_stage(facts)


def _prewrite_mode(value, graph):
    gate.require(type(value) is _OwnedPrewriteMode and value.graph is graph)
    value.assert_current()
    return value


@contextmanager
def _owned_prewrite(graph, bounds):
    mode = _OwnedPrewriteMode(graph, bounds)
    try:
        yield mode
        mode.assert_current()
    finally:
        mode.close()


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


def _source_bodies_owned(family, c, user, state, guard):
    """Business values come only from the issued family; SQL keys stay fresh."""
    from .spec_production import evidence_mode

    gate.require(type(state) is policy.Ledger and family.role == "source")
    gate.require(gate._trial_result(evidence_mode(c, family.run), guard) == "LIVE")
    slots = tuple(s for s in state.slots if s.identity.stage == "source")
    expected = {r.id for r in family.actual}
    gate.require(
        len(family.actual) == len(slots) == 2 and expected == {s.identity.attempt_id for s in slots}
    )
    for kind in (archive.REQUEST, archive.RESPONSE):
        keys = gate._trial_result(gate._keys(c, user, family.run.id, kind, _guard=guard), guard)
        gate._trial_result(archive._source_keys_from_facts(expected, keys), guard)
    requests, responses, public = [], [], []
    for slot in slots:
        aid = slot.identity.attempt_id
        _source_slot(family, state, aid)
        _source_row(family, aid)
        _, _, read = _source_parts(family, aid)
        canonical = _source_exchange(family, aid)
        wire, payload = read.wire, read.payload
        requests.append(wire)
        responses.append(payload)
        public.append(
            dict(
                attempt_id=aid,
                request_bytes=len(wire),
                request_sha256=read.request.sha256,
                decoded_body_bytes=len(payload),
                decoded_body_sha256=read.response.sha256,
                canonical_ascii_bytes=canonical.bytes,
                canonical_ascii_sha256=canonical.sha256,
            )
        )
        guard()
    return tuple(requests), tuple(responses), public


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
