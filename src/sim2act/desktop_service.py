"""Configured desktop API/Worker roles and their private process supervisor.

Production CLI always loads PostgreSQL Settings. SQLite is available only to
explicit test programs calling the role functions, with TEST_ONLY receipts.
No new user, token, grant, schema, migration or Run is created during preflight.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import socket
import sys
import threading

import uvicorn
from sqlalchemy.engine import make_url

from .config import Settings
from .desktop_protocol import CONFIGURED, ProtocolError, Supervisor, emit, ordinary, parse
from .process_env import application_environment


def _role_output(output, session, backend, role, event, **fields):
    emit(output, event, session=session, backend=backend, role=role, pid=os.getpid(), **fields)


def _role_control(stream, session, role, stop, activate, failed, request_stop):
    try:
        while True:
            line = stream.readline(514)
            if line == "":
                request_stop()
                return
            value = parse(line)
            if set(value) != {"command", "session", "role"} or value["session"] != session or value["role"] != role:
                raise ProtocolError("ROLE_CONTROL_IDENTITY")
            if value["command"] == "stop":
                request_stop()
                return
            if value["command"] != "activate" or role != "worker" or activate.is_set() or stop.is_set():
                raise ProtocolError("ROLE_CONTROL_COMMAND")
            activate.set()
    except Exception:
        failed.set()
        request_stop()


def run_worker_role(factory, *, session, backend, input_stream, output_stream):
    stop, activate, failed = threading.Event(), threading.Event(), threading.Event()
    worker = None
    ready = False
    clean = False

    def request_stop():
        stop.set()
        if worker is not None:
            worker.stop.set()

    control = threading.Thread(target=_role_control,
        args=(input_stream, session, "worker", stop, activate, failed, request_stop), daemon=True)
    control.start()
    try:
        if not stop.is_set():
            worker = factory()  # Original install/approval checks, never claims a Run.
            if stop.is_set():
                worker.stop.set()
            else:
                worker.store.heartbeat(worker.id)
                if not stop.is_set():
                    _role_output(output_stream, session, backend, "worker", "ROLE_READY", worker_id=worker.id)
                    ready = True
        while not stop.is_set() and not activate.wait(.02):
            pass
        if not stop.is_set():
            _role_output(output_stream, session, backend, "worker", "ROLE_ACTIVATED", worker_id=worker.id)
            while not stop.is_set() and not worker.stop.is_set():
                worker.once()  # Original leases, cancellation and final commit guards.
                stop.wait(1)
    except Exception as error:
        failed.set()
        _role_output(output_stream, session, backend, "worker", "ROLE_ERROR", error_type=type(error).__name__)
    finally:
        request_stop()
        control.join(1)
        try:
            # No thread-name guesses. A blocked owned heartbeat makes stop UNKNOWN.
            clean = worker is None or worker.drain_owned_heartbeats(10)
            if clean and worker is not None:
                worker.store.engine.dispose()
        except Exception:
            clean = False
        clean = clean and not failed.is_set() and not control.is_alive()
        _role_output(output_stream, session, backend, "worker", "ROLE_STOPPED", clean=clean, ready_seen=ready)
    return 0 if clean else 1


def run_api_role(factory, *, session, backend, port, input_stream, output_stream):
    stop, activate, failed = threading.Event(), threading.Event(), threading.Event()
    server = None
    ready = threading.Event()
    cleanup = None
    clean = False

    def request_stop():
        stop.set()
        if server is not None:
            server.should_exit = True

    control = threading.Thread(target=_role_control,
        args=(input_stream, session, "api", stop, activate, failed, request_stop), daemon=True)
    control.start()
    publisher = None
    try:
        if not stop.is_set():
            app, cleanup = factory()
            if not stop.is_set():
                with socket.socket() as listener:
                    if os.name == "nt":
                        listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
                    listener.bind(("127.0.0.1", port))
                    listener.listen(128)
                    address = "http://127.0.0.1:" + str(listener.getsockname()[1])
                    # Never cancel active requests to make a stop deadline look clean.
                    # The supervisor bounds its own wait and retains UNKNOWN instead.
                    server = uvicorn.Server(uvicorn.Config(app, access_log=False,
                        log_level="critical", timeout_graceful_shutdown=None))
                    if stop.is_set():
                        server.should_exit = True

                    def publish_ready():
                        while not stop.is_set() and not server.should_exit and not server.started:
                            stop.wait(.02)
                        if not stop.is_set() and server.started:
                            _role_output(output_stream, session, backend, "api", "ROLE_READY", url=address)
                            ready.set()

                    publisher = threading.Thread(target=publish_ready, daemon=True)
                    publisher.start()
                    server.run(sockets=[listener])
        clean = not failed.is_set()
    except Exception as error:
        failed.set()
        _role_output(output_stream, session, backend, "api", "ROLE_ERROR", error_type=type(error).__name__)
    finally:
        request_stop()
        control.join(1)
        if publisher is not None:
            publisher.join(1)
            clean = clean and not publisher.is_alive()
        if server is not None:
            clean = clean and not server.server_state.tasks and not server.server_state.connections
        try:
            if cleanup is not None:
                cleanup()
        except Exception:
            clean = False
        clean = clean and not failed.is_set() and not control.is_alive()
        _role_output(output_stream, session, backend, "api", "ROLE_STOPPED", clean=clean, ready_seen=ready.is_set())
    return 0 if clean else 1


def configuration_binding(settings):
    if not settings.database_url.startswith("postgresql+psycopg://"):
        raise ProtocolError("POSTGRESQL_CONFIGURATION_REQUIRED")
    url = make_url(settings.database_url)
    if not url.username or not url.host or not url.database:
        raise ProtocolError("EXPLICIT_DATABASE_IDENTITY_REQUIRED")
    # Preflight and children must not resolve different libpq defaults. Child
    # environment is deliberately narrow; never inherit PG* credentials/options.
    if any(name.startswith("PG") and os.environ[name] for name in os.environ):
        raise ProtocolError("EXTERNAL_LIBPQ_DEFAULTS_UNSUPPORTED")
    # Service files can invisibly change the endpoint/schema/identity. Do not
    # resolve them or read credential files as a desktop namespace authority.
    # Authentication remains in the URL password, excluded from this identity.
    if any(k.lower() in {"service", "servicefile", "passfile", "password", "sslpassword"}
           for k in url.query):
        raise ProtocolError("INDIRECT_DATABASE_IDENTITY_UNSUPPORTED")
    # options/search_path and libpq query endpoint overrides affect real data.
    # Keep their full ordered values, not just host/database from the URL body.
    query = tuple(sorted(url.normalized_query.items()))
    identity = repr((url.drivername, url.username, url.host, url.port, url.database, query)).encode()
    return hashlib.sha256(identity).hexdigest()


def configured_supervisor(settings, selected, preflight, *, port, input_stream, output_stream,
                          owned_database=None):
    binding = configuration_binding(settings)
    if input_stream is None or input_stream.isatty():
        raise ProtocolError("OWNED_STDIN_PIPE_REQUIRED")
    environment = application_environment(settings)

    def command(role, session, chosen_port):
        args = [sys.executable, "-u", "-m", "sim2act.desktop_service",
            "--role", role, "--session", session, "--port", str(chosen_port)]
        if selected:
            for key in ("user", "project", "trial", "approval", "account"):
                args.extend(["--spec-production-" + key, selected[key]])
        return args

    def cleanup(remaining):
        if owned_database.identity is None:
            return not owned_database.claim.exists()
        owned_database.stop(timeout=min(30,remaining))
        return True

    controller = Supervisor(settings.data_dir, CONFIGURED, binding, command, environment,
        port=port, input_stream=input_stream, output_stream=output_stream,
        owned_cleanup=cleanup if owned_database is not None else None)
    def prepare():
        controller.checkpoint()
        if owned_database is not None:
            owned_database.start()
            controller.checkpoint()
        preflight(controller.checkpoint)
    return controller.run(prepare)


def configured_entry(*, config, selection, port, input_stream, output_stream, managed_local=None):
    from sqlalchemy import event

    from .db_readiness import inspect_database
    from .launch_configuration import (
        check_selection,
        import_config,
        production_selection,
        validation_store,
    )

    if config and managed_local:
        raise ProtocolError('CONFLICTING_LOCAL_CONFIGURATION')
    if config:
        import_config(config)
    selected = production_selection(selection) if selection else None
    owned_database=None
    if managed_local:
        from .local_desktop_settings import local_settings
        settings,owned_database=local_settings(managed_local)
    else:
        ordinary(os.environ.get("SIM2ACT_DATA_DIR", ".sim2act"))
        settings = Settings.from_env()

    def preflight(checkpoint):
        store = validation_store(settings)
        try:
            event.listen(store.engine, "before_cursor_execute", lambda *_args: checkpoint())
            checkpoint()
            report = inspect_database(store.engine)
            checkpoint()
            if report["status"] != "STRUCTURAL_READY":
                raise ProtocolError("DATABASE_NOT_STRUCTURALLY_READY")
            if selected:
                check_selection(store, settings, selected)
                checkpoint()
        finally:
            store.engine.dispose()

    return configured_supervisor(settings, selected, preflight, port=port,
        input_stream=input_stream, output_stream=output_stream,owned_database=owned_database)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--role", choices=["api", "worker"])
    parser.add_argument("--session")
    parser.add_argument("--port", default=0, type=int)
    parser.add_argument("--supervise", action="store_true")
    parser.add_argument("--control-stdin", action="store_true")
    parser.add_argument("--config")
    parser.add_argument("--managed-local")
    parser.add_argument("--spec-selection")
    for field in ("user", "project", "trial", "approval", "account"):
        parser.add_argument("--spec-production-" + field)
    args = parser.parse_args()
    if args.supervise:
        if args.role or args.session or not args.control_stdin or any(
            getattr(args, "spec_production_" + k) for k in ("user", "project", "trial", "approval", "account")):
            parser.error("Private supervisor control only; use original selection file")
        try:
            result = configured_entry(config=args.config, selection=args.spec_selection,
                port=args.port, input_stream=sys.stdin, output_stream=sys.stdout,managed_local=args.managed_local)
        except Exception:
            # Never expose a configuration value, DSN, token or arbitrary error.
            parser.exit(1, "Configured desktop lifecycle unconfirmed; preserve data and claims.\n")
        raise SystemExit(result)
    if args.config or args.managed_local or args.spec_selection or args.control_stdin or args.role is None:
        parser.error("Use --supervise --control-stdin for a configured desktop parent")
    if not args.session or not re.fullmatch(r"[a-f0-9]{32}", args.session) or not 0 <= args.port <= 65535 or sys.stdin.isatty():
        parser.error("Private role/session/port required")
    selected = [getattr(args, "spec_production_" + key)
        for key in ("user", "project", "trial", "approval", "account")]
    if any(selected) and not all(selected):
        parser.error("Only a complete original production selection is supported")
    try:
        settings = Settings.from_env()  # Production role has no SQLite/test flag.
        from .db import Store
        if args.role == "worker":
            def factory():
                store = Store(settings.database_url)
                try:
                    if any(selected):
                        from .spec_production import install
                        return install(store, settings, user=selected[0], project_id=selected[1],
                            trial_key=selected[2], approval_key=selected[3], account_id=selected[4])
                    from .worker import Worker
                    return Worker(store, settings)
                except BaseException:
                    store.engine.dispose()
                    raise
            code = run_worker_role(factory, session=args.session, backend=CONFIGURED,
                input_stream=sys.stdin, output_stream=sys.stdout)
        else:
            def factory():
                from .api import create_app
                store = Store(settings.database_url)
                try:
                    selection=dict(zip(("user","project","trial","approval","account"),selected)) if any(selected) else None
                    return create_app(store, settings, production_selection=selection), store.engine.dispose
                except BaseException:
                    store.engine.dispose()
                    raise
            code = run_api_role(factory, session=args.session, backend=CONFIGURED,
                port=args.port, input_stream=sys.stdin, output_stream=sys.stdout)
    except Exception as error:
        _role_output(sys.stdout, args.session, CONFIGURED, args.role, "ROLE_ERROR", error_type=type(error).__name__)
        code = 1
    raise SystemExit(code)


if __name__ == "__main__":
    main()
