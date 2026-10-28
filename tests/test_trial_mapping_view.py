"""Keep execute/fetch pins; only the fixed non-fetching view is coalesced."""
import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Result

from sim2act import natural_live_admission as gate


@pytest.fixture
def connection():
    engine=create_engine('sqlite://')
    with engine.connect() as c:
        yield c
    engine.dispose()

def test_fixed_mapping_has_post_execute_and_post_fetch_pins(connection):
    observed=[]
    def pin():observed.append('pin')
    result=gate._trial_result(connection.execute(text('select 1 as value')),pin)
    value=gate._trial_result(gate._trial_mapping_view(result,pin).first(),pin)
    assert value['value']==1
    assert observed==['pin','pin']

def test_changed_mapping_keeps_intermediate_pin(connection,monkeypatch):
    observed=[]
    original=Result.mappings
    def changed(result):
        observed.append('changed')
        return original(result)
    monkeypatch.setattr(Result,'mappings',changed)
    result=connection.execute(text('select 1 as value'))
    assert gate._trial_mapping_view(result,lambda:observed.append('pin')).all()[0]['value']==1
    assert observed==['changed','pin']

def test_post_execute_mutation_rejected_before_view(connection,monkeypatch):
    observed=[]
    def mutated(*args):observed.append('sql event')
    event.listen(connection,'after_cursor_execute',mutated)
    def pin():
        assert observed==['sql event']
        raise RuntimeError('complete content changed')
    with pytest.raises(RuntimeError,match='complete content'):
        gate._trial_mapping_view(gate._trial_result(connection.execute(text('select 1')),pin),pin)

def test_fetch_processor_mutation_is_seen_by_final_pin(connection):
    from sqlalchemy import Integer, TypeDecorator, column, select
    observed=[]
    class Changed(TypeDecorator):
        impl=Integer
        cache_ok=True
        def process_result_value(self,value,dialect):
            observed.append('fetch')
            return value
    result=gate._trial_result(connection.execute(select(column('value',Changed())).select_from(text('(select 1 as value)'))),lambda:observed.append('execute pin'))
    view=gate._trial_mapping_view(result,lambda:observed.append('intermediate pin'))
    assert observed==['execute pin']
    gate._trial_result(view.all(),lambda:observed.append('fetch pin'))
    assert observed==['execute pin','fetch','fetch pin']

def test_changed_mapping_assignment_restores_intermediate_pin(connection, monkeypatch):
    from sqlalchemy.engine import MappingResult
    observed=[]
    def changed(self,name,value):
        observed.append('assignment')
        object.__setattr__(self,name,value)
    monkeypatch.setattr(MappingResult,'__setattr__',changed)
    view=gate._trial_mapping_view(connection.execute(text('select 1 as value')),lambda:observed.append('pin'))
    assert observed==['assignment']*3+['pin']
    assert view.first()['value']==1
