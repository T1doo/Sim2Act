"""Fresh complete proof-input comparison; never graph/permission/PASS reuse.

Native equality is stricter than the canonical SHA. A miss, unsupported data
or changed codec selects the original canonical check in the caller.
"""

import abc
import builtins
import dis
import json
from inspect import getattr_static
from types import FunctionType

from . import _cold_graph_structure_guard as structure
from . import db
from . import natural_spec_runtime as r
from .errors import DomainError

_PROOF = r._ModelSettlementRead
_PROOF_MRO, _PROOF_ITEMS = _PROOF.__mro__, tuple(vars(_PROOF).items())
_PROOF_METHODS = tuple(name for name, value in _PROOF_ITEMS if type(value) is FunctionType)
_DUMP = getattr_static(r.Limits, "model_dump")
_ALIASES = tuple((owner, name, getattr(owner, name)) for owner, names in (
    (r, ("_ModelSettlementRead", "_ColdTrialGraph", "_model_value", "fingerprint",
         "Mapping", "Limits", "require", "hashlib", "json", "_SOURCE_VIEW_TYPE", "_SOURCE_OWNER_TYPE")),
    (db, ("fingerprint", "json", "hashlib")),
    (builtins, ("isinstance",)),
    (abc, ("_abc_instancecheck", "_abc_subclasscheck")),
    (structure, ("_qualified", "_fixed_classes", "_same_items", "_NATIVE_SNAPSHOT",
                 "_NATIVE_MATCH", "_UNSUPPORTED", "_ARGS")),
) for name in names)
_FUNCTIONS = (r._model_value, r.fingerprint, _DUMP,
    *[value for _, value in _PROOF_ITEMS if type(value) is FunctionType], structure._qualified,
    structure._fixed_classes, structure._same_items,
    abc.ABCMeta.__instancecheck__, abc.ABCMeta.__subclasscheck__)
_CODE = tuple((fn, fn.__code__, fn.__defaults__, fn.__kwdefaults__,
    tuple((fn.__kwdefaults__ or {}).items())) for fn in _FUNCTIONS)
_JSON_ENCODER = json.JSONEncoder
_JSON_ITEMS = tuple(vars(_JSON_ENCODER).items())
_JSON_MRO = _JSON_ENCODER.__mro__
_JSON_VALUES = tuple((owner, name, getattr(owner, name)) for owner, names in (
    (json, ("dumps", "JSONEncoder")),
    (json.encoder, ("_make_iterencode", "c_make_encoder", "encode_basestring",
                    "encode_basestring_ascii", "INFINITY")),
) for name in names)
_JSON_CODE = tuple((fn, fn.__code__, fn.__defaults__, fn.__kwdefaults__,
    tuple((fn.__kwdefaults__ or {}).items())) for fn in (
        json.dumps, json.encoder._make_iterencode,
        *[value for value in vars(_JSON_ENCODER).values() if type(value) is FunctionType]))
_REDUCERS = tuple(fn.__code__ for fn in (r._ColdGraphPickler.reducer_override,
    r._cold_graph_limit_values, r._cold_graph_row_storage, r.require, r.codec.require))
_GLOBALS = tuple((fn, fn.__globals__, name,
    fn.__globals__.get(name, fn.__builtins__.get(name)))
    for fn in (*_FUNCTIONS, *[fn for fn, *_ in _JSON_CODE])
    for name in dict.fromkeys(item.argval for item in dis.get_instructions(fn)
        if item.opname in {"LOAD_GLOBAL", "LOAD_NAME"}))


def _same_items(current, items):
    return len(current) == len(items) and all(
        key is old_key and value is old_value
        for (key, value), (old_key, old_value) in zip(current.items(), items, strict=True))


def _canonical_current():
    return (all(vars(owner).get(name) is value for owner, name, value in (*_ALIASES, *_JSON_VALUES))
        and all(fn.__globals__ is namespace
            and namespace.get(name, fn.__builtins__.get(name)) is value
            for fn, namespace, name, value in _GLOBALS)
        and getattr_static(r.Limits, "model_dump") is _DUMP
        and type.__getattribute__(_JSON_ENCODER, "__mro__") is _JSON_MRO
        and _same_items(type.__getattribute__(_JSON_ENCODER, "__dict__"), _JSON_ITEMS)
        and all(fn.__code__ is code and fn.__defaults__ is defaults
            and fn.__kwdefaults__ is kwdefaults
            and _same_items(fn.__kwdefaults__ or {}, items)
            for fn, code, defaults, kwdefaults, items in (*_CODE, *_JSON_CODE)))


class _State:
    __slots__ = ("scope", "capsule")

    def __init__(self, scope, capsule):
        self.scope, self.capsule = scope, capsule


def _qualified(proof):
    if (type(proof) is not _PROOF
            or type.__getattribute__(_PROOF, "__mro__") is not _PROOF_MRO
            or not _same_items(type.__getattribute__(_PROOF, "__dict__"), _PROOF_ITEMS)
            or any(name in object.__getattribute__(proof, "__dict__") for name in _PROOF_METHODS)
            or not proof.active
            or proof.state in {"INVALID", "CLOSED"}
            or type(proof.post_graph) is not r._ColdTrialGraph
            or not _canonical_current() or not _helper_current()):
        return False
    c = proof.connection
    return (c.get_transaction() is proof.transaction
        and c.connection.driver_connection is proof.driver
        and proof.driver.total_changes == proof.changes
        and r.get_ident() == proof.thread
        and c.info.get("_model_settlement_scope") is proof.scope_nonce
        and proof.post_graph.guard.connection is c
        and proof.post_graph.guard.phase == "post"
        and structure._qualified(proof.post_graph.guard))


def _representation_miss(error):
    """Only errors from the fixed pure raw reducers select canonical fallback."""
    if type(error) is not DomainError:
        return False
    found = False
    tb = error.__traceback__
    while tb is not None:
        code = tb.tb_frame.f_code
        if code is not _SELECT_CODE and not any(code is old for old in _REDUCERS):
            return False
        found = found or any(code is old for old in _REDUCERS[:3])
        tb = tb.tb_next
    return found


def same(proof):
    """True means fresh complete input equality; None requires original SHA."""
    if not _helper_current() or not _qualified(proof):
        proof._input_structure = None
        return None
    scope = (proof, proof.scope_nonce, proof.input_fingerprint, proof.transaction, proof.driver)
    state = proof._input_structure
    if (type(state) is _State and type(state.scope) is tuple and len(state.scope) == 5
            and all(a is b for a, b in zip(state.scope, scope, strict=True))):
        try:
            matched = structure._NATIVE_MATCH(state.capsule, proof.inputs, scope)
        except DomainError as error:
            if not _representation_miss(error):
                raise
            matched = None
        if matched is True:
            return True
        proof._input_structure = None
        return None
    proof._input_structure = None
    if proof._inputs_key() != proof.input_fingerprint:
        return None
    try:
        capsule = structure._NATIVE_SNAPSHOT(proof.inputs, *structure._ARGS, scope,
            r._SOURCE_VIEW_TYPE, r._SOURCE_OWNER_TYPE)
        if capsule is structure._UNSUPPORTED:
            return None
        # Independent current walk closes calibration ABA. No hash-only result.
        matched = structure._NATIVE_MATCH(capsule, proof.inputs, scope)
    except DomainError as error:
        if not _representation_miss(error):
            raise
        return None
    if (matched is not True or not _qualified(proof)
            or proof._inputs_key() != proof.input_fingerprint):
        return None
    proof._input_structure = _State(scope, capsule)
    return True


_SELECT_CODE = same.__code__
_HELPER_STATE = _State
_STATE_ITEMS = tuple(vars(_State).items())
_HELPERS = tuple((fn.__name__, fn, fn.__code__) for fn in (
    _same_items, _canonical_current, _qualified, _representation_miss, same, _State.__init__))


def _helper_current():
    return (_helper_current is _HELPER_CURRENT and _helper_current.__code__ is _HELPER_CURRENT_CODE
        and _State is _HELPER_STATE and _same_items(vars(_State), _STATE_ITEMS)
        and all(fn.__code__ is code and (name == "__init__" or globals().get(name) is fn)
            for name, fn, code in _HELPERS))


_HELPER_CURRENT, _HELPER_CURRENT_CODE = _helper_current, _helper_current.__code__
