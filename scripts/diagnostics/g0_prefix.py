"""Exact finite composition of existing synthetic fixture helpers.

No work occurs at import. Called only by the bounded, explicitly granted child.
Never call the original full PB test or its damaged-copy matrix here.
"""


def run_prefix(root, patch, files, notify, healthy):
    import json
    import threading

    import httpx
    import test_natural_spec_apps as apps
    from conftest import env
    from fastapi.testclient import TestClient
    from g0_guard import (
        Boundary,
        G0Stop,
        MockBudget,
        StopBoundary,
        install_mock_counter,
        install_network_denials,
    )
    from test_pb_spec_production_controller import prepare_pb
    from test_pb_trial_dispatch import approve_stage
    from test_spec_production_controller import configured

    from sim2act import model
    from sim2act import natural_source_archives as archive
    from sim2act import natural_spec_runtime as runtime
    from sim2act import natural_specs as natural
    from sim2act import pa_trial_dispatch as trial
    from sim2act import pb_natural_specs as pb
    from sim2act import pb_natural_uses as use
    from sim2act import spec_production as controller
    from sim2act.api import create_app
    from sim2act.db import Store, fingerprint
    from sim2act.errors import DomainError

    # These module names and helper symbols are checked against frozen sources
    # before launch. No account/qualification/approval helper is replaced here.
    clients, stores = [], []
    before_threads = set(threading.enumerate())
    client_init = TestClient.__init__

    def track_client(self, *args, **kwargs):
        client_init(self, *args, **kwargs)
        clients.append(self)

    patch.setattr(TestClient, "__init__", track_client)
    install_network_denials(patch, httpx, model)
    mocks = MockBudget(healthy)
    boundary = StopBoundary(DomainError, mocks, notify)
    original_context = runtime._cold_model_before
    patch.setattr(
        runtime, "_cold_model_before", lambda *args: boundary.wrap(original_context, *args)
    )
    patch.setattr(
        runtime._ColdCommitDiagnostics,
        "__init__",
        boundary.observe_init(runtime._ColdCommitDiagnostics.__init__),
    )
    iterator = env.__wrapped__(root)
    fixture = None
    diagnostic = {"classification": "UNKNOWN", "g0": "NOT_REACHED"}
    try:
        original_env = next(iterator)
        stores.append(original_env[0])
        data, binding, fixture, factory = configured(
            original_env, root, patch, prepare_case=prepare_pb
        )
        normal = apps.transport([], apps.SOURCE)
        install_mock_counter(patch, httpx, mocks, fixture, normal)
        generation, _, release, source_instance, generated = apps.ready(data, style="ordered")
        if len(generated) != 3 or mocks.exchanges != 3:
            raise Boundary("Generate prefix not exactly three")
        mocks.stage = "source"
        source_id = apps.enqueue(
            data, release, source_instance, key=binding.contract.stage_keys.source
        )
        approve_stage(data, binding, "source", source_id)
        source_bytes = []

        def source_response(request):
            raw = normal.handle_request(request).json()
            raw["archive_note"] = "合成原始正文；非真实模型"
            payload = (json.dumps(raw, ensure_ascii=False, indent=2) + "\n").encode()
            source_bytes.append((request.content, payload))
            return httpx.Response(200, content=payload)

        if not factory(
            data[0], data[1], goal_planner_transport=httpx.MockTransport(source_response)
        ).once():
            raise Boundary("Source worker did not claim")
        result = apps.inspect(data, source_instance, source_id)
        if (
            result.status_code != 200
            or result.json()["status"] != "SUCCEEDED"
            or mocks.exchanges != 5
        ):
            raise Boundary("Source prefix failed")
        route = f"/api/projects/{data[4]}/natural-spec-task-runs/{source_id}"
        options = data[2].get(route + "/extraction-options")
        if options.status_code != 200:
            raise Boundary("extraction options refused")
        target = binding.contract.bindings[1]
        review = dict(
            source_run_id=source_id,
            expected_source_proof_fingerprint=options.json()["source_proof_fingerprint"],
            expected_source_recipe_fingerprint=options.json()["recipe_fingerprint"],
            card_id=target.card_id,
            expected_goal_version=target.goal_version,
            expected_goal_fingerprint=target.goal_fingerprint,
            expected_source_hash=target.source_hash,
            recipe=binding.contract.extraction_recipe.model_dump(exclude_none=True),
            name="P-B production-shaped fixture",
            request_key=binding.contract.extraction_request_key,
        )
        preview = data[2].post(route + "/extraction-reviews", json=review)
        if preview.status_code != 200:
            raise Boundary("extraction review refused")
        body = pb.ExtractInput(
            review=review,
            expected_review_fingerprint=preview.json()["review_fingerprint"],
            consent=pb.CONSENT,
            artifact_write_consent=natural.CONSENT,
        )

        def no_exchange(request):
            raise Boundary("Extraction must not send")

        extractor = factory(
            data[0], data[1], goal_planner_transport=httpx.MockTransport(no_exchange)
        )
        made = trial.extract_pb(extractor, data[3], source_id, body)
        if trial.extract_pb(extractor, data[3], source_id, body) != made or mocks.exchanges != 5:
            raise Boundary("extraction replay changed prefix")
        resolved = archive.resolve_trial_source(
            data[0], data[3], binding.contract, binding.approval_key
        )
        if (
            list(zip(resolved.request_bodies, resolved.response_bodies, strict=True))
            != source_bytes
            or resolved.public_receipt["verification"] != "SPEC_PRODUCTION_CONTROLLER_ARCHIVE"
            or resolved.public_receipt["live_allowed"] is not False
        ):
            raise Boundary("Source raw provenance differs")
        release, instance = apps.instance(data, made["id"])
        cold_store = Store(data[1].database_url, test_only=True)
        stores.append(cold_store)
        cold_client = TestClient(create_app(cold_store, data[1]))
        cold_client.headers["Authorization"] = "Bearer synthetic-test-A"
        cold_data = (cold_store, data[1], cold_client, *data[3:])
        original_environment = controller.environment

        def cold_environment(store, settings, transport):
            if store is cold_store:
                if (
                    settings is not data[1]
                    or transport is not None
                    or not store.test_only
                    or not store.sqlite
                ):
                    raise Boundary("Cold environment identity")
            else:
                original_environment(store, settings, transport)

        patch.setattr(controller, "environment", cold_environment)
        base = "/api/internal/instances/" + instance["id"]
        current_response = cold_client.get(base)
        app_response = cold_client.get("/api/apps/" + made["id"])
        if current_response.status_code != 200 or app_response.status_code != 200:
            raise Boundary("Cold instance/app not available")
        current, app = current_response.json(), app_response.json()
        if app["fingerprint"] != made["candidate_fingerprint"]:
            raise Boundary("Cold candidate identity")
        use_review = dict(
            expected_revision=current["revision"],
            expected_release_fingerprint=release["fingerprint"],
            expected_app_fingerprint=app["fingerprint"],
            expected_recipe_fingerprint=fingerprint(
                binding.contract.extraction_recipe.model_dump(exclude_none=True)
            ),
            resource_id=target.resource_id,
            card_id=target.card_id,
            expected_goal_version=target.goal_version,
            expected_goal_fingerprint=target.goal_fingerprint,
            expected_source_hash=target.source_hash,
            request_key=binding.contract.stage_keys.cold,
        )
        checked = cold_client.post(base + "/pb-use-reviews", json=use_review)
        if checked.status_code != 200:
            raise Boundary("Cold use review refused")
        submitted = dict(
            review=use_review,
            expected_review_fingerprint=checked.json()["review_fingerprint"],
            consent=use.CONSENT,
        )
        queued = cold_client.post(base + "/pb-use-runs", json=submitted)
        replayed = cold_client.post(base + "/pb-use-runs", json=submitted)
        if queued.status_code != 202 or replayed.status_code != 202:
            raise Boundary("Cold enqueue refused")
        first, replay = queued.json(), replayed.json()
        if (
            first["cached"] is not False
            or replay["cached"] is not True
            or {k: v for k, v in first.items() if k != "cached"}
            != {k: v for k, v in replay.items() if k != "cached"}
        ):
            raise Boundary("Cold idempotency")
        cold_id = first["run_id"]
        approve_stage(cold_data, binding, "cold", cold_id)
        files.writer("prefix-proof.json").json(
            dict(
                classification="SYNTHETIC_PREFIX_NOT_REAL_PRODUCTION_QUALIFICATION",
                contract=binding.contract.model_dump(mode="json"),
                approval_key=binding.approval_key,
                generation=generation,
                source=source_id,
                extraction=made["id"],
                cold=cold_id,
                source_receipt=resolved.public_receipt,
                same_key_replayed=True,
                mock_exchanges_before_cold=mocks.exchanges,
                real_models=0,
            )
        )
        mocks.stage = "cold"
        worker = factory(cold_store, data[1], goal_planner_transport=apps.transport([], apps.COLD))
        boundary.bind(worker, cold_id)
        try:
            worker.once()
        except G0Stop as stop:
            diagnostic = boundary.diagnostic(stop)
            # Preserve the original refusal before any client/heartbeat cleanup
            # can independently fail; never truncate or overwrite this record.
            files.writer("diagnostic.json").json(
                {"event": "g0_outcome_before_cleanup", **diagnostic}
            )
        else:
            raise Boundary("Cold returned without exact G0 stop")
    finally:
        if fixture is not None:
            for worker in fixture["workers"]:
                worker.stop.set()
        for client in reversed(clients):
            client.close()
        iterator.close()
        for store in reversed(stores):
            store.engine.dispose()
        remaining = [t for t in threading.enumerate() if t not in before_threads and t.is_alive()]
        if remaining:
            raise Boundary("owned fixture threads remain alive")
    diagnostic.update(
        mock_exchanges=mocks.exchanges,
        mock_methods=mocks.methods,
        source_delegates=mocks.source_sync,
        business_acceptance="INTERRUPTED",
        observer_overhead="NONZERO_NOT_COMPARABLE_TO_HISTORICAL_OBSERVER",
    )
    return diagnostic
