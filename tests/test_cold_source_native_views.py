"""Memory safety probes are isolated processes; no server, model or network."""
import subprocess
import sys


def test_semantically_malformed_view_nodes_rejected_in_isolated_process():
 script=r'''
import json
from sim2act import _cold_source_owned_impl as n
samples=[
 (0,(('m',(1,1,1,1,1)),('i',0)),(),(),(),(),(),((0,0),)),
 (0,(('r',(1,1,1)),('i',0)),(),(),(),(),(),()),
 (0,(('u',1),('i',0)),(),(),(),(),(),()),
]
for data in samples:
 owner=n.make_owned(data)
 if owner is not n.UNSUPPORTED:
  view=n.read_owner(owner)
  len(view)
  view['x']
  raise AssertionError('invalid model/row/quoted storage accepted')
print(json.dumps({'malformed_representations_rejected':len(samples),'real_model_calls':0}))
'''
 result=subprocess.run([sys.executable,'-c',script],capture_output=True,text=True,timeout=10)
 assert result.returncode==0,(result.returncode,result.stdout,result.stderr)
 assert 'malformed_representations_rejected' in result.stdout
