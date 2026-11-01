"""Passive before/after diagnostic counters; no model, clock or callee edits."""
import json
from types import BuiltinFunctionType
import pytest


@pytest.fixture(autouse=True)
def dictionary_version_counts(request,tmp_path):
    from sim2act import _cold_graph_structure as native
    entry=native.read_structure_counts
    assert type(entry) is BuiltinFunctionType and entry.__self__ is native
    before=entry()
    yield
    assert native.read_structure_counts is entry
    after=entry()
    delta={phase:{name:after[phase][name]-value for name,value in row.items()}
           for phase,row in before.items()}
    (tmp_path/'dictionary-version-counts.json').write_text(json.dumps(dict(
        classification='DIAGNOSTIC_VERSION_FACT_COUNTERS_NOT_AUTHORITY_OR_UNIQUE_WORKLOAD',
        test=request.node.nodeid,before=before,after=after,delta=delta,
        scope='All scopes in this test. pre/post are Graph phase labels, other includes proof driver scopes.',
        limits='Counts overlap across publication versions. Skipped logical edges are conservative work units, not CPU instructions or runtime savings.'
    ),indent=2)+'\n')
