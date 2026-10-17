import json,os
from pathlib import Path
current=None
calls=[]
def pytest_runtest_setup(item):
    global current
    current=item.nodeid

def pytest_collection_finish(session):
    import test_ordinary_goal_md as md
    original=md.ScriptedMd.request
    def request(self,messages,tools):
        calls.append(dict(node=current,model=type(self).__name__,mode=self.mode,tools=[t['function']['name'] for t in tools]))
        return original(self,messages,tools)
    md.ScriptedMd.request=request
    Path(os.environ['MD_EVIDENCE_OUTPUT'],'final-collected.json').write_text(json.dumps([i.nodeid for i in session.items],indent=2)+'\n')
def pytest_sessionfinish(session,exitstatus):
    Path(os.environ['MD_EVIDENCE_OUTPUT'],'final-scripted-models.json').write_text(json.dumps(dict(instrumented_ScriptedMd_requests=len(calls),calls=calls,not_all_legacy_Mock_or_MockTransport_calls=True,real_model_requests=0,real_human_signoff='NOT_RUN',process_restart='NOT_RUN',pg='NOT_RUN',native_browser='NOT_RUN',Windows='NOT_RUN',remote_CI='NOT_RUN',exitstatus=exitstatus),indent=2)+'\n')
