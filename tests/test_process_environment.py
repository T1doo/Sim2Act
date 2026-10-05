"""Real subprocess checks: environment names and app-role permissions, no secret output."""

import json
import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from sim2act.config import Settings
from sim2act.process_env import application_environment

ROOT = Path(__file__).parents[1]
FORBIDDEN = {"SIM2ACT_TEST_DATABASE_URL", "PGPASSWORD", "GH_TOKEN", "CI_PRIVATE_SENTINEL"}


@pytest.mark.parametrize("live", [False, True])
def test_actual_child_has_only_application_config_and_system_names(tmp_path, live):
    s = Settings(
        "postgresql+psycopg://synthetic-app@127.0.0.1/fixture",
        tmp_path,
        mode="live" if live else "mock",
        live_enabled=live,
        token="SYNTHETIC app token",
        quota_subject="SYNTHETIC quota",
        rpm=7,
        max_requests=2,
        max_tools=3,
        max_repairs=0,
        max_total_tokens=1000,
        max_output_tokens=100,
        run_seconds=60,
    )
    source = {key: "SYNTHETIC private value" for key in FORBIDDEN}
    source.update({"HTTPS_PROXY": "http://synthetic-proxy.invalid:8080", "NO_PROXY": "localhost,127.0.0.1"})
    source.update(
        {
            key: os.environ[key]
            for key in ("PATH", "SystemRoot", "WINDIR", "COMSPEC", "TEMP", "TMP")
            if key in os.environ
        }
    )
    child = subprocess.run(
        [
            sys.executable,
            "-c",
            """
import json, os
from sim2act.config import Settings
s=Settings.from_env()
assert s.quota_subject=='SYNTHETIC quota' and s.rpm==7
assert (s.max_requests,s.max_tools,s.max_repairs,s.max_total_tokens,s.max_output_tokens,s.run_seconds)==(2,3,0,1000,100,60)
assert bool(s.token)==s.live_enabled==(s.mode=='live')
assert os.environ['HTTPS_PROXY']=='http://synthetic-proxy.invalid:8080' and os.environ['NO_PROXY']=='localhost,127.0.0.1'
print(json.dumps({'environment_names':sorted(os.environ),'configuration_valid':True}))
""",
        ],
        env=application_environment(s, source),
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert child.returncode == 0, "Application configuration subprocess failed (values suppressed)"
    result = json.loads(child.stdout)
    assert result["configuration_valid"] and not FORBIDDEN & set(result["environment_names"])
    assert "INTERN_API_TOKEN" not in result["environment_names"]


def test_actual_child_application_role_cannot_use_owner_permissions(env, runtime_role):
    _, settings, *_ = env
    child_env = application_environment(replace(settings, database_url=runtime_role))
    child = subprocess.run(
        [
            sys.executable,
            "-c",
            """
import json, os
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sim2act.config import Settings
from sim2act.db import Store
store=Store(Settings.from_env().database_url)
with store.engine.connect() as c:
    flags=c.execute(text('SELECT rolsuper,rolcreatedb,rolcreaterole FROM pg_roles WHERE rolname=current_user')).one()
    ddl=c.execute(text("SELECT has_schema_privilege(current_user,current_schema(),'CREATE')")).scalar_one()
assert not any(flags) and not ddl
try:
    with store.engine.begin() as c:
        c.execute(text('CREATE TABLE child_must_be_denied (id integer)'))
except DBAPIError as error:
    assert getattr(error.orig,'sqlstate',None)=='42501'
else:
    raise AssertionError('Application child unexpectedly has DDL')
store.engine.dispose()
print(json.dumps({'environment_names':sorted(os.environ),'superuser':False,'create_database':False,'create_role':False,'schema_create':False,'ddl_denied':True}))
""",
        ],
        env=child_env,
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert child.returncode == 0, "Application-role subprocess failed (values suppressed)"
    result = json.loads(child.stdout)
    assert result["ddl_denied"] and not FORBIDDEN & set(result["environment_names"])
