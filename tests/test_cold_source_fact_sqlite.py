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
 reached=False
 with pytest.raises(DomainError),f.store.tx() as c,segment(f,c,phase='pre') as s:
  owned.own_fact(s.graph,'source-test:scope',{'value':1})
  del s.graph._source_fact_bindings
  reached=True
  s.graph.check(f.store,c)
 assert reached, "Expected rejection was not reached"


def test_fact_cannot_capture_graph_root(sql_facts):
 f=sql_facts
 reached=False
 with pytest.raises(DomainError),f.store.tx() as c,segment(f,c,phase='pre') as s:
  reached=True
  owned.own_fact(s.graph,'source-test:root',{'cycle':s.graph.inputs})
 assert reached, "Expected rejection was not reached"


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
 reached=False
 with pytest.raises(DomainError),f.store.tx() as c,segment(f,c,phase='pre') as s:
  owned.own_fact(s.graph,'source-test:numeric',{'n':saved})
  reached=True
  pb._cold_fields(f.store,c,s.graph,'source-test:numeric',{'n':candidate})

 assert reached, "Expected rejection was not reached"


@pytest.mark.parametrize('damage',['binding-copy','output-copy','proof-original-input'])
def test_source_proof_preserves_original_identity_boundaries(sql_facts,damage):
 from sqlalchemy import select
 from sim2act.db import runs
 from sim2act import natural_spec_runtime as runtime
 f=sql_facts
 reached=False
 with pytest.raises(DomainError),f.store.tx() as c,segment(f,c,phase='pre') as s:
  original=c.execute(select(runs).where(runs.c.id==f.source_id)).mappings().one()
  job=owned.own_fact(s.graph,'source-test:proof-job',original)
  s.graph._source_fact_run_ids=(f.source_id,)
  reader=runtime._cold_run_facts(f.store,c,job,s.graph)
  if damage=='proof-original-input':
   inputs={'synthetic':'not a model permit'}
   hit,_,key=reader.node_proof('verified',inputs)
   assert not hit
   reached=True
   reader.record_node_proof('verified',inputs,{'synthetic':True},key)
  else:
   binding={'synthetic_binding':1};reader.pin_receipt_binding(binding)
   result=reader.produced_value('receipt-result',({'step':{'value':1}},[{'step_id':'step'}]))
   outputs,proved=result[0],result[1]
   reader.record_receipts(binding,outputs,proved,None,True)
   reader.checked_receipts(binding,outputs,proved)
   if damage=='binding-copy':
    reached=True
    reader.checked_receipts(dict(binding),outputs,proved)
   else:
    copy=owned.own_fact(s.graph,'source-test:output-copy',{'step':{'value':1}})
    reached=True
    reader.checked_receipts(binding,copy,proved)

 assert reached, "Expected rejection was not reached"


@pytest.mark.parametrize('name',['_review_source_from_facts','_review_from_facts','_verify_from_review','_audit_from_source'])
def test_exact_pb_proof_callee_replacement_is_refused(monkeypatch,name):
 from sim2act import pb_natural_specs as pb
 owned.current()
 monkeypatch.setattr(pb,name,lambda *args,**kwargs:None)
 with pytest.raises(DomainError):owned.current()


@pytest.mark.parametrize('case',['merge-unshared','split-shared','parent-leaf','added-after-owner'])
@pytest.mark.parametrize('fallback',[False,True],ids=['native','full-sha'])
def test_atomic_owner_inventory_preserves_cross_domain_aliases(sql_facts,case,fallback):
 from sim2act import _cold_graph_structure_guard as structure
 f=sql_facts
 reached=False
 with pytest.raises(DomainError),f.store.tx() as c,segment(f,c,phase='pre') as s:
  a=bytes(bytearray(b'synthetic owner alias payload'))
  b=bytes(bytearray(a));assert a==b and a is not b
  legacy={'value':a if case=='split-shared' else b}
  if case!='added-after-owner':s.graph.add('source-test:legacy',legacy)
  if case=='parent-leaf':
   parents=[];data,anchors=owned.image.capture({'value':a},s.graph.input_bytes(_snapshot_values=True),_parents=parents)
   parent=owned.native.make_composite(data,tuple(parents))
   assert type(parent) is owned.native.Owned
   owned.own_fact(s.graph,'source-test:owner',{'parent':owned.native.read_owner(parent)})
  else:owned.own_fact(s.graph,'source-test:owner',{'value':a})
  if case=='added-after-owner':s.graph.add('source-test:legacy',legacy)
  for _ in range(5):s.graph.check(f.store,c)
  state=s.graph._structure_state
  assert state.capsule is not None and not state.declined
  if fallback:state.declined=True
  legacy['value']=b if case=='split-shared' else a
  if not fallback:
   assert structure.native.matches_fast(state.capsule,s.graph.input_bytes(_snapshot_values=True),state.scope) is False
  reached=True
  s.graph.check(f.store,c)
 assert reached, "Expected rejection was not reached"


def test_atomic_owner_keeps_equal_unaliased_ordinary_clone(sql_facts):
 from sim2act import _cold_graph_structure_guard as structure
 f=sql_facts
 with f.store.tx() as c,segment(f,c,phase='pre') as s:
  legacy={'value':bytes(bytearray(b'ordinary different value'))}
  s.graph.add('source-test:clone',legacy)
  owned.own_fact(s.graph,'source-test:owner',{'value':bytes(bytearray(b'owned value'))})
  for _ in range(5):s.graph.check(f.store,c)
  state=s.graph._structure_state;assert state.capsule is not None
  original=legacy['value'];legacy['value']=bytes(bytearray(original))
  assert legacy['value'] is not original and legacy['value']==original
  assert structure.native.matches_fast(state.capsule,s.graph.input_bytes(_snapshot_values=True),state.scope) is True
  s.graph.check(f.store,c)


def test_atomic_owner_inventory_cleanup_after_native_schema_failure(sql_facts):
 import sys,gc
 from sim2act import _cold_graph_structure_guard as structure,natural_spec_runtime as rt
 f=sql_facts
 with f.store.tx() as c,segment(f,c,phase='pre') as s:
  view=owned.own_fact(s.graph,'source-test:cleanup',{'value':bytes(bytearray(b'cleanup leaf'))})
  owner=view.owner();leaf=view['value'];scope=(s.graph,s.graph.nonce,s.graph.key,s.graph.epoch,s.graph.phase)
  value={'owned':owner,'unsupported':object()}
  gc.collect();before=sys.getrefcount(owner),sys.getrefcount(leaf)
  result=structure.native.snapshot(value,*structure._ARGS,scope,rt._SOURCE_VIEW_TYPE,rt._SOURCE_OWNER_TYPE)
  assert result is structure.native.UNSUPPORTED
  gc.collect();assert (sys.getrefcount(owner),sys.getrefcount(leaf))==before


def test_source_first_check_calibrates_complete_new_root_and_rejects_change(sql_facts):
 from sim2act import _cold_graph_structure_guard as structure
 f=sql_facts;reached=False
 with pytest.raises(DomainError),f.store.tx() as c,segment(f,c,phase='pre') as s:
  owned.own_fact(s.graph,'source-test:eager-owner',{'value':'synthetic'})
  legacy={'value':[1]}
  s.graph.add('source-test:eager-mutable',legacy)
  assert '_structure_state' not in vars(s.graph)
  s.graph.check(f.store,c)
  state=s.graph._structure_state
  assert state.count==1 and state.capsule is not None
  assert structure.native.matches_fast(state.capsule,s.graph.input_bytes(_snapshot_values=True),state.scope) is True
  legacy['value'].append(2)
  reached=True
  s.graph.check(f.store,c)
 assert reached,'Mutation must be reached after first-check calibration'
