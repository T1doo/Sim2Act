"""Schema annotation removal preserves named properties and validation keywords."""
import copy,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import sim2act
sim2act.__path__.append(str(Path('.local/windows-build-20261105/native-managed-d512c6c4/Sim2Act-preview/runtime/Lib/site-packages/sim2act').resolve()))
from sim2act.goal_applications import _schema_without_titles,_literal_initial_messages,candidate_diagnostic
from sim2act.errors import DomainError

original={'title':'Object label','type':'object','properties':{'title':{'title':'Field label','type':'string','minLength':1},'literal':{'const':{'title':'meaningful value'}}},'required':['title'],'additionalProperties':False,'$defs':{'title':{'title':'Definition label','enum':['title','other']}}}
saved=copy.deepcopy(original);result=_schema_without_titles(original)
assert original==saved
assert result=={'type':'object','properties':{'title':{'type':'string','minLength':1},'literal':{'const':{'title':'meaningful value'}}},'required':['title'],'additionalProperties':False,'$defs':{'title':{'enum':['title','other']}}}
goal={'snapshot':{'content':{'goal':'synthetic','title':'retain'}}};material={'resource_id':'res_'+'a'*32,'hash':'b'*64,'format':'txt'}
old=_literal_initial_messages(goal,{'output_protocol':'compact-candidate-json4096.v1'},material,{})
new=_literal_initial_messages(goal,{'output_protocol':'compact-candidate-json4096.v2'},material,{})
old_value=json.loads(old[1]['content']);new_value=json.loads(new[1]['content'])
assert 'title' in old_value['action_schema'] and 'title' not in new_value['action_schema']
for key in old_value:
    if key not in ('server_ids','action_schema','manifest_schema'):assert old_value[key]==new_value[key]
before=len(old[1]['content'].encode());after=len(new[1]['content'].encode())
assert after<before
error=DomainError('INVALID_MANIFEST','Manifest failed strict F1 validation')
message={'content':json.dumps({'manifest':{},'actions':[{'step_id':'run','input':'PRIVATE_SENTINEL'}]})}
assert candidate_diagnostic(error,message,'compact-candidate-json4096.v2')==error.public()
diagnostic=candidate_diagnostic(error,message,'compact-candidate-json4096.v3')
assert diagnostic['schema_errors'] and 'PRIVATE_SENTINEL' not in json.dumps(diagnostic)
action_errors=candidate_diagnostic(error,{'content':json.dumps({'manifest':{},'actions':[{}]})},'compact-candidate-json4096.v3')
assert all(set(item)=={'object','path','type'} for item in action_errors['schema_errors'])
print({'status':'PASS','checks':5,'initial_user_bytes_before':before,'initial_user_bytes_after':after,'saved_bytes_per_request':before-after,'scope':'schema annotations and frozen payload facts; not LIVE success'})
