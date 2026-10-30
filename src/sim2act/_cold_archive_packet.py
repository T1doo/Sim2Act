"""Owned post-resolver data, not an authorization or remembered validation.

The graph stores an exact tuple of metadata bytes and original immutable leaves.
Metadata retains container tags, order and the complete alias graph. Carrying
all str/bytes leaves separately retains their aliases with the unconverted graph.
No mutable producer object or model is retained; consumers never thaw a dict.
"""
from .errors import DomainError

TAG = 'cold-owned-resolved-archive.v1'
KEY = 'cold-trial:owned-resolved-archive'
_MAX_NODES, _MAX_EDGES, _MAX_WIRE, _MAX_LEAVES = 1024, 4096, 131072, 16 * 1024 * 1024
_RECEIPT_STR = frozenset(('version', 'verification', 'trial_fingerprint',
    'approval_fingerprint', 'source_run_id', 'source_app_id', 'extraction_app_id',
    'extraction_request_key', 'source_proof_fingerprint', 'extraction_recipe_fingerprint',
    'cold_goal_fingerprint'))
_RECEIPT_BOOL = frozenset(('live_allowed', 'dispatch_authorized', 'formal_publication_enabled'))
_RECEIPT_INT = frozenset(('new_model_requests', 'new_reservations', 'project_writes'))
_PROOF_STR = frozenset(('attempt_id', 'request_sha256', 'decoded_body_sha256', 'canonical_ascii_sha256'))
_PROOF_INT = frozenset(('request_bytes', 'decoded_body_bytes', 'canonical_ascii_bytes'))

class Capacity(ValueError):
    """Before publication only: retain the original complete resolver route."""


def require(ok):
    if not ok:
        raise DomainError('VERSION_CONFLICT', 'Owned resolved archive changed')


def is_packet(value):
    return type(value) is tuple and len(value) == 3 and type(value[0]) is str and value[0] == TAG


def reject_experiment(value):
    # The old resolver product is a dataclass, never an exact tuple. Do not
    # invoke an unknown classifier before refusing the new representation.
    require(type(value) is not tuple)


def _shape(receipt, requests, responses):
    require(type(receipt) is dict and all(type(k) is str for k in receipt)
        and receipt.keys() == _RECEIPT_STR | _RECEIPT_BOOL | _RECEIPT_INT | {'attempts'})
    require(all(type(receipt[k]) is str for k in _RECEIPT_STR)
        and all(type(receipt[k]) is bool for k in _RECEIPT_BOOL)
        and all(type(receipt[k]) is int for k in _RECEIPT_INT))
    proofs = receipt['attempts']
    require(type(proofs) is list and len(proofs) == 2)
    for proof in proofs:
        require(type(proof) is dict and all(type(k) is str for k in proof)
            and proof.keys() == _PROOF_STR | _PROOF_INT)
        require(all(type(proof[k]) is str for k in _PROOF_STR)
            and all(type(proof[k]) is int for k in _PROOF_INT))
    require(type(requests) is tuple and type(responses) is tuple
        and len(requests) == len(responses) == 2
        and all(type(v) is bytes for v in requests + responses))


def capture(receipt, requests, responses):
    """One bounded producer handoff; original mutable aliases are discarded."""
    current(_CONFIG)
    _shape(receipt, requests, responses)
    nodes, leaves, held, memo, active = [], [], [], {}, set()
    edges = size = 0
    def visit(value, depth=0):
        nonlocal edges, size
        if depth > 64 or len(nodes) >= _MAX_NODES:
            raise Capacity('archive nodes/depth')
        kind = type(value)
        require(kind in (dict, list, tuple, str, bytes, int, bool))
        identity = id(value)
        require(identity not in active)
        # Match the graph codec: integers/bools are values, not memoized objects.
        if kind not in (int, bool) and identity in memo:
            return memo[identity]
        ref = len(nodes); nodes.append(None)
        if kind not in (int, bool):
            memo[identity] = ref; held.append(value)
        active.add(identity)
        def child(v):
            nonlocal edges
            edges += 1
            if edges > _MAX_EDGES:
                raise Capacity('archive edges')
            return visit(v, depth + 1)
        if kind is str or kind is bytes:
            size += len(value) * (4 if kind is str else 1)
            if size > _MAX_LEAVES:
                raise Capacity('archive leaves')
            data = ('str' if kind is str else 'bytes', len(leaves)); leaves.append(value)
        elif kind is int:
            # Original graph native admission has signed-64 support; unknown
            # larger counters retain the unchanged original resolver route.
            if not -(1 << 63) <= value < (1 << 63):
                raise Capacity('archive integer')
            data = ('int', value)
        elif kind is bool:
            data = ('bool', value)
        elif kind is dict:
            data = ('dict', tuple((child(k), child(v)) for k,v in dict.items(value)))
        else:
            data = ('list' if kind is list else 'tuple', tuple(child(v) for v in value))
        nodes[ref] = data; active.remove(identity)
        return ref
    root = visit((receipt, requests, responses))
    # Fixed bounded binary metadata, not JSON/pickle or a callback codec.
    # Only immutable str/bytes leaves cross this representation as originals.
    wire = bytearray(b'S2A\x01')
    wire.extend(len(nodes).to_bytes(2, 'little')); wire.extend(root.to_bytes(2, 'little'))
    for tag, value in nodes:
        if tag in ('str', 'bytes'):
            wire.extend(b's' if tag == 'str' else b'b'); wire.extend(value.to_bytes(2, 'little'))
        elif tag == 'int':
            wire.extend(b'i'); wire.extend(value.to_bytes(8, 'little', signed=True))
        elif tag == 'bool':
            wire.extend(b't' if value else b'f')
        else:
            wire.extend({'dict': b'd', 'list': b'l', 'tuple': b'q'}[tag])
            wire.extend(len(value).to_bytes(2, 'little'))
            refs = tuple(v for pair in value for v in pair) if tag == 'dict' else value
            for ref in refs:wire.extend(ref.to_bytes(2, 'little'))
    if len(wire) > _MAX_WIRE:
        raise Capacity('archive metadata')
    wire = bytes(wire)
    return (TAG, wire, tuple(leaves))


class _View(tuple):
    """Invocation-local read-only node; never enters a graph or dispatch API."""
    __slots__ = ()
    def _body(self):
        return tuple.__getitem__(self, 0)[tuple.__getitem__(self, 2)]
    def __getitem__(self, key):
        nodes, leaves, ref = tuple.__iter__(self)
        tag, data = nodes[ref]
        if tag == 'dict':
            require(type(key) is str)
            for k,v in data:
                if _read(nodes, leaves, k) == key:
                    return _read(nodes, leaves, v)
            raise KeyError(key)
        require(tag in ('tuple', 'list') and type(key) is int)
        return _read(nodes, leaves, data[key])
    def __iter__(self):
        nodes, leaves, ref = tuple.__iter__(self)
        tag, data = nodes[ref]
        return iter(tuple(_read(nodes, leaves, k) for k in
            (tuple(k for k,_ in data) if tag == 'dict' else data)))
    def __len__(self):
        return len(self._body()[1])
    def index(self, value):
        for index, child in enumerate(self):
            if child == value:
                return index
        raise ValueError('archive value not in sequence')
    def __eq__(self, other):
        if type(other) is not _View:
            return False
        # Nodes come from the same immutable packet; preserve Python dict/list
        # value comparison (not alias equality) for the original proof.index().
        a, b = self._body(), other._body()
        if a[0] != b[0] or len(a[1]) != len(b[1]):
            return False
        if a[0] == 'dict':
            return all(k in tuple(other) and self[k] == other[k] for k in self)
        return all(x == y for x,y in zip(self, other, strict=True))
    def __ne__(self, other):
        return not self == other


def _read(nodes, leaves, ref):
    tag, value = nodes[ref]
    if tag in ('str', 'bytes'):
        return leaves[value]
    if tag == 'int':
        return value
    if tag == 'bool':
        return value
    return tuple.__new__(_View, (nodes, leaves, ref))


def read(packet):
    """Decode metadata once per consumer, never once per graph guard/pin."""
    current(_CONFIG)
    require(is_packet(packet) and type(packet[1]) is bytes and len(packet[1]) <= _MAX_WIRE
        and type(packet[2]) is tuple and len(packet[2]) <= _MAX_NODES)
    require(all(type(v) is str or type(v) is bytes for v in packet[2]))
    require(sum(len(v) * (4 if type(v) is str else 1) for v in packet[2]) <= _MAX_LEAVES)
    try:
        wire = packet[1]; position = 4
        require(wire[:4] == b'S2A\x01')
        def take(size):
            nonlocal position
            require(position + size <= len(wire))
            result = wire[position:position + size]; position += size
            return result
        count = int.from_bytes(take(2), 'little'); root = int.from_bytes(take(2), 'little')
        require(0 < count <= _MAX_NODES and 0 <= root < count)
        nodes = []; edge_count = 0
        for _ in range(count):
            tag = take(1)
            if tag in (b's', b'b'):
                value = int.from_bytes(take(2), 'little')
                require(value < len(packet[2]) and type(packet[2][value]) is (str if tag == b's' else bytes))
                tag = 'str' if tag == b's' else 'bytes'
            elif tag == b'i':
                tag, value = 'int', int.from_bytes(take(8), 'little', signed=True)
            elif tag in (b't', b'f'):
                tag, value = 'bool', tag == b't'
            else:
                require(tag in (b'd', b'l', b'q'))
                length = int.from_bytes(take(2), 'little')
                edge_count += length * (2 if tag == b'd' else 1)
                require(edge_count <= _MAX_EDGES)
                if tag == b'd':
                    value = tuple((int.from_bytes(take(2), 'little'), int.from_bytes(take(2), 'little')) for _ in range(length))
                else:
                    value = tuple(int.from_bytes(take(2), 'little') for _ in range(length))
                tag = {b'd': 'dict', b'l': 'list', b'q': 'tuple'}[tag]
            nodes.append((tag, value))
        require(position == len(wire))
        nodes = tuple(nodes)
        declared = tuple(value for tag,value in nodes if tag in ('str', 'bytes'))
        require(len(declared) == len(packet[2]) and set(declared) == set(range(len(packet[2])))
            and len({id(v) for v in packet[2]}) == len(packet[2]))
        active, done = set(), set(); edges = 0
        def check(ref, depth=0):
            nonlocal edges
            require(type(ref) is int and 0 <= ref < len(nodes) and depth <= 64 and ref not in active)
            if ref in done:return
            active.add(ref);tag, value = nodes[ref]
            refs = tuple(x for pair in value for x in pair) if tag == 'dict' else value if tag in ('list','tuple') else ()
            edges += len(refs); require(edges <= _MAX_EDGES)
            for child in refs:check(child, depth + 1)
            if tag == 'dict':
                keys = tuple(_read(nodes, packet[2], k) for k,_ in value)
                require(all(type(k) is str for k in keys) and len(set(keys)) == len(keys))
            active.remove(ref);done.add(ref)
        check(root);require(len(done) == len(nodes))
        result = _read(nodes, packet[2], root)
        _view_shape(result)
        return result
    except (ValueError, TypeError, RecursionError, OverflowError, IndexError) as error:
        raise DomainError('VERSION_CONFLICT', 'Invalid owned archive metadata') from error


def _view_shape(root):
    require(type(root) is _View and root._body()[0] == 'tuple' and len(root) == 3)
    receipt, requests, responses = root
    require(type(receipt) is _View and receipt._body()[0] == 'dict'
        and set(receipt) == _RECEIPT_STR | _RECEIPT_BOOL | _RECEIPT_INT | {'attempts'})
    require(all(type(receipt[k]) is str for k in _RECEIPT_STR)
        and all(type(receipt[k]) is bool for k in _RECEIPT_BOOL)
        and all(type(receipt[k]) is int for k in _RECEIPT_INT))
    proofs = receipt['attempts']
    require(type(proofs) is _View and proofs._body()[0] == 'list' and len(proofs) == 2)
    for proof in proofs:
        require(type(proof) is _View and proof._body()[0] == 'dict'
            and set(proof) == _PROOF_STR | _PROOF_INT)
        require(all(type(proof[k]) is str for k in _PROOF_STR)
            and all(type(proof[k]) is int for k in _PROOF_INT))
    for bodies in (requests, responses):
        require(type(bodies) is _View and bodies._body()[0] == 'tuple' and len(bodies) == 2
            and all(type(v) is bytes for v in bodies))


def bound(graph, packet):
    """Identity to the original full graph pin; caller retains its full guard."""
    current(_CONFIG)
    require(is_packet(packet) and graph.phase == 'post' and graph.inputs.get(KEY) is packet)
    return read(packet)


def witness(namespace, names):
    """Import-time code configuration only; never captures a data verdict."""
    return (namespace, tuple((name, namespace[name], namespace[name].__code__,
        namespace[name].__defaults__, namespace[name].__kwdefaults__,
        tuple((namespace[name].__kwdefaults__ or {}).items())) for name in names))


def current(config, *extra):
    """Fresh complete codec/view/callee configuration, independent of content."""
    for namespace, entries in (config[0], *extra):
        for name, fn, code, defaults, kw, items in entries:
            if (namespace.get(name) is not fn or fn.__code__ is not code
                    or fn.__defaults__ is not defaults or fn.__kwdefaults__ is not kw
                    or len(kw or {}) != len(items)
                    or any(k is not ok or v is not ov for (k,v),(ok,ov)
                        in zip((kw or {}).items(), items, strict=True))):
                raise DomainError('VERSION_CONFLICT', 'Owned archive code changed')
    for name, expected in config[2]:
        if globals().get(name) is not expected:
            raise DomainError('VERSION_CONFLICT', 'Owned archive configuration changed')
    for name, cls, mro, namespace, methods in config[1]:
        actual = tuple(type.__getattribute__(cls, '__dict__').items())
        if (globals().get(name) is not cls or type(cls) is not type
            or type.__getattribute__(cls, '__mro__') is not mro
            or len(actual) != len(namespace)
            or any(k is not old_k or v is not old_v for (k,v),(old_k,old_v) in zip(actual,namespace,strict=True))):
            raise DomainError('VERSION_CONFLICT', 'Owned archive class changed')
        for fn, code, defaults, kw, items in methods:
            if (fn.__code__ is not code or fn.__defaults__ is not defaults
                or fn.__kwdefaults__ is not kw or len(kw or {}) != len(items)
                or any(k is not ok or v is not ov for (k,v),(ok,ov)
                    in zip((kw or {}).items(), items, strict=True))):
                raise DomainError('VERSION_CONFLICT', 'Owned archive class code changed')


_CONFIG = (witness(globals(), ('require', 'is_packet', 'reject_experiment', '_shape',
    'capture', '_read', 'read', '_view_shape', 'bound', 'witness', 'current')),
    tuple((name, cls, type.__getattribute__(cls, '__mro__'), tuple(vars(cls).items()),
     tuple((fn,fn.__code__,fn.__defaults__,fn.__kwdefaults__,tuple((fn.__kwdefaults__ or {}).items()))
        for fn in vars(cls).values() if hasattr(fn,'__code__')))
        for name,cls in (('_View', _View), ('Capacity', Capacity))),
    tuple((name, globals()[name]) for name in ('TAG', 'KEY', '_MAX_NODES', '_MAX_EDGES',
        '_MAX_WIRE', '_MAX_LEAVES', '_RECEIPT_STR', '_RECEIPT_BOOL', '_RECEIPT_INT',
        '_PROOF_STR', '_PROOF_INT', 'DomainError')))
CHECK = (current, current.__code__, current.__defaults__, _CONFIG)
