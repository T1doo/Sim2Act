"""First-producer immutable facts over actual file SQLite read epochs."""
import pytest
from accounted_sqlite_fixture import segment
from test_cold_accounted_sqlite import sql_facts,forbid_execution
from sim2act import _cold_source_packet as owned
from sim2act.errors import DomainError


def test_fact_transfer_parent_alias_and_scope(sql_facts):
 f=sql_facts
 with f.store.tx() as c,segment(f,c,phase='pre') as s:
  shared=[{'value':'synthetic'}]
  original={'left':shared,'right':shared}
  value=owned.own_fact(s.graph,'source-test:rows',original)
  assert owned.image.same(value['left'],value['right'])
  assert owned.fact(s.graph,'source-test:rows') is value
  child=owned.own_fact(s.graph,'source-test:child',{'one':value['left'],'two':value['right']})
  assert owned.image.same(child['one'],value['left'])
  assert owned.image.same(child['one'],child['two'])
  assert owned.image.plain(child)=={'one':[{'value':'synthetic'}],'two':[{'value':'synthetic'}]}
  shared[0]['value']='old producer alias changed after transfer'
  assert value['left'][0]['value']=='synthetic'
  s.graph.check(f.store,c)


def test_fact_cannot_forget_registry_or_transfer_scope(sql_facts):
 f=sql_facts
 with pytest.raises(DomainError),f.store.tx() as c,segment(f,c,phase='pre') as s:
  owned.own_fact(s.graph,'source-test:scope',{'value':1})
  del s.graph._source_fact_bindings
  s.graph.check(f.store,c)


def test_fact_cannot_capture_graph_root(sql_facts):
 f=sql_facts
 with pytest.raises(DomainError),f.store.tx() as c,segment(f,c,phase='pre') as s:
  owned.own_fact(s.graph,'source-test:root',{'cycle':s.graph.inputs})


def test_source_reader_owns_first_sql_rows_and_keeps_canonical_references(sql_facts):
 from sqlalchemy import select
 from sim2act.db import runs
 from sim2act import natural_spec_runtime as runtime
 f=sql_facts
 with f.store.tx() as c,segment(f,c,phase='pre') as s:
  original=c.execute(select(runs).where(runs.c.id==f.source_id)).mappings().one()
  job=owned.own_fact(s.graph,'source-test:job',original)
  s.graph._source_fact_run_ids=(f.source_id,)
  reader=runtime._cold_run_facts(f.store,c,job,s.graph)
  rows=reader.attempt_rows()
  assert len(rows)==2 and all(owned.image.is_kind(row,'d') for row in rows)
  operations=reader.receipt_operations()
  assert owned.image.is_kind(operations,'l')
  assert owned.image.same(owned.fact(s.graph,reader.key+':attempts'),reader._raw['attempts'])
  assert owned.image.same(reader._get('attempts'),reader._raw['attempts'])
  assert owned.image.same(reader._get('attempts')[0],rows[0])
  reader.check(f.store,c,job)
  s.graph.add('source-test:consumer-projection',dict(job=job,attempt=rows[0]))
  for _ in range(5):s.graph.check(f.store,c)
  raw=s.graph.input_bytes()
  assert type(raw) is bytes and b'source-owned-node-v1' in raw


@pytest.mark.parametrize('saved,candidate',[(1,1.0),(1,True),(-0.0,0.0)])
def test_cold_fields_retains_original_canonical_numeric_distinctions(sql_facts,saved,candidate):
 from sim2act import pb_natural_specs as pb
 f=sql_facts
 with pytest.raises(DomainError),f.store.tx() as c,segment(f,c,phase='pre') as s:
  owned.own_fact(s.graph,'source-test:numeric',{'n':saved})
  pb._cold_fields(f.store,c,s.graph,'source-test:numeric',{'n':candidate})


@pytest.mark.parametrize('damage',['binding-copy','output-copy','proof-original-input'])
def test_source_proof_preserves_original_identity_boundaries(sql_facts,damage):
 from sqlalchemy import select
 from sim2act.db import runs
 from sim2act import natural_spec_runtime as runtime
 f=sql_facts
 with pytest.raises(DomainError),f.store.tx() as c,segment(f,c,phase='pre') as s:
  original=c.execute(select(runs).where(runs.c.id==f.source_id)).mappings().one()
  job=owned.own_fact(s.graph,'source-test:proof-job',original)
  s.graph._source_fact_run_ids=(f.source_id,)
  reader=runtime._cold_run_facts(f.store,c,job,s.graph)
  if damage=='proof-original-input':
   inputs={'synthetic':'not a model permit'}
   hit,_,key=reader.node_proof('verified',inputs)
   assert not hit
   reader.record_node_proof('verified',inputs,{'synthetic':True},key)
  else:
   binding={'synthetic_binding':1};reader.pin_receipt_binding(binding)
   result=reader.produced_value('receipt-result',({'step':{'value':1}},[{'step_id':'step'}]))
   outputs,proved=result[0],result[1]
   reader.record_receipts(binding,outputs,proved,None,True)
   reader.checked_receipts(binding,outputs,proved)
   if damage=='binding-copy':reader.checked_receipts(dict(binding),outputs,proved)
   else:
    copy=owned.own_fact(s.graph,'source-test:output-copy',{'step':{'value':1}})
    reader.checked_receipts(binding,copy,proved)


@pytest.mark.parametrize('name',['_review_source_from_facts','_review_from_facts','_verify_from_review','_audit_from_source'])
def test_exact_pb_proof_callee_replacement_is_refused(monkeypatch,name):
 from sim2act import pb_natural_specs as pb
 owned.current()
 monkeypatch.setattr(pb,name,lambda *args,**kwargs:None)
 with pytest.raises(DomainError):owned.current()
