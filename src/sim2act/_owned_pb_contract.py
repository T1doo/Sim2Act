"""Graph-neutral complete PB model/dump ownership; never approval or a PASS.

Issuance belongs after the original checked-contract parser, before publishing
the Binding to a Worker. Every Graph still owns its own version and dynamic
gates. Ordinary API/DB contracts remain the original Pydantic/JSON protocol.
"""
import sys
import hashlib
from types import FunctionType

from . import _cold_source_packet as facts
from . import natural_live_admission as gate
from .errors import DomainError

_CLASSES = facts.image.contract_classes()
_PB = _CLASSES[17]
_NATIVE = facts.native
_MODEL = None if not facts.available() else _NATIVE.contract_model
_MAKE = None if not facts.available() else _NATIVE.make_contract_owned
_VIEW = None if not facts.available() else _NATIVE.View
_SHA = hashlib.sha256
_TYPE, _ALL, _TUPLE, _VARS, _NEXT, _ID = type, all, tuple, vars, next, id
_PROFILE, _TRACE = sys.getprofile, sys.gettrace
_MODEL_TYPE = type if not facts.available() else _NATIVE.contract_type


def model_type(value):
    """Explicit owned schema identity, never isinstance/type impersonation."""
    _entry = 'sim2act:pb-data-entry.v1'
    if _entry is not None: _entry()
    return _MODEL_TYPE(value)


def is_model(value, expected):
    _entry = 'sim2act:pb-data-entry.v1'
    if _entry is not None: _entry()
    return model_type(value) is expected


def is_owned(value):
    _entry = 'sim2act:pb-data-entry.v1'
    if _entry is not None: _entry()
    return (_MODEL is not None and _TYPE(value) is _VIEW
        and _MODEL(value) is not None)


def current(value):
    _entry = 'sim2act:pb-data-entry.v1'
    if _entry is not None: _entry()
    facts.current()
    if not is_owned(value) or _NATIVE.contract_schema_current() is not True:
        raise DomainError('VERSION_CONFLICT', 'Exact complete PB owned data required')
    return value


def data(value):
    """Complete immutable data identity for the CURRENT model, not JSON/PASS."""
    _entry = 'sim2act:pb-data-entry.v1'
    if _entry is not None: _entry()
    current(value)
    return _NATIVE.view_pin(value)


def _config():
    """Original descriptor-only verifier config, without inventing a Graph."""
    _entry = 'sim2act:pb-data-entry.v1'
    if _entry is not None: _entry()
    from . import natural_spec_runtime as runtime
    from . import production_trial_policy as policy

    def descriptor(cls, name):
        _entry = 'sim2act:pb-data-entry.v1'
        if _entry is not None: _entry()
        return _NEXT(_VARS(base)[name] for base in cls.__mro__ if name in _VARS(base))

    models = _TUPLE((cls, cls.__module__ + '.' + cls.__qualname__,
        *(descriptor(cls, name) for name in ('__dict__', '__pydantic_fields_set__',
            '__pydantic_extra__', '__pydantic_private__'))) for cls in _CLASSES)
    names = ('max_requests', 'max_tools', 'max_repairs', 'max_total_tokens',
        'max_output_tokens', 'run_seconds')
    return (models, runtime._ColdGraphRowMapping,
        _TUPLE(descriptor(runtime._ColdGraphRowMapping, key) for key in
            ('_parent', '_data', '_key_to_index')),
        _TUPLE((cls, descriptor(cls, '_keys')) for cls in
            (runtime._ColdGraphCursorMeta, runtime._ColdGraphSimpleMeta)),
        runtime._ColdGraphQuotedName,
        (runtime.Limits, descriptor(runtime.Limits, '__dict__'), names),
        (policy.Ledger, descriptor(policy.Ledger, '__dict__')))


def issue_data(checked):
    """Actual bounded full model+original dump handoff, before publication.

    Unsupported configurations keep the original checked model. A changed
    current value after capture is a refusal, never an updated expectation.
    Production publication also seals the exact Binding identity and header.
    """
    _entry = 'sim2act:pb-data-entry.v1'
    if _entry is not None: _entry()
    if _TYPE(checked) is not _PB or _MAKE is None:
        return checked
    facts.current()
    if _PROFILE() is not None or _TRACE() is not None:
        return checked
    from ._cold_policy_segment import _fixed_schema
    if not _ALL(_fixed_schema(cls) for cls in _CLASSES):
        return checked
    config = _config()
    raw = _PB.model_dump(checked, warnings=False)
    gate._trial_typed_values([(_PB, checked, raw)])
    try:
        image, anchors = facts.image.capture((checked, raw), (), _contract=True)
    except (facts.image.Unsupported, facts.image.Bounds):
        return checked
    if anchors:
        return checked
    # Retain the original actual/raw storage gate and revalidate semantics.
    # The final C join below includes the full CURRENT model, fresh dump,
    # hidden storage, ordered containers and their joint alias partition.
    gate._trial_typed_values([(_PB, checked, raw)])
    fresh = _PB.model_dump(checked, warnings=False)
    _PB.model_validate(fresh)
    value = _MAKE(image, (checked, fresh), config)
    if value is _NATIVE.UNSUPPORTED:
        raise DomainError('VERSION_CONFLICT', 'PB contract changed during complete handoff')
    current(value)
    if _MODEL(value) is not _PB:
        raise DomainError('VERSION_CONFLICT', 'PB owned root schema changed')
    return value


def publish(binding, checked, approval_key, account_id):
    """Only the original checked constructor can publish a complete PB owner."""
    _entry = 'sim2act:pb-data-entry.v1'
    if _entry is not None: _entry()
    value = issue_data(checked)
    if not is_owned(value):
        return False
    _NATIVE.install_contract_binding(binding, value, checked, approval_key, account_id)
    return True


def bound(binding):
    """Current exact lifecycle; None means an ordinary legacy contract only."""
    _entry = 'sim2act:pb-data-entry.v1'
    if _entry is not None: _entry()
    if _MAKE is None:
        return None
    return _NATIVE.contract_binding_current(binding)


def _seal_entries():
    """Same fixed-callee constant pattern as the existing Graph protocol."""
    from types import CodeType
    marker = 'sim2act:pb-data-entry.v1'
    def seal(code):
        return code.replace(co_consts=_TUPLE((_NATIVE.contract_entry if _MAKE is not None else None) if _TYPE(v) is str and v == marker
            else seal(v) if _TYPE(v) is CodeType else v for v in code.co_consts))
    for fn in (model_type, is_model, is_owned, current, data, _config, issue_data, publish, bound):
        fn.__code__ = seal(fn.__code__)


def _register():
    if not facts.available():
        _seal_entries()
        return
    # Complete the original families before any fixed native entry is used.
    from . import natural_spec_runtime
    from .spec_production import ProductionTrialBinding
    from . import _cold_policy_segment as schema
    from pydantic_core import SchemaValidator, SchemaSerializer
    classes = {}
    for root in (ProductionTrialBinding, *_CLASSES, SchemaValidator, SchemaSerializer):
        for cls in (*root.__mro__, *_TYPE(root).__mro__):
            if _TYPE.__getattribute__(cls, '__flags__') & (1 << 9):
                classes[_ID(cls)] = cls
    rows = _TUPLE(_NEXT(r for r in schema._SCHEMAS if r[0] is cls) for cls in _CLASSES)
    leaves = _TUPLE(schema._CODE_LEAVES)
    # Keep original schema function leaves and their code/default/closure
    # states, rather than only storing their addresses in a schema shape.
    functions = {str(i): fn for i, fn in enumerate(leaves) if _TYPE(fn) is FunctionType}
    _seal_entries()
    facts.register(9, globals(), ('model_type', 'is_model', 'is_owned', 'current',
        'data', '_config', 'issue_data', 'publish', 'bound', '_seal_entries', '_register'), classes=(DomainError,),
        constants=('_CLASSES', '_PB', '_NATIVE', '_MODEL', '_MAKE', '_VIEW', '_SHA', '_MODEL_TYPE',
            '_TYPE', '_ALL', '_TUPLE', '_VARS', '_NEXT', '_ID', '_PROFILE', '_TRACE',
            'facts', 'gate', 'DomainError', 'sys', 'hashlib', 'FunctionType'),
        helpers=((_VARS(facts.image), ('contract_classes',)),
            (_VARS(facts), ('current', 'require', '_class')),
            (functions, _TUPLE(functions))),
        constant_helpers=((_VARS(hashlib), ('sha256',)),
            (_VARS(sys), ('getprofile', 'gettrace')),))
    _NATIVE.register_contract_models(_CLASSES, _SHA)
    _NATIVE.register_contract_schemas(rows, _TUPLE(facts._class(cls) for cls in classes.values()),
        leaves, (SchemaValidator, SchemaSerializer))
    from .spec_production import VERSION
    _NATIVE.register_contract_binding(ProductionTrialBinding, VERSION)


_register()
