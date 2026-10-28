"""Private SQLite writer for the default-off owned G0 experiment.

Creates a fresh, unexposed DB-API connection. Never clears callbacks/security
configuration on an existing connection, nor consumes its compiled/type caches.
The original Store, Worker, Engine identity and database file remain unchanged.
"""

from __future__ import annotations

import importlib.resources
import inspect
import json
import sqlite3
import sys
from contextlib import contextmanager
from types import CodeType, FunctionType

from sqlalchemy import event
from sqlalchemy.dialects.sqlite.pysqlite import SQLiteDialect_pysqlite
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.pool import QueuePool
from sqlalchemy.sql import sqltypes, visitors
from sqlalchemy.sql.elements import BindParameter
from sqlalchemy.util import immutabledict

from . import db
from ._immutable_settlement import UnsupportedPlan

_ISSUED = {}  # Strong per-lifetime references; removed before transaction disposal.
_CONNECT = sqlite3.connect
_DRIVER = sqlite3.Connection
with _CONNECT(":memory:") as _bootstrap_driver:
    _NATIVE_SQL_FUNCTIONS = _bootstrap_driver.execute(
        "SELECT name,builtin,narg,flags,enc,type FROM pragma_function_list ORDER BY name,narg,builtin,flags,enc,type"
    ).fetchall()
_bootstrap_driver.close()
del _bootstrap_driver
_AFFINITY = tuple(
    (kind, kind()._type_affinity)
    for kind in (sqltypes.String, sqltypes.Integer, sqltypes.Float, sqltypes.Boolean, sqltypes.JSON)
)
_CATALOG = json.loads(
    importlib.resources.files(__package__).joinpath("_owned_sql_catalog.json").read_text()
)
_TYPES = tuple(
    (table, tuple(table.c), tuple((column, column.type) for column in table.c))
    for table in db.meta.tables.values()
)


# Code/descriptor/operator witnesses from the already loaded original producer
# modules. No row, permission, query result or successful validation is stored.
_QUERY_KINDS = []
_QUERY_OPERATORS = []
for _key in _CATALOG["queries"]:
    _module_name, _name = _key.split(":", 1)
    _module = sys.modules.get(_module_name)
    if _module is None:
        continue
    _statement = vars(_module).get(_name)
    if _statement is None:
        continue
    for _node in visitors.iterate(_statement):
        if not any(type(_node) is kind for kind in _QUERY_KINDS):
            _QUERY_KINDS.append(type(_node))
        for _field in ("operator", "negate"):
            _operator = vars(_node).get(_field)
            if _operator is not None and not any(_operator is prior for prior in _QUERY_OPERATORS):
                _QUERY_OPERATORS.append(_operator)
_QUERY_KINDS = tuple(_QUERY_KINDS)
_QUERY_OPERATORS = tuple(_QUERY_OPERATORS)
_QUERY_SLOTS = tuple(
    (kind, name, inspect.getattr_static(kind, name))
    for root in _QUERY_KINDS
    for kind in root.__mro__
    if kind is not object
    for name in ("__getattribute__", "get_children", "_compiler_dispatch")
    if hasattr(kind, name)
)
_QUERY_CODE = tuple(
    (fn, fn.__code__)
    for fn in (*_QUERY_OPERATORS, *[value for _, _, value in _QUERY_SLOTS])
    if type(fn) is FunctionType
)
_ITERATE, _ITERATE_CODE = visitors.iterate, visitors.iterate.__code__


def _plain(value):
    kind = type(value)
    if kind is str or kind is int or kind is float or kind is bool or value is None:
        return (kind.__name__, value)
    if kind is list or kind is tuple:
        return (kind.__name__, tuple(_plain(item) for item in value))
    if kind is dict and all(type(key) is str for key in value):
        return ("dict", tuple((key, _plain(item)) for key, item in sorted(value.items())))
    raise UnsupportedPlan("Unknown SQL declaration value")


def declarations(dialect):
    """Fixed original table/type declarations and bounded static SQL catalogue."""
    if (
        visitors.iterate is not _ITERATE
        or _ITERATE.__code__ is not _ITERATE_CODE
        or any(
            inspect.getattr_static(kind, name) is not value for kind, name, value in _QUERY_SLOTS
        )
        or any(fn.__code__ is not code for fn, code in _QUERY_CODE)
    ):
        raise UnsupportedPlan("Unknown SQL expression code")
    actual = {}
    for table, columns, declared in _TYPES:
        current_columns = tuple(table.c)
        if len(current_columns) != len(columns) or any(
            a is not b for a, b in zip(current_columns, columns, strict=True)
        ):
            raise UnsupportedPlan("SQL table columns changed")
        for column, original_type in declared:
            if column.type is not original_type:
                raise UnsupportedPlan("SQL column type replaced")
            raw = vars(original_type)
            if any(
                callable(value)
                for key, value in raw.items()
                if key != "_type_affinity" and key != "dispatch"
            ):
                raise UnsupportedPlan("Shadow SQL type processor")
            fields = {
                key: value
                for key, value in raw.items()
                if not key.startswith("_") and key != "dispatch"
            }
            expected = _CATALOG["types"][table.name][column.name]
            if (
                type(original_type).__module__ != "sqlalchemy.sql.sqltypes"
                or type(original_type).__name__ != expected["kind"]
            ):
                raise UnsupportedPlan("Unknown SQL type implementation")
            if _plain(fields) != _plain(expected["declaration"]):
                raise UnsupportedPlan("SQL type declaration changed")
            if any(
                callable(value)
                for key, value in raw.items()
                if key != "_type_affinity" and key != "dispatch"
            ):
                raise UnsupportedPlan("Shadow SQL type processor")
            if "_type_affinity" in raw and not any(
                type(original_type) is kind and raw["_type_affinity"] is affinity
                for kind, affinity in _AFFINITY
            ):
                raise UnsupportedPlan("Unknown SQL type affinity")
            if original_type._variant_mapping:
                raise UnsupportedPlan("Unknown SQL type variant")
    for key, expected in _CATALOG["queries"].items():
        module_name, name = key.split(":", 1)
        module = sys.modules.get(module_name)
        if module is None:
            raise UnsupportedPlan("SQL producer module not loaded")
        statement = vars(module).get(name)
        if (
            type(statement).__module__ != "sqlalchemy.sql.selectable"
            or type(statement).__name__ != "Select"
        ):
            raise UnsupportedPlan("Unknown static SQL statement")
        options = object.__getattribute__(statement, "_execution_options")
        if type(options) is not dict and type(options) is not immutabledict:
            raise UnsupportedPlan("Unknown SQL execution options")
        if options:
            raise UnsupportedPlan("External statement execution options")
        # Declared library expressions only. Refuse callable bound values before
        # compile/params can evaluate them; no outside result cache is consulted.
        for node in visitors.iterate(statement):
            kind = type(node)
            if not any(kind is allowed for allowed in _QUERY_KINDS):
                raise UnsupportedPlan("Unknown SQL expression type")
            raw = object.__getattribute__(node, "__dict__")
            if any(
                key in raw for key in ("get_children", "_compiler_dispatch", "__getattribute__")
            ):
                raise UnsupportedPlan("Shadow SQL expression method")
            for name in ("operator", "negate"):
                operator = raw.get(name)
                if operator is not None and not any(
                    operator is original for original in _QUERY_OPERATORS
                ):
                    raise UnsupportedPlan("Unknown SQL expression operator")
            annotations = raw.get("_annotations")
            if (
                annotations is not None
                and type(annotations) is not dict
                and type(annotations) is not immutabledict
            ):
                raise UnsupportedPlan("Unknown SQL annotation storage")
            if annotations:
                raise UnsupportedPlan("Unknown SQL expression annotation")
            if any(base is BindParameter for base in kind.__mro__):
                if node.callable is not None:
                    raise UnsupportedPlan("Callable SQL parameter")
                _plain(node.value)
        compiled = statement.compile(dialect=dialect)
        if str(compiled) != expected["sql"] or _plain(compiled.params) != _plain(
            expected["parameters"]
        ):
            raise UnsupportedPlan("Original SQL constant changed")
        actual[key] = statement
    return actual


def _schema(driver):
    databases = driver.execute("PRAGMA database_list").fetchall()
    if len(databases) != 1 or databases[0][1] != "main":
        raise UnsupportedPlan("Attached or temporary SQLite database")
    rows = driver.execute(
        "SELECT type,name,tbl_name,sql FROM sqlite_schema WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name"
    ).fetchall()
    if [list(row) for row in rows] != _CATALOG["schema"]:
        raise UnsupportedPlan("Actual SQLite schema differs from fixed declaration")
    # A private driver starts without authorizers, progress/trace callbacks,
    # attachments, temporary objects or Python UDFs. Assert the visible extent;
    # never try to scrub an existing caller-owned connection into compliance.
    functions = driver.execute(
        "SELECT name,builtin,narg,flags,enc,type FROM pragma_function_list ORDER BY name,narg,builtin,flags,enc,type"
    ).fetchall()
    if functions != _NATIVE_SQL_FUNCTIONS:
        added = set(functions) - set(_NATIVE_SQL_FUNCTIONS)
        known = [
            (value[0], value[1], value[2], value[3])
            for value in added
            if value[0] in ("floor", "regexp", "match")
        ]
        raise UnsupportedPlan(
            "Unexpected private SQLite function; known="
            + str(known)
            + "; other_count="
            + str(len(added) - len(known))
        )
    return driver.execute("PRAGMA schema_version").fetchone()[0]


def _dispatch_empty(*owners):
    return all(
        not list(getattr(owner.dispatch, name))
        for owner in owners
        for name in owner.dispatch._event_names
    )


def _epoch_current(fn):
    codes = db.Store.__init__.__code__.co_consts
    expected = next(
        (
            code
            for code in codes
            if type(code) is CodeType and code.co_name == "proof_write_boundary"
        ),
        None,
    )
    return (
        type(fn) is FunctionType
        and fn.__code__ == expected
        and fn.__globals__ is vars(db)
        and fn.__closure__ is None
        and fn.__defaults__ is None
        and fn.__kwdefaults__ is None
    )


class Writer:
    """Owned connection provenance, valid only inside this one transaction."""

    def __init__(self, worker):
        self.worker = worker
        self.store = worker.store
        self.original_engine = worker.store.engine
        self.connection = self.driver = self.pool = None
        self.active = False
        self.committed = False
        self.rolled_back = False

    def check(self):
        c = self.connection
        if (
            not self.active
            or not connection_owned(self.store, c)
            or not self.transaction.is_active
            or c is None
            or c.closed
            or c.connection.driver_connection is not self.driver
            or c.dialect is not self.dialect
            or c.get_transaction() is not self.transaction
            or self.driver.row_factory is not None
            or self.driver.text_factory is not str
            or self.driver.execute("PRAGMA schema_version").fetchone()[0] != self.schema_version
            or c._execution_options.get("compiled_cache", object()) is not None
        ):
            raise UnsupportedPlan("Private SQLite writer provenance changed")


@contextmanager
def writer(worker, epoch_hook):
    """No Graph/approval/PASS transfer. Call only under the original renew lock."""
    if not worker.store.test_only or not worker.store.sqlite:
        raise UnsupportedPlan("Owned SQLite writer is synthetic only")
    url = worker.store.engine.url
    if url.drivername != "sqlite" or url.query or not url.database or url.database == ":memory:":
        raise UnsupportedPlan("Owned writer requires an existing file database")
    if sqlite3.connect is not _CONNECT:
        raise UnsupportedPlan("Unknown DB-API creator")
    if not _epoch_current(epoch_hook):
        raise UnsupportedPlan("Original epoch hook required")
    owned = Writer(worker)
    dialect = SQLiteDialect_pysqlite(dbapi=sqlite3)
    owned.dialect = dialect
    declarations(dialect)

    def create():
        if owned.driver is not None:
            raise UnsupportedPlan("Owned writer cannot reconnect")
        driver = _CONNECT(url.database, timeout=5, check_same_thread=True)
        if type(driver) is not _DRIVER:
            driver.close()
            raise UnsupportedPlan("Unknown owned DB-API driver")
        owned.driver = driver
        return driver

    pool = QueuePool(create, pool_size=1, max_overflow=0, dialect=dialect)
    owned.pool = pool
    engine = Engine(pool, dialect, url, execution_options={})
    owned.engine = engine
    # Inspect class/global listeners before a driver is created or can escape.
    if engine._has_events or not _dispatch_empty(engine, dialect, pool):
        pool.dispose()
        raise UnsupportedPlan("Unknown global connection listener")
    c = None
    try:
        c = Connection(engine, pool.connect(), _has_events=False, _allow_revalidate=False)
        owned.connection = c
        if not _dispatch_empty(c):
            raise UnsupportedPlan("Unknown global Connection listener")
        dialect.initialize(c)
        c.rollback()
        # Preserve the private Engine for transaction AND error handling. The
        # Store remains bound to its original Engine; its narrow provenance
        # relation recognises only this issued connection for this lifetime.
        c._execution_options = immutabledict({"compiled_cache": None})
        event.listen(c, "before_cursor_execute", epoch_hook)
        c.exec_driver_sql("BEGIN IMMEDIATE")
        owned.schema_version = _schema(owned.driver)
        owned.transaction = c.get_transaction()
        owned.active = True
        _ISSUED[id(c)] = owned
        owned.check()
        try:
            yield owned
            owned.check()
            c.commit()
            if owned.driver.in_transaction:
                raise RuntimeError("Owned SQLite commit was not confirmed")
            owned.committed = True
        except BaseException:
            c.rollback()
            owned.rolled_back = not owned.driver.in_transaction
            raise
    finally:
        owned.active = False
        if c is not None:
            _ISSUED.pop(id(c), None)
        if c is not None:
            c.close()
        pool.dispose()


def connection_owned(store, c):
    """Header relation only, not an authorization, PASS or cached SQL result."""
    if type(c) is not Connection or not store.test_only or not store.sqlite:
        return False
    issued = _ISSUED.get(id(c))
    return (
        type(issued) is Writer
        and issued.active
        and issued.store is store
        and issued.connection is c
        and store.engine is issued.original_engine
        and c.engine is issued.engine
        and c.dialect is issued.dialect
        and c.get_transaction() is issued.transaction
        and not c.closed
        and c.connection.driver_connection is issued.driver
        and issued.worker.store is store
    )


_SQLITE_CLASS = (Writer, tuple(vars(Writer).items()))
_SQLITE_FUNCTIONS = tuple(
    (name, globals()[name])
    for name in (
        "_plain",
        "declarations",
        "_schema",
        "_dispatch_empty",
        "_epoch_current",
        "writer",
        "connection_owned",
    )
)
_SQLITE_CODE = tuple(
    (fn, fn.__code__)
    for fn in (
        *[fn for _, fn in _SQLITE_FUNCTIONS],
        *[value for _, value in _SQLITE_CLASS[1] if type(value) is FunctionType],
    )
)
