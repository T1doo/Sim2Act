"""Private owned-process desktop protocol, independent of business authorization.

A session is a launch identity, never an API credential or a database fence.
Only production entry points choose CONFIGURED; test launchers must say TEST_ONLY.
"""
from __future__ import annotations

import json
import os
import queue
import re
import stat
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import psutil

PROTOCOL = "sim2act.desktop-service.v1"
CONFIGURED = "CONFIGURED_POSTGRESQL"
TEST_ONLY = "TEST_ONLY_SQLITE"
MAX_LINE = 8192


class ProtocolError(RuntimeError):
    pass


def parse(line):
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ProtocolError("DUPLICATE_FIELD")
            value[key] = item
        return value
    if not isinstance(line, str) or len(line) > MAX_LINE or not line.endswith("\n"):
        raise ProtocolError("INVALID_LINE")
    try:
        value = json.loads(line, object_pairs_hook=unique)
    except (ValueError, RecursionError) as error:
        raise ProtocolError("INVALID_JSON") from error
    if type(value) is not dict:
        raise ProtocolError("INVALID_OBJECT")
    return value


def emit(stream, event, **fields):
    stream.write(json.dumps(dict(protocol=PROTOCOL, event=event, **fields)) + "\n")
    stream.flush()


def ordinary(path):
    path = Path(path).absolute()
    for parent in (path, *path.parents):
        try:
            state = parent.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(state.st_mode) or getattr(state, "st_file_attributes", 0) & 0x400:
            raise ProtocolError("LINKED_DATA_PATH")
    return path


@dataclass
class Child:
    role: str
    process: subprocess.Popen
    command: list[str]
    created_at: float
    ready: dict | None = None
    activated: bool = False
    stopped: dict | None = None
    stdout_eof: bool = False
    stderr_eof: bool = False
    stderr_lines: int = 0
    readers: list[threading.Thread] = field(default_factory=list)


class Supervisor:
    """Own two real children; never terminate/kill or infer clean from PID death."""
    def __init__(self, data_dir, backend, binding, command_factory, environment, *,
                 port=0, startup_seconds=30, stop_seconds=20, input_stream, output_stream):
        if backend not in {CONFIGURED, TEST_ONLY} or not re.fullmatch(r"[a-f0-9]{64}", binding):
            raise ProtocolError("INVALID_LAUNCH")
        if type(port) is not int or not 0 <= port <= 65535:
            raise ProtocolError("INVALID_PORT")
        if not 0 < startup_seconds <= 30 or not 0 < stop_seconds <= 30:
            raise ProtocolError("INVALID_LIFECYCLE_BUDGET")
        self.root = ordinary(data_dir)
        self.backend, self.binding = backend, binding
        self.factory, self.environment = command_factory, environment
        self.port, self.startup_seconds, self.stop_seconds = port, startup_seconds, stop_seconds
        self.input, self.output = input_stream, output_stream
        self.session = uuid.uuid4().hex
        self.stop = threading.Event()
        self.input_error = threading.Event()
        self.input_started = threading.Event()
        self.overflow = threading.Event()
        self.events = queue.Queue(maxsize=256)
        self.children = {}
        self.errors = []
        self.ready_seen = False
        self.claim = None
        self.claim_file = self.root / "desktop-service-claim.json"
        self.origin_file = self.root / "desktop-service-origin.json"
        self.origin_bytes = None
        self.last_claim = b""
        self.preflight_thread = None
        self.preflight_error = None
        self.startup_until = None

    def checkpoint(self):
        if self.stop.is_set():
            raise ProtocolError("PARENT_STOPPED_BEFORE_READY")
        if self.startup_until is None or time.monotonic() >= self.startup_until:
            raise ProtocolError("PREFLIGHT_DEADLINE")

    def _preflight(self, callback):
        try:
            self.checkpoint()
            callback()
            self.checkpoint()
        except Exception as error:
            self.preflight_error = error

    def announce(self, event, **fields):
        emit(self.output, event, session=self.session, backend=self.backend, **fields)

    def _input(self):
        self.input_started.set()
        try:
            line = self.input.readline(514)
            if line == "":
                self.stop.set()
                return
            value = parse(line)
            if value != dict(command="stop", session=self.session):
                self.input_error.set()
        except Exception:
            self.input_error.set()
        self.stop.set()

    def _post(self, role, kind, value=None):
        try:
            self.events.put_nowait((role, kind, value))
        except queue.Full:
            self.overflow.set()

    def _reader(self, child, kind, stream):
        try:
            while True:
                line = stream.readline(MAX_LINE + 1)
                if line == "":
                    break
                if len(line) > MAX_LINE or not line.endswith("\n"):
                    self._post(child.role, "error", "OVERSIZED_CHILD_OUTPUT")
                    continue
                if kind == "stdout":
                    self._post(child.role, "message", parse(line))
                else:
                    # Do not echo or persist arbitrary errors/DSNs/HTTP bodies.
                    child.stderr_lines += 1
                    if child.stderr_lines > 128:
                        self._post(child.role, "error", "EXCESS_CHILD_STDERR")
        except Exception:
            self._post(child.role, "error", "UNREADABLE_CHILD_OUTPUT")
        finally:
            self._post(child.role, kind + "_eof")
            stream.close()

    def _write_claim(self):
        value = dict(protocol=PROTOCOL, session=self.session, backend=self.backend,
            controller_pid=os.getpid(), children=[dict(role=c.role, pid=c.process.pid,
                created_at=c.created_at, command=c.command) for c in self.children.values()])
        raw = (json.dumps(value, sort_keys=True) + "\n").encode()
        self.claim.seek(0)
        self.claim.write(raw)
        self.claim.truncate()
        self.claim.flush()
        os.fsync(self.claim.fileno())
        self.last_claim = raw

    def _claim_current(self):
        if self.claim is None:
            return False
        ordinary(self.claim_file)
        here, held = self.claim_file.stat(), os.fstat(self.claim.fileno())
        if (here.st_dev, here.st_ino) != (held.st_dev, held.st_ino) or here.st_size != len(self.last_claim):
            return False
        with self.claim_file.open("rb") as stream:
            return stream.read(len(self.last_claim) + 1) == self.last_claim

    def _release_claim(self):
        if not self._claim_current():
            raise ProtocolError("CLAIM_CHANGED")
        self.claim.close()
        self.claim = None
        self.claim_file.unlink()

    def _prior_origin(self):
        if not self.origin_file.exists():
            return
        ordinary(self.origin_file)
        with self.origin_file.open("rb") as stream:
            raw = stream.read(MAX_LINE + 1)
        value = parse(raw.decode())
        expected = dict(protocol=PROTOCOL, backend=self.backend, binding=self.binding,
            data_dir=str(self.root), port=value.get("port"))
        if value != expected or type(value["port"]) is not int or not 1 <= value["port"] <= 65535:
            raise ProtocolError("ORIGIN_IDENTITY_CHANGED")
        if self.port not in (0, value["port"]):
            raise ProtocolError("ORIGIN_PORT_CHANGED")
        self.port, self.origin_bytes = value["port"], raw

    def _bind_origin(self, url):
        match = re.fullmatch(r"http://127\.0\.0\.1:([1-9][0-9]{0,4})", url)
        if not match or not 1 <= int(match[1]) <= 65535 or self.port not in (0, int(match[1])):
            raise ProtocolError("INVALID_OWNED_ORIGIN")
        value = dict(protocol=PROTOCOL, backend=self.backend, binding=self.binding,
            data_dir=str(self.root), port=int(match[1]))
        raw = (json.dumps(value, sort_keys=True) + "\n").encode()
        if self.origin_bytes is None:
            with self.origin_file.open("xb") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            self.origin_bytes = raw
        elif self.origin_file.read_bytes() != self.origin_bytes:
            raise ProtocolError("ORIGIN_CHANGED_DURING_START")

    def _spawn(self, role):
        if self.stop.is_set() or self.input_error.is_set():
            return
        command = self.factory(role, self.session, self.port)
        if type(command) is not list or not command or not all(type(x) is str for x in command):
            raise ProtocolError("INVALID_OWNED_COMMAND")
        process = subprocess.Popen(command, cwd=self.root, env=self.environment,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", errors="strict", bufsize=1,
            **({"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}))
        # Keep the actual handle before any fallible observation or state write.
        child = Child(role, process, command, 0.0)
        self.children[role] = child
        for kind in ("stdout", "stderr"):
            thread = threading.Thread(target=self._reader,
                args=(child, kind, getattr(process, kind)), daemon=True)
            child.readers.append(thread)
            thread.start()
        self._write_claim()
        child.created_at = psutil.Process(process.pid).create_time()
        observed = psutil.Process(process.pid)
        if observed.cmdline() != command:
            raise ProtocolError("CHILD_COMMAND_MISMATCH")
        self._write_claim()

    def _send(self, child, command):
        if child.process.poll() is not None:
            raise ProtocolError("CHILD_EXITED_BEFORE_CONTROL")
        child.process.stdin.write(json.dumps(dict(command=command,
            session=self.session, role=child.role)) + "\n")
        child.process.stdin.flush()

    def _message(self, child, value):
        common = dict(protocol=PROTOCOL, session=self.session, role=child.role,
            pid=child.process.pid, backend=self.backend)
        if type(value.get("pid")) is not int or any(value.get(k) != v for k, v in common.items()):
            raise ProtocolError("CHILD_IDENTITY_MISMATCH")
        event = value.get("event")
        extras = {"event"} | set(common)
        if event == "ROLE_READY":
            extra = "url" if child.role == "api" else "worker_id"
            if set(value) != extras | {extra} or child.ready is not None or child.stopped:
                raise ProtocolError("INVALID_ROLE_READY")
            if child.role == "worker" and (type(value[extra]) is not str or not re.fullmatch(r"worker_[a-f0-9]{32}", value[extra])):
                raise ProtocolError("INVALID_WORKER_IDENTITY")
            child.ready = value
        elif event == "ROLE_ACTIVATED":
            if child.role != "worker" or child.ready is None or child.activated or set(value) != extras | {"worker_id"} or value["worker_id"] != child.ready["worker_id"]:
                raise ProtocolError("INVALID_ACTIVATION_RECEIPT")
            child.activated = True
        elif event == "ROLE_STOPPED":
            if set(value) != extras | {"clean", "ready_seen"} or child.stopped is not None or type(value["clean"]) is not bool or type(value["ready_seen"]) is not bool or value["ready_seen"] != (child.ready is not None):
                raise ProtocolError("INVALID_ROLE_STOPPED")
            child.stopped = value
        elif event == "ROLE_ERROR" and set(value) == extras | {"error_type"}:
            raise ProtocolError("CHILD_ROLE_ERROR")
        else:
            raise ProtocolError("UNEXPECTED_ROLE_EVENT")

    def _event(self, timeout=.05):
        try:
            role, kind, value = self.events.get(timeout=timeout)
        except queue.Empty:
            return
        child = self.children[role]
        if kind == "message":
            self._message(child, value)
        elif kind in {"stdout_eof", "stderr_eof"}:
            setattr(child, kind, True)
        else:
            raise ProtocolError(str(value))

    def _drained(self):
        return all(c.process.poll() is not None and c.stdout_eof and c.stderr_eof
                   and all(not t.is_alive() for t in c.readers) for c in self.children.values())

    def run(self, preflight):
        monitor = threading.Thread(target=self._input, daemon=True)
        monitor.start()  # Must precede database preflight and all child creation.
        if not self.input_started.wait(1):
            raise ProtocolError("CONTROL_MONITOR_UNAVAILABLE")
        self.announce("DESKTOP_SERVICE_STARTING")
        activated = False
        startup_until = self.startup_until = time.monotonic() + self.startup_seconds
        try:
            if self.stop.is_set():
                return self._no_start()
            self.root.mkdir(parents=True, exist_ok=True)
            self.claim = self.claim_file.open("x+b")
            self._write_claim()
            # Bound the parent's observation even if a driver call is stuck.
            # An undrained preflight can never certify clean shutdown.
            self.preflight_thread = threading.Thread(target=self._preflight,
                args=(preflight,), daemon=True)
            self.preflight_thread.start()
            while self.preflight_thread.is_alive() and not self.stop.wait(.02):
                self.checkpoint()
            if self.stop.is_set():
                raise ProtocolError("PARENT_STOPPED_BEFORE_READY")
            if self.preflight_error is not None:
                raise self.preflight_error
            self.checkpoint()
            self._prior_origin()
            for role in ("api", "worker"):
                if self.stop.is_set() or time.monotonic() >= startup_until:
                    break
                self._spawn(role)
            while not self.stop.is_set():
                self._event()
                if self.input_error.is_set() or self.overflow.is_set() or not self._claim_current():
                    raise ProtocolError("CONTROL_OR_CLAIM_CHANGED")
                if any(c.process.poll() is not None or c.stopped is not None for c in self.children.values()):
                    raise ProtocolError("CHILD_EXITED_WITHOUT_STOP")
                if self.origin_bytes is not None and self.origin_file.read_bytes() != self.origin_bytes:
                    raise ProtocolError("ORIGIN_CHANGED")
                all_ready = len(self.children) == 2 and all(c.ready is not None for c in self.children.values())
                if all_ready and not activated:
                    self._bind_origin(self.children["api"].ready["url"])
                    if self.stop.is_set() or time.monotonic() >= startup_until:
                        break
                    self._send(self.children["worker"], "activate")
                    activated = True
                if activated and self.children["worker"].activated and not self.ready_seen:
                    if self.stop.is_set() or time.monotonic() >= startup_until:
                        break
                    self.ready_seen = True
                    self.announce("DESKTOP_SERVICE_READY", url=self.children["api"].ready["url"],
                        data_dir=str(self.root), worker_id=self.children["worker"].ready["worker_id"],
                        api_pid=self.children["api"].process.pid, worker_pid=self.children["worker"].process.pid)
                if not self.ready_seen and time.monotonic() >= startup_until:
                    raise ProtocolError("STARTUP_DEADLINE")
        except Exception as error:
            if not (self.stop.is_set() and isinstance(error, ProtocolError)
                    and str(error) == "PARENT_STOPPED_BEFORE_READY"):
                self.errors.append(type(error).__name__)
                self.announce("DESKTOP_SERVICE_ERROR", error_type=type(error).__name__,
                    error_code=str(error) if isinstance(error, ProtocolError) else "PREFLIGHT_OR_START_FAILED")
                if self.claim is None:
                    self.announce("DESKTOP_SERVICE_STOPPED", clean=False, ready_seen=False,
                        children_started=0, claim_preserved=False)
        finally:
            if self.claim is not None:
                self._shutdown()
        return 0 if not self.errors else 1

    def _no_start(self):
        clean = not self.input_error.is_set()
        self.announce("DESKTOP_SERVICE_STOPPED", clean=clean, ready_seen=False,
            children_started=0, claim_preserved=False)
        return 0 if clean else 1

    def _shutdown(self):
        self.stop.set()
        for child in self.children.values():
            try:
                if child.process.poll() is None:
                    self._send(child, "stop")
            except Exception:
                self.errors.append("STOP_DELIVERY_UNKNOWN")
            finally:
                try:
                    child.process.stdin.close()
                except OSError:
                    pass
        until = time.monotonic() + self.stop_seconds
        while (not self._drained() or (self.preflight_thread is not None
                and self.preflight_thread.is_alive())) and time.monotonic() < until:
            try:
                self._event()
            except Exception:
                self.errors.append("STOP_RECEIPT_INVALID")
        # The queue can still contain STOPPED immediately before both EOFs.
        while not self.events.empty():
            try:
                self._event(timeout=0)
            except Exception:
                self.errors.append("STOP_RECEIPT_INVALID")
        clean = (not self.errors and not self.input_error.is_set() and not self.overflow.is_set()
            and (self.preflight_thread is None or not self.preflight_thread.is_alive())
            and (self.preflight_error is None or (self.stop.is_set()
                and isinstance(self.preflight_error, ProtocolError)
                and str(self.preflight_error) == "PARENT_STOPPED_BEFORE_READY"))
            and self._drained() and all(c.process.returncode == 0 and c.stopped is not None
                and c.stopped["clean"] for c in self.children.values()))
        if clean:
            try:
                self._release_claim()
            except Exception:
                clean = False
        if not clean:
            self.errors.append("OWNED_SERVICE_STOP_UNKNOWN")
        self.announce("DESKTOP_SERVICE_STOPPED", clean=clean, ready_seen=self.ready_seen,
            children_started=len(self.children), claim_preserved=not clean,
            preflight_stopped=self.preflight_thread is None or not self.preflight_thread.is_alive(),
            roles={k:dict(pid=c.process.pid, exitcode=c.process.poll(),
                stdout_eof=c.stdout_eof, stderr_eof=c.stderr_eof, receipt=c.stopped)
                for k, c in self.children.items()})
        if self.claim is not None:
            self.claim.close()
            self.claim = None
