import importlib.util
import os
from pathlib import Path
import pytest
from source_image import capture,deep_immutable

candidate_dir=Path(os.environ['SIM2ACT_SOURCE_OWNED_CANDIDATE_DIR'])
p=next(candidate_dir.glob('_source_owned_proto.*'))
spec=importlib.util.spec_from_file_location('_source_owned_proto',p);native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native)


def test_owner_is_not_constructible_or_mutable_and_has_no_supplied_wire():
 leaf=bytes(bytearray(b'synthetic owned bytes '+b'x'*128))
 data=((0,),(),(leaf,),())
 owner=native.make_owned(data)
 assert owner is not native.UNSUPPORTED
 assert native.owned_data(owner) is data
 assert native.owned_pin(owner)[1][0] is leaf
 assert deep_immutable(native.owned_data(owner))
 with pytest.raises(TypeError):native.Owned()
 with pytest.raises((TypeError,AttributeError)):object.__setattr__(owner,'data',())
 with pytest.raises((TypeError,AttributeError)):setattr(native.Owned,'data','forged')
 with pytest.raises(TypeError):native.make_owned(data,b'forged-wire')
 different=native.make_owned(((1,),(),(leaf,),()))
 assert native.owned_pin(owner)[0]!=native.owned_pin(different)[0]


def test_unknown_mutable_or_hook_objects_never_enter_owner():
 events=[]
 class Hook:
  def __reduce__(self):events.append('reduce');return tuple,()
 for value in ([1],{'x':1},Hook(),bytearray(b'x')):
  assert native.make_owned((0,(value,),(),())) is native.UNSUPPORTED
 assert events==[]


def test_original_leaf_alias_is_visible_in_complete_pin():
 from sim2act.natural_spec_runtime import _cold_graph_bytes
 leaf=bytes(bytearray(b'cross outside alias '+b'x'*128))
 data=(0,(('b',0),),(leaf,),())
 owner=native.make_owned(data)
 root=dict(owner_pin=native.owned_pin(owner),outside=leaf)
 before=_cold_graph_bytes(root)
 root['outside']=bytes(bytearray(leaf));assert root['outside'] is not leaf
 assert _cold_graph_bytes(root)!=before


def test_binding_scope_rebinding_and_complete_anchor_pin():
 from sim2act.natural_spec_runtime import _cold_graph_bytes
 nonce=object(); leaf=bytes(bytearray(b'scope synthetic '+b'x'*100))
 data=(0,(('b',0),),(leaf,),())
 owner=native.make_owned(data); anchor={'mutable':[leaf]}; anchors=(anchor,)
 binding=native.make_binding(owner,nonce,7,'post',anchors)
 assert native.binding_current(binding,owner,nonce,7,'post')
 for args in ((native.make_owned(data),nonce,7,'post'),(owner,object(),7,'post'),(owner,nonce,8,'post'),(owner,nonce,7,'pre')):
  assert not native.binding_current(binding,*args)
 with pytest.raises(TypeError):native.Binding()
 with pytest.raises((AttributeError,TypeError)):object.__setattr__(binding,'epoch',0)
 pin=native.binding_pin(binding)
 assert pin[2] is anchors
 clone=native.make_binding(owner,nonce,7,'post',({'mutable':[leaf]},))
 assert _cold_graph_bytes(native.binding_pin(clone))!=_cold_graph_bytes(pin)
 before=_cold_graph_bytes(pin);anchor['mutable'].append(3)
 assert _cold_graph_bytes(pin)!=before
 assert native.make_binding(owner,nonce,7,'pre',anchors) is native.UNSUPPORTED


def test_binding_anchor_cycle_is_garbage_collectable():
 import gc
 # A raw anchor can acquire a cycle after publication. The binding must not
 # leak that cycle merely because it was an immutable control record.
 anchor=[]; owner=native.make_owned((0,(),(),()))
 before=sum(type(v) is native.Binding for v in gc.get_objects())
 binding=native.make_binding(owner,object(),0,'post',(anchor,));anchor.append(binding)
 assert gc.is_tracked(binding)
 del anchor,binding,owner
 gc.collect()
 assert sum(type(v) is native.Binding for v in gc.get_objects())<=before


def test_cross_boundary_tuple_alias_cannot_be_split():
 from source_image import capture,matches_live
 from test_config import config
 original=tuple([1,2]);outside={'shared':original}
 data,anchors=capture(original,outside)
 assert anchors==(original,) and anchors[0] is original
 assert matches_live(data,original,outside,anchors)
 clone=tuple([1,2]);assert clone is not original
 assert not matches_live(data,clone,outside,anchors)
 owner=native.make_owned(data)
 assert native.match_live(owner,original,anchors,config(),outside)
 assert not native.match_live(owner,clone,anchors,config(),outside)


def test_native_outside_boundary_rejects_equal_clone_replacement():
 from test_config import config
 original=tuple([1,2]);outside={'shared':original};data,anchors=capture(original,outside)
 owner=native.make_owned(data)
 assert native.match_live(owner,original,anchors,config(),outside)
 assert not native.match_live(owner,original,anchors,config(),{'shared':tuple([1,2])})


def test_model_name_spoof_cannot_replace_exact_catalog_type():
 from sim2act import production_trial_policy as p
 from sim2act.natural_source_archives import BodyArchive
 from test_config import config
 from source_image import matches_live
 value=p.Outcome(outcome="RECEIVED",response_sha256="0"*64,response_ascii_bytes=0)
 # Fully populate original allowed Outcome using its model defaults, retaining
 # raw storage for an intentional class swap adversarial fixture.
 data,anchors=capture(value,())
 owner=native.make_owned(data)
 assert native.match_live(owner,value,anchors,config(),())
 raw=object.__getattribute__(value,'__dict__')
 clone=BodyArchive.model_construct()
 object.__setattr__(clone,'__dict__',raw)
 object.__setattr__(clone,'__pydantic_fields_set__',object.__getattribute__(value,'__pydantic_fields_set__'))
 before=(BodyArchive.__module__,BodyArchive.__qualname__)
 try:
  BodyArchive.__module__=p.Outcome.__module__;BodyArchive.__qualname__=p.Outcome.__qualname__
  assert not matches_live(data,clone,(),anchors)
  assert not native.match_live(owner,clone,anchors,config(),())
 finally:BodyArchive.__module__,BodyArchive.__qualname__=before


def test_native_live_gc_state_restored_with_real_mutating_callback():
 import gc
 from test_config import config
 value={'list':[1,2]};data,anchors=capture(value,())
 owner=native.make_owned(data);cfg=config();old_threshold=gc.get_threshold();old_enabled=gc.isenabled()
 events=[]
 def mutate(phase,info):
  if phase=='start':
   # A real collection callback changes the actual source. It must never run
   # inside the direct verifier's protected live-read interval.
   events.append(native.matching())
   value['list'].append(3)
 try:
  gc.collect();gc.callbacks.append(mutate);gc.set_threshold(1,1,1);gc.enable()
  accepted=native.match_live(owner,value,anchors,cfg,())
  assert gc.isenabled()
  gc.collect()
  assert events and not any(events)
  assert not native.match_live(owner,value,anchors,cfg,())
  # If a collection occurred before native entry, the changed input was read
  # freshly and rejected. A post-return callback cannot be treated as having
  # been observed inside the already completed verifier.
  if not accepted:assert value['list']!=[1,2]
  gc.disable()
  assert not native.match_live(owner,value,anchors,cfg,())
  assert not gc.isenabled()
 finally:
  gc.disable();gc.callbacks.remove(mutate);gc.set_threshold(*old_threshold)
  if old_enabled:gc.enable()


def test_malformed_cyclic_and_unreachable_image_rejected():
 from test_config import config
 value=[];value.append(value)
 owner=native.make_owned((0,(('l',(0,)),),(),(),(),(),(),()))
 assert not native.match_live(owner,value,(),config(),())
 owner=native.make_owned((0,(('i',1),('i',2)),(),(),(),(),(),()))
 assert not native.match_live(owner,1,(),config(),())


def test_gc_state_restored_on_native_storage_exception():
 import gc
 from sim2act.production_trial_policy import Outcome
 from test_config import config
 value=Outcome(outcome='RECEIVED',response_sha256='0'*64,response_ascii_bytes=0)
 data,anchors=capture(value,());owner=native.make_owned(data);cfg=config()
 broken=Outcome.__new__(Outcome)
 before=gc.isenabled()
 try:
  gc.enable()
  with pytest.raises(AttributeError):native.match_live(owner,broken,anchors,cfg,())
  assert gc.isenabled()
  gc.disable()
  with pytest.raises(AttributeError):native.match_live(owner,broken,anchors,cfg,())
  assert not gc.isenabled()
 finally:
  if before:gc.enable()
  else:gc.disable()


def test_forged_virtual_and_unused_metadata_rejected():
 from test_config import config
 leaf=bytes(bytearray(b'non-sensitive original '+b'x'*128));clone=bytes(bytearray(leaf))
 data,anchors=capture(leaf,());cfg=config()
 for altered in (
  (*data[:4],(data[0],),*data[5:]),
  (*data[:2],(*data[2],b'unused carrier'),*data[3:]),
  (*data[:2],(*data[2],data[2][0]),*data[3:]),
  (*data[:7],((data[0],0),)),
  (*data[:4],(len(data[1]),),*data[5:]),
 ):
  owner=native.make_owned(altered)
  assert not native.match_live(owner,clone,anchors,cfg,())
  assert not native.match_live(owner,leaf,anchors,cfg,())
 assert native.match_live(native.make_owned(data),leaf,anchors,cfg,())
 with pytest.raises(TypeError):native.match_live(native.make_owned(data),leaf,anchors,cfg)
