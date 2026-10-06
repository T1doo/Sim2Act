"""Owned synthetic PG subprocess fault fixture; never part of production dispatch."""

import os
import time
from dataclasses import replace
from pathlib import Path

from sim2act import app_jobs
from sim2act.config import Settings
from sim2act.db import Store
from sim2act.worker import Worker


class NoModel:
    def request(self, *_):
        raise AssertionError("Fixed internal worker must not request a model")


url = os.environ["SIM2ACT_SYNTHETIC_APP_URL"]
root = Path(os.environ["SIM2ACT_SYNTHETIC_FAULT_DIR"])
mode = os.environ["SIM2ACT_SYNTHETIC_FAULT"]
original_compute = app_jobs.compute
original_commit = app_jobs.commit_result


def compute(plan):
    (root / "entered").write_text("PREPARED; compute outside DB transaction")
    if mode == "hold":
        until = time.monotonic() + 12
        while not (root / "continue").exists():
            if time.monotonic() > until:
                raise RuntimeError("Bounded synthetic subprocess fault wait exhausted")
            time.sleep(0.03)
    output = original_compute(plan)
    if mode == "before_commit":
        os._exit(73)
    return output


def commit(worker, run, plan, output):
    original_commit(worker, run, plan, output)
    if mode == "after_commit":
        os._exit(74)


app_jobs.compute = compute
app_jobs.commit_result = commit
worker = Worker(Store(url), replace(Settings(url, root, mode="mock"), lease_seconds=1), NoModel())
worker.once()
