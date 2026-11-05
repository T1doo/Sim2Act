"""Versioned request checks only; no provider call or candidate fabrication."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import sim2act
sim2act.__path__.append(str(Path('.local/windows-build-20261105/native-managed-69fa5894/Sim2Act-preview/runtime/Lib/site-packages/sim2act').resolve()))
import httpx
from sim2act.goal_applications import body,SYSTEM,_literal_initial_messages
from sim2act.model import InternModel
from sim2act.contracts import ApplicationGenerationPolicy

checks=[]
legacy=[{'role':'system','content':SYSTEM},{'role':'user','content':json.dumps({'server_ids':{}})}]
expected=httpx.Request('POST',InternModel.ENDPOINT,json={'model':'intern-s2','messages':legacy,'tools':[],'stream':False,'max_tokens':1024}).content
assert body(legacy,[],1024)==expected
checks.append('legacy request bytes remain identical')
current=[legacy[0],{'role':'user','content':json.dumps({'server_ids':{'output_protocol':'compact-candidate-json.v1'}})}]
wire=json.loads(body(current,[],1024));assert wire['thinking_mode'] is False and wire['max_tokens']==1024
checks.append('new final JSON stage explicitly disables thinking without raising output budget')
wire=json.loads(body(current,[{'type':'function'}],1024));assert 'thinking_mode' not in wire
checks.append('tool selection retains original default thinking behavior')
goal={'snapshot':{'content':{'goal':'synthetic'}}};material={'resource_id':'res_'+'a'*32,'hash':'b'*64,'format':'txt'}
old=_literal_initial_messages(goal,{},material,{})
new=_literal_initial_messages(goal,{'output_protocol':'compact-candidate-json.v1'},material,{})
assert old[0]['content']==SYSTEM and 'compact JSON' in new[0]['content']
assert json.loads(new[1]['content'])['saved_goal']==goal
checks.append('new prompt changes formatting only and preserves saved goal facts')
assert ApplicationGenerationPolicy.model_fields['output_protocol'].default is None
checks.append('missing protocol stays legacy rather than silently upgrading saved contracts')
print({'status':'PASS','checks':checks,'scope':'wire compatibility, not LIVE generation success'})
