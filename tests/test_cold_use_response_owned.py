"""Per-use ownership keeps fixed routing and complete code registration gates."""
import subprocess
import sys
import pytest
from accounted_sqlite_fixture import segment
from test_cold_accounted_sqlite import sql_facts,forbid_execution
from sim2act import pb_natural_uses as use,_cold_source_packet as owned
from sim2act.errors import DomainError


@pytest.mark.parametrize('module,name',[
    ('use','_use_pair'),('spec','scope_gate'),('spec','pair'),
])
def test_native_graph_rejects_synthetic_scope_forwarders_before_sql(sql_facts,monkeypatch,module,name):
    """Legacy scope spies replace qualified code; they cannot grant native entry."""
    from sim2act import pa_spec_apps as spec
    from sqlalchemy import event
    f=sql_facts;executed=[];sql=[]
    def replacement(*args,**kwargs):
        executed.append(True)
        return True
    def observed(c,cursor,statement,parameters,context,executemany):sql.append(statement)
    monkeypatch.setattr({'use':use,'spec':spec}[module],name,replacement)
    with f.store.tx() as c:
        event.listen(c,'after_cursor_execute',observed)
        try:
            with pytest.raises(DomainError,match='Complete Source code changed') as error:
                with segment(f,c,phase='pre'):raise AssertionError('changed code entered graph')
            assert error.value.code=='VERSION_CONFLICT'
            assert executed==[] and sql==[]
        finally:event.remove(c,'after_cursor_execute',observed)


@pytest.mark.parametrize('field',['field','namespace','use','meta','consent','body_type','route','storage'])
def test_actual_graph_checkpoint_rejects_fixed_family_mutation(sql_facts,field):
    f=sql_facts;reached=False
    with pytest.raises(DomainError),f.store.tx() as c,segment(f,c,phase='pre') as s:
        family=use.PB;storage=object.__getattribute__(family,'__dict__')
        old=storage.get(field)
        try:
            if field=='storage':object.__setattr__(family,'__dict__',dict(storage))
            else:storage[field]=object() if field=='body_type' else 'changed-fixed-routing'
            reached=True
            use._use_read_checkpoint(f.store,c,s.graph)
        finally:
            if field=='storage':object.__setattr__(family,'__dict__',storage)
            else:storage[field]=old
    assert reached and not s.graph.active
    owned.current();use._use_family_current()


def test_response_classifier_replacement_is_refused_before_execution(monkeypatch):
    observed=[]
    def changed(*args,**kwargs):observed.append(True);return use.PB
    monkeypatch.setattr(use,'saved_family',changed)
    with pytest.raises(DomainError):owned.current()
    assert observed==[]


def test_partial_ninth_code_family_and_duplicate_registration_fail_closed():
    code=r'''
from sim2act import _cold_source_owned_impl as native
empty=((),(),())
assert native.verify_code() is False
for index in range(8):native.register_code(index,empty)
assert native.verify_code() is False
native.register_code(8,empty)
assert native.verify_code() is True  # Low-level metadata only, no app authority.
for index in (-1,8,9):
 try:native.register_code(index,empty)
 except RuntimeError:pass
 else:raise AssertionError('duplicate or out-of-range registration accepted')
# Pre-registering empty records cannot install the real application closure.
try:from sim2act import _cold_source_packet
except RuntimeError:pass
else:raise AssertionError('pre-registered foreign code replaced application metadata')
print('bounded one-time nine-family registration PASS')
'''
    result=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True,timeout=10)
    assert result.returncode==0,(result.returncode,result.stdout,result.stderr)
