import sys,subprocess
sys.path.insert(0,'/workspace/Sim2Act-application-use/tests')
from conftest import env
import test_application_use as target

def test_other_instance_button_remains_usable(env,tmp_path,monkeypatch):
    normal_create=target.create_instance
    def create(*args,**kwargs):
        first=normal_create(*args,**kwargs)
        second=normal_create(*args,**{**kwargs,'request_key':'independent-existing-second-instance'})
        return first
    monkeypatch.setattr(target,'create_instance',create)
    normal=subprocess.run
    def run(command,**kwargs):
        if len(command)>1 and command[1]=='tests/application_use.cjs':command=[command[0],'/tmp/sim2act-app-use-independent/list-driver.cjs',*command[2:]]
        return normal(command,**kwargs)
    monkeypatch.setattr(subprocess,'run',run)
    target.test_application_use_actual_http(env,tmp_path)
