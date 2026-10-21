"""Exact, default-off first-model receipt continuation; never receipt evidence.

The candidate preloads original raw readers in the same SQLite transaction.
This changes their SELECT timing, not their contents or the original receipt
validation. SQL decoding and original full codec checks remain baseline work;
new qualification/copy/continuation administration is logically prepaid.
"""

from typing import Any

from . import natural_live_admission as gate
from . import natural_spec_runtime as rt
from . import natural_specs as natural
from ._cold_accounted_budget import _Unsupported


def _receipt_for_frontier(frontier):
    from ._cold_accounted_native import _Frontier, _NativeCandidate

    gate.require(type(frontier) is _Frontier and type(frontier.mode._native) is _NativeCandidate)
    candidate = frontier.mode._native
    receipt = candidate.receipt
    if receipt is not None:
        gate.require(type(receipt) is _ReceiptClosure and receipt.candidate is candidate
                     and receipt.graph is frontier.graph and candidate.frontier is frontier,
                     'Exact native receipt protocol required')
    return receipt


class _ReceiptClosure:
    def __init__(self, candidate, platform):
        from .app_jobs import _ColdBindingPrefix

        graph = candidate.graph
        gate.require(type(platform) is rt._ColdBindingGraph and platform.guard is graph)
        reader, prefix = platform.counter_reader, platform.binding_prefix
        gate.require(type(reader) is rt._ColdRunFacts and reader.guard is graph
                     and type(prefix) is _ColdBindingPrefix and prefix.guard is graph
                     and prefix.job is reader.job
                     and graph.inputs[prefix.key + ':bound:complete'] is platform.binding)
        reader.check(graph.store, graph.connection, reader.job)
        call = graph.inputs.get('call')
        gate.require(type(call) is dict and type(call.get('meta')) is dict)
        meta = call['meta']
        gate.require(type(meta.get('operation_id')) is str)
        self.candidate, self.graph, self.platform = candidate, graph, platform
        self.reader, self.job, self.binding = reader, reader.job, platform.binding
        self.prefix, self.meta, self.pending = prefix, meta, meta['operation_id']
        self.m = len(reader._receipt_proofs)
        self.phase = 'UNISSUED'
        self.result: Any = None

    def preload(self, ledger):
        """No intent/receipt recreation: original raw methods, at most two ops."""
        plan = self.binding['plan']
        definition = plan['definition']
        steps, actions = definition['manifest']['workflow'], definition['actions']
        if (not natural.is_candidate(definition) or type(steps) is not list
                or type(actions) is not list or len(steps) != len(actions) or len(steps) < 2
                or actions[0]['executor']['ref'] != natural.READ
                or actions[1]['executor']['ref'] not in natural.MODEL_KINDS
                or self.meta.get('step_id') != steps[1]['step_id']
                or type(self.meta.get('ordinal')) is not int or self.meta['ordinal'] != 0
                or self.job['context']['tools'] != 1):
            raise _Unsupported('receipt_prefix')
        # No ORDER BY exists in this original reader. Map just the approved two
        # rows, never infer workflow order from SQL row order or model ordinal.
        rows = self.reader.receipt_operations()
        if len(rows) != 2:
            raise _Unsupported('receipt_operations')
        first = next((op for op in rows if op['call_id'] == steps[0]['step_id']), None)
        pending = next((op for op in rows if op['call_id'] == steps[1]['step_id']), None)
        if (first is None or pending is None or first is pending
                or type(first['id']) is not str or type(pending['id']) is not str
                or first['run_id'] != self.job['id'] or pending['run_id'] != self.job['id']
                or first['status'] != 'VERIFIED' or first['tool_ref'] != natural.READ
                or pending['status'] != 'DISPATCHED' or pending['id'] != self.pending
                or pending['tool_ref'] != actions[1]['executor']['ref']):
            raise _Unsupported('receipt_operation_prefix')
        intent_extent = len(first['id']) + len(pending['id']) + 16
        ledger.reserve('resident', 2048 + 16 * intent_extent)
        ledger.spend(8 * intent_extent)
        self.intent_names = ('intent:' + first['id'], 'intent:' + pending['id'])
        self.reader.intent(first['id'])
        self.reader.intent(pending['id'])
        self.reader.has_effect(first['id'])
        anchors = self.reader.step_anchors(first['id'])
        if (len(anchors) != 1 or type(anchors[0]) is not dict
                or anchors[0].keys() != {'step_id', 'operation_id', 'fence'}
                or anchors[0]['step_id'] != steps[0]['step_id']
                or anchors[0]['operation_id'] != first['id']
                or type(anchors[0]['fence']) is not int
                or not 1 <= anchors[0]['fence'] <= self.job['fence']):
            raise _Unsupported('receipt_anchor_shape')
        self.reader.progress_event('CLAIMED', anchors[0]['fence'])
        self.reader.check(self.graph.store, self.graph.connection, self.job)
        # Pay key copying/hashing before constructing either data-sized string.
        key_extent = 2 * len(self.reader.key) + 128
        ledger.reserve('resident', 2048 + 16 * key_extent)
        ledger.spend(8 * key_extent)
        self.names = (self.reader.key + ':receipt-binding:' + str(self.m),
                      self.reader.key + ':receipts:' + str(self.m))
        gate.require(all(name not in self.graph.inputs for name in self.names),
                     'Receipt continuation cannot rebind an existing root')

    def budget(self, ledger, sizing_type):
        # Complete values consumed by _receipts, not a field-pruned projection.
        # Other binding/raw/job fields stay in the full mutable frontier; the
        # new receipt root aliases binding and does not deepcopy that binding.
        # The bounded copy
        # meters aliases, hidden storage and leaves before allocation. Compute
        # JSON's UNFOLDED DAG extent without unfolding it: fingerprint's JSON
        # encoder revisits aliases, unlike deepcopy. Overflow simply LEGACYs.
        with ledger.projection() as unused:
            ticket = unused.ticket
            p = sizing_type(ledger, ticket)
            prepared = p.copy(dict(plan=self.binding['plan'], source=self.binding['source'],
                operations=self.reader._raw['receipt-operations'],
                intents=tuple(self.reader._raw[name] for name in self.intent_names)), typed=True)
            ledger.reserve('resident', 8192 + 512 * (p.nodes + p.edges))
            # Extent DP is new qualification work, distinct from the later
            # consumer allowance: charge its bounded DAG traversal first.
            ledger.spend(8 * (p.nodes + p.edges + p.leaf + 1)**4)
            memo: dict[int, int] = {}
            ceiling = ledger.limits.resident // 1024

            def extent(value):
                ident = id(value)
                if ident in memo:
                    return memo[ident]
                if type(value) is dict:
                    size = 1 + sum(extent(k) + extent(v) for k, v in value.items())
                elif type(value) in (tuple, list):
                    size = 1 + sum(extent(v) for v in value)
                elif type(value) in (str, bytes, rt._ColdGraphQuotedName):
                    size = 1 + 16 * len(value)  # Includes 12-byte astral JSON escapes.
                else:
                    size = 64 + (value.bit_length() if type(value) is int else 0)
                if size > ceiling:
                    raise _Unsupported('receipt_unfolded_extent')
                memo[ident] = size
                return size

            units = extent(prepared) + sum(len(name) for name in self.names) + 256
            # Two intent resolve/schema/deepcopy/fingerprint passes; one read
            # deepcopy, wanted receipt and all its fingerprint buffers; retained
            # outputs/proved/root values overlap. 1024 logical units per byte/
            # unfolded entry conservatively covers these fixed two-step copies.
            ledger.reserve('resident', 65536 + 1024 * units)
            ledger.spend(8 * (units + 1)**4)
            memo.clear()
            del prepared, p

    def begin(self, store, c, job, binding, reader, pending_id, allow_pending):
        graph = self.graph
        gate.require(store is graph.store and c is graph.connection and job is self.job
                     and reader is self.reader and reader.guard is graph
                     and self.platform.guard is graph and self.platform.counter_reader is reader
                     and self.platform.binding is self.binding and binding is self.binding
                     and self.platform.binding_prefix is self.prefix
                     and graph.inputs[self.prefix.key + ':bound:complete'] is binding
                     and graph.inputs['call']['meta'] is self.meta
                     and type(pending_id) is str
                     and pending_id == self.pending == self.meta['operation_id']
                     and allow_pending is False and self.phase == 'READY'
                     and len(reader._receipt_proofs) == self.m,
                     'Exact native receipt continuation required')
        reader.check(store, c, job)
        self.phase = 'BEGIN'

    def produced(self, result):
        gate.require(self.phase == 'BOUND' and type(result) is tuple and len(result) == 2
                     and type(result[0]) is dict and type(result[1]) is list
                     and len(self.reader._receipt_proofs) == self.m)
        self.result, self.phase = result, 'RESULT'

    def added(self, name, reader, value):
        gate.require(reader is self.reader and reader.guard is self.graph
                     and reader.job is self.job and reader.connection is self.graph.connection
                     and reader.store is self.graph.store
                     and len(reader._receipt_proofs) == self.m,
                     'Foreign native receipt root')
        if name == self.names[0]:
            gate.require(self.phase == 'BEGIN' and value is self.binding,
                         'Exact native receipt binding required')
            self.phase = 'BOUND'
        else:
            gate.require(name == self.names[1] and self.phase == 'RESULT'
                         and type(value) is dict
                         and value.keys() == {'binding', 'outputs', 'proved', 'pending_id', 'allow_pending'}
                         and value['binding'] is self.binding
                         and value['outputs'] is self.result[0] and value['proved'] is self.result[1]
                         and value['pending_id'] == self.pending and value['allow_pending'] is False,
                         'Exact native receipt result required')
            self.phase = 'RECORDED'

    def finish(self):
        gate.require(self.phase == 'RECORDED' and len(self.reader._receipt_proofs) == self.m + 1
                     and self.reader._receipt_proofs[-1] == 'receipts:' + str(self.m))
        self.phase = 'DONE'

    def release(self):
        self.result = None
        self.phase = 'CLOSED'
