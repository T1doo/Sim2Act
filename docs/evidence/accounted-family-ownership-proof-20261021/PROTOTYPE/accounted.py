"""Offline complete-value adapter, NOT a producer proof or issued capability.

The original producer and every dynamic gate remain required. No runtime imports
this module. Its records demonstrate a representation seam only.
"""
from sqlalchemy.engine import RowMapping
from sim2act import natural_live_admission as gate
from sim2act import production_trial_policy as policy
from sim2act import production_trial_sender as sender
from sim2act import natural_source_archives as archive
from sim2act.db import runs, attempts
from sim2act.natural_spec_runtime import _cold_graph_row_storage
from owned_graph import freeze, Rejected


def model_value(expected, value):
    # Exact nested storage check before using the fixed trusted serializer.
    storage = gate._trial_typed_storage(expected, value)
    dumped = expected.model_dump(value, warnings=False)
    gate._trial_typed_values([(expected, value, dumped)])
    if not gate._trial_typed_equal(storage, dumped):
        raise Rejected('model representation drift')
    return dumped


def capture_accounted(value, role, bounds):
    """Copy one complete family. Does not authorize, verify or cache a fact."""
    if type(role) is not str or role not in ('source', 'generate'):
        raise Rejected('role')
    if type(value) is not tuple or len(value) != 4:
        raise Rejected('family shape')
    run, actual, chains, ns_reads = value
    count = 2 if role == 'source' else 3
    if type(actual) not in (list, tuple) or type(chains) not in (list, tuple):
        raise Rejected('sequence shape')
    if type(ns_reads) not in (list, tuple) or not (
            len(actual) == len(chains) == count and len(ns_reads) == (2 if role == 'source' else 0)):
        raise Rejected('family counts')
    sidecars = []

    def row(value, table, label):
        if type(value) is RowMapping:
            storage = _cold_graph_row_storage(value)
            # This owned sidecar retains ALL data positions and safe aliases;
            # visible dict(row) alone would lose hidden raw storage.
            names = tuple(str(k) for k in storage[0])
            if len(set(names)) != len(names):
                raise Rejected('duplicate row keys')
            # Keep keys/data references until the single final freeze, never
            # reuse a previously sealed result across producer invocations.
            sidecars.append((label, storage))
            visible = {str(k): storage[1][storage[2][str(k)]] for k in storage[0]}
        elif type(value) is dict and all(type(k) is str for k in value):
            visible = dict(value)
        else:
            raise Rejected('row type')
        if set(visible) != set(table.c.keys()):
            raise Rejected('complete row columns')
        return visible

    projected_run = row(run, runs, 'run')
    projected_actual = tuple(row(a, attempts, ('actual', i)) for i, a in enumerate(actual))
    projected_chains = []
    for i, chain in enumerate(chains):
        if type(chain) is not tuple or len(chain) != 6:
            raise Rejected('chain shape')
        slot, capture, parsed, checked, wire, payload = chain
        if type(wire) is not bytes or type(payload) is not bytes:
            raise Rejected('chain bytes')
        projected_chains.append((model_value(policy.Slot, slot),
            model_value(sender.Capture, capture), parsed,
            row(checked, attempts, ('checked', i)), wire, payload))
    projected_ns = []
    for read in ns_reads:
        if type(read) is not tuple or len(read) != 5:
            raise Rejected('archive read shape')
        aid, request, wire, response, payload = read
        if type(aid) is not str or type(wire) is not bytes or type(payload) is not bytes:
            raise Rejected('archive read types')
        projected_ns.append((aid, model_value(archive.BodyArchive, request), wire,
            model_value(archive.BodyArchive, response), payload))
    # Domain/schema is private. This digest NEVER replaces a business hash.
    return freeze(dict(domain='offline-accounted-family-proof.v1', role=role,
        value=dict(run=projected_run, actual=projected_actual,
            chains=tuple(projected_chains), ns_reads=tuple(projected_ns)),
        row_storage=tuple(sidecars)), bounds)
