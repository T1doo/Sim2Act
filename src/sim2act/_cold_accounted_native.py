"""Default-off native accounted candidate; no public/runtime activation switch.

Only pre-origin SQLite graphs qualify. Legacy byte exports remain legacy; the
candidate's private continuity frontier never enters a persisted proof.
"""

import math
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from sqlalchemy.engine import RowMapping

from . import cold_accounted as o
from . import natural_live_admission as gate
from . import natural_spec_runtime as rt
from . import production_trial_policy as policy
from ._cold_accounted_budget import _Capacity, _Ledger, _Projection, _Unsupported
from ._cold_accounted_values import _Node, _Packet

# No public setting enables this protocol. The one original first/second
# transaction has exactly these post-selection additions (second observation is
# produced by _recheck->_source_value, not a second archive replay).
_FUTURE_ROOTS = frozenset((
    'cold-trial:complete', 'commit:first:context', 'cold-trial:semantic-authorities',
    'commit:first:source-observation', 'commit:first:trial-output',
    'settlement-current-attempt', 'settlement-parsed', 'commit:second',
    'commit:second:current', 'commit:second:context',
    'commit:second:source-observation', 'commit:second:trial-output',
))


class _SizingProjection(_Projection):
    """Admission-only full remaining-root size, never a consumer source.

    Nested SQL carriers are an unsupported optimization subdomain, not a new
    business rejection. Row child depths retain their offset; completed memo
    reuse checks the entire longest descendant path.
    """
    def __init__(self, ledger, ticket):
        super().__init__(ledger, ticket)
        self.row_base = None

    def copy(self, value, depth=0, *, typed=False):
        if self.row_base is not None and depth == 0:
            depth = self.row_base + 1
        if type(value) is RowMapping:
            if self.row_base is not None:
                raise _Capacity('nested_sizing_row')
            key = id(value), typed
            limit = min(self.b.bounds.depth - 16, (sys.getrecursionlimit() - 200) // 5)
            if id(value) in self.active:
                raise o._Rejected('cyclic sizing row')
            if key in self.done:
                if depth + self.done[key][2] > limit:
                    raise _Capacity('sizing_row_depth')
                return self.done[key][1]
            if self.nodes >= self.b.bounds.nodes or depth > limit:
                raise _Capacity('sizing_row')
            self.nodes += 1
            self.alloc(512)
            self.active.add(id(value))
            self.row_base = depth
            try:
                copied = self.row(value, None)
            finally:
                self.row_base = None
            self.active.remove(id(value))
            # All raw keys/data/safe-index descendants were metered by row.
            # Including older completed heights overestimates, never truncates.
            self.b.spend(len(self.done))
            height = 1 + max((entry[2] for entry in self.done.values()), default=0)
            if depth + height > limit:
                raise _Capacity('sizing_row_depth')
            self.done[key] = value, copied, height
            return copied
        return super().copy(value, depth, typed=typed)


class _Arena:
    """One issuance's immutable accessors, prepaid before any construction.

    No validation result, external reference or mutable comparison is cached.
    Node/children/value/record views are built eagerly, not by first-use growth.
    """

    def __init__(self, ledger, packets):
        n = sum(len(p.nodes) for p in packets.values())
        e = sum(p.edges for p in packets.values())
        # Node and native scalar, two child tables, all fixed-schema Records,
        # Value, dict slots/keys, tuples and Family's five fixed chains/2 reads.
        ledger.reserve('resident', 65536 + 8192 * n + 1024 * e)
        self.nodes, self.items, self.sequences, self.scalars = {}, {}, {}, {}
        self.values, self.records, self.families, self.canonicals = {}, {}, {}, {}
        self.classes = {}
        self.usage: Any = set()
        self.ledger = ledger
        for packet in packets.values():
            ident = id(packet)
            nodes = tuple(_Node(packet, ref, ledger) for ref in range(len(packet.nodes)))
            self.nodes[ident] = nodes
            for ref, (tag, body) in enumerate(packet.nodes):
                key = ident, ref
                if tag == 'dict':
                    self.items[key] = tuple((packet.nodes[k][1], nodes[v]) for k, v in body)
                elif tag in ('tuple', 'list'):
                    self.sequences[key] = tuple(nodes[v] for v in body)
                elif tag != 'row':
                    self.scalars[key] = float.fromhex(body) if tag == 'float' else body

    def __setattr__(self, name, value):
        if getattr(self, '_sealed', False):
            raise AttributeError('immutable issued arena')
        object.__setattr__(self, name, value)

    def seal(self):
        for name in ('nodes', 'items', 'sequences', 'scalars', 'values', 'records', 'families', 'canonicals', 'classes'):
            setattr(self, name, MappingProxyType(getattr(self, name)))
        self.usage = frozenset(self.usage)
        self._sealed = True

    def release(self):
        for name in ('nodes', 'items', 'sequences', 'scalars', 'values', 'records', 'families', 'canonicals', 'classes'):
            object.__setattr__(self, name, MappingProxyType({}))
        object.__setattr__(self, 'usage', frozenset())

    def classify(self, packets):
        # Sorting adds sum(d log d) dictionary-edge work to the node walk.
        # Structural interning holds only child class integers, never unfolded
        # descendant trees. Collisions still compare complete native tuple keys.
        # One global table makes equivalent values in either family comparable.
        n = sum(len(p.nodes) for p in packets.values())
        e = sum(p.edges for p in packets.values())
        leaf = sum(len(p.encoded) for p in packets.values())
        self.ledger.spend(8 * (n + e + leaf + 1)**4)
        temp = self.ledger.reserve(units=8192 + 2048 * (n + e))
        try:
            intern: dict[tuple, int] = {}
            for packet in packets.values():
                classes: list[Any] = [None] * len(packet.nodes)
                def visit(ref, *, packet=packet, classes=classes):
                    if classes[ref] is not None:
                        return classes[ref]
                    tag, body = packet.nodes[ref]
                    if tag == 'dict':
                        body = tuple(sorted((packet.nodes[k][1], visit(v)) for k, v in body))
                    elif tag in ('list', 'tuple'):
                        body = tuple(visit(v) for v in body)
                    elif tag == 'row':
                        body = visit(body)
                    elif tag == 'float':
                        body = float.fromhex(body)  # Equal +/- zero share one domain class.
                    key = tag, body
                    if key not in intern:
                        intern[key] = len(intern)
                    classes[ref] = intern[key]
                    return classes[ref]
                for ref in range(len(packet.nodes)):
                    visit(ref)
                self.classes[id(packet)] = tuple(classes)
        finally:
            temp.close()

    def equal(self, left, right):
        gate.require(type(left) is _Node and type(right) is _Node
                     and left.allocation is self.ledger and right.allocation is self.ledger,
                     'Comparison must use this exact issued arena')
        self.node(left.packet, left.ref)
        self.node(right.packet, right.ref)
        return self.classes[id(left.packet)][left.ref] == self.classes[id(right.packet)][right.ref]

    def node(self, packet, ref):
        gate.require(self.ledger.active, 'Closed native arena')
        gate.require(type(packet) is _Packet and type(packet.nodes) is tuple and type(ref) is int
                     and 0 <= ref < len(packet.nodes), 'Exact arena reference required')
        gate.require(id(packet) in self.nodes, 'Foreign packet')
        nodes = self.nodes[id(packet)]
        gate.require(nodes[ref].packet is packet)
        return nodes[ref]

    def bind(self, family):
        packet = family.scope._issued[family.handle][1]
        for node in self.nodes[id(packet)]:
            key = id(packet), node.ref
            if node.tag in ('dict', 'list', 'tuple'):
                self.values[key] = o._Value(family, node)
            if node.tag == 'dict':
                for schema in o._FIELDS:
                    self.records[key, schema] = o._Record(family, node, schema)
        root = self.node(packet, packet.root).get('value')
        def record(node, schema):
            return self.records[(id(packet), node.ref), schema]
        actual = tuple(record(n, 'attempt') for n in root.get('actual').sequence())
        chains = []
        for node in root.get('chains').sequence():
            s, c, p, a, w, b = node.sequence()
            chains.append(o._Chain(record(s, 'slot'), record(c, 'capture'),
                                   self.values[id(packet), p.ref], record(a, 'attempt'),
                                   w.scalar(), b.scalar()))
        reads = []
        for node in root.get('ns_reads').sequence():
            aid, q, w, r, b = node.sequence()
            reads.append(o._NSRead(aid.scalar(), record(q, 'body'), w.scalar(),
                                  record(r, 'body'), b.scalar()))
        self.families[family.role] = (record(root.get('run'), 'run'), actual,
                                      tuple(chains), tuple(reads))


    def read(self, node):
        if node.tag in ('dict', 'list', 'tuple'):
            return self.values[id(node.packet), node.ref]
        return node.scalar()

    def record(self, family, node, schema):
        result = self.records[(id(node.packet), node.ref), schema]
        gate.require(result._family is family)
        return result


def _mapping(raw, *, typed):
    """No model_dump or foreign RowMapping index operation in live joins."""
    if typed:
        allowed = (policy.Ledger, policy.Slot, policy.ReservationIdentity, policy.Outcome)
        gate.require(any(type(raw) is t for t in allowed))
        kind = type(raw)
        storage = object.__getattribute__(raw, '__dict__')
        fields = type.__getattribute__(kind, '__pydantic_fields__')
        selected = object.__getattribute__(raw, '__pydantic_fields_set__')
        gate.require(type(storage) is dict and type(fields) is dict and type(selected) is set
                     and all(type(k) is str for k in storage)
                     and all(type(k) is str for k in selected)
                     and storage.keys() == fields.keys() and selected <= fields.keys()
                     and object.__getattribute__(raw, '__pydantic_extra__') is None
                     and object.__getattribute__(raw, '__pydantic_private__') is None)
        return storage
    gate.require(type(raw) is dict)
    return raw


def _native_equal(node, raw, *, visible=False, typed=False):
    """Fresh complete domain comparison, never a cached mutable PASS.

    Fixed typed Ledger/Slot and generated JSON/Run inputs only. Native rows are
    compared by their visible business projection, exactly as old _same_native;
    their hidden extent remains in the issued packet and any independent pins.
    Iterator frames + active strong refs avoid broad pending-list allocations;
    completed pair memo prevents shared-DAG unfolding. Cycles never coinduct.
    """
    active, done = set(), {}

    def visit(expected, value, model):
        original, raw_id = value, id(value)
        key = expected.ref, raw_id
        gate.require(raw_id not in active, 'Cyclic native comparison')
        if key in done:
            return True
        tag = expected.tag
        if tag == 'dict':
            if visible and type(value) is RowMapping:
                parent = object.__getattribute__(value, '_parent')
                data = object.__getattribute__(value, '_data')
                index = object.__getattribute__(value, '_key_to_index')
                gate.require((type(parent) is rt._ColdGraphCursorMeta
                              or type(parent) is rt._ColdGraphSimpleMeta)
                             and type(data) is tuple and type(index) is dict)
                names = object.__getattribute__(parent, '_keys')
                gate.require(type(names) is list and all(type(k) is str
                             or type(k) is rt._ColdGraphQuotedName for k in names))
                if len(names) != len(expected.items()):
                    return False
                # No rebuilt lookup, keys list, visible dict or hidden-data copy.
                # Even ignored foreign index entries are iterated without their
                # hash/equality/conversion. Exact string collisions are native.
                for name, position in dict.items(index):
                    if type(name) is str or type(name) is rt._ColdGraphQuotedName:
                        gate.require(type(position) is int and 0 <= position < len(data))
                active.add(raw_id)
                for name, child in expected.items():
                    if sum(k == name for k in names) != 1:
                        return False
                    position = None
                    for key_name, offset in dict.items(index):
                        if (type(key_name) is str or type(key_name) is rt._ColdGraphQuotedName) and key_name == name:
                            position = offset
                    if position is None or not visit(child, data[position], model):
                        return False
                active.remove(raw_id)
                done[key] = original
                return True
            elif model and any(type(value) is t for t in
                               (policy.Ledger, policy.Slot, policy.ReservationIdentity, policy.Outcome)):
                value = _mapping(value, typed=True)
            elif type(value) is not dict:
                return False
            if len(value) != len(expected.items()) or not all(type(k) is str for k in value):
                return False
            active.add(raw_id)
            for name, child in expected.items():
                if name not in value or not visit(child, value[name], model):
                    return False
            active.remove(raw_id)
        elif tag in ('list', 'tuple'):
            if type(value) is not (list if tag == 'list' else tuple):
                return False
            children = expected.sequence()
            if len(value) != len(children):
                return False
            active.add(raw_id)
            for child, item in zip(children, value, strict=True):
                if not visit(child, item, model):
                    return False
            active.remove(raw_id)
        else:
            expected_value = expected.scalar()
            if type(value) is not type(expected_value) or value != expected_value:
                return False
        done[key] = original
        return True

    return visit(node, raw, typed)


class _Frontier:
    """Exact path closure. Independent aliases/roots are still serialized fresh."""

    def __init__(self, mode, raw):
        self.mode, self.graph = mode, mode.graph
        self.raw = raw
        self.complete: Any = None
        self.generation: Any = None
        self.run: Any = None
        self.projected = dict(self.graph.inputs)
        self.replacement, self.gen_replacement = {}, {}
        self.tokens = {}
        for role in ('source', 'generate'):
            packet = mode.scope._issued[mode.inputs['cold-trial:accounted-' + role].handle][1]
            self.tokens[role] = ('owned-accounted-native-continuity.v1', role, packet.digest)
        self.run_token = ('owned-accounted-native-run.v1', self.tokens['generate'])
        self.expected = self.key()

    @staticmethod
    def _refresh(destination, original, excluded):
        gate.require(type(original) is dict and len(destination) == len(original)
                     and all(type(k) is str for k in original))
        for key, value in dict.items(original):
            gate.require(key in destination, 'Frontier keys changed')
            if key not in excluded:
                destination[key] = value

    def values(self):
        graph, values = self.graph, self.projected
        self._refresh(values, graph.inputs, ('cold-trial:accounted-source',
                                            'cold-trial:accounted-generate',
                                            'cold-trial:complete'))
        for role in ('source', 'generate'):
            key = 'cold-trial:accounted-' + role
            gate.require(graph.inputs[key] is self.raw[role])
            values[key] = self.tokens[role]
        if self.complete is not None:
            full = graph.inputs['cold-trial:complete']
            gate.require(full is self.complete and full['source'] is self.raw['source']
                         and full['generated'] is self.raw['generate']
                         and full['generation'] is self.generation
                         and self.generation['run'] is self.run)
            self._refresh(self.replacement, full, ('source', 'generated', 'generation'))
            self._refresh(self.gen_replacement, self.generation, ('run',))
            values['cold-trial:complete'] = self.replacement
        return values

    def key(self):
        return self.graph._frontier_input_key(self.values())

    def check(self):
        gate.require(type(self.mode) is o._OwnedPrewriteMode and self.mode.graph is self.graph
                     and type(self.mode._native) is _NativeCandidate
                     and self.mode._native.graph is self.graph and self.mode._native.mode is self.mode
                     and self.mode._native.frontier is self and self.graph._accounted_frontier is self)
        gate.require(self.mode.active and self.key() == self.expected,
                     'Native mutable frontier changed')

    def added(self, name, *, run_facts=None):
        gate.require(name in self.mode._native.future_roots and name not in self.projected,
                     'Unexpected native continuation root')
        from ._cold_accounted_receipts import _receipt_for_frontier
        receipt = _receipt_for_frontier(self)
        if receipt is not None and name in receipt.names:
            receipt.added(name, run_facts, self.graph.inputs[name])
        self.projected[name] = self.graph.inputs[name]
        if name == 'cold-trial:complete':
            full = self.graph.inputs[name]
            self.complete, self.generation = full, full['generation']
            self.run = self.generation['run']
            self.replacement = dict(full)
            self.gen_replacement = dict(self.generation, run=self.run_token)
            self.replacement['source'] = self.tokens['source']
            self.replacement['generated'] = self.tokens['generate']
            self.replacement['generation'] = self.gen_replacement
        self.expected = self.key()


@dataclass(frozen=True)
class _NativeConfig:
    bounds: object
    limits: object


class _NativeCandidate:
    """Unissued staging at the original two producer positions. No producer here."""

    def __init__(self, graph, config):
        gate.require(type(graph) is rt._ColdGraphRead and type(config) is _NativeConfig and graph.phase == 'pre'
                     and graph.store.test_only and graph.store.sqlite)
        graph.check(graph.store, graph.connection)
        self.graph, self.config = graph, config
        self.completed, self.mode, self.result = {}, None, None
        self.upstreams = None
        self.owned_ready = False
        self.receipt = None
        # Scalar diagnostic state only; never a pin, authority or routing input.
        self.qualification_phase = 'NOT_STARTED'
        self.selection: dict[str, Any] = dict(route='NOT_SELECTED', reason=None, budget=None)
        self.diagnostic_ledger: Any = None
        self.diagnostic_incomplete = False

    def observe(self, *, phase=None, role=None, route=None, error=None, ledger=None):
        """Ordinary observation faults never change routing/cleanup or an error."""
        try:
            if phase is not None:
                self.qualification_phase = phase if role is None else phase + role
            if route is not None:
                self.selection = dict(route=route,
                    reason=error.reason if isinstance(error, _Capacity) else None,
                    error_type=None if error is None else type(error).__name__,
                    budget=self.budget_record(ledger))
        except Exception:
            self.diagnostic_incomplete = True

    def budget_record(self, ledger):
        return dict(resident=ledger.resident, live=ledger.live, peak=ledger.peak,
                    work=ledger.work, active=ledger.active)

    def selection_record(self):
        try:
            result = dict(self.selection, phase=self.qualification_phase)
            if self.diagnostic_ledger is not None:
                result['after_scope'] = self.budget_record(self.diagnostic_ledger)
            result['diagnostic_incomplete'] = self.diagnostic_incomplete
            return result
        except Exception:
            self.diagnostic_incomplete = True
            return dict(route='UNKNOWN', phase='UNKNOWN', reason=None,
                        diagnostic_incomplete=True)

    def stage(self, role, facts):
        self.graph.check(self.graph.store, self.graph.connection)
        gate.require(self.result is None and role == ('source' if not self.completed else 'generate')
                     and role not in self.completed and type(facts) is tuple)
        self.completed[role] = facts

    def choose(self, state, *, upstreams=None, receipt_platform=None):
        gate.require(self.result is None and tuple(self.completed) == ('source', 'generate'))
        ledger = _Ledger(self.config.bounds, self.config.limits)
        self.diagnostic_ledger = ledger
        mode = o._OwnedPrewriteMode(self.graph, self.config.bounds)
        self.mode = mode
        mode._native = self
        self.state = state
        self.upstreams = upstreams
        self.receipt_platform = receipt_platform
        try:
            self.result = mode._select_completed(ledger, self.completed, native=self)
            return self.result
        except BaseException as error:
            try:
                self.observe(route='ERROR', error=error, ledger=ledger)
            finally:
                try:
                    mode.close()
                finally:
                    ledger.close()
            raise

    def qualify(self, mode, packets, ledger):
        self.observe(phase='native:representation')
        if (not all(type(k) is str for k in self.graph.inputs)
                or 'cold-trial:complete' in self.graph.inputs):
            raise _Unsupported('native_root_representation')
        if self.receipt_platform is not None:
            from ._cold_accounted_receipts import _ReceiptClosure
            self.observe(phase='native:receipt-preload')
            ledger.reserve('resident', 4096)
            self.receipt = _ReceiptClosure(self, self.receipt_platform)
            self.receipt.preload(ledger)
            self.observe(phase='native:receipt-budget')
            self.receipt.budget(ledger, _SizingProjection)
        # Ledger is fixed typed and retains its old full dynamic typed guards.
        # Its entire extent, including non-Source slots, must fit before issue.
        self.observe(phase='native:ledger')
        with ledger.snapshot(self.state, typed=True) as state_packet:
            self.ledger_nodes, self.ledger_edges = len(state_packet.nodes), state_packet.edges
            del state_packet
        if self.upstreams is not None:
            gate.require(type(self.upstreams) is tuple and len(self.upstreams) == 2)
            for role, value in zip(('source', 'generate'), self.upstreams, strict=True):
                self.observe(phase='native:upstream:', role=role)
                with ledger.snapshot(value, visible=True) as raw:
                    expected = o._node(packets[role]).get('value').get('run')
                    gate.require(ledger.equal(expected, o._node(raw)), 'Full upstream Run differs')
                    del raw, expected
        ticket = ledger.reserve()
        sizing = copied = header = bound = release = None
        try:
            self.observe(phase='native:frontier-sizing')
            sizing = _SizingProjection(ledger, ticket)
            copied = sizing.copy(self.graph.inputs, typed=True)
            sizing.copy(self.graph.binding.contract, typed=True)
            self.frontier_metrics = dict(nodes=sizing.nodes, edges=sizing.edges,
                                         leaf=sizing.leaf, units=sizing.units)
            # Derive exact lazy Release keys from this same full bounded copy,
            # not by allocating another RowMapping projection or querying early.
            header = copied.get('cold-trial:bound')
            if type(header) is not dict:
                raise _Unsupported('missing_native_bound')
            ledger.reserve('resident', 65536 + 2048 * (len(self.graph.inputs) + len(_FUTURE_ROOTS)
                + 2 + (len(self.receipt.names) if self.receipt is not None else 0)))
            future = set(_FUTURE_ROOTS)
            if self.receipt is not None:
                future.update(self.receipt.names)
            user = self.graph.binding.contract.principal_id
            for role in ('binding', 'source_binding'):
                bound = header.get(role)
                if type(bound) is not dict or type(bound.get('snapshot')) is not dict:
                    raise _Unsupported('native_bound_snapshot')
                release = bound.get('release')
                rid = bound['snapshot'].get('release_id')
                if type(user) is not str or type(rid) is not str or type(release) is not dict:
                    raise _Unsupported('native_release_key')
                gate.require(type(release.get('id')) is str and rid == release['id'],
                             'Native bound Release relation changed')
                ledger.reserve('resident', 256 + 16 * (len(user) + len(rid) + 32))
                ledger.spend(len(user) + len(rid) + 32)
                future.add('release-pointer:' + user + ':' + rid)
            self.future_roots = frozenset(future)
        finally:
            # Drop every data-dependent temporary before refunding its ticket.
            sizing = copied = header = bound = release = None
            ticket.close()
        self.observe(phase='native:arena')
        self.arena = _Arena(ledger, packets)
        # A Slot contains only fixed models and scalar leaves. The conservative
        # full key/value tree is 1+2*5 + (1+2*15) + (1+2*6) = 55 nodes.
        # First boundary: SourceBodies 2 + Archive 2 Slot comparisons, and the
        # resolver receipt + 2 byte tuples. Second: no archive in _recheck.
        # Reserve two independent copies of the first-boundary maximum, also
        # covering the intentionally stronger offline replay control.
        slot_nodes = 1 + 2 * len(o._FIELDS['slot']) + 1 + 2 * len(o._FIELDS['identity']) + 1 + 2 * len(o._FIELDS['outcome'])
        receipt_nodes = 1 + 2 * 18 + 1 + 2 * (1 + 2 * 7) + 2 * 3
        self.text_limit = self.frontier_metrics['leaf'] + sum(len(p.encoded) for p in packets.values()) + 1024
        self.continuation_units = 2 * 1024 * (4 * slot_nodes**2 + receipt_nodes + self.ledger_nodes + 64)
        self.observe(phase='native:continuation-budget')
        ledger.reserve('resident', self.continuation_units)
        ledger.spend(2 * (4 * slot_nodes**2 + receipt_nodes + self.ledger_edges + 64) * (8 * self.text_limit + 64))
        size = sum(len(chain[4]) + len(chain[5]) for chain in self.completed['source'][2])
        # Both Source strict-json/canonical/usage trees overlap with fixed
        # immutable accessor initialization. Prepay both, never reuse a promise.
        self.observe(phase='native:source-budget')
        ledger.reserve('resident', 2 * (1024 * size + 65536))
        ledger.spend(2 * (64 * size + 65536))
        self.raw = {role: self.graph.inputs['cold-trial:accounted-' + role]
                    for role in ('source', 'generate')}
        self.observe(phase='native:classify')
        self.arena.classify(packets)
        ledger._native_arena = self.arena

    def issued(self, mode):
        for role in ('source', 'generate'):
            family = mode.inputs['cold-trial:accounted-' + role]
            self.arena.bind(family)
        for role in ('source', 'generate'):
            family = mode.inputs['cold-trial:accounted-' + role]
            for row in family.actual:
                o._stage_usage(family, row.id)
                self.arena.usage.add((role, row.id))
        for row in self.arena.families['source'][1]:
            family = mode.inputs['cold-trial:accounted-source']
            self.arena.canonicals[row.id] = o._source_exchange_value(family, row.id)
        # Last original full scan BEFORE installing the projected frontier.
        mode._assert_raw_before_owned()
        self.frontier = _Frontier(mode, self.raw)
        self.arena.seal()
        self.graph._accounted_frontier = self.frontier
        if self.receipt is not None:
            self.receipt.phase = 'READY'
        mode._discard_oracle()
        self.completed.clear()

    def release(self):
        arena = getattr(self, 'arena', None)
        if arena is not None:
            arena.release()
        if self.receipt is not None:
            from ._cold_accounted_receipts import _ReceiptClosure
            if (type(self.receipt) is _ReceiptClosure and self.receipt.candidate is self
                    and self.receipt.graph is self.graph):
                self.receipt.release()
        self.receipt = self.receipt_platform = None
        self.completed.clear()

    def close(self):
        if self.mode is not None:
            self.mode.close()
        self.completed.clear()


@contextmanager
def _native_candidate(graph, config):
    candidate = _NativeCandidate(graph, config)
    try:
        yield candidate
        if candidate.mode is not None:
            candidate.mode.assert_current()
    except BaseException:
        candidate.close()
        raise
    else:
        if getattr(graph, '_accounted_frontier', None) is None:
            candidate.close()
        # OWNED resources belong to the ORIGINAL graph scope, not this lexical
        # helper. Its final original check runs before invalidate closes arena.


_RECEIPT_STR = frozenset(('version', 'verification', 'trial_fingerprint',
    'approval_fingerprint', 'source_run_id', 'source_app_id', 'extraction_app_id',
    'extraction_request_key', 'source_proof_fingerprint', 'extraction_recipe_fingerprint',
    'cold_goal_fingerprint'))
_RECEIPT_BOOL = frozenset(('live_allowed', 'dispatch_authorized', 'formal_publication_enabled'))
_RECEIPT_INT = frozenset(('new_model_requests', 'new_reservations', 'project_writes'))
_RECEIPT_FIELDS = _RECEIPT_STR | _RECEIPT_BOOL | _RECEIPT_INT | {'attempts'}
_PROOF_STR = frozenset(('attempt_id', 'request_sha256', 'decoded_body_sha256', 'canonical_ascii_sha256'))
_PROOF_INT = frozenset(('request_bytes', 'decoded_body_bytes', 'canonical_ascii_bytes'))
_PROOF_FIELDS = _PROOF_STR | _PROOF_INT


def _resolved_shape(resolved):
    """All fields of the real resolver's fixed output, before any traversal.

    This is a private producer-output mutation guard, not a new HTTP/SQL limit.
    No string-size cap: unused strings are type-checked without hashing/copying;
    consumed strings compare with bounded owned values (length mismatch is O(1)).
    Unknown fields are rejected, never dropped. The legacy mode is unchanged.
    """
    receipt = resolved.public_receipt
    gate.require(type(receipt) is dict and len(receipt) == 18
                 and all(type(k) is str for k in receipt))
    gate.require(receipt.keys() == _RECEIPT_FIELDS, 'Native resolver output fields changed')
    gate.require(all(type(receipt[k]) is str for k in _RECEIPT_STR)
                 and all(type(receipt[k]) is bool for k in _RECEIPT_BOOL)
                 and all(type(receipt[k]) is int for k in _RECEIPT_INT))
    proofs = receipt['attempts']
    gate.require(type(proofs) is list and len(proofs) == 2)
    for proof in proofs:
        gate.require(type(proof) is dict and len(proof) == 7
                     and all(type(k) is str for k in proof))
        gate.require(proof.keys() == _PROOF_FIELDS, 'Native resolver proof fields changed')
        gate.require(all(type(proof[k]) is str for k in _PROOF_STR)
                     and all(type(proof[k]) is int for k in _PROOF_INT))
    for bodies in (resolved.request_bodies, resolved.response_bodies):
        gate.require(type(bodies) is tuple and len(bodies) == 2
                     and all(type(v) is bytes for v in bodies))


def _native_domain(value):
    """Fresh full representation gate, including unused receipt/proof data.

    Exact native containers only; strong completed memo, cycle/nonfinite gates.
    Producer-fixed receipt + two byte tuples is the native continuation domain.
    This does not accept user-supplied receipt objects as production evidence.
    """
    active, done = set(), {}
    def visit(raw):
        kind, ident = type(raw), id(raw)
        gate.require(ident not in active, 'Cyclic resolved source')
        if ident in done:
            return
        gate.require(any(kind is t for t in (dict, list, tuple, str, bytes, int, float, bool, type(None))),
                     'Unsupported resolved source value')
        if kind is float:
            gate.require(math.isfinite(raw), 'Nonfinite resolved source')
        elif kind is dict:
            gate.require(all(type(k) is str for k in raw), 'Exact resolved keys required')
            active.add(ident)
            for key, item in dict.items(raw):
                visit(key)
                visit(item)
            active.remove(ident)
        elif kind in (list, tuple):
            active.add(ident)
            for item in raw:
                visit(item)
            active.remove(ident)
        done[ident] = raw
    visit(value)


def _archive_native(family, state, resolved):
    """Same full Slot/Identity/Outcome and original bytes; no new packet."""
    _resolved_shape(resolved)
    receipt = resolved.public_receipt
    _native_domain(receipt)
    _native_domain(resolved.request_bodies)
    _native_domain(resolved.response_bodies)
    gate.require(type(receipt) is dict and all(type(k) is str for k in receipt))
    gate.require(type(receipt['attempts']) in (list, tuple)
                 and type(receipt['verification']) is str
                 and type(receipt['source_run_id']) is str
                 and type(resolved.request_bodies) is tuple
                 and type(resolved.response_bodies) is tuple
                 and len(resolved.request_bodies) == len(resolved.response_bodies) == 2
                 and all(type(v) is bytes for v in resolved.request_bodies)
                 and all(type(v) is bytes for v in resolved.response_bodies))
    slots = tuple(s for s in state.slots if s.identity.stage == 'source')
    proofs = receipt['attempts']
    gate.require(state.halted is False and len(slots) == len(proofs) == len(family.chains)
                 == len(family.ns_reads) == 2
                 and receipt['verification'] == 'SPEC_PRODUCTION_CONTROLLER_ARCHIVE'
                 and receipt['live_allowed'] is False and receipt['source_run_id'] == family.run.id)
    for index, (slot, proof) in enumerate(zip(slots, proofs, strict=True)):
        gate.require(type(proof) is dict and all(type(k) is str for k in proof)
                     and type(proof['attempt_id']) is str)
        aid = proof['attempt_id']
        row, chain, _ = o._source_parts(family, aid)
        identity, capture = chain.slot.identity, chain.capture
        gate.require(_native_equal(chain.slot._node, slot, typed=True)
                     and any(o._same(chain.checked, a) for a in family.actual)
                     and row.run_id == identity.run_id == family.run.id
                     and identity.attempt_id == aid
                     and o._scalar_same(identity.wire_sha256, proof['request_sha256'])
                     and o._scalar_same(identity.wire_bytes, proof['request_bytes'])
                     and o._scalar_same(capture.raw_sha256, proof['decoded_body_sha256'])
                     and o._scalar_same(capture.raw_bytes, proof['decoded_body_bytes'])
                     and o._scalar_same(capture.canonical_sha256, proof['canonical_ascii_sha256'])
                     and o._scalar_same(capture.canonical_ascii_bytes, proof['canonical_ascii_bytes'])
                     and resolved.request_bodies[index] == chain.wire
                     and resolved.response_bodies[index] == chain.payload)
