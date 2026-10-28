"""Explicit synthetic SQLite experiment using owned data and original PUBLIC G0.

Default product selection never constructs this handle. No graph, source verdict,
permission or postwrite proof can be transferred by it. Original G1 is untouched.
"""

from __future__ import annotations

import ast
import functools
import inspect
import signal
import sys
import threading
import time
import types
from contextlib import contextmanager
from pathlib import Path
from sqlite3 import Connection as SQLiteConnection

from sqlalchemy import event
from sqlalchemy.dialects.sqlite.pysqlite import SQLiteDialect_pysqlite
from sqlalchemy.engine import Connection, Engine, RootTransaction, RowMapping
from sqlalchemy.sql import sqltypes

from . import _owned_sqlite as _private_sql
from . import db as _gate_db
from ._immutable_settlement import ContentPlan, OwnedValue, UnsupportedPlan
from .errors import DomainError

_SQL_CLASSES = (
    Engine,
    Connection,
    RootTransaction,
    RowMapping,
    SQLiteConnection,
    SQLiteDialect_pysqlite,
    SQLiteDialect_pysqlite.statement_compiler,
    SQLiteDialect_pysqlite.execution_ctx_cls,
    sqltypes.String,
    sqltypes.Integer,
    sqltypes.Float,
    sqltypes.Boolean,
    sqltypes.JSON,
)
_SQL_SLOTS = tuple(
    (kind, name, value)
    for root in _SQL_CLASSES
    for kind in root.__mro__
    if kind is not object
    for name, value in vars(kind).items()
    if callable(value)
    or type(value) is property
    or type(value) is classmethod
    or type(value) is staticmethod
)
_SQL_CODE = tuple(
    (
        value.__func__ if type(value) is classmethod or type(value) is staticmethod else value,
        (
            value.__func__ if type(value) is classmethod or type(value) is staticmethod else value
        ).__code__,
    )
    for _, _, value in _SQL_SLOTS
    if type(value.__func__ if type(value) is classmethod or type(value) is staticmethod else value)
    is types.FunctionType
)


# Test harness supplies an explicit, reviewed fixture callback list. It never
# installs an entitlement resolver or changes production environment selection.


def _codes(root):
    yield root
    for value in root.co_consts:
        if type(value) is types.CodeType:
            yield from _codes(value)


_SQL_EPOCH_HOOK = next(
    code
    for code in _codes(
        compile(
            Path(_gate_db.__file__).read_bytes(),
            _gate_db.__file__,
            "exec",
            dont_inherit=True,
            optimize=sys.flags.optimize,
        )
    )
    if code.co_qualname == "Store.__init__.<locals>.proof_write_boundary"
)


class _Code:
    """Fresh function/code/default witnesses, never input/PASS witnesses."""

    def __init__(self, callbacks):
        from . import _cold_policy_segment as schema
        from . import db

        self.functions, self.slots, self.models, self.files = [], [], [], {}
        self.callbacks = callbacks
        self.schema = schema
        self.shape, self.matches = schema._schema_shape, schema._schema_matches
        self.keep = []
        self.ast_files = {}
        self.node_indexes = {}
        seen = set()

        def function(fn):
            if id(fn) in seen:
                return
            seen.add(id(fn))
            code = fn.__code__
            path = Path(code.co_filename)
            if any(fn is allowed for allowed in callbacks):
                pass  # Exact caller-supplied synthetic fixture object only.
            else:
                if path.parent.name != "sim2act" and not (
                    path.name == "contextlib.py"
                    and code.co_qualname == "contextmanager.<locals>.helper"
                ):
                    raise UnsupportedPlan(
                        "Unknown Python callback: " + fn.__module__ + "." + fn.__qualname__
                    )
                if str(path) not in self.files:
                    self.files[str(path)] = tuple(
                        _codes(
                            compile(
                                path.read_bytes(),
                                str(path),
                                "exec",
                                dont_inherit=True,
                                optimize=sys.flags.optimize,
                            )
                        )
                    )
                if not any(code == expected for expected in self.files[str(path)]):
                    raise UnsupportedPlan(
                        "Changed callback code: " + fn.__module__ + "." + fn.__qualname__
                    )
            defaults = self.shape((fn.__defaults__, fn.__kwdefaults__), self.keep)
            self.functions.append(
                (
                    fn,
                    code,
                    defaults,
                    fn.__closure__,
                    tuple(cell.cell_contents for cell in fn.__closure__ or ()),
                )
            )
            for cell in fn.__closure__ or ():
                value = cell.cell_contents
                if type(value) is types.FunctionType:
                    function(value)

        def target(owner, name, fn, qualname):
            if any(fn is allowed for allowed in callbacks):
                return
            path = Path(
                owner.__file__
                if type(owner) is types.ModuleType
                else sys.modules[owner.__module__].__file__
            )
            if str(path) not in self.files:
                self.files[str(path)] = tuple(
                    _codes(
                        compile(
                            path.read_bytes(),
                            str(path),
                            "exec",
                            dont_inherit=True,
                            optimize=sys.flags.optimize,
                        )
                    )
                )
            expected = next(
                (code for code in self.files[str(path)] if code.co_qualname == qualname), None
            )
            if str(path) not in self.ast_files:
                self.ast_files[str(path)] = ast.parse(path.read_bytes())
            if str(path) not in self.node_indexes:
                self.node_indexes[str(path)] = {
                    line: node
                    for node in ast.walk(self.ast_files[str(path)])
                    if type(node) is ast.FunctionDef or type(node) is ast.AsyncFunctionDef
                    for line in [
                        node.lineno,
                        *[decorator.lineno for decorator in node.decorator_list],
                    ]
                }
            node = self.node_indexes[str(path)].get(
                None if expected is None else expected.co_firstlineno
            )
            matches = () if node is None else (node,)
            decorators = set()
            for node in matches:
                for decorator in node.decorator_list:
                    item = decorator.func if type(decorator) is ast.Call else decorator
                    if type(item) is ast.Name:
                        decorators.add(item.id)
                    elif type(item) is ast.Attribute:
                        decorators.add(item.attr)
            original = fn
            while expected is not None and original.__code__ != expected:
                if original.__code__.co_qualname.split(".", 1)[0] not in decorators:
                    break
                cells = original.__closure__ or ()
                if len(cells) != 1 or type(cells[0].cell_contents) is not types.FunctionType:
                    raise UnsupportedPlan("Unknown public decorator closure")
                original = cells[0].cell_contents
            if expected is None or original.__code__ != expected:
                raise UnsupportedPlan("Changed target slot: " + qualname)
            if node is None:
                raise UnsupportedPlan("Missing original default declaration")
            positional = original.__defaults__ or ()
            keywords = original.__kwdefaults__ or {}
            expressions = [
                *node.args.defaults,
                *[value for value in node.args.kw_defaults if value is not None],
            ]
            actual_defaults = [
                *positional,
                *[
                    keywords.get(arg.arg)
                    for arg, value in zip(node.args.kwonlyargs, node.args.kw_defaults, strict=True)
                    if value is not None
                ],
            ]
            if len(positional) != len(node.args.defaults) or len(keywords) != sum(
                value is not None for value in node.args.kw_defaults
            ):
                raise UnsupportedPlan("Changed declared default arity: " + qualname)
            for expression, actual in zip(expressions, actual_defaults, strict=True):
                try:
                    declared = ast.literal_eval(expression)
                except (ValueError, TypeError):
                    if type(expression) is ast.Name and actual is original.__globals__.get(
                        expression.id
                    ):
                        continue
                    raise UnsupportedPlan("Unqualified nonliteral default: " + qualname) from None
                if not OwnedValue.capture(declared).matches(actual):
                    raise UnsupportedPlan("Changed declared default: " + qualname)

        for name, module in tuple(sys.modules.items()):
            if not name.startswith("sim2act.") or type(module) is not types.ModuleType:
                continue
            if name in {"sim2act._owned_g0_candidate", "sim2act._immutable_settlement"}:
                continue
            module_path = Path(module.__file__)
            if module_path.suffix != ".py":
                continue
            definitions = {
                node.name
                for node in self.ast_files.setdefault(
                    str(module_path), ast.parse(module_path.read_bytes())
                ).body
                if type(node) is ast.FunctionDef or type(node) is ast.AsyncFunctionDef
            }
            for key in definitions:
                if name == "sim2act.natural_spec_runtime" and key == "fail_owned":
                    continue
                value = vars(module).get(key)
                if type(value) is functools._lru_cache_wrapper:
                    wrapped = object.__getattribute__(value, "__wrapped__")
                    if type(wrapped) is not types.FunctionType:
                        raise UnsupportedPlan("Unknown cached function")
                    target(module, key, wrapped, key)
                    function(wrapped)
                    self.slots.extend(((module, key, value), (value, "__wrapped__", wrapped)))
                    continue
                if type(value) is not types.FunctionType:
                    raise UnsupportedPlan("Unknown callable in original function slot: " + key)
                target(module, key, value, key)
                function(value)
                self.slots.append((module, key, value))
            for key, value in tuple(vars(module).items()):
                # These callbacks execute outside G0 and do not become trusted
                # pure calls merely because a fixture observes their results.
                if name == "sim2act.natural_spec_runtime" and key == "fail_owned":
                    continue
                if type(value) is types.FunctionType and value.__module__.startswith("sim2act"):
                    function(value)
                    self.slots.append((module, key, value))
                elif name == "sim2act.spec_production" and key == "environment":
                    function(value)
                    self.slots.append((module, key, value))
                elif name == "sim2act.production_evidence" and key == "resolve_account":
                    function(value)
                    self.slots.append((module, key, value))
                elif name == "sim2act.production_trial_admission" and key == "_qualified":
                    function(value)
                    self.slots.append((module, key, value))
        from . import natural_spec_runtime as runtime
        from . import pa_spec_apps as spec

        for owner, keys in (
            (spec, ("bound", "commit_guard", "receipts", "receipt_for", "compile_candidate")),
            (runtime, ("enabled", "parse", "validate_value")),
        ):
            for key in keys:
                value = inspect.getattr_static(owner, key)
                if type(value) is not types.FunctionType:
                    raise UnsupportedPlan("Changed public G0 callable")
                function(value)
                self.slots.append((owner, key, value))
        for key in (
            "__init__",
            "owns_connection",
            "guard",
            "authorize",
            "_frozen_contract_after_scope",
            "event",
        ):
            value = inspect.getattr_static(db.Store, key)
            target(db.Store, key, value, "Store." + key)
            function(value)
            self.slots.append((db.Store, key, value))
        # Every model schema/compiled serializer in the original trial schema
        # catalogue is checked afresh. No model instance or result is retained.
        for kind, *_unused in schema._SCHEMAS:
            namespace = vars(kind)
            for key, value in namespace.items():
                method = (
                    value.__func__
                    if type(value) is classmethod or type(value) is staticmethod
                    else value
                )
                if type(method) is types.FunctionType and method.__module__.startswith("sim2act"):
                    target(kind, key, method, kind.__qualname__ + "." + key)
                    function(method)
                    self.slots.append((kind, key, value))
            self.models.append(
                (
                    kind,
                    namespace.get("__pydantic_validator__"),
                    namespace.get("__pydantic_serializer__"),
                    self.shape(namespace.get("__pydantic_core_schema__"), self.keep),
                    tuple(namespace.items()),
                )
            )

    def current(self):
        from . import _immutable_settlement as owned
        from . import natural_spec_runtime as runtime

        for kind, items in (*_CANDIDATE_CLASSES, *owned._OWNED_CLASSES, _private_sql._SQLITE_CLASS):
            current = vars(kind)
            if len(current) != len(items) or any(
                current.get(key) is not value for key, value in items
            ):
                return False
        if (
            any(globals().get(name) is not fn for name, fn in _CANDIDATE_FUNCTIONS)
            or any(vars(owned).get(name) is not fn for name, fn in owned._OWNED_FUNCTIONS)
            or any(
                vars(_private_sql).get(name) is not fn
                for name, fn in _private_sql._SQLITE_FUNCTIONS
            )
            or any(
                fn.__code__ is not code
                for fn, code in (*_CANDIDATE_CODE, *owned._OWNED_CODE, *_private_sql._SQLITE_CODE)
            )
            or any(fn.__code__ is not code for fn, code in self.schema._PAIR_CODE)
            or not runtime._base_segments.serializers_current()
            or runtime._raw_read_settlement.time.time is not runtime._RAW_DYNAMIC_CLOCKS[0]
            or runtime._raw_read_settlement.time.monotonic is not runtime._RAW_DYNAMIC_CLOCKS[1]
        ):
            return False
        if (
            self.schema._schema_shape is not self.shape
            or self.schema._schema_matches is not self.matches
        ):
            return False
        for fn in self.callbacks:
            values = dict(
                zip(
                    fn.__code__.co_freevars,
                    (cell.cell_contents for cell in fn.__closure__ or ()),
                    strict=True,
                )
            )
            fixture = values.get("fixture")
            if fixture is not None and (
                type(fixture) is not dict
                or not all(type(key) is str for key in dict.keys(fixture))
                or type(dict.get(fixture, "revoked")) is not bool
                or type(dict.get(fixture, "source_reads")) is not int
            ):
                return False
        if any(
            inspect.getattr_static(owner, name) is not value for owner, name, value in self.slots
        ):
            return False
        for fn, code, defaults, cells, contents in self.functions:
            if (
                fn.__code__ is not code
                or fn.__closure__ is not cells
                or any(
                    cell.cell_contents is not value
                    for cell, value in zip(cells or (), contents, strict=True)
                )
                or not self.matches((fn.__defaults__, fn.__kwdefaults__), defaults)
            ):
                return False
        for kind, validator, serializer, shape, items in self.models:
            namespace = vars(kind)
            if len(namespace) != len(items) or any(
                namespace.get(key) is not value for key, value in items
            ):
                return False
            if not self.schema._fixed_schema(kind):
                return False
            if (
                namespace.get("__pydantic_validator__") is not validator
                or namespace.get("__pydantic_serializer__") is not serializer
                or not self.matches(namespace.get("__pydantic_core_schema__"), shape)
            ):
                return False
        return True


def _sql_current(worker, c, own_listeners=()):
    from . import db
    from .config import Settings
    from .natural_live_admission import PBTrialContract
    from .spec_production import ProductionTrialBinding
    from .worker import Worker

    if (
        type(worker) is not Worker
        or type(worker.store) is not db.Store
        or type(worker.s) is not Settings
        or type(worker.pa_trial) is not ProductionTrialBinding
        or type(worker.pa_trial.contract) is not PBTrialContract
        or type(c) is not Connection
        or type(c.engine) is not Engine
        or type(c.engine.dialect) is not SQLiteDialect_pysqlite
        or type(c.get_transaction()) is not RootTransaction
        or type(c.connection.driver_connection) is not SQLiteConnection
        or c.connection.driver_connection.row_factory is not None
        or c.connection.driver_connection.text_factory is not str
        or c.engine.dialect._json_serializer is not None
        or c.engine.dialect._json_deserializer is not None
        or any(inspect.getattr_static(kind, name) is not value for kind, name, value in _SQL_SLOTS)
        or any(fn.__code__ is not code for fn, code in _SQL_CODE)
    ):
        return False
    for owner in (c, c.engine, c.engine.dialect):
        raw = object.__getattribute__(owner, "__dict__")
        if type(raw) is not dict or any(type(key) is not str for key in raw):
            return False
        for kind, key, value in _SQL_SLOTS:
            if (
                any(kind is base for base in type(owner).__mro__)
                and key in raw
                and raw[key] is not value
            ):
                return False
    for table in db.attempts.metadata.tables.values():
        for column in table.c:
            if not any(
                type(column.type) is allowed
                for allowed in (
                    sqltypes.String,
                    sqltypes.Integer,
                    sqltypes.Float,
                    sqltypes.Boolean,
                    sqltypes.JSON,
                )
            ):
                return False
    # Only the original epoch-invalidation hook is permitted. Unknown SQL
    # callbacks select legacy BEFORE business; additions after selection reject.
    expected = _SQL_EPOCH_HOOK
    for owner in (c, c.engine):
        for name in (
            "before_execute",
            "after_execute",
            "before_cursor_execute",
            "after_cursor_execute",
        ):
            for fn in getattr(owner.dispatch, name):
                if any(fn is own for own in own_listeners):
                    continue
                if name != "before_cursor_execute" or type(fn) is not types.FunctionType:
                    return False
                if (
                    fn.__code__.co_qualname
                    != "ConnectionEvents._listen.<locals>.wrap_before_cursor_execute"
                ):
                    return False
                cells = fn.__closure__ or ()
                if len(cells) != 1 or type(cells[0].cell_contents) is not types.FunctionType:
                    return False
                actual = cells[0].cell_contents
                if any(actual is own for own in own_listeners):
                    continue
                if actual.__code__ != expected or actual.__closure__ is not None:
                    return False
    return True


class MockCandidate:
    """Explicit handle for synthetic tests; no environment/API flag selects it."""

    def __init__(self, *, fixture_callbacks=()):
        if type(fixture_callbacks) is not tuple or not all(
            type(fn) is types.FunctionType for fn in fixture_callbacks
        ):
            raise UnsupportedPlan("Exact synthetic callbacks required")
        self.code = _Code(fixture_callbacks)
        self.selected = 0
        self.fallback = 0
        self.timings = []
        self.transactions = []

    @contextmanager
    def connection(self, worker, plan):
        if plan is None:
            with worker.store.tx() as c:
                yield c, None
            return
        manager = _private_sql.writer(worker, types.FunctionType(_SQL_EPOCH_HOOK, vars(_gate_db)))
        started = time.monotonic()
        try:
            owned = manager.__enter__()
        except UnsupportedPlan:
            self.fallback += 1
            with worker.store.tx() as c:
                yield c, None
            return
        try:
            try:
                yield owned.connection, plan
            except BaseException:
                manager.__exit__(*sys.exc_info())
                raise
            else:
                manager.__exit__(None, None, None)
        finally:
            self.transactions.append(
                dict(
                    seconds=time.monotonic() - started,
                    outcome="COMMITTED"
                    if owned.committed
                    else "ROLLED_BACK"
                    if owned.rolled_back
                    else "UNKNOWN",
                )
            )

    def prepare(self, worker, binding, call, platform):
        if not worker.store.test_only or not worker.store.sqlite:
            raise DomainError("PERMISSION_DENIED", "Owned G0 candidate requires synthetic SQLite")
        if not self.code.current() or not _execution_current(worker):
            self.fallback += 1
            return None
        try:
            return ContentPlan.compile(
                dict(
                    candidate=binding["draft"]["candidate"],
                    call=call,
                    platform=platform.model_dump(),
                )
            )
        except (UnsupportedPlan, DomainError):
            self.fallback += 1
            return None


def _execution_current(worker=None):
    if sys.gettrace() is not None or sys.getprofile() is not None:
        return False
    monitoring = getattr(sys, "monitoring", None)
    if monitoring is not None and any(monitoring.get_tool(i) is not None for i in range(6)):
        return False
    for number in signal.valid_signals():
        try:
            handler = signal.getsignal(number)
        except (ValueError, OSError):
            continue
        if callable(handler) and handler is not signal.default_int_handler:
            return False
    current = threading.current_thread()
    for thread in threading.enumerate():
        if thread is current:
            continue
        target = vars(thread).get("_target")
        from . import text_workflows

        expected = next(
            code
            for code in _codes(text_workflows.process_job.__code__)
            if code.co_qualname == "process_job.<locals>.beat"
        )
        if type(target) is not types.FunctionType or target.__code__ != expected:
            return False
        cells = target.__closure__ or ()
        values = dict(
            zip(target.__code__.co_freevars, (cell.cell_contents for cell in cells), strict=True)
        )
        if values.get("worker") is not worker or type(values.get("state")) is not dict:
            return False
    return True


class _Scope:
    """One read-only writer epoch, bounded by original finite deadlines."""

    def __init__(self, candidate, plan, worker, c, current, original_call, platform):
        from .natural_spec_runtime import _cold_graph_bytes
        from .pb_natural_specs import _source_reads_current

        self.candidate, self.plan = candidate, plan
        self.owned_writer = _private_sql._ISSUED.get(id(c))
        self.worker, self.store, self.settings = worker, worker.store, worker.s
        self.binding, self.stop, self.transport = (
            worker.pa_trial,
            worker.stop,
            worker.goal_planner_transport,
        )
        self.worker_id, self.c, self.transaction = worker.id, c, c.get_transaction()
        self.driver = c.connection.driver_connection
        self.changes = self.driver.total_changes
        self.thread = threading.get_ident()
        self.epoch, self.token = (
            c.info.get("source_proof_write_epoch", 0),
            c.info.get("pb_source_reads"),
        )
        self.settings_values = dict(vars(self.settings))
        self.roots = dict(current=current, call=original_call, platform=platform)
        self.encode, self.source_current = _cold_graph_bytes, _source_reads_current
        self.key = self.encode(self.roots)
        self.current = OwnedValue.capture(dict(current)).materialize()
        self.current_key = OwnedValue.capture(self.current)
        if not plan.call_values.matches(dict(call=original_call, platform=platform.model_dump())):
            raise DomainError("VERSION_CONFLICT", "Plan inputs changed before writer entry")
        self.private = plan.private_inputs()
        self.private_key = self.encode(self.private)
        self.outputs = {}
        self.output_key = self.encode(
            dict(
                original=self.roots,
                private=self.private,
                current=self.current,
                outputs=self.outputs,
            )
        )
        self.binding_key = self.encode(
            dict(
                contract=self.binding.contract.model_dump(),
                approval=self.binding.approval_key,
                account=self.binding.account_id,
                version=self.binding.version,
                fingerprint=self.binding.contract_fingerprint,
            )
        )
        self.end = min(
            current["lease_until"],
            self.binding.contract.expires_at,
            original_call["meta"]["deadline"],
            current["created_at"] + platform.run_seconds,
        )
        self.own_listeners = ()
        self.active = True
        self.check()

    def check(self, *unused):
        if self.owned_writer is not None:
            try:
                self.owned_writer.check()
            except UnsupportedPlan as error:
                raise DomainError("VERSION_CONFLICT", "Owned writer provenance changed") from error
        from .model_settlement import checkpoint

        w, c = self.worker, self.c
        checkpoint(w)
        valid = (
            self.active
            and self.candidate.code.current()
            and _execution_current(w)
            and _sql_current(w, c, self.own_listeners)
            and w.store is self.store
            and w.s is self.settings
            and type(object.__getattribute__(w.s, "__dict__")) is dict
            and len(vars(w.s)) == len(self.settings_values)
            and all(
                type(key) is str
                and key in self.settings_values
                and value is self.settings_values[key]
                for key, value in vars(w.s).items()
            )
            and w.pa_trial is self.binding
            and w.stop is self.stop
            and w.goal_planner_transport is self.transport
            and getattr(w, "_journal_trial_store", None) is self.store
            and getattr(w, "_journal_trial_binding", None) is self.binding
            and getattr(w, "_journal_trial_drift", None) is False
            and w.id == self.worker_id
            and self.store.owns_connection(c)
            and not c.closed
            and c.get_transaction() is self.transaction
            and c.connection.driver_connection is self.driver
            and self.driver.total_changes == self.changes
            and threading.get_ident() == self.thread
            and self.epoch == c.info.get("source_proof_write_epoch", 0)
            and self.source_current(self.store, c, self.token)
            and self.encode(self.roots) == self.key
            and self.current_key.matches(self.current)
            and self.plan.inputs.matches(self.private)
            and self.encode(
                dict(
                    original=self.roots,
                    private=self.private,
                    current=self.current,
                    outputs=self.outputs,
                )
            )
            == self.output_key
            and self.encode(
                dict(
                    contract=self.binding.contract.model_dump(),
                    approval=self.binding.approval_key,
                    account=self.binding.account_id,
                    version=self.binding.version,
                    fingerprint=self.binding.contract_fingerprint,
                )
            )
            == self.binding_key
            and not self.stop.is_set()
            and time.time() < self.end
        )
        if not valid:
            self.active = False
            raise DomainError(
                "VERSION_CONFLICT", "Owned G0 writer inputs or dynamic interval changed"
            )

    def hold(self, name, value):
        self.check()
        if type(name) is not str or name in self.outputs:
            raise DomainError("VERSION_CONFLICT", "Owned G0 output cannot be rebound")
        self.outputs[name] = value
        self.output_key = self.encode(
            dict(
                original=self.roots,
                private=self.private,
                current=self.current,
                outputs=self.outputs,
            )
        )
        self.check()
        return value

    def call(self, fn, *args, **kwargs):
        self.check()
        if not self.candidate.code.current():
            raise DomainError("VERSION_CONFLICT", "Owned G0 code configuration changed")
        started = time.monotonic()
        try:
            result = fn(*args, **kwargs)
        finally:
            self.candidate.timings.append(
                dict(stage=fn.__name__, seconds=time.monotonic() - started)
            )
        self.check()
        return result


@contextmanager
def prewrite(candidate, plan, worker, c, current, original_call, platform):
    """No fallback/replay after selection and no scope survives the five writes."""
    if type(candidate) is not MockCandidate or type(plan) is not ContentPlan:
        raise DomainError("PERMISSION_DENIED", "Explicit owned G0 candidate required")
    if not worker.store.test_only or not worker.store.sqlite:
        raise DomainError("PERMISSION_DENIED", "Synthetic SQLite candidate only")
    scope = _Scope(candidate, plan, worker, c, current, original_call, platform)

    def before(*args):
        scope.check()

    def after(*args):
        scope.check()

    event.listen(c, "before_cursor_execute", before)
    event.listen(c, "after_cursor_execute", after)
    scope.own_listeners = (before, after)
    candidate.selected += 1
    try:
        yield scope
        scope.check()
    finally:
        scope.active = False
        event.remove(c, "before_cursor_execute", before)
        event.remove(c, "after_cursor_execute", after)


def run(candidate, plan, worker, c, current, original_call, platform):
    """Complete original public prewrite chain; return no authority or proof."""
    from sqlalchemy import select

    from . import natural_spec_runtime as runtime
    from . import pa_spec_apps as spec
    from .contracts import Limits, validate_value
    from .db import attempts

    with prewrite(candidate, plan, worker, c, current, original_call, platform) as scope:
        current = scope.current
        call = scope.private["call"]
        limits = Limits(**scope.private["platform"])
        scope.hold("limits", limits)
        binding = scope.call(spec.bound, worker.store, c, current["principal_id"], current, limits)
        scope.hold("binding", binding)
        scope.call(plan.check_binding, binding)
        scope.call(spec.commit_guard, worker, c, call["call_run"], binding)
        scope.call(runtime.enabled, worker)
        scope.call(
            spec.receipts,
            worker.store,
            c,
            current,
            binding,
            pending_id=call["meta"]["operation_id"],
        )
        row = scope.call(
            lambda: (
                c.execute(
                    select(attempts).where(
                        attempts.c.id == call["aid"], attempts.c.run_id == current["id"]
                    )
                )
                .mappings()
                .one()
            )
        )
        scope.hold("attempt", row)
        runtime.require(
            row["status"] == "RECEIVED"
            and row["parameters"]["natural_spec"] == call["meta"]
            and row["response"] == call["response"]
        )
        value, usage = scope.call(
            runtime.parse,
            call["raw"],
            binding["source"],
            call["action"]["executor"]["ref"],
            call["node"],
            row["reserved_tokens"],
        )
        scope.hold("parsed", dict(value=value, usage=usage))
        runtime.require(usage == row["usage"])
        scope.call(validate_value, call["action"]["output_schema"], value)
        receipt = scope.call(
            spec.receipt_for,
            original_call["meta"]["operation_id"],
            original_call["step"],
            original_call["action"],
            binding["plan"],
            original_call["intent"],
            value,
        )
        scope.hold("receipt", receipt)
        current_admission = {}
        scope.call(
            spec.commit_guard, worker, c, call["call_run"], binding, _model_out=current_admission
        )
        runtime.require(
            type(current_admission.get("source_deadline")) in (float, int),
            "Current source deadline required after second original admission",
        )
        source_deadline = current_admission["source_deadline"]
        frozen = scope.call(worker.store._frozen_contract_after_scope, c, current)
        frozen_limits = scope.hold("fresh_frozen_limits", frozen.limits)
        roles = runtime._cold_model_roles(worker, limits, first="platform")
        scope.hold("role_limits", roles)
        deadlines = [
            scope.end,
            source_deadline,
            binding["snapshot"]["natural_spec_clock"]["deadline"],
            current["created_at"] + frozen_limits.run_seconds,
            current["created_at"]
            + binding["draft"]["candidate"]["manifest"]["runtime_limits"]["run_seconds"],
            call["meta"]["deadline"],
            current["created_at"] + call["node"].run_seconds,
        ]
        deadlines.extend(
            current["created_at"] + value.run_seconds
            for value in roles.values()
            if value is not None
        )
        import math

        runtime.require(
            all(
                (type(value) is int or type(value) is float) and math.isfinite(value) and value > 0
                for value in deadlines
            ),
            "All original G0 finite bounds required",
        )
        scope.end = min(deadlines)
    # Read the business clock AFTER the final complete-content check and scope
    # removal; original five writes follow directly in the caller's transaction.
    runtime.require(
        not worker.stop.is_set() and time.time() < min(scope.end, source_deadline),
        "Original finite settlement interval expired after owned G0 closure",
    )
    return binding, receipt


_CANDIDATE_CLASSES = tuple(
    (kind, tuple(vars(kind).items())) for kind in (_Code, MockCandidate, _Scope)
)
_CANDIDATE_FUNCTIONS = tuple(
    (name, globals()[name])
    for name in ("_codes", "_sql_current", "_execution_current", "prewrite", "run")
)
_CANDIDATE_CODE = tuple(
    (fn, fn.__code__)
    for fn in (
        *[fn for _, fn in _CANDIDATE_FUNCTIONS],
        *[
            value
            for _, items in _CANDIDATE_CLASSES
            for _, value in items
            if type(value) is types.FunctionType
        ],
    )
)
