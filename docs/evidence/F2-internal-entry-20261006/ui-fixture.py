"""Synthetic UI harness only. Production HTTP routes, no extra fixture endpoints or grants at run time."""
import sys
from pathlib import Path

import uvicorn

from sim2act.errors import DomainError

from sim2act.api import create_app
from sim2act.apps import create_csv_draft
from sim2act.config import Settings
from sim2act.contracts import Limits
from sqlalchemy import select

from sim2act.db import Store, projects

root = Path('/tmp/sim2act-e19-ui')
root.mkdir(exist_ok=True)
if '--fresh' in sys.argv:
    (root / 'fixture.db').unlink(missing_ok=True)  # Only this owned synthetic UI test DB.
store = Store('sqlite:///' + str(root / 'fixture.db'), test_only=True)
store.initialize()
try:
    user = store.authenticate('synthetic-e19-ui')
except DomainError:
    user = store.user('synthetic internal UI', 'synthetic-e19-ui')
settings = Settings(str(store.engine.url), root, mode='mock')
limits = Limits(**{k:getattr(settings,k) for k in Limits.model_fields})
with store.tx() as c:
    seeded = c.execute(select(projects.c.id).where(projects.c.owner_id == user)).first()
for title in ([] if seeded else ['SYNTHETIC internal A','SYNTHETIC internal B']):
    pid = store.project(user,title)
    rid = store.resource(user,pid,'synthetic.csv','csv','amount,quantity\n10,2\n30,3\n')
    create_csv_draft(store,user,pid,title,rid,'synthetic fixed readonly sum',limits)
if __name__ == '__main__':
    uvicorn.run(create_app(store,settings),host='127.0.0.1',port=8073)
