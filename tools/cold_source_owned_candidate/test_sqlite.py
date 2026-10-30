import json
import pytest
from accounted_sqlite_fixture import segment
from test_cold_accounted_sqlite import sql_facts as sql_facts, forbid_execution as forbid_execution
from sim2act import natural_spec_runtime as rt
from source_image import capture,deep_immutable,Unsupported,read,image_equal,matches_live


def test_actual_source_joint_image_and_hidden_storage(sql_facts,tmp_path):
 f=sql_facts
 with f.store.tx() as c,segment(f,c,phase='post') as s:
  data=s.graph.input_bytes(_snapshot_values=True)
  outside=dict(data,inputs=dict(data['inputs']))
  for key in ('cold-trial:accounted-source','cold-trial:accounted-generate','cold-trial:complete','trial-generated-model-facet'):
   outside['inputs'].pop(key,None)
  incoming=(s.source,s.graph.inputs['cold-trial:accounted-source'])
  image,anchors=capture(incoming,outside)
  assert deep_immutable(image)
  assert matches_live(image,incoming,outside,anchors)
  from test_native import native
  from test_config import config
  native_owner=native.make_owned(image)
  assert native.match_live(native_owner,incoming,anchors,config(),outside), (native.diagnostic(),image[1][native.diagnostic()[0]][0])
  tags=[n[0] for n in image[1]]
  assert tags.count('m')>=8 and tags.count('r')>=5 and tags.count('e')==tags.count('m')
  assert len(anchors)==len(image[3]) and len({id(v) for v in anchors})==len(anchors)
  family,raw=read(image)
  run,actual,chains,ns=family
  assert run['id']==f.source_id and len(actual)==len(chains)==len(ns)==2
  for old_chain,new_chain in zip(s.source[2],chains,strict=True):
   assert new_chain[0].identity.attempt_id==old_chain[0].identity.attempt_id
   assert new_chain[1].raw_sha256==old_chain[1].raw_sha256
   fresh,_=capture(old_chain[0],())
   assert image_equal(new_chain[0],read(fresh))
  for old_read,new_read in zip(s.source[3],ns,strict=True):
   assert new_read[1].sha256==old_read[1].sha256
   assert new_read[2] is old_read[2] and new_read[4] is old_read[4]
  # Explicitly introduce a typed/raw storage alias. One memo must emit the
  # model's original dict exactly once and preserve its external boundary.
  body=s.source[3][0][1]
  shared=object.__getattribute__(body,'__dict__')
  augmented=dict(outside,synthetic_shared_storage=shared)
  linked,boundaries=capture(incoming,augmented)
  assert any(value is shared for value in boundaries)
  assert deep_immutable(linked)
  assert matches_live(linked,incoming,augmented,boundaries)
  # Direct live checks, rather than comparing a second transformed image.
  original_sha=shared['sha256'];clone=original_sha.encode().decode()
  assert clone is not original_sha
  shared['sha256']=clone
  try:
   assert not matches_live(linked,incoming,augmented,boundaries)
   assert not native.match_live(native.make_owned(linked),incoming,boundaries,config(),augmented)
  finally:shared['sha256']=original_sha
  detached=dict(augmented,synthetic_shared_storage=dict(shared))
  assert not matches_live(linked,incoming,detached,boundaries)
  replaced=tuple(dict(v) if type(v) is dict else v for v in boundaries)
  assert not matches_live(linked,incoming,augmented,replaced)
  raw=s.graph.inputs['cold-trial:accounted-source']
  original_parameters=raw['actual'][0]['parameters']
  raw['actual'][0]['parameters']=dict(original_parameters)
  try:
   assert not matches_live(image,incoming,outside,anchors)
   assert not native.match_live(native_owner,incoming,anchors,config(),outside)
  finally:raw['actual'][0]['parameters']=original_parameters
  index=object.__getattribute__(s.source[0],'_key_to_index')
  assert '__owned_hidden_probe__' not in index
  index['__owned_hidden_probe__']=0
  try:
   assert not matches_live(image,incoming,outside,anchors)
   assert not native.match_live(native_owner,incoming,anchors,config(),outside)
  finally:index.pop('__owned_hidden_probe__')
  # A Slot raw dict contains nested models: the original graph codec cannot
  # represent that outside boundary, so reject before any publication.
  slot_storage=object.__getattribute__(s.source[2][0][0],'__dict__')
  with pytest.raises(Unsupported):capture(incoming,dict(outside,bad_shared=slot_storage))
  (tmp_path/'prototype-result.json').write_text(json.dumps(dict(
   status='PROTOTYPE_CAPTURE_ONLY_NOT_INSTALLED_NOT_CONSUMER_CLOSURE',nodes=len(image[1]),
   immutable_leaves=len(image[2]),models=tags.count('m'),rows=tags.count('r'),
   boundary_count=len(anchors),explicit_typed_raw_boundary=True,
   real_model_calls=0,worker_executions=0),indent=2)+'\n')
