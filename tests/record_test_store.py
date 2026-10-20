"""Cold connections for the record workflow must keep the owned fixture schema."""

import re

from sim2act.db import Store


def reopen_record_test_store(source):
    if type(source) is not Store or not source.test_only:
        raise ValueError("Only an explicit record test Store can be reopened")
    options = dict(source.engine.get_execution_options())
    if not source.sqlite:
        mapping = options.get("schema_translate_map")
        schema = mapping.get(None) if isinstance(mapping, dict) else None
        if (not isinstance(schema, str) or re.fullmatch(r"test_[a-f0-9]{32}", schema) is None
                or any(key not in (None, "_none") or value != schema for key, value in mapping.items())):
            raise ValueError("An exact owned PostgreSQL test schema is required before reopening")
        # initialize() permits SQLAlchemy's same-schema internal alias. Drop the
        # compiler-added alias and use a fresh map for the independent engine.
        options["schema_translate_map"] = {None: schema}
    cold = Store(source.engine.url.render_as_string(hide_password=False), test_only=True)
    if options:
        cold.engine = cold.engine.execution_options(**options)
    return cold
