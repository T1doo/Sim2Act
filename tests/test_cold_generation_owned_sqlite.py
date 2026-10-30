"""Actual SQLite Generation fact transfer; complete-source stays a typed boundary."""
import pytest
from sqlalchemy import select
from accounted_sqlite_fixture import segment
from test_cold_accounted_sqlite import sql_facts
from sim2act import goal_applications as ga
from sim2act import _cold_source_packet as owned
from sim2act.db import runs
from sim2act.errors import DomainError


def test_generation_records_transfer_before_consumers_and_keep_independent_copies(sql_facts):
    f=sql_facts
    with f.store.tx() as c, segment(f,c,phase='pre') as s:
        run=c.execute(select(runs).where(runs.c.id==f.source_id)).mappings().one()
        reader=ga._GenerationFactsReader(f.store,c,run,s.graph)
        assert owned.image.is_kind(reader.run_pin,'d')
        shared=[{'value':'synthetic'}]
        raw={'left':shared,'right':shared}
        key=reader._raw_key('synthetic-transfer')
        value=reader._raw_put(key,'synthetic-transfer',raw)
        assert owned.image.is_kind(value,'d')
        assert owned.image.same(value['left'],value['right'])
        assert owned.image.same(reader._raw_get(key),value)
        # Each original record is an independent deepcopy domain.
        other=reader.record('second-copy',raw)
        assert not owned.image.same(other['left'],value['left'])
        shared[0]['value']='producer changed after transfer'
        assert value['left'][0]['value']=='synthetic'
        assert other['left'][0]['value']=='synthetic'
        assert owned.image.plain(value)=={'left':[{'value':'synthetic'}],'right':[{'value':'synthetic'}]}
        with pytest.raises(TypeError):value['left'][0]['value']='consumer mutation'
        reader.check()


@pytest.mark.parametrize('damage',['raw-entry','root','run'])
def test_generation_rejects_raw_rebinding_and_current_run_change(sql_facts,damage):
    f=sql_facts
    reached=False
    with pytest.raises(DomainError), f.store.tx() as c, segment(f,c,phase='pre') as s:
        run=dict(c.execute(select(runs).where(runs.c.id==f.source_id)).mappings().one())
        reader=ga._GenerationFactsReader(f.store,c,run,s.graph)
        key=reader._raw_key('synthetic-transfer')
        reader._raw_put(key,'synthetic-transfer',{'value':1})
        name,entry,value=reader._raw_cache[key]
        if damage=='raw-entry':
            clone=owned.own_fact(s.graph,'synthetic:equal-clone',owned.image.plain(entry))
            reader._raw_cache[key]=(name,clone,clone["value"])
        elif damage=='root':
            s.graph.inputs[name]=s.graph.inputs[name][0],tuple(list(s.graph.inputs[name][1]))
        else:run['version']+=1
        reached=True
        reader._raw_get(key)
    assert reached


def test_generation_code_and_module_alias_replacement_is_refused(monkeypatch):
    from types import SimpleNamespace
    owned.current()
    monkeypatch.setattr(ga,'_generation_owned',SimpleNamespace(available=lambda:False))
    with pytest.raises(DomainError):owned.current()


@pytest.mark.parametrize('name',['_candidate_attempt_from_history','_candidate_validation_seal',
    '_candidate_from_checked_facts','_source_body','checked_usage','normalize_usage',
    'returned_model_identity','require_returned_model','_GenerationFactsReader','FrozenRunContract'])
def test_generation_fixed_callee_replacement_is_refused(monkeypatch,name):
    owned.current()
    monkeypatch.setattr(ga,name,lambda *a,**kw:None)
    with pytest.raises(DomainError):owned.current()
