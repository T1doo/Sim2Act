"""Explicit launcher-only tail evidence, never a validator or authority.

No product imports at module load. Rejected comparisons are a post-exception
read of existing safe argument storage, NOT the original short-circuit trace.
No SQL, business clock, guard, model dump, repr, serializer or I/O is invoked.
"""

import math
from contextlib import contextmanager
from threading import get_ident
from time import monotonic_ns, thread_time_ns

NAMES = ("second_prefix", "second_commit", "recheck", "scope_exit")
RUN_MESSAGE = "Run identity, cancellation, version or finite lease changed"


def safe_dict(value, maximum=64):
    if type(value) is not dict or len(value) > maximum:
        raise TypeError("unsupported diagnostic dictionary")
    if any(type(key) is not str for key in value):
        raise TypeError("unsupported diagnostic dictionary keys")
    return value


def safe_number(value):
    kind = type(value)
    if kind is int:
        if int.bit_length(value) > 64:
            raise TypeError("diagnostic integer range")
    elif kind is float:
        if math.isfinite(value) and abs(value) > 1e20:
            raise TypeError("diagnostic float range")
    elif kind is not bool:
        raise TypeError("unsupported diagnostic number")
    return value


def run_comparisons(args, types):
    """Only fixed fields of exact built-ins/RowMapping/known model __dict__."""
    user, contract, stage, run, version, fence, approval, phase, at = args

    def model(value, allowed):
        if not any(type(value) is known for known in allowed):
            raise TypeError("unsupported diagnostic model storage")
        data = object.__getattribute__(value, "__dict__")
        return safe_dict(data)

    def text(value):
        if type(value) is not str or len(value) > 256:
            raise TypeError("unsupported diagnostic text")
        return value

    c = model(contract, types["contract"])
    caps = model(c["caps"], types["caps"])
    bindings = c["bindings"]
    if type(bindings) is not list or len(bindings) != 2 or type(stage) is not str:
        raise TypeError("unsupported diagnostic bindings")
    b = model(bindings[1 if stage == "cold" else 0], types["binding"])
    a = model(approval, types["approval"])
    p = None if phase is None else model(phase, types["phase"])
    keys = model(c["stage_keys"], types["keys"])
    for mapping, names in ((c, ("project_id", "runtime_id")),
                           (b, ("resource_id",)), (keys, ("generate",))):
        for key in names:
            text(mapping[key])
    for value in (c["expires_at"], caps["run_seconds"], a["approved_at"], at, version, fence):
        safe_number(value)
    if p is not None:
        text(p["runtime_id"])
    text(user)
    if run is None:
        return dict(comparisons={"run_present": False}, scalars={}, incomplete=True)
    if not any(type(run) is known for known in types["row"]):
        raise TypeError("unsupported diagnostic row storage")
    if type(run) is dict:
        safe_dict(run)
        get = run.__getitem__
    else:
        data = object.__getattribute__(run, "_data")
        index = object.__getattribute__(run, "_key_to_index")
        if type(data) is not tuple or len(data) > 64 or type(index) is not dict or len(index) > 256:
            raise TypeError("unsupported diagnostic SQL row scale")
        lookup = {}
        # Iterate without hashing/comparing any foreign Column/alias key.
        for key, position in dict.items(index):
            if type(key) is str or type(key) is types["quoted"]:
                if len(key) > 256 or type(position) is not int or not 0 <= position < len(data):
                    raise TypeError("unsupported diagnostic SQL index")
                lookup[str.__str__(key)] = position
        def get(key):
            return data[lookup[key]]
    # Never iterate/copy a whole row or any hidden payload.
    r = {key: get(key) for key in (
        "principal_id", "project_id", "runtime_id", "request_key", "status",
        "cancel_intent", "version", "fence", "created_at", "lease_until")}
    for key in ("principal_id", "project_id", "runtime_id", "request_key", "status"):
        text(r[key])
    for key in ("version", "fence", "created_at", "lease_until"):
        safe_number(r[key])
    if type(r["cancel_intent"]) is not bool:
        raise TypeError("unsupported diagnostic cancellation field")
    refs = get("resource_refs")
    if type(refs) is not list:
        raise TypeError("unsupported diagnostic resource list")
    resource_equal = len(refs) == 1 and text(refs[0]) == b["resource_id"]
    created, lease, expiry = r["created_at"], r["lease_until"], c["expires_at"]
    run_deadline = created + caps["run_seconds"]
    comparisons = {}
    incomplete = False

    def check(name, calculation):
        nonlocal incomplete
        try:
            result = calculation()
            if type(result) is not bool:
                raise TypeError("diagnostic comparison not boolean")
            comparisons[name] = result
        except BaseException:
            comparisons[name] = None
            incomplete = True

    for name, calculation in (
        ("version_type_int", lambda: type(version) is int),
        ("fence_type_int", lambda: type(fence) is int),
        ("run_present", lambda: run is not None),
        ("principal_equal", lambda: r["principal_id"] == user),
        ("project_equal", lambda: r["project_id"] == c["project_id"]),
        ("runtime_equal", lambda: r["runtime_id"] == (c["runtime_id"] if p is None else p["runtime_id"])),
        ("request_key_or_phase", lambda: p is not None or r["request_key"] == keys["generate"]),
        ("resource_refs_equal", lambda: resource_equal),
        ("status_running", lambda: r["status"] == "RUNNING"),
        ("not_cancelled", lambda: r["cancel_intent"] is False),
        ("version_equal", lambda: r["version"] == version),
        ("fence_equal", lambda: r["fence"] == fence),
        ("fence_positive", lambda: fence >= 1),
        ("created_type_numeric", lambda: type(created) in (int, float)),
        ("created_finite", lambda: math.isfinite(created)),
        ("created_in_approval_interval", lambda: a["approved_at"] <= created <= at),
        ("lease_type_numeric", lambda: type(lease) in (int, float)),
        ("lease_finite", lambda: math.isfinite(lease)),
        ("before_min_deadline", lambda: at < min(lease, run_deadline, expiry)),
        ("before_lease", lambda: at < lease),
        ("before_run_deadline", lambda: at < run_deadline),
        ("before_contract_expiry", lambda: at < expiry),
    ):
        check(name, calculation)

    def number(value):
        nonlocal incomplete
        if not (type(value) is int or type(value) is float) or not math.isfinite(value):
            incomplete = True
            return None  # Never export NaN/Infinity or stringify an object.
        return value

    return dict(comparisons=comparisons, scalars=dict(at=number(at),
        lease_until=number(lease), run_deadline=number(run_deadline),
        contract_expires_at=number(expiry), min_deadline=number(min(lease, run_deadline, expiry))),
        incomplete=incomplete)


class TailObserver:
    def __init__(self, metrics, trial, *, wall=monotonic_ns, cpu=thread_time_ns, thread=get_ident,
                 prefix_type=None):
        self.metrics, self.trial = metrics, trial
        self.wall, self.cpu, self.thread = wall, cpu, thread
        self.prefix_type = prefix_type
        self.owner = None
        self.active = None
        self.incomplete = False
        self.rows = {name: dict(calls=0, returns=0, raises=0,
            wall_ns=0, cpu_ns=0, check_calls=0, input_key_calls=0, complete=True) for name in NAMES}
        self.failures = []  # Hard maximum 4, no business payload retained.
        try:
            self.owner = thread()
        except BaseException:
            self.safe_fault()

    def fault(self):
        self.incomplete = True

    def safe_fault(self):
        try:
            self.fault()
        except BaseException:
            pass

    def eligible(self, trial):
        try:
            return trial is not None and trial is self.trial() and self.thread() == self.owner
        except BaseException:
            self.safe_fault()
            return False

    def snapshot(self, guard):
        wall, cpu = self.wall(), self.cpu()
        checks, keys = guard._diagnostic_counts
        if any(type(v) is not int for v in (wall, cpu, checks, keys)):
            raise TypeError("invalid tail clock/counters")
        return wall, cpu, checks, keys

    @contextmanager
    def span(self, name, guard):
        region, before, row = None, None, None
        previous = self.active
        try:
            row = self.rows[name]
            row["calls"] += 1
            if row["calls"] != 1:
                raise ValueError("duplicate fixed tail span")
            self.active = name
            region = self.metrics.region(name)
            region.__enter__()
            before = self.snapshot(guard)
        except BaseException:
            self.safe_fault()
        returned = False
        try:
            yield
            returned = True
        finally:
            try:
                if row is not None:
                    row["returns" if returned else "raises"] += 1
                    after = self.snapshot(guard)
                    if before is None or any(a < b for a, b in zip(after, before, strict=True)):
                        raise ValueError("incomplete tail delta")
                    for key, a, b in zip(("wall_ns", "cpu_ns", "check_calls", "input_key_calls"), after, before, strict=True):
                        row[key] += a - b
            except BaseException:
                self.safe_fault()
                if row is not None:
                    row["complete"] = False
            finally:
                try:
                    if region is not None:
                        region.__exit__(None, None, None)
                except BaseException:
                    self.safe_fault()
                self.active = previous

    def context(self, original):
        observer = self

        class Context:
            def __init__(self, current):
                self.current, self.value = current, None

            def __enter__(self):
                self.value = self.current.__enter__()
                return self.value

            def __exit__(self, *exc):
                guard = None
                try:
                    if observer.eligible(self.value):
                        guard = self.value.guard
                except BaseException:
                    observer.safe_fault()
                if guard is not None:
                    with observer.span("scope_exit", guard):
                        return self.current.__exit__(*exc)
                return self.current.__exit__(*exc)

        def wrapped(*args, **kwargs):
            return Context(original(*args, **kwargs))

        return wrapped

    def commit(self, original):
        def wrapped(trial, prefix):
            guard = None
            try:
                if self.eligible(trial) and type(prefix) is self.prefix_type:
                    key = safe_dict(object.__getattribute__(prefix, "__dict__"))["key"]
                    if type(key) is str and key == "commit:second":
                        guard = trial.guard
            except BaseException:
                self.safe_fault()
            if guard is not None:
                with self.span("second_commit", guard):
                    return original(trial, prefix)
            return original(trial, prefix)
        return wrapped

    def recheck(self, original):
        def wrapped(trial, *args, **kwargs):
            guard = None
            try:
                if self.eligible(trial) and self.active == "second_commit":
                    guard = trial.guard
            except BaseException:
                self.safe_fault()
            if guard is not None:
                with self.span("recheck", guard):
                    return original(trial, *args, **kwargs)
            return original(trial, *args, **kwargs)
        return wrapped

    def prefix(self, original):
        def wrapped(worker, c, run, binding, guard, boundary, *args, **kwargs):
            observe = False
            try:
                trial = self.trial()
                observe = (self.eligible(trial) and type(boundary) is str and boundary == "second" and guard is trial.guard
                           and worker is trial.worker and c is trial.c)
            except BaseException:
                self.safe_fault()
            if observe:
                with self.span("second_prefix", guard):
                    return original(worker, c, run, binding, guard, boundary, *args, **kwargs)
            return original(worker, c, run, binding, guard, boundary, *args, **kwargs)
        return wrapped

    def run_predicate(self, original, types):
        def wrapped(*args, **kwargs):
            try:
                return original(*args, **kwargs)
            except BaseException as error:
                try:
                    if (type(self.active) is str and self.active in NAMES and self.thread() == self.owner
                            and type(args[2]) is str and args[2] == "cold"):
                        if len(self.failures) >= 4:
                            raise ValueError("tail failure evidence capacity")
                        message = None
                        if type(error) is types["error"]:
                            message = safe_dict(object.__getattribute__(error, "__dict__")).get("message")
                        record = dict(evaluation_basis="POST_EXCEPTION_EXISTING_SAFE_ARGUMENTS_NOT_SHORT_CIRCUIT_TRACE",
                            error_type=type.__getattribute__(type(error), "__name__"), predicate_message_matches=(
                                type(message) is str and message == RUN_MESSAGE))
                        self.failures.append(record)
                        try:
                            record.update(run_comparisons(args, types))
                        except BaseException:
                            record["incomplete"] = True
                        if record.get("incomplete"):
                            self.safe_fault()
                except BaseException:
                    self.safe_fault()
                raise  # Same original object, traceback, cause and suppression.
        return wrapped

    def report(self):
        try:
            rows = {name: dict(row) for name, row in self.rows.items()}
            outer, inner = rows["second_commit"], rows["recheck"]
            remainder = None
            if all(r["calls"] == 1 and r["complete"] for r in (outer, inner)):
                remainder = {k: outer[k] - inner[k] for k in ("wall_ns", "cpu_ns", "check_calls", "input_key_calls")}
                if any(v < 0 for v in remainder.values()):
                    remainder = None
                    self.safe_fault()
            if outer["calls"] and remainder is None:
                self.safe_fault()
            if self.metrics.incomplete or self.active is not None:
                self.safe_fault()
            return dict(status="INCOMPLETE" if self.incomplete else "COMPLETE_OBSERVATION",
                regions=rows, second_commit_minus_observed_recheck=remainder,
                remainder_basis="INCLUSIVE_MINUS_OBSERVED_RECHECK_ONLY_NOT_ALL_CHILDREN",
                run_rejections=self.failures, original_clock="existing at argument; no time.time/SQL/guard replay",
                timing_basis="monotonic_ns wall and foreground thread_time_ns; nonzero overhead",
                unavailable_regions="calls=0 means NOT_REACHED; no cost extrapolation or success proof")
        except BaseException:
            self.safe_fault()
            return dict(status="INCOMPLETE", detail="tail report unavailable")

    def install(self, patch, runtime, gate, spec):
        from sqlalchemy.engine import RowMapping
        from sqlalchemy.sql.elements import quoted_name

        types = dict(contract=(gate.TrialContract, gate.TrialContractV2, gate.PBTrialContract),
            caps=(gate.TrialCaps,), binding=(gate.MaterialGoal,), approval=(gate.Approval,),
            keys=(gate.StageKeys,), phase=(gate.StageAuthority, gate.StageAuthorityV2), row=(dict, RowMapping),
            quoted=quoted_name, error=gate.DomainError)
        self.prefix_type = spec._ColdCommitPrefix
        patch.setattr(runtime._ColdTrialGraph, "commit", self.commit(runtime._ColdTrialGraph.commit))
        patch.setattr(runtime._ColdTrialGraph, "_recheck", self.recheck(runtime._ColdTrialGraph._recheck))
        patch.setattr(spec, "_cold_commit_prefix", self.prefix(spec._cold_commit_prefix))
        patch.setattr(gate, "_require_run_context_row", self.run_predicate(gate._require_run_context_row, types))
