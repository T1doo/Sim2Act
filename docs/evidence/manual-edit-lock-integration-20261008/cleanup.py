"""Remove this task's own isolated resources, only after final tests complete."""
import json
import shutil
import subprocess
import time
from pathlib import Path

from sqlalchemy import create_engine, text

root = Path(__file__).resolve().parent
container = 'sim2act-lock-integration-pg'
engine = create_engine('postgresql+psycopg://sim2act_owned@/sim2act_owned?host=/tmp/sim2act-lock-integration-db/socket')
with engine.connect() as c:
    schemas = c.execute(text("SELECT nspname FROM pg_namespace WHERE nspname LIKE 'test_%'")).scalars().all()
    roles = c.execute(text("SELECT rolname FROM pg_roles WHERE rolname LIKE 'test_app_%'")).scalars().all()
    public = c.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public'")).scalars().all()
    version = c.execute(text('SHOW server_version')).scalar_one()
assert not schemas and not roles and not public
engine.dispose()
info = json.loads(subprocess.check_output(['docker', 'inspect', container], text=True))[0]
assert info['HostConfig']['NetworkMode'] == 'none' and not info['NetworkSettings']['Ports']
report = dict(container_id=info['Id'], image_id=info['Image'], server_version=version,
    schemas=schemas, temporary_roles=roles, public_tables=public, network='none', ports={}, force=False)
(root / 'cleanup.json').write_text(json.dumps(report, indent=2) + '\n')
subprocess.check_call(['docker', 'stop', container])
for _ in range(100):
    remaining = subprocess.check_output(['docker', 'ps', '-a', '--filter', 'name=' + container, '--format', '{{.ID}}'], text=True).strip()
    if not remaining:
        break
    time.sleep(.1)
assert not remaining
subprocess.check_call(['docker', 'image', 'rm', 'postgres:17.9'])
assert not subprocess.check_output(['docker', 'image', 'ls', 'postgres:17.9', '--format', '{{.ID}}'], text=True).strip()
paths = [Path('/tmp/sim2act-lock-integration-' + suffix) for suffix in [
    'final-sqlite', 'final-pg', 'archives', 'db', 'node']]
for p in paths:
    if p.exists():
        shutil.rmtree(p)
assert not any(p.exists() for p in paths)
report.update(container_remaining=False, image_remaining=False, removed_paths=[str(p) for p in paths])
(root / 'cleanup.json').write_text(json.dumps(report, indent=2) + '\n')
print('Owned catalog zero; container/image/temporary test and npm paths removed')
