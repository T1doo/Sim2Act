"""One finite, signed SQLite settlement interval; no model retry or permit.

SQLite holds its writer through both proof epochs. A background heartbeat
cannot commit there. Reserve the new contract's explicit interval beforehand,
then shorten it after the transaction, without ever reviving an expired owner.
"""

import logging
import math
import time
from contextlib import contextmanager

from sqlalchemy import select, update

from .db import attempts, events, runs
from .errors import DomainError

RESERVED = "NS_SETTLEMENT_LEASE_RESERVED"
RELEASED = "NS_SETTLEMENT_LEASE_RELEASED"


def _require(ok, message):
    if not ok:
        raise DomainError("VERSION_CONFLICT", message)


def _publish(state, worker, job, lease):
    if state is None:
        return
    # The caller holds renewal_lock, so this exact committed value supersedes
    # the previous publication, including when the interval is shortened.
    with state["lock"]:
        sequence = state.get("sync_renewal", {}).get("sequence", 0) + 1
        state["lease_until"] = lease
        state["sync_renewal"] = dict(sequence=sequence, worker_id=worker.id,
            run_id=job["id"], fence=job["fence"], lease_until=lease)


@contextmanager
def original_interval(worker, job, deadline, state):
    """Carry the actually committed ordinary lease to the final writer clock.

    This issues no renewal beyond the original heartbeat and no graph/permit.
    The conservative monotonic bound begins before that renewal, so time spent
    committing it or a wall-clock rollback cannot create additional lifetime.
    The caller owns the same renewal/writer locks until this scope closes.
    """
    store, settings, stop, owner = worker.store, worker.s, worker.stop, worker.id
    _require(store.sqlite and not hasattr(worker, '_settlement_interval'),
             'Original SQLite settlement cannot reenter')
    lease_seconds = settings.lease_seconds
    run_deadline = job['created_at'] + settings.run_seconds
    _require(all(type(v) in (int, float) and math.isfinite(v)
                 for v in (lease_seconds, deadline, run_deadline))
        and 0 < lease_seconds <= 30, 'Finite original ordinary lease required')
    started_mono, started_wall = time.monotonic(), time.time()
    cutoff = min(deadline, run_deadline)
    if state is not None:
        with state['lock']:
            original_deadline = state['deadline']
        if original_deadline is not None:
            _require(type(original_deadline) in (int, float) and math.isfinite(original_deadline),
                     'Finite original state deadline required')
            cutoff = min(cutoff, original_deadline)
    _require(not stop.is_set() and started_wall < cutoff, 'Original settlement interval ended')
    if state is None:
        lease = store.heartbeat(owner, job['id'], job['fence'], lease_seconds,
            _deadline=cutoff, _wait_seconds=min(5., cutoff-started_wall), _running_only=True)
    else:
        from .text_workflows import _renew_sync_locked
        lease = _renew_sync_locked(worker, job, state, deadline=cutoff)
    _require(type(lease) in (int, float) and math.isfinite(lease)
        and worker.store is store and worker.s is settings and worker.stop is stop
        and worker.id == owner, 'Original committed heartbeat or owner changed')
    cutoff = min(cutoff, lease)
    token = (started_mono + min(lease_seconds, cutoff-started_wall), cutoff)
    worker._settlement_interval = token
    try:
        checkpoint(worker)
        yield
    finally:
        if getattr(worker, '_settlement_interval', None) is token:
            del worker._settlement_interval
        else:
            # Retain an original failure and never delete foreign metadata.
            stop.set()


@contextmanager
def interval(worker, job, attempt_id, deadline, state):
    from . import natural_live_admission as gate
    from .spec_production import ProductionTrialBinding

    store, binding = worker.store, worker.pa_trial
    _require(not hasattr(worker, "_settlement_interval"), "Settlement cannot reenter")
    _require(store.sqlite and type(binding) is ProductionTrialBinding
        and type(binding.contract) is gate.PBTrialContract
        and type(binding.contract.caps) is gate.SQLiteSettlementCaps,
        "Explicit signed SQLite settlement policy required")
    contract = binding.contract
    caps = gate.SQLiteSettlementCaps.model_validate(contract.caps.model_dump())
    cutoff = min(deadline, job["created_at"] + worker.s.run_seconds,
        job["created_at"] + caps.run_seconds, contract.expires_at)
    _require(math.isfinite(cutoff) and not worker.stop.is_set(), "Settlement stopped")
    if state is not None:
        with state["lock"]:
            fatal = state.get("fatal_heartbeat")
            original_deadline = state.get("deadline", False)
        if fatal is not None:
            raise fatal
        if original_deadline is not None:
            _require(type(original_deadline) in (int, float) and math.isfinite(original_deadline),
                     "Finite original state deadline required")
            cutoff = min(cutoff, original_deadline)
    def booking_check():
        _require(not worker.stop.is_set() and time.monotonic() < booking_deadline
            and time.time() < min(current['lease_until'], lease, cutoff),
            'Settlement expired before commit')
    with store.tx(wait_seconds=5, _cap_wait=True, _commit_check=booking_check,
                  _commit_clock_check=booking_check) as c:
        current = store.guard(c, job["id"], job["fence"])
        _require(current["worker_id"] == worker.id
            and current["version"] == job["version"]
            and current["status"] == "RUNNING" and not current["cancel_intent"],
            "Settlement owner/version changed")
        gate._approved(store, c, job["principal_id"], contract, binding.approval_key)
        attempt = c.execute(select(attempts).where(attempts.c.id == attempt_id,
            attempts.c.run_id == job["id"])).mappings().one()
        meta = attempt["parameters"]["natural_spec"]
        _require(attempt["status"] == "RECEIVED"
            and meta["fence"] == job["fence"] and meta["run_version"] == job["version"]
            and meta["deadline"] == deadline, "Settlement received attempt changed")
        prior = c.execute(select(events.c.id).where(events.c.run_id == job["id"],
            events.c.kind == RESERVED,
            events.c.data["attempt_id"].as_string() == attempt_id)).first()
        _require(prior is None, "This attempt already reserved its one settlement interval")
        origin_mono = time.monotonic()
        now = time.time()
        lease = min(now + caps.settlement_seconds, cutoff)
        monotonic_deadline = origin_mono + min(caps.settlement_seconds, cutoff - now)
        booking_deadline = origin_mono + min(current['lease_until']-now, lease-now, cutoff-now)
        _require(not worker.stop.is_set() and now < min(current["lease_until"], lease),
            "Settlement cannot revive an expired interval")
        changed = c.execute(update(runs).where(runs.c.id == job["id"],
            runs.c.worker_id == worker.id, runs.c.fence == job["fence"],
            runs.c.version == job["version"], runs.c.status == "RUNNING",
            runs.c.cancel_intent.is_(False), runs.c.lease_until == current["lease_until"])
            .values(lease_until=lease))
        _require(changed.rowcount == 1, "Settlement lease competed")
        store.event(c, job["id"], RESERVED, dict(attempt_id=attempt_id,
            protocol=caps.settlement_protocol, seconds=caps.settlement_seconds,
            contract_fingerprint=binding.contract_fingerprint, worker_id=worker.id,
            fence=job["fence"], version=job["version"],
            previous_lease_until=current["lease_until"], lease_until=lease, deadline=cutoff))
        _require(not worker.stop.is_set() and time.time() < min(current["lease_until"], lease, cutoff),
            "Settlement expired before commit")
    _publish(state, worker, job, lease)
    # Monotonic bound also prevents a wall-clock rollback stretching this
    # critical section. The proof's existing wall-clock predicates remain.
    token = (monotonic_deadline, lease)
    worker._settlement_interval = token
    try:
        checkpoint(worker)
        yield
    finally:
        del worker._settlement_interval
        try:
            with store.tx(wait_seconds=5, _cap_wait=True) as c:
                now = time.time()
                ordinary = min(lease, cutoff, now + caps.lease_seconds)
                # A shortening CAS only. Do not resurrect expiry, cancellation,
                # terminal state, a changed version/fence or another worker.
                changed = c.execute(update(runs).where(runs.c.id == job["id"],
                    runs.c.worker_id == worker.id, runs.c.fence == job["fence"],
                    runs.c.version == job["version"], runs.c.status == "RUNNING",
                    runs.c.cancel_intent.is_(False), runs.c.lease_until == lease,
                    runs.c.lease_until > now).values(lease_until=ordinary))
                if changed.rowcount == 1:
                    store.event(c, job["id"], RELEASED, dict(attempt_id=attempt_id,
                        fence=job["fence"], lease_until=ordinary))
            if changed.rowcount == 1:
                _publish(state, worker, job, ordinary)
        except Exception as error:
            # The business transaction may already be committed. Cleanup must
            # never turn a VERIFIED response into a RECEIVED rejection/retry or
            # overwrite its original exception. The finite lease still expires.
            worker._settlement_cleanup_error = error
            worker.stop.set()
            if state is not None:
                with state["lock"]:
                    state["fatal_heartbeat"] = error
            logging.getLogger(__name__).error("Settlement lease cleanup failed; worker stopped (%s)",
                type(error).__name__)


def checkpoint(worker):
    control = getattr(getattr(worker, "store", None), "_local_model_control", None)
    if control is not None:
        control.checkpoint(worker)
    token = getattr(worker, "_settlement_interval", None)
    if token is not None and (worker.stop.is_set() or time.monotonic() >= token[0]
            or time.time() >= token[1]):
        raise DomainError("BUDGET_EXHAUSTED", "Finite model settlement interval ended")


def commit_checkpoint(worker, interval, stop, *, control=True):
    """Original control callback first; immutable scope/time/stop checks last."""
    if control:checkpoint(worker)
    _require(worker.stop is stop and getattr(worker, '_settlement_interval', None) is interval,
             'Finite model commit scope changed')
    if stop.is_set() or interval is not None and (time.monotonic() >= interval[0]
            or time.time() >= interval[1]):
        raise DomainError('BUDGET_EXHAUSTED', 'Finite model settlement interval ended')
