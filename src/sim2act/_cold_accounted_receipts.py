"""Exact bounded READ/one-or-two-MODEL continuation; never receipt evidence.

The candidate preloads original raw readers in the same SQLite transaction.
This changes their SELECT timing, not their contents or the original receipt
validation. SQL decoding and original full codec checks remain baseline work;
new qualification/copy/continuation administration is logically prepaid.
"""

import sys
from typing import Any

from . import natural_live_admission as gate
from . import natural_spec_runtime as rt
from . import natural_specs as natural


def _receipt_for_frontier(frontier):
    from ._cold_accounted_native import _Frontier, _NativeCandidate

    gate.require(type(frontier) is _Frontier and type(frontier.mode._native) is _NativeCandidate)
    candidate = frontier.mode._native
    receipt = candidate.receipt
    if receipt is not None:
        gate.require(type(receipt) is _ReceiptClosure and receipt.candidate is candidate
                     and receipt.graph is frontier.graph and candidate.frontier is frontier,
                     'Exact native receipt protocol required')
        gate.require(not any(name in vars(receipt) for name in (
            'preload','budget','_budget_admin','_publish_admin','_preload_verified_model','begin','produced','added',
            '_node_added','finish','release'))
            and type(receipt.reader) is rt._ColdRunFacts
            and not any(name in vars(receipt.reader) for name in (
                'check','_get','_put','_present','_read_loaded','produced_value',
                'node_proof','record_node_proof','receipt_operations','intent',
                'pin_receipt_binding','record_receipts','checked_counters',
                'canonical_counter_manifest','pin_manifest','record_counters',
                'attempt_rows','association','mode','model_reserved','anchor_ids',
                'reservation','anchor_rows','model_operations','has_effect',
                'step_anchors','progress_event')),
            'Receipt methods cannot be replaced on an instance')
        gate.require(type(receipt.ordinal) is int and receipt.ordinal in (0,1)
            and type(receipt.m) is int and receipt.m>=0
            and type(receipt.phase) is str and type(receipt.names) is tuple
            and len(receipt.names)==(2 if receipt.ordinal==0 else 4)
            and all(type(name) is str for name in receipt.names),
            'Receipt protocol metadata changed')
    return receipt


def _receipt_phase_same(actual, outputs, proved, pending, max_nodes, max_edges):
    """Exact independent deepcopy domain; no hash or remembered PASS.

    Original deepcopy retains exact immutable scalar objects. Match both ways
    for containers, including order and sharing, without following an unknown
    subtree when its corresponding original shape/length already differs.
    """
    expected=dict(pending_id=pending,allow_pending=False,index=1,outputs=outputs,proved=proved)
    forward,reverse={},{}
    visited=edges=0
    def same(left,right):
        nonlocal visited,edges
        visited+=1
        if visited>max_nodes:return False
        kind=type(right)
        if type(left) is not kind:return False
        if kind not in (dict,list,tuple):return left is right
        if kind in (dict,list) and left is right:return False
        if len(left)!=len(right):return False
        key=id(right)
        if key in forward:return forward[key][0] is left
        if id(left) in reverse:return False
        edges+=len(right)
        if edges>max_edges:return False
        forward[key]=left,right;reverse[id(left)]=right
        if kind is dict:
            return all(lk is rk and same(lv,rv)
                for (lk,lv),(rk,rv) in zip(left.items(),right.items(),strict=True))
        return all(same(lv,rv) for lv,rv in zip(left,right,strict=True))
    return same(actual,expected)


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
        self.node_inputs = None
        self.node_value = None

    def preload(self, ledger):
        """Original readers only; no proof/intent/receipt is recreated here."""
        from ._cold_accounted_budget import _Unsupported
        plan = self.binding['plan']
        definition = plan['definition']
        steps, actions = definition['manifest']['workflow'], definition['actions']
        ordinal = self.meta.get('ordinal')
        if (not natural.is_candidate(definition)
                or not (type(steps) is list or rt._source_owned_code.image.is_kind(steps,'l'))
                or not (type(actions) is list or rt._source_owned_code.image.is_kind(actions,'l'))
                or len(steps) != len(actions)
                or type(ordinal) is not int or ordinal not in (0, 1)
                or len(steps) < ordinal + 2
                or actions[0]['executor']['ref'] != natural.READ
                or any(actions[i]['executor']['ref'] not in natural.MODEL_KINDS
                    for i in range(1, ordinal + 2))
                or self.meta.get('step_id') != steps[ordinal + 1]['step_id']
                or self.reader._source_owned is not False
                or self.job['context']['tools'] != 1):
            raise _Unsupported('receipt_prefix')
        self.ordinal = ordinal
        # No ORDER BY exists. Map only the closed workflow prefix, never infer
        # dependency order from operation ID, SQL order or model ordinal alone.
        rows = self.reader.receipt_operations()
        if len(rows) != ordinal + 2:
            raise _Unsupported('receipt_operations')
        ordered = tuple(next((op for op in rows if op['call_id'] == steps[i]['step_id']), None)
                        for i in range(ordinal + 2))
        if (any(op is None or type(op['id']) is not str
                or op['run_id'] != self.job['id']
                or op['tool_ref'] != actions[i]['executor']['ref']
                or op['status'] != ('DISPATCHED' if i == ordinal + 1 else 'VERIFIED')
                for i, op in enumerate(ordered))
                or len({op['id'] for op in ordered}) != ordinal + 2
                or ordered[-1]['id'] != self.pending):
            raise _Unsupported('receipt_operation_prefix')
        self.operations = ordered
        intent_extent = sum(len(op['id']) for op in ordered) + 32
        ledger.reserve('resident', 2048 + 16 * intent_extent)
        ledger.spend(8 * intent_extent)
        self.intent_names = tuple('intent:' + op['id'] for op in ordered)
        for op in ordered:
            self.reader.intent(op['id'])
        for i, op in enumerate(ordered[:-1]):
            self.reader.has_effect(op['id'])
            anchors = self.reader.step_anchors(op['id'])
            if (len(anchors) != 1 or type(anchors[0]) is not dict
                    or anchors[0].keys() != {'step_id', 'operation_id', 'fence'}
                    or anchors[0]['step_id'] != steps[i]['step_id']
                    or anchors[0]['operation_id'] != op['id']
                    or type(anchors[0]['fence']) is not int
                    or not 1 <= anchors[0]['fence'] <= self.job['fence']):
                raise _Unsupported('receipt_anchor_shape')
            self.reader.progress_event('CLAIMED', anchors[0]['fence'])
        if ordinal == 1:
            _ReceiptClosure._preload_verified_model(self)
        self.reader.check(self.graph.store, self.graph.connection, self.job)
        # Pay key copying/hashing before constructing either data-sized string.
        key_extent = (2 * len(self.reader.key) + 256 if ordinal == 0
            else 12 * len(self.reader.key) + 1024)
        ledger.reserve('resident', 2048 + 16 * key_extent)
        ledger.spend(8 * key_extent)
        self.binding_name = self.reader.key + ':receipt-binding:' + str(self.m)
        self.result_name = self.reader.key + ':receipts:' + str(self.m)
        self.names = (self.binding_name, self.result_name)
        if ordinal == 1:
            # pin_receipt_binding adds exactly one raw entry before node_proof.
            # Neither raw nor proof registry is updated early by this protocol.
            self.node_input_key = 'node-input:verified:' + str(len(self.reader._raw) + 1)
            self.node_proof_key = 'node-proof:verified:0'
            self.names = (self.binding_name, self.reader.key + ':' + self.node_input_key,
                          self.reader.key + ':' + self.node_proof_key, self.result_name)
        gate.require(all(name not in self.graph.inputs for name in self.names),
                     'Receipt continuation cannot rebind an existing root')

    def _preload_verified_model(self):
        """Preload every original counter/node reader, not its validation."""
        from ._cold_accounted_budget import _Unsupported
        if self.reader._node_proofs:
            raise _Unsupported('receipt_prior_node_proof')
        rows = self.reader.attempt_rows()
        if (type(rows) is not list or len(rows) != 2
                or any(type(row) is not dict or type(row.get('parameters')) is not dict
                    or type(row['parameters'].get('natural_spec')) is not dict
                    for row in rows)):
            raise _Unsupported('receipt_model_attempts')
        selected = []
        for ordinal, op in enumerate(self.operations[1:]):
            matching = [row for row in rows
                if row['parameters'].get('natural_spec', {}).get('operation_id') == op['id']]
            if (len(matching) != 1 or matching[0]['run_id'] != self.job['id']
                    or matching[0]['status'] != ('VERIFIED' if ordinal == 0 else 'RECEIVED')
                    or type(matching[0]['id']) is not str
                    or matching[0]['parameters']['natural_spec'].get('ordinal') != ordinal
                    or type(matching[0]['parameters']['natural_spec'].get('ordinal')) is not int
                    or matching[0]['parameters']['natural_spec'].get('step_id') != op['call_id']):
                raise _Unsupported('receipt_model_attempt_prefix')
            selected.append(matching[0])
        self.model_attempt = selected[0]
        from .natural_trial_runs import MARKER
        if MARKER in self.job['context']:
            self.reader.association()
        self.reader.model_reserved()
        for kind in ('NS_RESERVED', 'NS_RECEIVED', 'NS_SETTLED', 'NS_REJECTED'):
            self.reader.anchor_ids(kind)
        self.reader.mode()
        for row in rows:
            self.reader.reservation(row['id'])
            self.reader.anchor_rows('NS_RESERVED', row['id'])
        self.reader.model_operations()
        self.reader.anchor_rows('NS_SETTLED', self.model_attempt['id'])
        self.reader.anchor_rows('NS_RECEIVED', self.model_attempt['id'])

    def budget(self, ledger, sizing_type):
        from ._cold_accounted_budget import _Unsupported
        if self.ordinal == 1:
            return _ReceiptClosure._budget_admin(self,ledger,sizing_type)
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
            value = dict(plan=self.binding['plan'], source=self.binding['source'],
                operations=self.reader._raw['receipt-operations'],
                intents=tuple(self.reader._raw[name] for name in self.intent_names))
            if self.ordinal == 1:
                value.update(job=self.job, draft=self.binding['draft'],
                    human_correction=self.binding.get('human_correction'), raw=self.reader._raw)
            prepared = p.copy(value, typed=True)
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
            del prepared, p, value

    def _budget_admin(self,ledger,sizing_type):
        """New protocol administration only, not the original codec/SQL work.

        No model-value/JSON/parser consumer is replaced or copied by this
        protocol. Its original raw/proof/phase roots already live in the reader
        until scope exit. Full mutable/hidden-input sizing still follows in
        NativeCandidate.qualify. The additional phase comparison visits only
        an independent READ-output/receipt deepcopy domain, without copying
        strings or unfolding shared subtrees. Never estimate that domain from
        a Source View pin: these inputs are original plain SQL JSON values.
        """
        from ._cold_accounted_budget import _Projection
        p=prepared=value=None
        with ledger.projection() as unused:
            try:
                # The base projection rejects Views/Rows/models in this JSON
                # prefix; a hidden owner pin is not a visible phase size bound.
                p=_Projection(ledger,unused.ticket)
                value=dict(receipt=self.operations[0]['receipt'],
                    intent=self.reader._raw[self.intent_names[0]])
                prepared=p.copy(value,typed=False)
                # Includes fixed wanted-receipt/wrapper additions and repeated
                # edges. Both maps/frames remain prepaid until scope close.
                n=4*(p.nodes+p.edges+64);e=8*(p.nodes+p.edges+64)
                ledger.reserve('resident',65536+1024*(n+e+64))
                ledger.spend(8*(n+e+64)**4)
                self.phase_limits=(n,e)
            finally:
                # Clear our private projections before their ticket is closed.
                # A copy exception unwinds the whole unissued candidate; it
                # does not reuse/refund this ledger to issue another mode.
                prepared=p=value=None
        _ReceiptClosure._publish_admin(self,ledger,sizing_type)

    def _publish_admin(self,ledger,sizing_type):
        # This NEW root publication executes complete guard/encoding calls.
        # Meter the actual COMPLETE graph+contract first, independently of the
        # READ-only alias bound. Prepay three independent conservative encoder
        # envelopes using the existing Projection.encoded_upper formula; do
        # not assume a configured ceiling implies this graph fits it.
        from ._cold_accounted_budget import _Capacity
        p=prepared=value=None;buffers=None
        with ledger.projection() as unused:
            try:
                p=sizing_type(ledger,unused.ticket)
                b=self.graph.binding
                value=dict(inputs=self.graph.inputs,role_limits=self.graph.role_limits,
                    phase=self.graph.phase,binding=dict(contract=b.contract,key=b.approval_key,
                        account=b.account_id,version=b.version,fingerprint=b.contract_fingerprint))
                prepared=p.copy(value,typed=True)
                upper=p.encoded_upper()+65536
                if upper>ledger.bounds.encoded_bytes:
                    raise _Capacity('receipt_admin_encoded')
                buffers=ledger.reserve(units=3*(p.units+9*upper+256*(p.nodes+p.edges+1)))
                ledger.spend(24*(p.nodes+p.edges+p.leaf+65536)**4)
                # Metadata is pinned into the SAME full graph before issuance. Its
                # immutable tuple cannot be enlarged via mutable closure fields.
                self.admin_name=self.reader.key+':receipt-admin:'+str(self.m)
                self.reader._put('receipt-admin:'+str(self.m),self.phase_limits)
            finally:
                prepared=value=p=None
                if buffers is not None:buffers.close()
        # Metadata is pinned into the SAME full graph before issuance. Its
        # immutable tuple cannot be enlarged via mutable closure attributes.
        self.node_input_key='node-input:verified:'+str(len(self.reader._raw)+1)
        self.names=(self.binding_name,self.reader.key+':'+self.node_input_key,
                    self.reader.key+':'+self.node_proof_key,self.result_name)
        gate.require(all(name not in self.graph.inputs for name in self.names),
            'Receipt continuation cannot rebind an existing root')

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
        if self.ordinal == 1:
            gate.require(type(self.admin_name) is str
                and self.admin_name == self.reader.key+':receipt-admin:'+str(self.m)
                and self.graph.inputs[self.admin_name] is self.phase_limits,
                'Receipt phase budget changed')
        self.phase = 'BEGIN'

    def produced(self, result):
        gate.require(self.phase == ('BOUND' if self.ordinal == 0 else 'NODE_PROVED')
                     and type(result) is tuple and len(result) == 2
                     and type(result[0]) is dict and type(result[1]) is list
                     and len(self.reader._receipt_proofs) == self.m)
        self.result, self.phase = result, 'RESULT'

    def added(self, name, reader, value):
        gate.require(reader is self.reader and reader.guard is self.graph
                     and reader.job is self.job and reader.connection is self.graph.connection
                     and reader.store is self.graph.store
                     and len(reader._receipt_proofs) == self.m,
                     'Foreign native receipt root')
        if name == self.binding_name:
            gate.require(self.phase == 'BEGIN' and value is self.binding,
                         'Exact native receipt binding required')
            self.phase = 'BOUND'
        elif self.ordinal == 1 and name in self.names[1:3]:
            _ReceiptClosure._node_added(self, name, reader, value)
        else:
            gate.require(name == self.result_name and self.phase == 'RESULT'
                         and type(value) is dict
                         and value.keys() == {'binding', 'outputs', 'proved', 'pending_id', 'allow_pending'}
                         and value['binding'] is self.binding
                         and value['outputs'] is self.result[0] and value['proved'] is self.result[1]
                         and value['pending_id'] == self.pending and value['allow_pending'] is False,
                         'Exact native receipt result required')
            self.phase = 'RECORDED'

    def _node_added(self, name, reader, value, _getframe=sys._getframe):
        # Only original node_proof/record_node_proof inside the complete
        # original _prove_node may publish these exact names. An injected
        # callback cannot plant a memo HIT or fabricate a proof for this scope.
        from . import pa_spec_apps as spec
        frame = _getframe(1)
        expected = (self.added.__func__.__code__, self.candidate.frontier.added.__func__.__code__,
            rt._ColdGraphRead.add.__code__, rt._ColdRunFacts._put.__code__)
        for code in expected:
            gate.require(frame.f_code is code, 'Original receipt publication stack required')
            frame = frame.f_back
        producer = frame
        wanted = rt._ColdRunFacts.node_proof if name == self.names[1] else rt._ColdRunFacts.record_node_proof
        gate.require(producer.f_code is wanted.__code__ and producer.f_locals['self'] is reader
            and producer.f_locals['kind'] == 'verified', 'Original verified node producer required')
        frame = producer.f_back
        receipt_frame = None
        for function in (rt._prove_node, rt._prove_node_from_facts, spec._receipts, spec._cold_receipts):
            gate.require(frame.f_code is function.__code__, 'Original complete node verification required')
            if function is spec._receipts:receipt_frame=frame
            frame = frame.f_back
        node = producer.f_back
        gate.require(node.f_locals['job'] is self.job and node.f_locals['binding'] is self.binding
            and node.f_locals['op'] is self.operations[1]
            and node.f_locals['a'] is self.model_attempt
            and node.f_locals['_facts'] is reader,
            'Original verified model inputs required')
        if name == self.names[1]:
            gate.require(type(self.admin_name) is str
                and self.admin_name == self.reader.key+':receipt-admin:'+str(self.m),
                'Original receipt phase budget key required')
            limits=self.graph.inputs[self.admin_name]
            gate.require(self.phase == 'BOUND' and type(value) is dict
                and limits is self.phase_limits and type(limits) is tuple and len(limits)==2
                and all(type(n) is int and n>0 for n in limits)
                and value is producer.f_locals['inputs'] is node.f_locals['node_inputs']
                and value.keys() == {'run','plan','draft','source','human_correction','operation',
                    'intent','action','attempt','meta','node_limits','receipt_phase'}
                and value['run'] is self.job and value['plan'] is self.binding['plan']
                and value['draft'] is self.binding['draft'] and value['source'] is self.binding['source']
                and value['human_correction'] is self.binding.get('human_correction')
                and value['operation'] is self.operations[1] and value['attempt'] is self.model_attempt
                and value['intent'] is node.f_locals['intent']
                and value['action'] is node.f_locals['action']
                and rt._source_owned_code.image.same(value['action'],self.binding['plan']['definition']['actions'][1])
                and value['meta'] is self.model_attempt['parameters']['natural_spec']
                and value['node_limits'] is value['meta'].get('limits')
                and type(value['receipt_phase']) is dict
                and type(receipt_frame.f_locals['pending_id']) is str
                and receipt_frame.f_locals['pending_id'] == self.pending
                and receipt_frame.f_locals['allow_pending'] is False
                and _receipt_phase_same(value['receipt_phase'],receipt_frame.f_locals['outputs'],
                    receipt_frame.f_locals['proved'],receipt_frame.f_locals['pending_id'],*limits),
                'Complete original verified node input required')
            self.node_inputs, self.phase = value, 'NODE_INPUT'
        else:
            gate.require(self.phase == 'NODE_INPUT' and type(value) is dict
                and value.keys() == {'inputs_key','value'} and value['inputs_key'] == self.node_input_key
                and producer.f_locals['inputs'] is self.node_inputs
                and producer.f_locals['inputs_key'] == self.node_input_key
                and value['value'] is producer.f_locals['value'] is node.f_locals['expected']
                and node.f_locals['inputs_key'] == self.node_input_key,
                'Original completed verified node proof required')
            self.node_value, self.phase = value['value'], 'NODE_PROVED'

    def finish(self):
        gate.require(self.phase == 'RECORDED' and len(self.reader._receipt_proofs) == self.m + 1
                     and self.reader._receipt_proofs[-1] == 'receipts:' + str(self.m))
        if self.ordinal == 1:
            gate.require(self.reader._node_proofs == [self.node_proof_key]
                and self.reader._raw[self.node_input_key] is self.node_inputs
                and self.reader._raw[self.node_proof_key]['value'] is self.node_value,
                'Original node registry publication incomplete')
        self.phase = 'DONE'

    def release(self):
        self.result = None
        self.node_inputs = self.node_value = None
        self.phase = 'CLOSED'
