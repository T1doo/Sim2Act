"""Owned subprocess fixture: existing Worker with a synthetic application role."""

import os
from pathlib import Path

from sim2act import csv_dag
from sim2act.config import Settings
from sim2act.db import Store
from sim2act.worker import Worker


class NoModel:
    def request(self, *args, **kwargs):
        raise AssertionError("Fixed DAG must never request a model")


url = os.environ["SIM2ACT_SYNTHETIC_APP_URL"]
store = Store(url)
worker = Worker(store, Settings(url, Path(os.environ["SIM2ACT_SYNTHETIC_DIR"]), mode="mock"), NoModel())
job = store.claim(worker.id, worker.s.lease_seconds)
assert job and job["id"] == os.environ["SIM2ACT_SYNTHETIC_RUN"]
count = int(os.environ["SIM2ACT_SYNTHETIC_STEPS"])
if count:
    for _ in range(count):
        assert csv_dag.advance(worker, job)
else:
    worker.process(job)
store.engine.dispose()
