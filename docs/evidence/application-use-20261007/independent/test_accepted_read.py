import sys, subprocess
sys.path.insert(0, '/workspace/Sim2Act-application-use/tests')
from conftest import env
from test_application_use import test_application_use_actual_http as original_test

def test_accepted_readonly_recovery(env,tmp_path,monkeypatch):
    original=subprocess.run
    def run(command,**kwargs):
        if len(command)>1 and command[1]=='tests/application_use.cjs':command=[command[0],'/tmp/sim2act-app-use-independent/accepted-read-driver.cjs',*command[2:]]
        return original(command,**kwargs)
    monkeypatch.setattr(subprocess,'run',run)
    original_test(env,tmp_path)
