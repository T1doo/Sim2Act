import sys, subprocess
sys.path.insert(0, '/workspace/Sim2Act-task-read-failure/tests')
from conftest import env
from test_task_read_failure import test_task_read_failure_actual_http as original_test

def test_direct_project_change_queued_commands(env,tmp_path,monkeypatch):
    normal=subprocess.run
    def run(command,**kwargs):
        if len(command)>1 and command[1]=='tests/task_read_failure.cjs':
            command=[command[0],'/tmp/sim2act-read-failure-independent/project-change-driver.cjs',*command[2:]]
        return normal(command,**kwargs)
    monkeypatch.setattr(subprocess,'run',run)
    original_test(env,tmp_path)
