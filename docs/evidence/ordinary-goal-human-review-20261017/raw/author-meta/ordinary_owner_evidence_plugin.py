import json,os,time
from pathlib import Path
import sim2act.model
_original=sim2act.model.MockModel.request
_calls=[]
def counted(self,messages,tools):
    _calls.append(dict(at=time.time(),model_type=type(self).__name__,tools=[t['function']['name'] for t in tools]))
    return _original(self,messages,tools)
def pytest_sessionstart(session):
    sim2act.model.MockModel.request=counted

def pytest_collection_finish(session):
    Path(os.environ['OWNER_EVIDENCE_OUTPUT'],'final-collected.json').write_text(json.dumps([i.nodeid for i in session.items],indent=2)+'\n')
def pytest_sessionfinish(session,exitstatus):
    Path(os.environ['OWNER_EVIDENCE_OUTPUT'],'final-mock-boundary.json').write_text(json.dumps(dict(synthetic_MockModel_requests=len(_calls),calls=_calls,other_offline_MockTransport_calls='see per-case source/proof',real_model_calls=0,real_human_signoff='NOT_RUN',pg='NOT_RUN',native_browser='NOT_RUN',windows='NOT_RUN',remote_CI='NOT_RUN',exitstatus=exitstatus),indent=2)+'\n')
