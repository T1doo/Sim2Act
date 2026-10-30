"""Original SQL producers/consumers; synthetic records, no Worker execution."""
import pytest
from accounted_sqlite_fixture import segment
from test_cold_accounted_sqlite import sql_facts,forbid_execution
from sim2act import _cold_source_packet as owned
from sim2act import natural_source_archives as archive,natural_live_admission as gate
from sim2act import pa_trial_dispatch as dispatch


def test_post_source_producer_and_all_direct_consumers(sql_facts):
 f=sql_facts
 assert owned.available()
 with f.store.tx() as c,segment(f,c,phase='post') as s:
  assert owned.is_packet(s.source)
  assert owned.pin(s.graph,s.source) is s.graph.inputs[owned.KEY]
  facts=owned.facts(s.graph,s.source)
  assert facts[0]['id']==f.source_id
  source_job=owned.own_fact(s.graph,'source-owned-consumer:job',s.stage[0])
  source_stage=(source_job,*s.stage[1:])
  phase,checked_job=gate._graph_stage_current(s.graph,f.store,c,f.user,f.contract,'source',source_stage)
  assert phase==f.phase.authority and checked_job is source_job
  models=[]
  gate._graph_trial_accounted_models(s.graph,f.store,c,models,s.source,'source')
  assert models==[]
  guard=lambda: s.graph.check(f.store,c)
  owned.stage_usage(s.graph,s.source,guard)
  requests,responses,proofs=archive._graph_source_bodies(s.graph,f.store,c,f.user,f.contract,s.state,s.source)
  assert len(requests)==len(responses)==len(proofs)==2
  resolved=archive._graph_resolve_trial_source(s.graph,f.store,c,f.user,f.contract,
      f.binding.approval_key,s.state,source_stage,f.proof,s.source,f.extraction)
  dispatch._graph_pb_archive_chain(s.graph,f.store,c,f.binding,s.state,resolved,s.source)


def test_post_cold_stage_and_runtime_collector(sql_facts):
 from accounted_sqlite_fixture import seed_cold
 from sim2act import natural_spec_runtime as rt
 f=sql_facts;seed_cold(f)
 with f.store.tx() as c,segment(f,c,phase='post') as s:
  source_job=owned.own_fact(s.graph,'source-owned-collector:job',s.stage[0])
  source_stage=(source_job,*s.stage[1:])
  phase,job=gate._graph_stage_current(s.graph,f.store,c,f.user,f.contract,'cold',s.cold_stage)
  assert phase==f.cold_phase.authority and job['id']==f.cold_job['id']
  graph=object.__new__(rt._ColdTrialGraph)
  graph.__dict__.update(worker=f.worker,c=c,guard=s.graph,accounted_prewrite=None,
    platform=None,trial=None,audit_seed=None,journal=(s.state,s.cursor,s.graph.inputs['cold-trial:journal']['revision']),
    source_accounted=s.source,generate_accounted=s.generated,cold_stage_facts=s.cold_stage,
    source_stage_facts=source_stage,sealed_fields=s.graph.inputs['cold-trial:complete'],
    source_proof=f.proof,original=f.contract,live_source=None,context_record=None,
    authority_record=None,authority_fields=None,phase='COMPLETE')
  graph.check()
  models=graph._typed_parameter_models()
  from sim2act import production_trial_sender as sender
  assert not any(kind is archive.BodyArchive for kind,model,raw in models)
  assert sum(kind is sender.Capture for kind,model,raw in models)==3
  assert graph._accounted_fields(s.source) is s.graph.inputs[owned.KEY]


@pytest.mark.parametrize('which',['inputs','roles'])
def test_bound_source_rejects_equal_root_rebinding(sql_facts,which):
 from sim2act.errors import DomainError
 f=sql_facts
 with pytest.raises(DomainError),f.store.tx() as c,segment(f,c,phase='post') as s:
  if which=='inputs':s.graph.inputs=dict(s.graph.inputs)
  else:s.graph.role_limits=dict(s.graph.role_limits)
  s.graph.check(f.store,c)
 assert not s.graph.active


def test_native_view_is_immutable_even_to_class_changes(sql_facts):
 f=sql_facts
 with f.store.tx() as c,segment(f,c,phase='post') as s:
  root=owned.facts(s.graph,s.source)
  with pytest.raises((TypeError,AttributeError)):setattr(type(root),'__getitem__',lambda *a:None)
  with pytest.raises((TypeError,AttributeError)):object.__setattr__(root,'data',())
  with pytest.raises(TypeError):type(root)()
  s.graph.check(f.store,c)


def test_fresh_slot_join_rejects_field_set_change(sql_facts):
 from sim2act.errors import DomainError
 f=sql_facts
 with f.store.tx() as c,segment(f,c,phase='post') as s:
  chain=owned.facts(s.graph,s.source)[2][0];slot=chain[0];aid=slot.identity.attempt_id
  actual=next(value for value in s.state.slots if value.identity.attempt_id==aid)
  original=object.__getattribute__(actual,'__pydantic_fields_set__')
  object.__setattr__(actual,'__pydantic_fields_set__',set())
  try:
   with pytest.raises(DomainError):owned.slot_join(s.graph,s.source,s.state,slot,aid,lambda:s.graph.check(f.store,c))
  finally:object.__setattr__(actual,'__pydantic_fields_set__',original)


def test_same_roots_do_not_allow_transfer_to_a_cloned_graph(sql_facts):
 from sim2act import natural_spec_runtime as rt
 from sim2act.errors import DomainError
 f=sql_facts
 with f.store.tx() as c,segment(f,c,phase='post') as s:
  clone=object.__new__(rt._ColdGraphRead);clone.__dict__.update(vars(s.graph))
  with pytest.raises(DomainError):owned.bound(clone,s.source)
  s.graph.check(f.store,c)


def test_current_ledger_selection_observes_in_place_slot_replacement(sql_facts):
 from sim2act.errors import DomainError
 f=sql_facts
 with f.store.tx() as c,segment(f,c,phase='post') as s:
  slot=owned.facts(s.graph,s.source)[2][0][0];aid=slot.identity.attempt_id
  original=object.__getattribute__(s.state,'__dict__')['slots']
  slots=list(original);object.__getattribute__(s.state,'__dict__')['slots']=slots
  changed=[]
  def guard():
   s.graph.check(f.store,c)
   if not changed:
    i=next(i for i,v in enumerate(slots) if v.identity.attempt_id==aid)
    clone=slots[i].model_copy(deep=True)
    object.__setattr__(clone,'__pydantic_fields_set__',set())
    slots[i]=clone;changed.append(True)
  try:
   with pytest.raises(DomainError):owned.slot_join(s.graph,s.source,s.state,slot,aid,guard)
   assert changed
  finally:object.__getattribute__(s.state,'__dict__')['slots']=original


@pytest.mark.parametrize('name',['publish','available'])
def test_source_producer_qualifies_before_replaceable_dispatch(sql_facts,monkeypatch,name):
 from sim2act.errors import DomainError
 events=[];f=sql_facts
 def bad(*args,**kwargs):events.append(name);return False
 monkeypatch.setattr(owned,name,bad)
 with pytest.raises(DomainError),f.store.tx() as c,segment(f,c,phase='post'):
  pytest.fail('unknown publisher must never become a Source family')
 assert events==[]


@pytest.mark.parametrize('damage',['duplicate-normalized-row-key','raw-set','root-rebind'])
def test_first_handoff_preserves_original_domain_and_current_roots(sql_facts,damage):
 from sim2act import natural_spec_runtime as rt,pb_natural_specs as pb
 from sim2act.errors import DomainError
 f=sql_facts
 with f.store.tx() as c,segment(f,c,phase='pre') as pre:
  value=pre.source;raw=pre.graph.inputs[owned.KEY]
 # This exercises only the transfer boundary using already validated synthetic
 # SQL facts. It does not issue a stage grant or claim a second Worker run.
 with pytest.raises(DomainError),f.store.tx() as c,pb._source_reads(f.store,c),rt._cold_graph_read(
      f.worker,c,{'transfer-boundary':True},dict.fromkeys(('source','generate','platform','trial','per_use')),'post') as graph:
  original_keys=None;parsed=None
  if damage=='duplicate-normalized-row-key':
   original_keys=object.__getattribute__(object.__getattribute__(value[0],'_parent'),'_keys')
   original_keys.append(original_keys[0])
  if damage=='raw-set':
   parsed=value[2][0][2];assert '__raw_set_probe__' not in parsed
   parsed['__raw_set_probe__']={1}
  def guard():
   graph.check(f.store,c)
   if damage=='root-rebind':graph.inputs=dict(graph.inputs)
  try:
   owned.publish(graph,value,raw,guard)
   pytest.fail('invalid handoff must not publish')
  finally:
   if original_keys is not None:original_keys.pop()
   if parsed is not None:parsed.pop('__raw_set_probe__')
   assert owned.KEY not in graph.inputs


def test_original_reservation_observers_do_not_change_source_callee_closure(monkeypatch):
 from test_pb_spec_production_controller import observe_reservation_reads
 owned.current()
 observe_reservation_reads(monkeypatch)
 # The original observer retains its token/read/write assertions unchanged.
 owned.current()


@pytest.mark.parametrize('name',['_graph_stage_accounted','_graph_journal_chain','_journal_source',
    '_journal_capture_from_facts','_stage_usage_from_facts','_archive_chain_values'])
def test_each_selected_source_callee_change_is_refused(monkeypatch,name):
 from sim2act.errors import DomainError
 original=getattr(dispatch,name)
 def bad(*args,**kwargs):return None
 monkeypatch.setattr(dispatch,name,bad)
 with pytest.raises(DomainError):owned.current()
 assert getattr(dispatch,name) is not original
