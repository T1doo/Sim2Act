"""A logger callback is an external effect, not an owned SQL implementation."""

import logging

import pytest
from sqlalchemy import select
from test_cold_accounted_sqlite import sql_facts  # noqa: F401
from test_owned_g0_candidate import prepared
from test_owned_sqlite import hook

from sim2act import pb_natural_specs as pb
from sim2act._immutable_settlement import UnsupportedPlan
from sim2act._owned_g0_candidate import prewrite
from sim2act._owned_sqlite import writer
from sim2act.db import runs
from sim2act.errors import DomainError


class RejectHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.called = 0

    def emit(self, record):
        self.called += 1
        pytest.fail("Experimental path invoked an unqualified logging callback")


@pytest.mark.parametrize("name", ["sqlalchemy.engine.Engine", "sqlalchemy.pool.impl.QueuePool"])
@pytest.mark.parametrize("level", [logging.INFO, logging.DEBUG])
def test_enabled_sql_logging_refuses_before_connect_without_emitting(sql_facts, name, level):
    f = sql_facts
    target, handler = logging.getLogger(name), RejectHandler()
    original = target.level
    target.addHandler(handler)
    target.setLevel(level)
    try:
        with pytest.raises(UnsupportedPlan, match="logging callbacks"):
            with writer(f.worker, hook()):
                pytest.fail("Logged SQL entered owned business")
        assert handler.called == 0
    finally:
        target.removeHandler(handler)
        target.setLevel(original)


def test_new_logger_class_refuses_before_constructing_it(sql_facts):
    f = sql_facts
    calls = []
    class Unknown(logging.Logger):
        def __init__(self, *args, **kwargs):
            calls.append(True)
            super().__init__(*args, **kwargs)
    original = logging.getLoggerClass()
    logging.setLoggerClass(Unknown)
    try:
        with pytest.raises(UnsupportedPlan, match="logger configuration"):
            with writer(f.worker, hook()):
                pytest.fail("Unknown logger constructor entered owned business")
        assert calls == []
    finally:
        logging.setLoggerClass(original)


def test_engine_logging_change_after_selection_rejects_before_query(sql_facts):
    f = sql_facts
    candidate, plan, call, platform = prepared(f)
    handler = RejectHandler()
    with pytest.raises(DomainError):
        with candidate.connection(f.worker, plan) as (c, _), pb._source_reads(f.store, c):
            with prewrite(candidate, plan, f.worker, c, f.cold_job, call, platform):
                target = c.engine.logger
                original = target.level
                target.addHandler(handler)
                target.setLevel(logging.INFO)
                try:
                    c.execute(select(runs.c.id)).all()
                finally:
                    target.removeHandler(handler)
                    target.setLevel(original)
    assert handler.called == 0
    assert candidate.transactions[-1]["outcome"] == "ROLLED_BACK"
