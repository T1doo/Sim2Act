"""SQLite fault injection: reject actual evaluation of protected historical cells.

SELECTs use guarded TEMP views; writes keep the original main-table semantics.
The guard runs when SQLite evaluates a cell, regardless of query parameters,
aliases, joins, IN, subqueries or aggregates. Direct main-table reads cannot
bypass the views. This is a test barrier, not a production authorization layer.
"""

import re
import sqlite3
from contextlib import AbstractContextManager

from sqlalchemy import event, select
from sqlalchemy.exc import DatabaseError

from sim2act.db import operation_intents, operations, resources, run_contracts, runs


class PrivateReadBarrier(AbstractContextManager):
    def __init__(self, store, old_runs, old_resources=()):
        if not store.sqlite:
            raise ValueError("Actual row-cell barrier requires isolated SQLite")
        old_runs = set(old_runs)
        with store.engine.connect() as c:
            old_operations = set(c.execute(select(operations.c.id).where(
                operations.c.run_id.in_(old_runs))).scalars())
        self.rules = {
            "runs": (runs, "id", set(old_runs), {"context", "result", "goal", "resource_refs", "error"}),
            "run_contracts": (run_contracts, "run_id", set(old_runs), {"snapshot"}),
            "resources": (resources, "id", set(old_resources), {"content", "hash"}),
            "operations": (operations, "run_id", old_runs, {"receipt"}),
            "operation_intents": (operation_intents, "operation_id", old_operations, {"request"}),
        }
        self.blocked, self.evaluated, self.statements = [], [], []
        self.engines, self.connections = [], []
        self.attach(store)

    def _cell(self, table, rid, column, value):
        fact = {"table": table, "row_id": rid, "column": column}
        self.evaluated.append(fact)
        if rid in self.rules[table][2]:
            self.blocked.append(fact)
            raise ValueError("Protected historical private cell evaluated")
        return value

    def _authorize(self, action, table, column, database, source):
        if (action == sqlite3.SQLITE_READ and database == "main" and table in self.rules
                and column in self.rules[table][3]
                and source != "private_read_" + table):
            self.blocked.append({"table": table, "column": column, "direct_main": True})
            return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK

    def _checkout(self, raw, record, proxy):
        if any(raw is existing for existing in self.connections):
            return
        raw.create_function("private_cell_guard", 4, self._cell)
        for name, (table, key, _, private) in self.rules.items():
            columns = [column.name for column in table.columns]
            expressions = [
                (f"private_cell_guard('{name}', \"{key}\", '{column}', \"{column}\")"
                 if column in private else f'"{column}"') + f' AS "{column}"'
                for column in columns
            ]
            raw.execute(f'CREATE TEMP VIEW "private_read_{name}" AS SELECT {", ".join(expressions)} FROM main."{name}"')
        raw.set_authorizer(self._authorize)
        self.connections.append(raw)

    def _trace(self, conn, cursor, statement, parameters, context, many):
        original = statement
        tokens = re.findall(r"'(?:''|[^'])*'|\"(?:\"\"|[^\"])*\"|`[^`]*`|\[[^\]]*\]|--[^\n]*|/\*.*?\*/|[A-Za-z_][A-Za-z_0-9]*|\s+|.", statement, re.S)
        meaningful = [t for t in tokens if not t.isspace() and not t.startswith(("--", "/*"))]
        if meaningful and meaningful[0].upper() in {"SELECT", "WITH"}:
            # Lex tokens, preserving literals/comments and explicit main bypasses.
            # No parameter content is used to decide whether any cell is private.
            significant = []
            for i, token in enumerate(tokens):
                name = token.strip('"`[]').lower()
                if name.startswith("private_read_"):
                    # The authorizer's source is also the CTE name. Reject caller
                    # references to our reserved namespace before substituting
                    # views, otherwise a same-name CTE can impersonate a view.
                    self.blocked.append({"reserved_view_reference": name})
                    raise DatabaseError(original, parameters,
                                        sqlite3.OperationalError("Reserved barrier view namespace"))
                if name in self.rules and not (
                    len(significant) >= 2 and significant[-1] == "."
                    and significant[-2].strip('"`[]').lower() in {"main", "temp"}
                ):
                    tokens[i] = '"private_read_' + name + '"'
                if not token.isspace() and not token.startswith(("--", "/*")):
                    significant.append(token)
            statement = "".join(tokens)
        self.statements.append({"sql": original, "executed_sql": statement, "parameters": repr(parameters)})
        return statement, parameters

    def attach(self, store):
        if store.engine in self.engines:
            return
        self.engines.append(store.engine)
        event.listen(store.engine, "checkout", self._checkout)
        event.listen(store.engine, "before_cursor_execute", self._trace, retval=True)

    def __exit__(self, *exc):
        for engine in self.engines:
            event.remove(engine, "checkout", self._checkout)
            event.remove(engine, "before_cursor_execute", self._trace)
        for raw in self.connections:
            raw.set_authorizer(None)
            for name in self.rules:
                raw.execute(f'DROP VIEW "private_read_{name}"')
            raw.create_function("private_cell_guard", 4, None)
        return False
