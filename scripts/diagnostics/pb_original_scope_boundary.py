"""One bounded original mock-preparation boundary probe; zero provider/PG IO.

Explicit SQLite literal, existing fixed synthetic fixture identities, original
API consent and original Worker/account validators. Never extends a contract or
refreshes/replaces a binding. This is NOT a complete P-B or production-source test.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests"))

import httpx  # noqa: E402
import test_natural_spec_apps as apps  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import func, select  # noqa: E402

from sim2act import natural_live_admission as gate  # noqa: E402
from sim2act import natural_trial_budget as budget  # noqa: E402
from sim2act import pa_trial_dispatch as trial  # noqa: E402
from sim2act import production_trial_admission as production  # noqa: E402
from sim2act import production_trial_journal as journal  # noqa: E402
from sim2act import spec_production  # noqa: E402
from sim2act.api import create_app  # noqa: E402
from sim2act.config import Settings  # noqa: E402
from sim2act.db import Store, attempts, delivery_graph_requests, fingerprint, runs  # noqa: E402
from sim2act.errors import DomainError  # noqa: E402
from sim2act.worker import Worker  # noqa: E402


def require(condition, code):
    if not condition:
        raise RuntimeError(code)


def trace(error):
    frames = []
    current = error.__traceback__
    while current is not None:
        frame = current.tb_frame
        filename = Path(frame.f_code.co_filename)
        if filename.is_relative_to(ROOT):
            frames.append(
                dict(
                    file=str(filename.relative_to(ROOT)),
                    function=frame.f_code.co_name,
                    line=current.tb_lineno,
                )
            )
        current = current.tb_next
    return frames


def execute(root):
    # Explicit checks survive -O. No fixture/environment can select PostgreSQL.
    require(
        root.parent == Path("/workspace/scratch")
        and re.fullmatch(r"pb-original300-[a-z0-9-]+", root.name),
        "NEW_OWN_SCRATCH_ROOT_REQUIRED",
    )
    root.mkdir(mode=0o700, exist_ok=False)
    started = time.monotonic()
    phases = []
    dispatches = []
    source = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    store = Store("sqlite:///" + str(root / "fixture.db"), test_only=True)
    require(store.sqlite and store.test_only, "EXPLICIT_SQLITE_ONLY")
    settings = Settings(
        str(store.engine.url),
        root,
        mode="mock",
        live_enabled=False,
        token="",
        goal_planner_provider="intern-s2",
        rpm=1,
        max_requests=3,
        max_repairs=0,
    )
    account_id = "offline-pb-original300-account"
    settings = replace(settings, quota_subject=production.canonical_quota_subject(account_id))
    store.initialize(quota_subject=settings.quota_subject)
    # Reused public fixed synthetic fixture tokens, never generated production credentials.
    user = store.user("fixture A", "synthetic-test-A")
    client = TestClient(create_app(store, settings))
    client.headers["Authorization"] = "Bearer synthetic-test-A"
    result = dict(
        source_sha=source,
        backend="TEST_ONLY_SQLITE",
        mode="mock",
        actual_provider_calls=0,
        pg_operations=0,
        business_source_changes=0,
        clock_or_expiry_changes=0,
        binding_replacements=0,
        synthetic_identity_only=True,
        phases=phases,
    )
    try:
        at = time.monotonic()
        project = client.post(
            "/api/projects", json=dict(name="Original300 boundary synthetic notes")
        )
        require(project.status_code == 201, "PROJECT_NOT_CREATED")
        pid = project.json()["id"]
        _, first = apps.material(client, pid, apps.SOURCE)
        _, cold = apps.material(client, pid, apps.COLD)
        base = f"/api/projects/{pid}/natural-trials/original-boundary"
        prepared_at = time.time()
        reply = client.post(
            base + "/preparation",
            json=dict(
                path="P-B",
                bindings=[
                    dict(card_id=c["id"], expected_version=c["version"]) for c in (first, cold)
                ],
                extraction_recipe=apps.recipe("single"),
            ),
        )
        require(reply.status_code == 200, "ORIGINAL_PREPARATION_REJECTED")
        receipt = reply.json()
        contract = gate.PBTrialContract.model_validate(receipt["contract"])
        require(
            prepared_at + 300 <= contract.expires_at <= time.time() + 300, "ORIGINAL_EXPIRY_CHANGED"
        )
        require(contract.caps == gate.TrialCaps(), "ORIGINAL_CAPS_CHANGED")
        consent = client.post(
            base + "/consent",
            json=dict(review_token=receipt["review_token"], confirm_exact_scope=True),
        )
        require(consent.status_code == 200, "ORIGINAL_CONSENT_REJECTED")
        recovered = client.get(base + "/preparation")
        require(
            recovered.status_code == 200 and recovered.json()["approved"] is True,
            "ORIGINAL_APPROVAL_NOT_READABLE",
        )
        phases.append(
            dict(stage="original_preparation_consent", seconds=time.monotonic() - at, status="PASS")
        )
        result["scope"] = dict(
            lease_seconds=contract.caps.lease_seconds,
            run_seconds=contract.caps.run_seconds,
            expires_at=contract.expires_at,
            prepared_at_bounds=[prepared_at, time.time()],
            quota_kind="UNCONFIGURED_MOCK"
            if contract.quota_subject == "unconfigured:" + user
            else "OTHER",
            canonical_account_matches=contract.quota_subject == settings.quota_subject,
            contract_fingerprint=fingerprint(contract.model_dump()),
            live_allowed=receipt["live_allowed"],
        )
        require(
            result["scope"]["quota_kind"] == "UNCONFIGURED_MOCK"
            and not result["scope"]["canonical_account_matches"],
            "UNEXPECTED_MOCK_AUTHORITY",
        )
        at = time.monotonic()
        submitted = client.post(
            f"/api/projects/{pid}/goal-cards/{first['id']}/application-runs",
            json=dict(
                expected_version=first["version"],
                expected_fingerprint=first["fingerprint"],
                request_key=contract.stage_keys.generate,
                family="natural_spec",
            ),
        )
        require(submitted.status_code == 202, "GENERATE_NOT_ACCEPTED")
        rid = submitted.json()["run_id"]
        phases.append(
            dict(stage="original_generate_enqueue", seconds=time.monotonic() - at, status="QUEUED")
        )
        account = production.AccountEvidence(
            principal_id=user,
            project_id=pid,
            trial_key=contract.trial_key,
            contract_fingerprint=fingerprint(contract.model_dump()),
            account_id=account_id,
            quota_subject=settings.quota_subject,
            evidence_sha256="b" * 64,
            checked_at=time.time(),
            expires_at=contract.expires_at,
            legal_free_entitlement=True,
            enforced_non_chargeable=True,
        )
        binding = trial.PATrialBinding(
            contract,
            contract.stage_keys.generate + "_approval",
            production.OfflineRegistry((account,), production.OfflineSender()),
        )

        def no_send(request):
            dispatches.append(True)
            raise RuntimeError("NO_MODEL_TRANSPORT_PERMITTED")

        result["worker_rejections"] = []
        for label, candidate_settings in [
            ("canonical_runtime", settings),
            (
                "runtime_matching_original_mock_contract",
                replace(settings, quota_subject=contract.quota_subject),
            ),
        ]:
            at = time.monotonic()
            worker = None
            try:
                worker = Worker(
                    store,
                    candidate_settings,
                    goal_planner_transport=httpx.MockTransport(no_send),
                    pa_trial=binding,
                )
            except DomainError as error:
                require(error.code == "LIVE_BLOCKED", "UNEXPECTED_ACCOUNT_ERROR")
                result["worker_rejections"].append(
                    dict(runtime=label, code=error.code, trace=trace(error))
                )
                phases.append(
                    dict(
                        stage="original_worker_" + label,
                        seconds=time.monotonic() - at,
                        status="LIVE_BLOCKED",
                    )
                )
            else:
                worker.stop.set()
                require(worker.drain_owned_heartbeats(10), "OWNED_HEARTBEAT_UNKNOWN")
                raise RuntimeError("UNEXPECTED_MOCK_ACCOUNT_ADMITTED")
        at = time.monotonic()
        try:
            spec_production.environment(store, settings, None)
        except DomainError as error:
            require(error.code == "LIVE_BLOCKED", "UNEXPECTED_PRODUCTION_ERROR")
            result["production_binding_rejection"] = dict(
                code=error.code, issues=spec_production.configuration_issues(store, settings, None)
            )
            phases.append(
                dict(
                    stage="original_production_environment_check",
                    seconds=time.monotonic() - at,
                    status="LIVE_BLOCKED",
                )
            )
        else:
            raise RuntimeError("UNEXPECTED_PRODUCTION_ENVIRONMENT_ADMITTED")
        before = client.get("/api/runs/" + rid)
        require(
            before.status_code == 200 and before.json()["status"] == "QUEUED",
            "UNEXPECTED_RUN_CHANGE",
        )
        at = time.monotonic()
        cancelled = client.post(
            "/api/runs/" + rid + "/commands",
            json=dict(command="cancel", version=before.json()["version"]),
        )
        require(cancelled.status_code == 200, "ORIGINAL_CANCEL_REJECTED")
        final = client.get("/api/runs/" + rid)
        require(
            final.status_code == 200
            and final.json()["status"] == "CANCELLED"
            and final.json()["result"] is None,
            "CANCEL_NOT_TERMINAL",
        )
        repeated = client.post(
            "/api/runs/" + rid + "/commands",
            json=dict(command="cancel", version=final.json()["version"]),
        )
        require(repeated.status_code == 409, "TERMINAL_REPEAT_CHANGED")
        withdrawn = client.post(
            base + "/withdrawal",
            json=dict(review_token=receipt["review_token"], confirm_withdrawal=True),
        )
        require(
            withdrawn.status_code == 200 and withdrawn.json()["status"] == "REVOKED",
            "TRIAL_WITHDRAWAL_UNKNOWN",
        )
        with store.tx() as c:
            count = c.execute(
                select(func.count()).select_from(attempts).where(attempts.c.run_id == rid)
            ).scalar_one()
            row = (
                c.execute(select(runs.c.status, runs.c.result).where(runs.c.id == rid))
                .mappings()
                .one()
            )
            slots = list(
                c.execute(
                    select(delivery_graph_requests.c.kind).where(
                        delivery_graph_requests.c.kind.in_(
                            [
                                budget.KIND,
                                budget.KIND + "_seal",
                                journal.KIND,
                                journal.KIND + "_seal",
                            ]
                        )
                    )
                ).scalars()
            )
        require(count == 0 and not dispatches and not slots, "UNEXPECTED_MODEL_ATTEMPT_OR_LEDGER")
        result["cancel"] = dict(
            status=row["status"],
            result_present=row["result"] is not None,
            repeat_http=repeated.status_code,
            trial_withdrawn=True,
            model_attempts=count,
        )
        result["run_id"] = rid
        result["journal_kinds_present"] = slots
        phases.append(
            dict(
                stage="original_cancel_repeat_and_withdraw",
                seconds=time.monotonic() - at,
                status="PASS",
            )
        )
        result.update(
            status="ORIGINAL_MOCK_BOUNDARY_CONFIRMED",
            elapsed_seconds=time.monotonic() - started,
            g0_entered=False,
            g1_entered=False,
            claim_attempted=False,
            source_cold_started=False,
        )
        # Remove client/session then prove ordinary new Store/API reads terminal state.
        client.close()
        store.engine.dispose()
        reopened = Store("sqlite:///" + str(root / "fixture.db"), test_only=True)
        try:
            with TestClient(create_app(reopened, settings)) as again:
                again.headers["Authorization"] = "Bearer synthetic-test-A"
                reread = again.get("/api/runs/" + rid)
                scope = again.get(base + "/preparation")
                require(
                    reread.status_code == 200
                    and reread.json()["status"] == "CANCELLED"
                    and reread.json()["result"] is None,
                    "REOPEN_CHANGED_CANCEL",
                )
                require(
                    scope.status_code == 200 and scope.json()["revoked"] is True,
                    "REOPEN_CHANGED_WITHDRAWAL",
                )
            result["new_store_api_reread"] = True
        finally:
            reopened.engine.dispose()
        raw = json.dumps(result, indent=2) + "\n"
        fd = os.open(root / "result.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as out:
            out.write(raw)
        result["receipt_sha256"] = hashlib.sha256(raw.encode()).hexdigest()
        print(json.dumps(result, indent=2))
        return result
    finally:
        client.close()
        store.engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    execute(args.root.absolute())
