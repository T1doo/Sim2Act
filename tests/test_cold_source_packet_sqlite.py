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
  models=[]
  gate._graph_trial_accounted_models(s.graph,f.store,c,models,s.source,'source')
  assert models==[]
  guard=lambda: s.graph.check(f.store,c)
  owned.stage_usage(s.graph,s.source,guard)
  requests,responses,proofs=archive._graph_source_bodies(s.graph,f.store,c,f.user,f.contract,s.state,s.source)
  assert len(requests)==len(responses)==len(proofs)==2
  resolved=archive._graph_resolve_trial_source(s.graph,f.store,c,f.user,f.contract,
      f.binding.approval_key,s.state,s.stage,f.proof,s.source,f.extraction)
  dispatch._graph_pb_archive_chain(s.graph,f.store,c,f.binding,s.state,resolved,s.source)
