"""Explicit first-use provisioning for a bundled Windows PostgreSQL runtime.

No service registration, startup task, existing-cluster adoption or model calls.
"""
import hashlib
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
from urllib.parse import quote

import psycopg
from psycopg import sql

from .db import Store
from .db_readiness import inspect_database
from .desktop_protocol import ordinary, ProtocolError
from .private_postgres import PrivatePostgres
from .windows_credentials import write_dpapi


def _private_directory(path):
    path.mkdir()
    # Literal environment data, never interpolated into executable shell text.
    env={**os.environ,'SIM2ACT_PRIVATE_DIRECTORY':str(path)}
    # Windows PowerShell 5 must not inherit PowerShell 7 module directories.
    env={key:value for key,value in env.items() if key.upper()!='PSMODULEPATH'}
    command="""$ErrorActionPreference='Stop';$id=[Security.Principal.WindowsIdentity]::GetCurrent().User;$acl=New-Object Security.AccessControl.DirectorySecurity;$acl.SetOwner($id);$acl.SetAccessRuleProtection($true,$false);$rule=New-Object Security.AccessControl.FileSystemAccessRule($id,'FullControl','ContainerInherit,ObjectInherit','None','Allow');$acl.AddAccessRule($rule);Set-Acl -LiteralPath $env:SIM2ACT_PRIVATE_DIRECTORY -AclObject $acl"""
    result=subprocess.run([str(Path(os.environ['SystemRoot'])/'System32/WindowsPowerShell/v1.0/powershell.exe'),'-NoProfile','-NonInteractive','-Command',command],env=env,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=20,creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:raise ProtocolError('PRIVATE_DIRECTORY_PROTECTION_FAILED')


def initialize(runtime,data_root,model_token='',*,consent=False):
    if os.name!='nt' or consent is not True:raise ProtocolError('EXPLICIT_WINDOWS_SETUP_REQUIRED')
    if not isinstance(model_token,str) or len(model_token)>8192:raise ProtocolError('INVALID_MODEL_CREDENTIAL')
    runtime=ordinary(runtime);root=ordinary(data_root)
    if root.exists():raise ProtocolError('EXISTING_INSTALLATION_PRESERVED')
    manifest=json.loads((runtime/'runtime-manifest.json').read_text(encoding='utf-8'))
    if manifest.get('format')!='sim2act-private-postgres-runtime.v1':raise ProtocolError('UNVERIFIED_PG_RUNTIME')
    init=ordinary(runtime/'pgsql/bin/initdb.exe')
    expected=manifest['files']['pgsql/bin/initdb.exe']
    if init.stat().st_size!=expected['bytes'] or hashlib.sha256(init.read_bytes()).hexdigest()!=expected['sha256']:
        raise ProtocolError('PRIVATE_POSTGRES_BINARY_CHANGED')
    # Parent must be an explicitly chosen existing folder; never create a tree
    # elsewhere or replace a partial installation after an unknown failure.
    if not root.parent.is_dir():raise ProtocolError('SETUP_PARENT_MISSING')
    _private_directory(root)
    private=root/'private';private.mkdir()
    data=root/'data'
    with socket.socket() as probe:
        probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
    credentials={'bootstrap_user':'sim2act_bootstrap','bootstrap_password':secrets.token_hex(32),
        'migration_password':secrets.token_hex(32),'app_password':secrets.token_hex(32),
        'ui_token':secrets.token_hex(32),'port':port,'data_dir':str(data)}
    credential_file=private/'application-credentials.dpapi'
    write_dpapi(credential_file,json.dumps(credentials))
    key_file=private/'intern.dpapi'
    if model_token:write_dpapi(key_file,model_token)
    password_file=private/'init-password.tmp'
    with password_file.open('x',encoding='utf-8') as stream:stream.write(credentials['bootstrap_password'])
    try:
        with (private/'init.log').open('xb') as log:
            result=subprocess.run([str(init),'-D',str(data),'-U','sim2act_bootstrap','--auth=scram-sha-256','--encoding=UTF8','--locale=C','--pwfile='+str(password_file)],stdin=subprocess.DEVNULL,stdout=log,stderr=log,timeout=60,creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode:raise ProtocolError('PRIVATE_POSTGRES_INIT_UNCONFIRMED')
    finally:password_file.unlink(missing_ok=True)
    with (data/'postgresql.conf').open('a',encoding='ascii') as stream:
        stream.write(f"\nlisten_addresses='127.0.0.1'\nport={port}\nshared_buffers='64MB'\nmax_connections=20\npassword_encryption='scram-sha-256'\n")
    (data/'sim2act-private.json').write_text(json.dumps({'format':'sim2act.private-postgres.v1','data_dir':str(data),'port':port,'instance_id':secrets.token_hex(16)}),encoding='utf-8')
    controller=PrivatePostgres(runtime,data);store=None
    def connect(user,password,database='postgres'):
        return psycopg.connect(host='127.0.0.1',port=port,user=user,password=password,dbname=database,autocommit=True,connect_timeout=5)
    def url(user,password):return f'postgresql+psycopg://{user}:{quote(password,safe="")}@127.0.0.1:{port}/sim2act_local'
    try:
        controller.start()
        with connect(credentials['bootstrap_user'],credentials['bootstrap_password']) as admin:
            for role,key in [('sim2act_migrator','migration_password'),('sim2act_app','app_password')]:
                admin.execute(sql.SQL('CREATE ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS').format(sql.Identifier(role),sql.Literal(credentials[key])))
            admin.execute('CREATE DATABASE sim2act_local OWNER sim2act_migrator')
            admin.execute('REVOKE ALL ON DATABASE sim2act_local FROM PUBLIC')
            admin.execute('GRANT CONNECT ON DATABASE sim2act_local TO sim2act_app')
        store=Store(url('sim2act_migrator',credentials['migration_password']))
        quota_subject='default-intern-account'
        if model_token:
            from .production_evidence import ACCOUNT_ID
            from .production_trial_admission import canonical_quota_subject
            quota_subject=canonical_quota_subject(ACCOUNT_ID)
        store.initialize(quota_subject);store.engine.dispose();store=None
        with connect('sim2act_migrator',credentials['migration_password'],'sim2act_local') as owner:
            owner.execute('REVOKE CREATE ON SCHEMA public FROM PUBLIC')
            owner.execute('GRANT USAGE ON SCHEMA public TO sim2act_app')
            owner.execute('GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO sim2act_app')
            owner.execute('GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA public TO sim2act_app')
        store=Store(url('sim2act_app',credentials['app_password']))
        if inspect_database(store.engine)['status']!='STRUCTURAL_READY':raise ProtocolError('DATABASE_NOT_STRUCTURALLY_READY')
        store.user('本机使用者',credentials['ui_token'])
    finally:
        if store is not None:store.engine.dispose()
        if controller.identity is not None:controller.stop()
    selection={'format':'sim2act.local-installation.v1','runtime':str(runtime),'data':str(data),
        'credentials':str(credential_file),'workspace':str(root/'workspace'),
        'model_key':str(key_file) if model_token else None,'live':bool(model_token),
        'generation_enabled':bool(model_token),'generation_run_selection':bool(model_token)}
    if model_token:selection['production_account']=ACCOUNT_ID
    target=root/'local-installation.json'
    with target.open('x',encoding='utf-8') as stream:json.dump(selection,stream);stream.flush();os.fsync(stream.fileno())
    return target


if __name__=='__main__':
    import sys
    try:
        raw=sys.stdin.readline(20001)
        if len(raw)>20000:raise ValueError
        value=json.loads(raw)
        if set(value)!={'runtime','data_root','model_token','consent'}:raise ValueError
        target=initialize(value['runtime'],value['data_root'],value['model_token'],consent=value['consent'])
        print(json.dumps({'status':'LOCAL_SETUP_READY','selection':str(target)}),flush=True)
    except Exception:
        print(json.dumps({'status':'LOCAL_SETUP_UNCONFIRMED','action':'Preserve the selected data directory and private initialization log.'}),flush=True)
        raise SystemExit(1) from None
