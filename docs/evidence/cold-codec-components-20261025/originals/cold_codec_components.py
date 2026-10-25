"""One offline codec cost group; never runs a Worker, prefix, grant or model.

The reserve encoder is an experiment, not a product switch. Full stored rows
are genuine synthetic archive data; their runtime G0 alias topology is unknown.
"""

from __future__ import annotations

import builtins
import cProfile
import gzip
import hashlib
import io
import json
import pstats
import statistics
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.engine import RowMapping
from sqlalchemy.engine.result import SimpleResultMetaData
from sqlalchemy.sql.elements import quoted_name

from sim2act import db
from sim2act import natural_live_admission as gate
from sim2act import natural_spec_runtime as runtime
from sim2act.errors import DomainError

RESERVE = 1024 * 1024
PREFIX = b"SIM2ACT_COLD_GRAPH_PICKLE_V2\x00"
ROOT = Path("docs/evidence/g0-685d62e-once-20261025")
FIXTURE = ROOT / "originals/runs/g0-685d62e-09239e81521f4a45a273cf7a02244977/fixture.db.gz"
CONTRACT = dict(rounds=12, calls_per_arm=8, warmup_per_arm=4, reserve_bytes=RESERVE,
    output_bytes_limit=16 * 1024 * 1024, work_seconds=45, automatic_retry=0,
    minimum_wall_wins=9, maximum_wall_median_ratio=0.95, maximum_cpu_median_ratio=0.95,
    cprofile_calls=1, instrumented_calls=1, expected_baseline_calls=1,
    paired_calls_total=200, semantic_and_scope_calls_are_additional=True)
SOURCES = ("scripts/diagnostics/cold_codec_components.py",
           "src/sim2act/natural_spec_runtime.py", "src/sim2act/natural_live_admission.py")


def reserve_bytes(values):
    """Same actual output type/Pickler, extra capacity only before traversal."""
    output = io.BytesIO()
    output.seek(RESERVE - 1)
    output.write(b"\x00")
    output.seek(0)
    output.write(PREFIX)
    runtime._ColdGraphPickler(output, protocol=5).dump(values)
    output.truncate(output.tell())
    return output.getvalue()


def load_corpus():
    original = gzip.decompress(FIXTURE.read_bytes())
    index = json.loads((ROOT / "ORIGINALS.json").read_text())
    identity = next(v for k, v in index.items() if k.endswith("/fixture.db"))
    assert hashlib.sha256(original).hexdigest() == identity["original_sha256"]
    engine = create_engine("sqlite+pysqlite:///:memory:")
    try:
        with engine.connect() as c:
            driver = c.connection.driver_connection
            driver.deserialize(original)
            driver.execute("PRAGMA query_only=ON")
            stored = {}
            for name in ("runs", "attempts", "delivery_graph_requests", "events", "operations", "grants"):
                table = getattr(db, name)
                stored[name] = list(c.execute(select(table).order_by(*table.primary_key.columns)).mappings())
            contract_raw = next(r["snapshot"]["request"] for r in stored["delivery_graph_requests"]
                                if r["kind"] == "natural-live-trial.v1.scope")
            contract = gate.PBTrialContract.model_validate(contract_raw)
    finally:
        engine.dispose()
    shared = dict(values=[None, False, 1, 1.5, "synthetic shared content", b"wire"])
    keys = [quoted_name("visible", True)]
    metadata = SimpleResultMetaData(keys)
    data = (shared, dict(hidden=[shared, b"hidden data", True]))
    hidden = RowMapping(metadata, None, {"visible": 0, "hidden_alias": 1}, data)
    inputs = dict(stored=stored, first=shared, again=[shared, stored["attempts"][0]],
                  hidden_row=hidden, hidden_data=data,
                  hidden_keys=object.__getattribute__(metadata, "_keys"))
    limits = gate._limits(contract)
    return dict(contract=contract, contract_fingerprint=db.fingerprint(contract.model_dump()), inputs=inputs,
                role_limits={name: limits for name in ("source", "generate", "platform", "trial", "per_use")}), dict(
        fixture_sha256=identity["original_sha256"],
        fixture_gzip_sha256=hashlib.sha256(FIXTURE.read_bytes()).hexdigest(),
        stored_rows={name: len(values) for name, values in stored.items()},
        stored_columns={name: list(getattr(db, name).c.keys()) for name in stored},
        synthetic_aliases="shared dict/list, actual stored RowMapping, explicit hidden RowMapping/data/keys aliases",
        runtime_g0_frontier=False, database_engine_disposed=True)


def envelope(data):
    return dict(inputs=data["inputs"], role_limits=data["role_limits"], phase="pre",
        binding=dict(contract=gate._trial_typed_storage(gate.PBTrialContract, data["contract"]),
            key="offline-profile-only", account="synthetic-offline", version="PROFILE_ONLY",
            fingerprint=data["contract_fingerprint"]))


def semantic_checks(data):
    checks = []
    for size in (0, 65535, 65536, RESERVE - 1, RESERVE, RESERVE + 1):
        shared = dict(value=b"x" * size, limits=data["role_limits"]["trial"])
        value = dict(a=shared, b=[shared], row=data["inputs"]["hidden_row"])
        assert reserve_bytes(value) == runtime._cold_graph_bytes(value)
        checks.append("frame/reserve boundary " + str(size))
    before = runtime._cold_graph_bytes(envelope(data))
    assert reserve_bytes(envelope(data)) == before
    data["inputs"]["first"]["values"].append("mutation-between-calls")
    after = reserve_bytes(envelope(data))
    assert after == runtime._cold_graph_bytes(envelope(data)) and after != before
    data["inputs"]["first"]["values"].pop()
    checks.append("fresh cross-root alias mutation, no content cache")
    caps = object.__getattribute__(data["contract"].caps, "__dict__")
    previous = caps["max_output_tokens"]
    try:
        caps["max_output_tokens"] -= 1
        changed_contract = reserve_bytes(envelope(data))
        assert changed_contract == runtime._cold_graph_bytes(envelope(data)) and changed_contract != before
    finally:
        caps["max_output_tokens"] = previous
    checks.append("fresh full contract despite fixed binding fingerprint metadata")

    class Foreign:
        def __reduce__(self):
            raise AssertionError("foreign reducer must not run")

    invalid_row = RowMapping(SimpleResultMetaData(["visible"]), None,
                            {"visible": True}, ("value",))
    for value in (dict(unknown=Foreign(), bad=invalid_row), dict(bad=invalid_row, unknown=Foreign())):
        outcomes = []
        for encoder in (runtime._cold_graph_bytes, reserve_bytes):
            try:
                encoder(value)
            except DomainError as error:
                outcomes.append((type(error), error.code, str(error)))
            else:
                raise AssertionError("invalid value was accepted")
        assert outcomes[0] == outcomes[1]
    checks.append("mixed unknown/invalid-row rejection order")
    imported, errors = [], []
    original_import = builtins.__import__
    for encoder in (runtime._cold_graph_bytes, reserve_bytes):
        calls = []
        def refusing(name, *args, calls=calls, **kwargs):
            if name == runtime.__name__:
                calls.append(name)
                raise ValueError("synthetic import refusal")
            return original_import(name, *args, **kwargs)
        try:
            builtins.__import__ = refusing
            try:
                encoder(data["role_limits"]["trial"])
            except Exception as error:
                errors.append((type(error), str(error)))
            else:
                raise AssertionError("marker import did not refuse")
        finally:
            builtins.__import__ = original_import
        imported.append(calls)
    assert errors[0] == errors[1] and imported[0] == imported[1] == [runtime.__name__]
    checks.append("original marker import refusal and translation")
    concurrency = []
    for encoder in (runtime._cold_graph_bytes, reserve_bytes):
        entered, changed = threading.Event(), threading.Event()
        value = dict(limits=data["role_limits"]["trial"], after=dict(value="before"))
        callback_calls = []
        def mutate(value=value, entered=entered, changed=changed):
            if entered.wait(2):
                value["after"]["value"] = "changed-at-original-import-boundary"
                changed.set()
        thread = threading.Thread(target=mutate)
        def importing(name, *args, entered=entered, changed=changed,
                      callback_calls=callback_calls, **kwargs):
            if name == runtime.__name__:
                callback_calls.append(name)
                entered.set()
                assert changed.wait(2), "owned mutation thread failed"
            return original_import(name, *args, **kwargs)
        thread.start()
        try:
            builtins.__import__ = importing
            encoded = encoder(value)
        finally:
            builtins.__import__ = original_import
            entered.set()
            thread.join(3)
        assert not thread.is_alive() and changed.is_set()
        concurrency.append((encoded, callback_calls))
    assert concurrency[0] == concurrency[1]
    checks.append("two joined owned threads; mutation at same original import boundary")
    assert io.BytesIO is runtime._ColdGraphBytesIO
    assert runtime._ColdGraphPicklerBase.__module__ == "_pickle"
    return checks


def scope_checks(data):
    """Actual small CGR lifecycle, no claim/Worker.once/admission or G0."""
    from sim2act import pb_natural_specs as pb
    from sim2act.config import Settings
    from sim2act.production_trial_admission import canonical_quota_subject
    from sim2act.spec_production import ProductionTrialBinding
    from sim2act.worker import Worker

    original = runtime._cold_graph_bytes
    checks = []
    try:
        for encoder in (original, reserve_bytes):
            runtime._cold_graph_bytes = encoder
            store = db.Store("sqlite:///:memory:", test_only=True)
            account = "offline-codec-only-no-admission"
            contract = data["contract"].model_copy(update=dict(quota_subject=canonical_quota_subject(account)))
            binding = ProductionTrialBinding(contract, "synthetic-unapproved-codec", account)
            worker = object.__new__(Worker)
            worker.store, worker.s, worker.pa_trial = store, Settings("sqlite:///:memory:", Path("/tmp")), binding
            worker.id, worker.stop, worker.goal_planner_transport = "codec-only-reader", threading.Event(), None
            worker._journal_trial_store, worker._journal_trial_binding, worker._journal_trial_drift = store, binding, False
            try:
                for mutation in ("content", "write", "epoch", "closed"):
                    rejected = False
                    with store.tx() as c:
                        c.exec_driver_sql("CREATE TABLE IF NOT EXISTS codec_probe(value TEXT)")
                        payload = dict(value=[1, 2])
                        try:
                            with pb._source_reads(store, c), runtime._cold_graph_read(worker, c,
                                    dict(payload=payload), data["role_limits"], "pre") as guard:
                                guard.check(store, c)
                                if mutation == "content":
                                    payload["value"].append(3)
                                elif mutation == "write":
                                    c.exec_driver_sql("INSERT INTO codec_probe VALUES ('synthetic')")
                                elif mutation == "epoch":
                                    c.info["source_proof_write_epoch"] += 1
                                if mutation != "closed":
                                    guard.check(store, c)
                        except DomainError:
                            rejected = True
                        assert rejected == (mutation != "closed")
                        assert not guard.active
                        try:
                            guard.check(store, c)
                        except DomainError:
                            pass
                        else:
                            raise AssertionError("invalid scope revived")
                    checks.append(dict(encoder="original" if encoder is original else "reserve",
                                       mutation=mutation, invalid_scope_rejected=True))
            finally:
                store.engine.dispose()
    finally:
        runtime._cold_graph_bytes = original
    return checks


class MeasuredBuffer(io.BytesIO):
    """Diagnostic only: adds Python frames/clock calls during Pickler.dump."""
    def __init__(self):
        super().__init__()
        self.writes = []

    def write(self, value):
        start = time.thread_time_ns()
        count = super().write(value)
        elapsed = time.thread_time_ns() - start
        self.writes.append(dict(bytes=len(value), cpu_ns=elapsed))
        return count


def components(data, expected):
    start = time.thread_time_ns()
    values = envelope(data)
    envelope_ns = time.thread_time_ns() - start
    output = MeasuredBuffer()
    output.write(PREFIX)
    first = len(output.writes)
    start = time.thread_time_ns()
    runtime._ColdGraphPickler(output, protocol=5).dump(values)
    dump_ns = time.thread_time_ns() - start
    buffer_sizeof_before_getvalue = output.__sizeof__()
    start = time.thread_time_ns()
    encoded = output.getvalue()
    getvalue_ns = time.thread_time_ns() - start
    assert encoded == expected
    start = time.thread_time_ns()
    digest = hashlib.sha256(encoded).hexdigest()
    sha_ns = time.thread_time_ns() - start
    observed_write = sum(item["cpu_ns"] for item in output.writes[first:])
    return dict(envelope_cpu_ns=envelope_ns, dump_inclusive_cpu_ns=dump_ns,
        observed_buffer_write_cpu_ns=observed_write,
        dump_minus_observed_write_cpu_ns=dump_ns - observed_write,
        residual_scope="includes reducer/adapter Python, C Pickler and unmeasured observer overhead; NOT pure C exclusive",
        getvalue_cpu_ns=getvalue_ns, sha256_cpu_ns=sha_ns,
        buffer_sizeof_before_getvalue=buffer_sizeof_before_getvalue,
        buffer_write_records=output.writes, sha256=digest,
        instrumented=True, new_python_write_frames=True, used_for_net_benefit=False)


def main(output):
    started = time.monotonic()
    output = Path(output)
    assert not output.exists()
    output.mkdir()
    hashes = {name: hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in SOURCES}
    data, corpus = load_corpus()
    plan = dict(contract=CONTRACT, sources=hashes, corpus=corpus,
        created_at=datetime.now(timezone.utc).isoformat(),
        python_version=sys.version, original_pickler_module=runtime._ColdGraphPicklerBase.__module__,
        base_head="c3e83a20827ae5388a70ce22dd8ef33456ac7a4a",
        scope="one offline group, full stored rows + declared synthetic aliases, NOT G0 replay")
    (output / "plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    report = dict(plan=plan, status="RUNNING", rounds=[])
    try:
        report["semantic_checks"] = semantic_checks(data)
        report["scope_checks"] = scope_checks(data)
        expected = runtime._cold_graph_bytes(envelope(data))
        assert len(expected) <= CONTRACT["output_bytes_limit"]
        report.update(encoded_bytes=len(expected), sha256=hashlib.sha256(expected).hexdigest())

        def run(encoder, count):
            assert time.monotonic() - started < CONTRACT["work_seconds"]
            wall, cpu = time.perf_counter_ns(), time.thread_time_ns()
            total = 0
            for _ in range(count):
                encoded = encoder(envelope(data))
                digest = hashlib.sha256(encoded).hexdigest()
                assert digest == report["sha256"]
                total += len(encoded)
            return dict(wall_ns=time.perf_counter_ns() - wall,
                        cpu_ns=time.thread_time_ns() - cpu, total_bytes=total)

        for encoder in (runtime._cold_graph_bytes, reserve_bytes):
            run(encoder, CONTRACT["warmup_per_arm"])
        for i in range(CONTRACT["rounds"]):
            row = dict(index=i, order=["original", "reserve"] if i % 2 == 0 else ["reserve", "original"])
            for name in row["order"]:
                row[name] = run(runtime._cold_graph_bytes if name == "original" else reserve_bytes,
                                CONTRACT["calls_per_arm"])
            report["rounds"].append(row)
        report["wall_ratio"] = statistics.median(r["reserve"]["wall_ns"] / r["original"]["wall_ns"] for r in report["rounds"])
        report["cpu_ratio"] = statistics.median(r["reserve"]["cpu_ns"] / r["original"]["cpu_ns"] for r in report["rounds"])
        report["wall_wins"] = sum(r["reserve"]["wall_ns"] < r["original"]["wall_ns"] for r in report["rounds"])
        report["local_net_qualified"] = (report["wall_wins"] >= CONTRACT["minimum_wall_wins"]
            and report["wall_ratio"] <= CONTRACT["maximum_wall_median_ratio"]
            and report["cpu_ratio"] <= CONTRACT["maximum_cpu_median_ratio"])
        report["components"] = components(data, expected)
        profile = cProfile.Profile(timer=time.thread_time)
        encoded = profile.runcall(runtime._cold_graph_bytes, envelope(data))
        assert encoded == expected
        profile.dump_stats(str(output / "original.pstats"))
        stats = pstats.Stats(profile)
        report["cprofile"] = [dict(file=k[0], line=k[1], function=k[2], primitive_calls=v[0],
            total_calls=v[1], exclusive_cpu_s=v[2], inclusive_cpu_s=v[3])
            for k, v in sorted(stats.stats.items(), key=lambda item: item[1][2], reverse=True)[:25]]
        assert time.monotonic() - started < CONTRACT["work_seconds"]
        report.update(status="GROUP_COMPLETED_NOT_PRODUCT_QUALIFIED", product_switch=False,
            limitation="resource-exhaustion, callback and real epoch/concurrency equivalence not established by byte tests")
    except BaseException as error:
        report.update(status="FAILED_NO_RETRY", error=type(error).__name__)
        raise
    finally:
        after_sources = {name: hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in SOURCES}
        source_unchanged = after_sources == hashes
        if not source_unchanged:
            report.update(status="FAILED_SOURCE_DRIFT", product_switch=False)
        report.update(after_sources=after_sources, source_unchanged=source_unchanged,
            elapsed_seconds=time.monotonic() - started, http=0, worker_starts=0, model_calls=0,
            database_engine_disposed=corpus["database_engine_disposed"])
        (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps({k: v for k, v in report.items()
            if k in ("status", "encoded_bytes", "sha256", "wall_ratio", "cpu_ratio", "wall_wins", "local_net_qualified", "elapsed_seconds")}))
        assert source_unchanged, "Frozen source changed"


if __name__ == "__main__":
    main(sys.argv[1])
