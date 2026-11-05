"""Explicitly owned Windows PostgreSQL lifecycle; no service registration.

Not yet wired into desktop startup. Provisioning must create the ownership
marker only after explicit initialization of a new private cluster.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path

import psutil

from .desktop_protocol import ProtocolError, ordinary


def verify_process(identity, *, pid, created, executable, data_dir, port):
    if (identity.get('pid') != pid or identity.get('created') != created
            or Path(identity.get('executable','')).resolve() != Path(executable).resolve()
            or Path(identity.get('data_dir','')).resolve() != Path(data_dir).resolve()
            or identity.get('port') != port):
        raise ProtocolError('PRIVATE_POSTGRES_IDENTITY_MISMATCH')


class PrivatePostgres:
    def __init__(self, runtime, data_dir):
        self.runtime = ordinary(runtime)
        self.data = ordinary(data_dir)
        self.marker = json.loads((self.data/'sim2act-private.json').read_text(encoding='utf-8'))
        if (self.marker.get('format') != 'sim2act.private-postgres.v1'
                or Path(self.marker.get('data_dir','')).resolve() != self.data.resolve()
                or type(self.marker.get('port')) is not int
                or not 1024 <= self.marker['port'] <= 65535):
            raise ProtocolError('PRIVATE_POSTGRES_MARKER_INVALID')
        if (self.data/'PG_VERSION').read_text().strip() != '16':
            raise ProtocolError('PRIVATE_POSTGRES_VERSION_MISMATCH')
        self.port = self.marker['port']
        self.claim = self.data/'sim2act-running.json'
        self.identity = None
        manifest = json.loads((self.runtime/'runtime-manifest.json').read_text())
        for name in ('pgsql/bin/pg_ctl.exe','pgsql/bin/postgres.exe'):
            binary = ordinary(self.runtime/name)
            expected = manifest['files'][name]
            if hashlib.sha256(binary.read_bytes()).hexdigest() != expected['sha256']:
                raise ProtocolError('PRIVATE_POSTGRES_BINARY_CHANGED')
        self.pg_ctl = self.runtime/'pgsql/bin/pg_ctl.exe'
        self.postgres = self.runtime/'pgsql/bin/postgres.exe'

    def _command(self, *arguments, timeout=35):
        env = {k:v for k,v in os.environ.items() if not k.upper().startswith('PG')}
        try:
            # A Windows server descendant can inherit a pipe writer, causing
            # communicate() to wait after pg_ctl exits. File handles avoid
            # coupling control completion to the server's lifetime.
            with tempfile.TemporaryFile() as output:
                result = subprocess.run([str(self.pg_ctl),*arguments],env=env,
                    stdin=subprocess.DEVNULL,stdout=output,stderr=output,
                    timeout=timeout,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        except (OSError,subprocess.TimeoutExpired) as error:
            raise ProtocolError('PRIVATE_POSTGRES_CONTROL_UNCONFIRMED') from error
        if result.returncode:
            raise ProtocolError('PRIVATE_POSTGRES_CONTROL_UNCONFIRMED')

    def _observed(self):
        rows=(self.data/'postmaster.pid').read_text().splitlines()
        if len(rows)<4 or Path(rows[1]).resolve()!=self.data.resolve() or int(rows[3])!=self.port:
            raise ProtocolError('PRIVATE_POSTGRES_PID_FILE_MISMATCH')
        process=psutil.Process(int(rows[0]))
        if Path(process.exe()).resolve()!=self.postgres.resolve():
            raise ProtocolError('PRIVATE_POSTGRES_EXECUTABLE_MISMATCH')
        return dict(pid=process.pid,created=process.create_time(),executable=process.exe(),
                    data_dir=str(self.data.resolve()),port=self.port)

    def start(self):
        if self.identity is not None or (self.data/'postmaster.pid').exists():
            raise ProtocolError('PRIVATE_POSTGRES_EXISTING_INSTANCE')
        # Existing/uncertain ownership is never silently removed or adopted.
        with self.claim.open('x',encoding='utf-8') as stream:
            json.dump({'state':'STARTING','owner_pid':os.getpid()},stream)
        self._command('start','-D',str(self.data),'-p',str(self.postgres),'-w','-t','30',
                      '-l',str(self.data/'server.log'),'-o',f'-h 127.0.0.1 -p {self.port}')
        self.identity=self._observed()
        self.claim.write_text(json.dumps(self.identity),encoding='utf-8')
        return dict(self.identity)

    def stop(self, timeout=30):
        if not 1 <= timeout <= 30:
            raise ProtocolError('PRIVATE_POSTGRES_STOP_BUDGET_EXHAUSTED')
        if self.identity is None:
            raise ProtocolError('PRIVATE_POSTGRES_NOT_OWNED')
        verify_process(self.identity,**self._observed())
        if json.loads(self.claim.read_text())!=self.identity:
            raise ProtocolError('PRIVATE_POSTGRES_CLAIM_CHANGED')
        self._command('stop','-D',str(self.data),'-w','-t',str(int(timeout)),'-m','smart',timeout=timeout)
        if (self.data/'postmaster.pid').exists():
            raise ProtocolError('PRIVATE_POSTGRES_STOP_UNCONFIRMED')
        try:
            remaining=psutil.Process(self.identity['pid'])
            if remaining.create_time()==self.identity['created']:
                raise ProtocolError('PRIVATE_POSTGRES_STOP_UNCONFIRMED')
        except psutil.NoSuchProcess:
            pass
        self.claim.unlink()
        self.identity=None
