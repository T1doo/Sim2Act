"""Candidate refusal boundaries; no product grant, Worker or model exchange."""
import gc
import json
import subprocess
import sys
from pathlib import Path
from types import FunctionType

import pytest
from test_cold_accounted_sqlite import forbid_execution as forbid_execution
from test_cold_accounted_sqlite import sql_facts as sql_facts

from sim2act import _cold_cohort_backend as candidate
from sim2act import natural_live_admission as gate


def test_ordinary_gc_policy_is_never_changed(sql_facts):
    assert candidate._READY
    model = sql_facts.contract
    raw = model.model_dump()
    prior = gc.isenabled()
    gc.enable()
    try:
        assert candidate._PROBE() is False
        assert candidate.try_triple(type(model), model, raw) is None
        assert gc.isenabled()
    finally:
        if not prior:
            gc.disable()


def test_already_disabled_gc_is_preserved_and_content_is_fresh(sql_facts):
    model = sql_facts.contract
    raw = model.model_dump()
    prior = gc.isenabled()
    gc.disable()
    try:
        assert candidate._PROBE() is True
        assert candidate.try_triple(type(model), model, raw) is True
        raw['expires_at'] += 1
        with pytest.raises(Exception, match='Typed trial storage changed'):
            candidate.try_triple(type(model), model, raw)
        assert not gc.isenabled()
    finally:
        if prior:
            gc.enable()


def test_same_helper_identity_with_changed_code_declines(sql_facts):
    model = sql_facts.contract
    raw = model.model_dump()
    fn, code = gate.require, gate.require.__code__
    reference = FunctionType(code,fn.__globals__,argdefs=fn.__defaults__)
    calls = []
    names = ('_cohort_test_reference','_cohort_test_calls')
    assert all(name not in fn.__globals__ for name in names)
    fn.__globals__.update(zip(names,(reference,calls),strict=True))
    def hooked(ok,message='Exact natural trial changed'):
        _cohort_test_calls.append(ok)
        return _cohort_test_reference(ok,message)
    prior = gc.isenabled()
    gc.disable()
    try:
        fn.__code__ = hooked.__code__
        assert candidate.native.current() is False
        assert candidate.try_triple(type(model),model,raw) is None
        assert calls == []
    finally:
        fn.__code__ = code
        for name in names:
            del fn.__globals__[name]
        if prior:
            gc.enable()


def test_foreign_gc_namespace_key_never_dispatches_equality(sql_facts):
    calls = []
    class Key:
        def __hash__(self):
            return hash('callbacks')
        def __eq__(self,other):
            calls.append('eq')
            return False
    key = Key()
    namespace = vars(gc)
    namespace[key] = 'diagnostic'
    calls.clear()
    try:
        assert candidate.native.current() is False
        assert calls == []
    finally:
        del namespace[key]


@pytest.mark.parametrize('damage',['gc-callback','helper-code','serializer-and-schema',
    'raw-equal-alias','stream-require-alias','gate-type-shadow'])
def test_bootstrap_never_promotes_unknown_metadata(damage,tmp_path):
    program = r'''
import gc,json
from sim2act import natural_spec_runtime
from sim2act import _cold_typed_stream as stream
from sim2act import natural_live_admission as gate
from sim2act.contracts import AppManifest
from pydantic_core import SchemaSerializer,core_schema
damage=DAMAGE
if damage=='gc-callback':
 gc.callbacks.append(lambda *a:None)
elif damage=='helper-code':
 def changed(*args,**kwargs):return True
 stream._stream_values.__code__=changed.__code__
elif damage=='serializer-and-schema':
 schema=core_schema.any_schema(serialization=core_schema.plain_serializer_function_ser_schema(lambda value: {'wrong':True}))
 AppManifest.__pydantic_core_schema__=schema
 AppManifest.__pydantic_serializer__=SchemaSerializer(schema)
elif damage=='raw-equal-alias':
 gate._RAW_EQUAL=lambda *a:True
elif damage=='stream-require-alias':
 stream.require=lambda *a:None
elif damage=='gate-type-shadow':
 gate.type=lambda *a:dict
from sim2act import _cold_cohort_backend as candidate
assert candidate._READY is False
assert candidate.ENABLED is False
print(json.dumps({'ready':candidate._READY,'runtime_enabled':candidate.ENABLED,'kind':damage}))
'''.replace('DAMAGE',repr(damage))
    result = subprocess.run([sys.executable,'-X','faulthandler','-c',program],
        text=True,capture_output=True,timeout=20)
    (tmp_path/'stdout.txt').write_text(result.stdout)
    (tmp_path/'stderr.txt').write_text(result.stderr)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['ready'] is False
