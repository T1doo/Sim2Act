"""Explicit synthetic local demo; never the ordinary PostgreSQL launcher.

Uses the existing loopback/Store(test_only=True)/MockTransport fixture pattern.
No .env discovery, DSN, credential, provider URL, automatic worker or live mode.
Prepare keeps its new directory for a later, separate-process read-only verify.
"""

import argparse
import hashlib
import json
import os
import socket
import tempfile
import threading
import time
from contextlib import contextmanager
from pathlib import Path

import httpx
import uvicorn
from sqlalchemy import select

from sim2act import natural_specs as natural
from sim2act import pb_natural_specs as pb
from sim2act import pb_natural_uses as uses
from sim2act.api import create_app
from sim2act.config import Settings
from sim2act.db import (
    Store,
    events,
    fingerprint,
    internal_instance_data,
    internal_run_bindings,
    meta,
    run_contracts,
    runs,
)
from sim2act.worker import Worker

MARKER = {"version": "sim2act-local-candidate.v1", "mode": "SYNTHETIC_MOCK_ONLY"}
PUBLIC_TOKEN = "public-synthetic-local-candidate"
DATABASE = "synthetic-demo.db"


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def write_json(path, value):
    require(not path.is_symlink(), "Refuse linked demo output: " + path.name)
    # Replace the directory entry atomically; never open/follow an output link.
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                     prefix=".owned-demo-", delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)  # Only our own unique temporary file.


def unlinked_path(path):
    absolute = Path(os.path.abspath(path))
    require(not any(part.is_symlink() for part in [absolute, *absolute.parents]),
            "Demo directory and its parents cannot be symlinks")
    return absolute


def settings_for(root):
    # Deliberately never Settings.from_env(), even if real credentials are present.
    return Settings("sqlite:///" + str(root / DATABASE), root,
                    mode="mock", goal_planner_provider="intern-s2")


def checked_directory(path):
    root = unlinked_path(path)
    for name in ["fixture.json", DATABASE, "demo-receipt.json"]:
        require((root / name).is_file() and not (root / name).is_symlink(),
                "Expected owned synthetic fixture file: " + name)
    require(json.loads((root / "fixture.json").read_text(encoding="utf-8")) == MARKER,
            "Directory is not this explicit synthetic fixture")
    require(not (root / "cold-read-receipt.json").is_symlink(), "Refuse linked cold-read output")
    return root


@contextmanager
def loopback(store, settings, *, port=0, read_only=False):
    """Reserve the actual listening socket, start/stop only our own server."""
    app = create_app(store, settings)
    if read_only:
        from starlette.responses import JSONResponse

        @app.middleware("http")
        async def reads_only(request, call_next):
            if request.method not in {"GET", "HEAD"}:
                return JSONResponse({"error": {"code": "SYNTHETIC_READ_ONLY",
                    "message": "Saved mock results only; no worker is running"}}, status_code=405)
            return await call_next(request)

    with socket.socket() as listener:
        listener.bind(("127.0.0.1", port))
        listener.listen(128)
        url = "http://127.0.0.1:" + str(listener.getsockname()[1])
        server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", log_level="error",
                                             timeout_graceful_shutdown=5))
        thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
        thread.start()
        try:
            deadline = time.monotonic() + 10
            while not server.started:
                require(thread.is_alive() and time.monotonic() < deadline,
                        "Owned loopback API failed to start")
                time.sleep(.02)
            origin = httpx.URL(url)

            def owned_origin(request):
                require((request.url.scheme, request.url.host, request.url.port) ==
                        (origin.scheme, origin.host, origin.port), "Only the owned loopback origin is permitted")

            with httpx.Client(base_url=url, timeout=60, trust_env=False,
                              event_hooks={"request": [owned_origin]},
                              headers={"Authorization": "Bearer " + PUBLIC_TOKEN}) as client:
                yield client, url
        finally:
            server.should_exit = True
            thread.join(10)
            require(not thread.is_alive(), "Owned loopback API did not stop")


class NeverModel:
    def request(self, *_args, **_kwargs):
        raise AssertionError("Real model forbidden in synthetic candidate")

    complete = request


def serve_accepted_run(worker, read_header, observe):
    """Ordinary Worker service, bounded by the original accepted Run deadline.

    once() reports progress, not completion. Only Store.claim may reclaim an
    expired owner. This controller never submits, resumes or changes a Run.
    """
    accepted = read_header()
    require(accepted["status"] == "QUEUED", "Expected the just accepted synthetic Run")
    identity = {key: accepted[key] for key in ("id", "principal_id", "project_id", "created_at", "deadline")}
    turns = []
    try:
        # Matches worker.main's original one-second service cadence, not a
        # tightened heartbeat schedule or an enlarged business budget.
        for number in range(worker.s.run_seconds + 1):
            before = read_header()
            require(all(before[key] == value for key, value in identity.items()), "Accepted Run identity or deadline changed")
            require(not before["unexpected_active_run_ids"], "Unexpected active Run in isolated synthetic fixture")
            require(set(before["service_claimed_run_ids"]) <= {accepted["id"]}, "Worker claimed an unexpected synthetic Run")
            require(before["status"] in {"QUEUED", "RUNNING"}, "Synthetic Run is blocked or stopped: " + before["status"])
            require(time.time() < accepted["deadline"] and not worker.stop.is_set(), "Original accepted Run deadline or stop reached")
            turn = dict(number=number + 1, before=before, started_at=time.time())
            try:
                turn["claimed_work"] = worker.once()
                after = read_header()
            except BaseException as error:
                turn.update(finished_at=time.time(), error_type=type(error).__name__, error=str(error))
                turns.append(turn)
                observe(turns)
                raise  # No restart after an unexpected exception.
            turn.update(finished_at=time.time(), after=after)
            turns.append(turn)
            observe(turns)
            require(all(after[key] == value for key, value in identity.items()), "Accepted Run identity or deadline changed")
            require(not after["unexpected_active_run_ids"], "Unexpected active Run in isolated synthetic fixture")
            require(set(after["service_claimed_run_ids"]) <= {accepted["id"]}, "Worker claimed an unexpected synthetic Run")
            if after["status"] in {"SUCCEEDED", "PARTIAL"}:
                require(set(after["service_claimed_run_ids"]) == {accepted["id"]}, "Expected actual target claim by this service")
                return after
            require(after["status"] in {"QUEUED", "RUNNING"}, "Synthetic Run is blocked or stopped: " + after["status"])
            remaining = accepted["deadline"] - time.time()
            require(remaining > 0, "Original accepted Run deadline reached")
            worker.stop.wait(min(1.0, remaining))
        raise RuntimeError("Bounded ordinary Worker service ended without a terminal result")
    finally:
        worker.stop.set()


class Demo:
    def __init__(self, store, settings, client, root):
        self.store, self.settings, self.client, self.root = store, settings, client, root
        self.http, self.claims, self.mock_calls = [], [], []
        fixture = Path(__file__).with_name("local-candidate") / "mock-fixtures.json"
        self.fixtures = json.loads(fixture.read_text(encoding="utf-8"))
        require(self.fixtures["version"] == "sim2act-local-mock-fixtures.v1", "Mock fixtures changed")

    def request(self, method, path, body=None, status=200):
        response = self.client.request(method, path, json=body) if body is not None else self.client.request(method, path)
        self.http.append({"method": method, "path": path, "status": response.status_code})
        write_json(self.root / "http-receipts.json", self.http)
        require(response.status_code == status, f"{method} {path}: {response.status_code}: {response.text}")
        return response.json()

    def material(self, project, key):
        content = self.fixtures["materials"][key]["content"]
        resource = self.request("POST", f"/api/projects/{project}/resources",
            dict(name=key + ".txt", format="txt", content=content), 201)
        card = self.request("POST", f"/api/projects/{project}/goal-cards", dict(
            title="MOCK " + key,
            goal="Extract duties, conditions, exceptions and pending choices into a reusable cited review checklist",
            known=[], assumptions=[], unresolved=["Human question " + str(i) for i in range(16)],
            constraints=["Preserve the full source and uncertain relations"],
            acceptance_checks=["Human review of completeness and meaning"],
            resource_refs=[resource["id"]]), 201)
        return resource["id"], self.request("GET", "/api/goal-cards/" + card["id"])

    def release(self, app_id, sample):
        app = self.request("GET", "/api/apps/" + app_id)
        approval = self.request("POST", f"/api/internal/apps/{app_id}/release-approvals",
            dict(expected_draft_fingerprint=app["fingerprint"], sample_input=sample), 201)
        release = self.request("POST", f"/api/internal/approvals/{approval['id']}/commit",
            dict(fingerprint=approval["fingerprint"]))
        instance = self.request("POST", f"/api/internal/releases/{release['id']}/instances",
            dict(expected_release_fingerprint=release["fingerprint"], request_key="mock-instance"), 201)
        return app, release, instance

    def serve_run(self, run_id, transport=None):
        worker = Worker(self.store, self.settings, NeverModel(), goal_planner_transport=transport)
        turns = []

        def header():
            # Only owned synthetic identifiers and scheduling scalars. Avoid
            # repeatedly opening full HTTP proof transactions while it runs.
            with self.store.engine.connect() as connection:
                row = dict(connection.execute(select(runs.c.id, runs.c.principal_id,
                    runs.c.project_id, runs.c.created_at, runs.c.status, runs.c.fence,
                    runs.c.worker_id, runs.c.lease_until,
                    run_contracts.c.snapshot["limits"]["run_seconds"].as_integer().label("seconds"),
                    internal_run_bindings.c.snapshot["natural_spec_clock"].label("clock"))
                    .join(run_contracts, run_contracts.c.run_id == runs.c.id)
                    .outerjoin(internal_run_bindings, internal_run_bindings.c.run_id == runs.c.id)
                    .where(runs.c.id == run_id)).mappings().one())
                row["unexpected_active_run_ids"] = list(connection.execute(select(runs.c.id).where(
                    runs.c.id != run_id, runs.c.status.in_(["QUEUED", "RUNNING", "PAUSE_REQUESTED", "CANCEL_REQUESTED"]))
                    .order_by(runs.c.id)).scalars())
                row["service_claimed_run_ids"] = list(connection.execute(select(runs.c.id).where(
                    runs.c.worker_id == worker.id).order_by(runs.c.id)).scalars())
            clock = row.pop("clock")
            row["deadline"] = row["created_at"] + min(self.settings.run_seconds, row.pop("seconds"))
            if clock is not None:
                require(clock["created_at"] == row["created_at"], "Original natural clock changed")
                row["deadline"] = min(row["deadline"], clock["deadline"])
            return row

        def observe(value):
            turns[:] = value
            write_json(self.root / ("worker-service-" + run_id + ".json"), turns)

        try:
            completed = serve_accepted_run(worker, header, observe)
            require(completed["worker_id"] == worker.id, "Unexpected worker completed this isolated synthetic Run")
            return self.request("GET", "/api/runs/" + run_id)
        finally:
            with self.store.engine.connect() as connection:
                current = dict(connection.execute(select(runs.c.fence, runs.c.status, runs.c.worker_id)
                    .where(runs.c.id == run_id)).mappings().one())
                ledger = [dict(row) for row in connection.execute(select(events.c.kind, events.c.created_at,
                    events.c.data).where(events.c.run_id == run_id,
                    events.c.kind.in_(["CLAIMED", "WORKER_LOST", "RECONCILED"]))
                    .order_by(events.c.created_at, events.c.id)).mappings()]
                service_ledger = [dict(row) for row in connection.execute(select(events.c.run_id,
                    events.c.kind, events.c.created_at, events.c.data).join(runs, runs.c.id == events.c.run_id)
                    .where(runs.c.worker_id == worker.id, events.c.kind == "CLAIMED")
                    .order_by(events.c.created_at, events.c.id)).mappings()]
            self.claims.append(dict(run_id=run_id, service_worker_id=worker.id, **current,
                claim_count=sum(row["kind"] == "CLAIMED" for row in ledger),
                service_turns=len(turns), service_ledger=ledger, service_all_claims=service_ledger,
                last_observation=header(),
                service="NORMAL_WORKER_WITH_ORIGINAL_ACCEPTED_DEADLINE"))
            write_json(self.root / "worker-receipts.json", self.claims)

    def mock(self, stage, material="source"):
        count = 0
        fixed = self.fixtures["materials"][material]

        def handler(request):
            nonlocal count
            count += 1
            payload = json.loads(request.content)
            values = json.loads(payload["messages"][1]["content"])
            self.mock_calls.append(dict(stage=stage, call=count, transport="httpx.MockTransport"))
            write_json(self.root / "mock-receipts.json", self.mock_calls)
            if stage == "generation":
                candidate = dict(recipe=self.fixtures["recipe"], sample_nodes=[dict(
                    step_id="infer_pick", items=fixed["items"])],
                    source_hash=hashlib.sha256(fixed["content"].encode()).hexdigest(),
                    goal=values["saved_goal"]["snapshot"]["content"])
                if count == 1:
                    tool, args = natural.READ, dict(resource_id=values["source"]["resource_id"])
                elif count == 2:
                    tool, args = "spec.check_candidate", dict(candidate=candidate)
                else:
                    require(count == 3, "Mock generation exceeded three responses")
                    message = dict(role="assistant", content=json.dumps(candidate))
                if count <= 2:
                    message = dict(role="assistant", content="", tool_calls=[dict(
                        id="mock-" + str(count), type="function", function=dict(
                            name=tool, arguments=json.dumps(args)))])
            else:
                require(count == 1 and values["current_inputs"]["content"] == fixed["content"]
                        and not payload["tools"], "Unexpected mock runtime input")
                message = dict(role="assistant", content=json.dumps(dict(items=fixed["items"])))
            return httpx.Response(200, json=dict(model="intern-s2", choices=[dict(
                finish_reason="tool_calls" if "tool_calls" in message else "stop", message=message)],
                usage=dict(prompt_tokens=100, completion_tokens=900, total_tokens=1000)))

        return httpx.MockTransport(handler)

    def natural_run(self, project, app, release, instance, family, material, *, per_use=False, request_key=None):
        route = "/api/internal/instances/" + instance["id"]
        if family == "pa" and not per_use:
            # Legacy prepare branch: original saved material/Goal only.
            # prepare-pa below explicitly selects the per-use branch instead.
            submit = route + "/runs"
            commit = dict(expected_revision=instance["revision"],
                expected_release_fingerprint=release["fingerprint"], input={}, request_key="mock-pa-source")
            submission = "ORIGINAL_SAVED_MATERIAL_AND_GOAL"
        else:
            resource, card = self.material(project, material)
            body = dict(expected_revision=instance["revision"],
                expected_release_fingerprint=release["fingerprint"],
                expected_app_fingerprint=app["fingerprint"],
                expected_recipe_fingerprint=(app["candidate"]["spec_task"]["edited_recipe_fingerprint"]
                    if family == "pb" else fingerprint(app["candidate"]["spec_recipe"])),
                resource_id=resource, card_id=card["id"], expected_goal_version=card["version"],
                expected_goal_fingerprint=card["fingerprint"],
                expected_source_hash=hashlib.sha256(self.fixtures["materials"][material]["content"].encode()).hexdigest(),
                request_key=request_key or "mock-" + family + "-use")
            review = self.request("POST", route + f"/{family}-use-reviews", body)
            commit = dict(review=body, expected_review_fingerprint=review["review_fingerprint"],
                consent=uses.CONSENT if family == "pb" else uses.PA_CONSENT)
            submit = route + f"/{family}-use-runs"
            submission = "EXPLICIT_NEW_MATERIAL_GOAL_PER_USE_REVIEW"
        queued = self.request("POST", submit, commit, 202)
        # An identical original intent is idempotent, never a second Run.
        duplicate = self.request("POST", submit, commit, 202)
        require(queued["run_id"] == duplicate["run_id"], "Duplicate submit changed Run")
        run_id = queued["run_id"]
        result = self.serve_run(run_id, self.mock(family, material))
        require(result["status"] == "SUCCEEDED", "Natural mock Run did not succeed")
        artifact = self.request("GET", f"/api/internal/app-run-jobs/{run_id}/spec-artifact")
        checklist = json.loads(artifact["resource"]["content"])
        require(checklist["source_content"] == self.fixtures["materials"][material]["content"]
                and checklist["owner_acceptance"] == "PENDING"
                and checklist["semantic_goal_acceptance"] == "NOT_RUN", "Mock result contract changed")
        owner_path = route + f"/runs/{run_id}/spec-owner-review"
        owner = self.request("GET", owner_path)
        require(owner["owner_acceptance"] == "PENDING" and owner["content_access"],
                "Same-Run manual review unavailable")
        return dict(app_id=app["id"], instance_id=instance["id"], run_id=run_id,
            submission=submission,
            artifact_sha256=hashlib.sha256(artifact["resource"]["content"].encode()).hexdigest(),
            result_version=artifact["result_version"], manual_review=owner_path,
            owner_acceptance="PENDING", semantic_acceptance="NOT_RUN")

    def run(self, *, pa_new_material=False):
        require(self.request("GET", "/health")["database"] == "UP", "Database unavailable")
        require(self.client.get("/").status_code == 200, "Normal page unavailable")
        project = self.request("POST", "/api/projects", dict(name="SYNTHETIC MOCK local candidate"), 201)["id"]
        resource = self.request("POST", f"/api/projects/{project}/resources",
            dict(name="fixed.csv", format="csv", content="item,amount\nA,10\nB,20\n"), 201)
        draft = self.request("POST", f"/api/projects/{project}/apps/csv-preview",
            dict(name="Deterministic CSV sum", resource_id=resource["id"], goal="Sum amount"), 201)
        app, release, instance = self.release(draft["id"], dict(column="amount"))
        queued = self.request("POST", f"/api/internal/instances/{instance['id']}/runs", dict(
            expected_release_fingerprint=release["fingerprint"], expected_revision=instance["revision"],
            input=dict(column="amount"), request_key="mock-csv-run"), 202)
        require(self.serve_run(queued["run_id"])["status"] == "SUCCEEDED", "CSV Run failed")
        detail_path = f"/api/internal/instances/{instance['id']}/runs/{queued['run_id']}"
        result = self.request("GET", detail_path)
        require(result["result"]["sum"] == "30" and result["result_version"] == 1, "Wrong CSV result")
        deterministic = dict(app_id=app["id"], instance_id=instance["id"],
                             run_id=queued["run_id"], detail=detail_path, sum="30", result_version=1)
        print("PASS deterministic CSV = 30; starting explicit MOCK natural P-A", flush=True)

        _, card = self.material(project, "source")
        generated = self.request("POST", f"/api/projects/{project}/goal-cards/{card['id']}/application-runs",
            dict(expected_version=card["version"], expected_fingerprint=card["fingerprint"],
                 request_key="mock-pa-generation", family="natural_spec"), 202)
        generation = self.serve_run(generated["run_id"], self.mock("generation"))
        require(generation["status"] == "PARTIAL", "Expected reviewable mock candidate")
        saved = self.request("POST", f"/api/runs/{generated['run_id']}/confirm-application-candidate", dict(
            expected_version=generation["version"],
            candidate_fingerprint=generation["result"]["candidate_fingerprint"],
            request_key="mock-confirm-pa", name="MOCK natural P-A", artifact_write_consent=natural.CONSENT))
        pa_app, pa_release, pa_instance = self.release(saved["id"], {})
        if pa_new_material:
            first = self.natural_run(project, pa_app, pa_release, pa_instance, "pa", "pa_use", per_use=True)
            with self.store.engine.connect() as connection:
                first_row = dict(connection.execute(select(internal_instance_data).where(
                    internal_instance_data.c.instance_id == pa_instance["id"], internal_instance_data.c.version == 1)).mappings().one())
            second = self.natural_run(project, pa_app, pa_release, pa_instance, "pa", "pb_use",
                per_use=True, request_key="mock-pa-use-second")
            with self.store.engine.connect() as connection:
                rows = [dict(row) for row in connection.execute(select(internal_instance_data).where(
                    internal_instance_data.c.instance_id == pa_instance["id"]).order_by(internal_instance_data.c.version)).mappings()]
            require([row["version"] for row in rows] == [1, 2] and rows[0] == first_row,
                    "First PA result changed or same-instance version did not advance")
            require(first["result_version"] == 1 and second["result_version"] == 2,
                    "Expected first two results from explicit PA per-use")
            require(len(self.mock_calls) == 5, "Expected three generation and two PA runtime mock responses")
            return dict(**MARKER, status="PASS", scenario="PA_NEW_MATERIAL_TWICE", project_id=project,
                deterministic=deterministic, natural_pa_previous=first, natural_pa=second,
                natural_pa_history=[dict(version=row["version"], fingerprint=row["fingerprint"],
                    row_sha256=hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest()) for row in rows],
                worker_claims=self.claims, mock_responses=len(self.mock_calls), real_model_requests=0,
                pa_new_material_per_use="PASS_TWO_ACTUAL_RUNS_V1_V2", formal_publication_enabled=False,
                windows="NOT_RUN", postgres="NOT_RUN", real_semantics="NOT_RUN")
        pa_result = self.natural_run(project, pa_app, pa_release, pa_instance, "pa", "source")
        print("PASS MOCK P-A original saved material/Goal; starting P-B extraction", flush=True)

        resource, card = self.material(project, "pb_target")
        path = f"/api/projects/{project}/natural-spec-task-runs/{pa_result['run_id']}"
        options = self.request("GET", path + "/extraction-options")
        body = dict(source_run_id=pa_result["run_id"],
            expected_source_proof_fingerprint=options["source_proof_fingerprint"],
            expected_source_recipe_fingerprint=options["recipe_fingerprint"], card_id=card["id"],
            expected_goal_version=card["version"], expected_goal_fingerprint=card["fingerprint"],
            expected_source_hash=hashlib.sha256(self.fixtures["materials"]["pb_target"]["content"].encode()).hexdigest(),
            recipe=options["recipe"], name="MOCK natural P-B", request_key="mock-pb-extraction")
        review = self.request("POST", path + "/extraction-reviews", body)
        saved = self.request("POST", path + "/extractions", dict(review=body,
            expected_review_fingerprint=review["review_fingerprint"], consent=pb.CONSENT,
            artifact_write_consent=natural.CONSENT), 201)
        app, release, instance = self.release(saved["id"], {})
        pb_result = self.natural_run(project, app, release, instance, "pb", "pb_use")
        directory = self.request("GET", "/api/apps?metadata_only=true")
        families = {item["id"]: item.get("use_family") for item in directory["items"]}
        require(families[pa_app["id"]] == "NATURAL_PA" and families[app["id"]] == "NATURAL_PB",
                "Directory natural classification changed")
        require(len(self.mock_calls) == 5, "Unexpected mock response count")
        return dict(**MARKER, status="PASS", project_id=project, deterministic=deterministic,
            natural_pa=pa_result, natural_pb=pb_result, worker_claims=self.claims,
            pa_new_material_per_use="NOT_RUN_IN_THIS_CANDIDATE",
            mock_responses=len(self.mock_calls), real_model_requests=0,
            formal_publication_enabled=False, windows="NOT_RUN", postgres="NOT_RUN",
            real_semantics="NOT_RUN", prior_lock_validation="Separate historical staged evidence")


def prepare(path, *, pa_new_material=False):
    path = unlinked_path(path)
    require(not path.exists() and not path.is_symlink(), "Prepare requires a NEW directory; existing data preserved")
    path.mkdir(parents=True, exist_ok=False)
    root = path.resolve()
    write_json(root / "fixture.json", MARKER)
    settings = settings_for(root)
    store = Store(settings.database_url, test_only=True)
    try:
        store.initialize()  # Only this explicitly created fresh synthetic SQLite fixture.
        store.user("PUBLIC synthetic mock identity", PUBLIC_TOKEN)
        with loopback(store, settings) as (client, _):
            result = Demo(store, settings, client, root).run(pa_new_material=pa_new_material)
        write_json(root / "demo-receipt.json", result)
        print("PASS saved synthetic mock fixture; run verify in a separate process for cold reads", flush=True)
    finally:
        store.engine.dispose()


def snapshot(store):
    with store.engine.connect() as connection:
        return {table.name: sorted((dict(row) for row in connection.execute(select(table)).mappings()),
            key=lambda row: json.dumps(row, sort_keys=True, default=str)) for table in meta.sorted_tables}


def verify(path):
    root = checked_directory(path)
    receipt = json.loads((root / "demo-receipt.json").read_text(encoding="utf-8"))
    require(receipt["mode"] == MARKER["mode"] and receipt["status"] == "PASS", "Incomplete fixture")
    settings = settings_for(root)
    store = Store(settings.database_url, test_only=True)
    try:
        before = snapshot(store)
        with loopback(store, settings, read_only=True) as (client, _):
            csv = client.get(receipt["deterministic"]["detail"])
            require(csv.status_code == 200 and csv.json()["result"]["sum"] == "30", "Cold CSV failed")
            keys = (["natural_pa_previous", "natural_pa"] if receipt.get("scenario") == "PA_NEW_MATERIAL_TWICE"
                    else ["natural_pa", "natural_pb"])
            for key in keys:
                result = receipt[key]
                response = client.get(f"/api/internal/app-run-jobs/{result['run_id']}/spec-artifact")
                require(response.status_code == 200, "Cold artifact denied")
                artifact = response.json()
                require(hashlib.sha256(artifact["resource"]["content"].encode()).hexdigest() == result["artifact_sha256"]
                        and artifact["result_version"] == result["result_version"], "Cold result changed")
                owner = client.get(result["manual_review"])
                require(owner.status_code == 200 and owner.json()["owner_acceptance"] == "PENDING",
                        "Cold same-Run manual review failed")
            require(client.post("/api/projects", json={"name": "must not write"}).status_code == 405,
                    "Cold demo permits writes")
        if receipt.get("scenario") == "PA_NEW_MATERIAL_TWICE":
            with store.engine.connect() as connection:
                rows = [dict(row) for row in connection.execute(select(internal_instance_data).where(
                    internal_instance_data.c.instance_id == receipt["natural_pa"]["instance_id"])
                    .order_by(internal_instance_data.c.version)).mappings()]
            history = [dict(version=row["version"], fingerprint=row["fingerprint"],
                row_sha256=hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest()) for row in rows]
            require(history == receipt["natural_pa_history"], "Cold first/second PA typed rows changed")
        require(snapshot(store) == before, "Cold reads changed persisted rows")
        report = dict(**MARKER, status="PASS", cold_process=True, persisted_rows_unchanged=True,
                      existing_results=3, workers_started=0, model_requests=0)
        write_json(root / "cold-read-receipt.json", report)
        print(json.dumps(report), flush=True)
    finally:
        store.engine.dispose()


def serve(path, port):
    root = checked_directory(path)
    settings = settings_for(root)
    store = Store(settings.database_url, test_only=True)
    try:
        with loopback(store, settings, port=port, read_only=True) as (_, url):
            print("SYNTHETIC MOCK saved results (read-only): " + url, flush=True)
            print("Public fixture login: " + PUBLIC_TOKEN, flush=True)
            print("Choose the SYNTHETIC MOCK project → saved applications → instance → Run results/manual review.", flush=True)
            print("No worker or model is running. Ctrl+C stops only this server; data remains.", flush=True)
            try:
                threading.Event().wait()
            except KeyboardInterrupt:
                pass
    finally:
        store.engine.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["prepare", "prepare-pa", "verify", "serve"])
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8000, help="serve only; loopback, 0 for dynamic port")
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error("port must be between 0 and 65535")
    try:
        if args.command in {"prepare", "prepare-pa"}:
            prepare(args.data_dir, pa_new_material=args.command == "prepare-pa")
        elif args.command == "verify":
            verify(args.data_dir)
        else:
            serve(args.data_dir, args.port)
    except (RuntimeError, OSError, ValueError) as error:
        # Preserve every created fixture on failure; never delete/retry unknown work.
        parser.exit(1, "Synthetic demo stopped; data preserved: " + str(error) + "\n")


if __name__ == "__main__":
    main()
