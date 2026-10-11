"""Read-only served-resource audit using actual ASGI HTTP; synthetic SQLite fixture."""
import hashlib,json,os
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
import conftest

out=Path('/tmp/pa-text-edit-generation-http-review-20261011')
web=Path('/workspace/Sim2Act/src/sim2act/web')
os.environ.pop('SIM2ACT_TEST_DATABASE_URL',None)
base=out/'asset-fixture';base.mkdir(exist_ok=True)
fixture=conftest.env.__wrapped__(base);env=next(fixture)
loads=[]
class Assets(HTMLParser):
    def __init__(self):super().__init__();self.scripts=[];self.styles=[]
    def handle_starttag(self,tag,attrs):
        values=dict(attrs)
        if tag=='script' and values.get('src'):self.scripts.append(values['src'])
        if tag=='link' and values.get('rel')=='stylesheet':self.styles.append(values['href'])
def read(path,filename,media_type):
    response=env[2].get(path)
    digest=hashlib.sha256(response.content).hexdigest()
    expected=hashlib.sha256((web/filename).read_bytes()).hexdigest()
    loads.append({'path':path,'status':response.status_code,'content_type':response.headers.get('content-type'),'bytes':len(response.content),'sha256':digest,'expected_sha256':expected})
    assert response.status_code==200
    assert response.headers.get('content-type','').split(';',1)[0]==media_type
    assert digest==expected
    return response
try:
    index=read('/','index.html','text/html')
    parsed=Assets();parsed.feed(index.text)
    assert len(parsed.scripts)==16 and '/goal-application.js' in parsed.scripts
    for source in parsed.scripts+parsed.styles:
        target=urlsplit(source)
        assert not target.scheme and not target.netloc and target.path.startswith('/')
        read(source,target.path[1:],'text/javascript' if source in parsed.scripts else 'text/css')
    not_registered=env[2].get('/not-registered-script.js')
    assert not_registered.status_code==404,'Only exact served filenames should be routed'
    result={'status':'PASS','scope':'Actual in-process HTTP GET of HTML, all16 scripts and CSS; exact200/ctype/bytes/SHA. No native-browser claim.','loads':loads,'unregistered_script_status':404,'live_requests':0,'models':'NOT_CALLED','native_browser':'NOT_RUN'}
    (out/'http-assets.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({'status':'PASS','assets':len(loads),'scripts':len(parsed.scripts),'goal_application_sha256':next(i['sha256'] for i in loads if i['path']=='/goal-application.js'),'live_requests':0}))
finally:
    try:next(fixture)
    except StopIteration:pass
