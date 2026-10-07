import sys,subprocess
sys.path.insert(0,'/workspace/Sim2Act-application-use/tests')
from conftest import env
import test_application_use as target
from sqlalchemy import select,update
from sim2act.db import grants

def test_revoked_read_and_version_binding(env,tmp_path,monkeypatch):
    normal_app=target.create_app
    def app(store,settings):
        result=normal_app(store,settings);assert store.test_only
        with store.tx() as c:original=[dict(r) for r in c.execute(select(grants)).mappings()]
        @result.post('/test-only-authorization-fault/{action}')
        def fault(action:str):
            assert store.test_only
            with store.tx() as c:
                for row in original:
                    c.execute(update(grants).where(grants.c.id==row['id']).values(revoked=True if action=='revoke' else row['revoked'],revision=row['revision']))
            return {'synthetic_fixture_only':True}
        return result
    monkeypatch.setattr(target,'create_app',app)
    normal=subprocess.run
    def run(command,**kwargs):
        if len(command)>1 and command[1]=='tests/application_use.cjs':command=[command[0],'/tmp/sim2act-app-use-independent/permissions-driver.cjs',*command[2:]]
        return normal(command,**kwargs)
    monkeypatch.setattr(subprocess,'run',run)
    target.test_application_use_actual_http(env,tmp_path)
