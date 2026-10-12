"""PREPARED, NOT YET CALIBRATED OR EXECUTED.

SQLite private-cell fault injection. Full selected cells run an error UDF.
Only exact, enumerated JSON identifier paths are replaced by dedicated view
columns whose UDF returns the selected identifier, wrapped in a JSON object.
The latter necessarily evaluates its backing JSON inside the trusted projection;
this is not a claim of zero backing JSON evaluation. No body is returned from it.
SELECTs are rewritten; mutations keep their original production semantics.
"""

import json
import re
import sqlite3
from contextlib import AbstractContextManager

from sqlalchemy import event
from sqlalchemy.exc import DatabaseError


TOKEN = re.compile(r"'(?:''|[^'])*'|\"(?:\"\"|[^\"])*\"|`[^`]*`|\[[^\]]*\]|--[^\n]*|/\*.*?\*/|[A-Za-z_][A-Za-z_0-9]*|\s+|.", re.S)


def name(token):
    return token.strip('"`[]').lower()


def path_parts(value):
    """Exact SQLite/SQLAlchemy field and nonnegative array-index path dialect."""
    if not isinstance(value, str) or not value.startswith("$"):
        return None
    parts, offset = [], 1
    pattern = re.compile(r'\."([A-Za-z_][A-Za-z_0-9]*)"|\.([A-Za-z_][A-Za-z_0-9]*)|\[([0-9]+)\]')
    while offset < len(value):
        match = pattern.match(value, offset)
        if not match:
            return None
        parts.append(int(match.group(3)) if match.group(3) is not None else match.group(1) or match.group(2))
        offset = match.end()
    return tuple(parts)


class IdentifierPrivateBarrier(AbstractContextManager):
    """Rules: table -> key, rows, private columns, enumerated column/path pairs."""

    def __init__(self, store, rules):
        if not store.sqlite:
            raise ValueError("SQLite-only independent barrier")
        self.rules = rules
        self.blocked, self.private_evaluated, self.identifier_evaluated, self.statements = [], [], [], []
        self.engines, self.connections = [], []
        self.projections = {}
        for table, rule in rules.items():
            for column, paths in rule.get("paths", {}).items():
                for path in sorted(paths, key=repr):
                    key = (table, column, tuple(path))
                    self.projections[key] = "__identifier_" + str(len(self.projections))
        self.attach(store)

    def _cell(self, table, rid, column, value):
        fact = {"table": table, "row_id": rid, "column": column}
        self.private_evaluated.append(fact)
        if rid in self.rules[table]["rows"]:
            self.blocked.append(fact)
            raise ValueError("Independent protected full private cell evaluated")
        return value

    def _identifier(self, table, rid, column, path_json, value):
        parts = tuple(json.loads(path_json))
        if (table, column, parts) not in self.projections:
            raise ValueError("Unenumerated identifier projection")
        self.identifier_evaluated.append({"table": table, "row_id": rid, "column": column, "path": parts})
        current = json.loads(value) if value is not None else None
        for part in parts:
            if isinstance(part, int):
                current = current[part] if isinstance(current, list) and part < len(current) else None
            else:
                current = current.get(part) if isinstance(current, dict) else None
        # The whitelist contains identifiers, discriminators and identifier arrays.
        # Never return an arbitrary object through an accidentally changed shape.
        if isinstance(current, dict) or isinstance(current, list) and any(not isinstance(item, str) for item in current):
            raise ValueError("Identifier projection contains body/object")
        return json.dumps({"value": current}, separators=(",", ":"))

    def _authorize(self, action, table, column, database, source):
        if (action == sqlite3.SQLITE_READ and database == "main" and table in self.rules
            and column in self.rules[table]["private"] and source != "ir_private_" + table):
            self.blocked.append({"table": table, "column": column, "direct_main": True})
            return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK

    def _checkout(self, raw, record, proxy):
        if any(raw is existing for existing in self.connections):
            return
        raw.create_function("ir_full_private_cell", 4, self._cell)
        raw.create_function("ir_identifier", 5, self._identifier)
        for table, rule in self.rules.items():
            columns = [row[1] for row in raw.execute('PRAGMA main.table_info("' + table + '")')]
            expressions = []
            for column in columns:
                expr = (f"ir_full_private_cell('{table}', \"{rule['key']}\", '{column}', \"{column}\")"
                        if column in rule["private"] else f'"{column}"')
                expressions.append(expr + ' AS "' + column + '"')
            for (source_table, column, path), alias in self.projections.items():
                if source_table == table:
                    literal = json.dumps(path, separators=(",", ":")).replace("'", "''")
                    expressions.append(f"ir_identifier('{table}', \"{rule['key']}\", '{column}', '{literal}', \"{column}\") AS \"{alias}\"")
            raw.execute(f'CREATE TEMP VIEW "ir_private_{table}" AS SELECT {", ".join(expressions)} FROM main."{table}"')
        raw.set_authorizer(self._authorize)
        self.connections.append(raw)

    def _rewrite(self, statement, parameters):
        tokens = [(m.group(), m.start(), m.end()) for m in TOKEN.finditer(statement)
                  if not m.group().isspace() and not m.group().startswith(("--", "/*"))]
        if not tokens or tokens[0][0].upper() not in {"SELECT", "WITH"}:
            return statement, parameters
        if any(name(t[0]).startswith("ir_private_") or name(t[0]).startswith("__identifier_") for t in tokens):
            self.blocked.append({"reserved_namespace": True})
            raise DatabaseError(statement, parameters, sqlite3.OperationalError("Reserved independent barrier namespace"))
        if tokens[0][0].upper() == "WITH" and any(
            name(tokens[i][0]) in self.rules and tokens[i + 1][0].upper() == "AS" and tokens[i + 2][0] == "("
            for i in range(len(tokens) - 2)
        ):
            self.blocked.append({"colliding_table_cte": True})
            raise DatabaseError(statement, parameters, sqlite3.OperationalError("Colliding barrier table CTE"))
        aliases = {table: table for table in self.rules}
        for i, (token, _, _) in enumerate(tokens[:-1]):
            if token.upper() in {"FROM", "JOIN"} and name(tokens[i + 1][0]) in self.rules:
                table = name(tokens[i + 1][0]); j = i + 2
                if j < len(tokens) and tokens[j][0].upper() == "AS":
                    j += 1
                if j < len(tokens) and re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*', name(tokens[j][0])) and tokens[j][0].upper() not in {"WHERE", "JOIN", "ON", "ORDER", "GROUP", "LIMIT", "LEFT", "RIGHT", "INNER", "OUTER", "UNION"}:
                    aliases[name(tokens[j][0])] = table
        bind_indexes, count = {}, 0
        for i, (token, _, _) in enumerate(tokens):
            if token == "?":
                bind_indexes[i] = count; count += 1
        if count and not isinstance(parameters, (tuple, list)):
            raise ValueError("Independent barrier requires SQLite positional binds")

        def parse(i):
            if i >= len(tokens):
                return None
            token = tokens[i][0]
            upper = token.upper()
            if upper in {"JSON_EXTRACT", "JSON_QUOTE"} and i + 1 < len(tokens) and tokens[i + 1][0] == "(":
                child = parse(i + 2)
                if child is None:
                    return None
                end, qualifier, table, column, parts, consumed = child
                if upper == "JSON_QUOTE":
                    return (end + 1, qualifier, table, column, parts, consumed) if end < len(tokens) and tokens[end][0] == ")" else None
                if end + 2 >= len(tokens) or tokens[end][0] != "," or tokens[end + 2][0] != ")":
                    return None
                raw = tokens[end + 1][0]
                if raw == "?":
                    index = bind_indexes[end + 1]; value = parameters[index]; consumed = consumed | {index}
                elif raw.startswith("'"):
                    value = raw[1:-1].replace("''", "'")
                else:
                    return None
                extension = path_parts(value)
                return (end + 3, qualifier, table, column, parts + extension, consumed) if extension is not None else None
            if i + 2 < len(tokens) and tokens[i + 1][0] == ".":
                qualifier, column = tokens[i][0], name(tokens[i + 2][0])
                table = aliases.get(name(qualifier))
                if table in self.rules and column in self.rules[table]["private"]:
                    return i + 3, qualifier, table, column, (), set()
            return None

        candidates = []
        for i, token in enumerate(tokens):
            if token[0].upper() != "JSON_EXTRACT":
                continue
            parsed = parse(i)
            if parsed is None:
                continue
            end, qualifier, table, column, parts, consumed = parsed
            alias = self.projections.get((table, column, parts))
            if alias:
                candidates.append((tokens[i][1], tokens[end - 1][2], f"JSON_EXTRACT({qualifier}.\"{alias}\", '$.value')", consumed))
        replacements, dropped = [], set()
        for start, end, replacement, consumed in sorted(candidates, key=lambda item: (item[0], -item[1])):
            if any(a <= start < b for a, b, _, _ in replacements):
                continue
            replacements.append((start, end, replacement, consumed)); dropped |= consumed
        for start, end, replacement, _ in sorted(replacements, reverse=True):
            statement = statement[:start] + replacement + statement[end:]
        if dropped:
            parameters = tuple(v for i, v in enumerate(parameters) if i not in dropped)
        # Re-tokenize after expression substitution; preserve literal/comment text.
        pieces, significant = [], []
        for match in TOKEN.finditer(statement):
            token = match.group(); normalized = name(token)
            explicit = len(significant) >= 2 and significant[-1] == "." and name(significant[-2]) in {"main", "temp"}
            pieces.append('"ir_private_' + normalized + '"' if normalized in self.rules and not explicit else token)
            if not token.isspace() and not token.startswith(("--", "/*")):
                significant.append(token)
        return "".join(pieces), parameters

    def _trace(self, conn, cursor, statement, parameters, context, many):
        executed, bound = self._rewrite(statement, parameters)
        self.statements.append({"sql": statement, "executed_sql": executed, "bind_count_before": len(parameters), "bind_count_after": len(bound)})
        return executed, bound

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
            for table in self.rules:
                raw.execute('DROP VIEW "ir_private_' + table + '"')
            raw.create_function("ir_full_private_cell", 4, None)
            raw.create_function("ir_identifier", 5, None)
        return False


def pa_rules(run_ids=(), resource_ids=(), card_ids=()):
    """Allowed projections match the finite P-A gate, plus namespace-only classifier hints."""
    return {
        "runs": dict(key="id", rows=set(run_ids), private={"context", "result", "goal", "error"},
                     paths={"context": {("kind",), ("namespace",)}}),
        "run_contracts": dict(key="run_id", rows=set(run_ids), private={"snapshot"}, paths={"snapshot": {
            ("application_generation", "version"), ("application_generation", "app_id"), ("application_generation", "activation", "approval_id"),
            ("runtime_id",), ("goal", "owner_id"), ("goal", "project_id"), ("goal", "resource_refs"),
            ("resources", 0, "resource_id"), ("source_goal_card", "snapshot", "content", "resource_refs"),
            ("contract", "namespace"), ("namespace",),
        }}),
        "goal_card_versions": dict(key="card_id", rows=set(card_ids), private={"snapshot"},
                                  paths={"snapshot": {("content", "resource_refs")}}),
        "resources": dict(key="id", rows=set(resource_ids), private={"content", "hash"}, paths={}),
        "attempts": dict(key="run_id", rows=set(run_ids), private={"parameters", "response"},
                        paths={"parameters": {("generation_activation", "approval_id")}}),
    }
