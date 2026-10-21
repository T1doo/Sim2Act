"""Exact finite composition of existing synthetic fixture helpers.

No work occurs at import. Called only by the bounded, explicitly granted child.
Never call the original full PB test or its damaged-copy matrix here.
"""


class CandidateObservation:
    """Target-local scalar evidence; never validation, authority or a replay."""

    def __init__(self):
        self.trial = None
        self.commits = []
        self.scope_returned = False
        self.valid = True

    def context(self, original, *args, **kwargs):
        from contextlib import contextmanager

        @contextmanager
        def observe():
            with original(*args, **kwargs) as trial:
                try:
                    self.trial = trial
                except Exception:
                    self.valid = False
                yield trial
            # Set only after the ORIGINAL context's final hash and stop/clock.
            self.scope_returned = True
        return observe()

    def wrap_commit(self, original):
        def observed(trial, prefix):
            if trial is not self.trial:
                return original(trial, prefix)
            record = None
            try:
                if len(self.commits) >= 2:
                    self.valid = False
                else:
                    record = dict(ordinal=len(self.commits) + 1, returned=False, deadlines=None)
                    self.commits.append(record)
            except Exception:
                self.valid = False
            try:
                result = original(trial, prefix)
            except BaseException as error:
                try:
                    if record is not None:
                        record['error_type'] = type(error).__name__
                except Exception:
                    self.valid = False
                raise
            else:
                try:
                    import math

                    if record is None:
                        self.valid = False
                        return result
                    record['returned'] = True
                    expected = ('commit:first', 'commit:second')[record['ordinal'] - 1]
                    # Read only the successful original output, never rerun a check.
                    output = trial.authority_record
                    deadlines = output.get('deadlines') if type(output) is dict else None
                    if (prefix.key != expected or trial.authority_record_key != expected + ':trial-output'
                            or type(deadlines) is not tuple or not deadlines
                            or not all(type(v) in (int, float) and math.isfinite(v) and v > 0 for v in deadlines)):
                        self.valid = False
                    else:
                        record['deadlines'] = tuple(deadlines)
                except Exception:
                    self.valid = False
                return result
        return observed

    def report(self):
        try:
            return self._report()
        except Exception:
            self.valid = False
            return dict(selection=dict(route='UNKNOWN', phase='UNKNOWN', diagnostic_incomplete=True),
                        commits=(), complete=False, diagnostic_incomplete=True,
                        trace_valid=False, original_scope_returned=False,
                        both_commits_returned=False, final_deadlines=None,
                        final_deadline_check='NOT_PROVEN')

    def _report(self):
        selection = dict(route='NOT_REACHED', phase='NOT_REACHED', reason=None, budget=None)
        if self.trial is not None and self.trial.accounted_candidate is not None:
            selection = self.trial.accounted_candidate.selection_record()
        incomplete = selection.get('diagnostic_incomplete', False)
        complete = (self.valid and not incomplete and self.scope_returned and len(self.commits) == 2
                    and all(r['returned'] and r['deadlines'] for r in self.commits))
        return dict(selection=selection, commits=tuple(dict(r) for r in self.commits),
                    original_scope_returned=self.scope_returned, trace_valid=self.valid,
                    diagnostic_incomplete=not self.valid or incomplete,
                    both_commits_returned=len(self.commits) == 2 and all(r['returned'] for r in self.commits),
                    complete=bool(complete),
                    deadline_basis='successful_original_authority_record_deadlines',
                    final_deadlines=self.commits[-1]['deadlines'] if complete else None,
                    final_deadline_check='PASSED_BY_ORIGINAL_CONTEXT_RETURN' if complete else 'NOT_PROVEN')


def record_candidate(diagnostic, observation):
    try:
        report = observation.report()
        diagnostic['candidate'] = report
        if diagnostic['classification'] == 'G0_COMPLETED_NO_W5':
            route = report['selection']['route']
            if not report['complete'] or route not in ('OWNED', 'LEGACY'):
                diagnostic['classification'] = 'UNKNOWN'
            elif route == 'LEGACY':
                diagnostic['classification'] = 'G0_COMPLETED_LEGACY_NO_W5'
    except Exception as error:
        diagnostic['classification'] = 'UNKNOWN'
        diagnostic['candidate'] = dict(diagnostic_incomplete=True, error_type=type(error).__name__)


def _mock_accounted_context(original, config, observation=None):
    """Explicit test selection only; not account evidence or a run grant."""
    if config is None:
        return original
    from functools import partial

    from sim2act._cold_accounted_native import _NativeConfig

    if type(config) is not _NativeConfig:
        raise ValueError('Exact explicit Mock accounted config required')
    if observation is not None:
        return partial(observation.context, original, _mock_accounted_config=config)
    return partial(original, _mock_accounted_config=config)


def run_prefix(root, patch, files, notify, healthy, *, _mock_accounted_config=None):
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
        exception_chain,
        install_mock_counter,
        install_network_denials,
    )
    from g0_stage_observer import StageObserver
    from test_pb_spec_production_controller import prepare_pb
    from test_pb_trial_dispatch import approve_stage
    from test_spec_production_controller import configured

    from sim2act import model
    from sim2act import natural_live_admission as gate
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
    # Default launcher supplies None. An explicit future diagnostic must bind
    # its finite config/mode in a new reviewed grant; this option is no grant.
    original_context = runtime._cold_model_before
    observation = None if _mock_accounted_config is None else CandidateObservation()
    selected_context = (None if _mock_accounted_config is None else
                        _mock_accounted_context(original_context, _mock_accounted_config, observation))
    if observation is not None:
        patch.setattr(runtime._ColdTrialGraph, 'commit', observation.wrap_commit(runtime._ColdTrialGraph.commit))
    patch.setattr(
        runtime, "_cold_model_before", lambda *args: boundary.wrap(
            original_context, *args, _target_context=selected_context)
    )
    patch.setattr(
        runtime._ColdCommitDiagnostics,
        "__init__",
        boundary.observe_init(runtime._ColdCommitDiagnostics.__init__),
    )
    observer = StageObserver()
    observer.install(
        patch, runtime, gate,
        lambda instance: boundary.entered and instance is boundary.instance,
    )
    iterator = env.__wrapped__(root)
    fixture = None
    diagnostic = {"classification": "UNKNOWN", "g0": "NOT_REACHED"}

    def phase(name):
        import time

        notify(
            dict(
                event="phase",
                phase=name,
                at=time.monotonic(),
                mock_exchanges=mocks.exchanges,
                mock_methods=mocks.methods,
            )
        )

    try:
        phase("fixture_start")
        original_env = next(iterator)
        stores.append(original_env[0])
        data, binding, fixture, factory = configured(
            original_env, root, patch, prepare_case=prepare_pb
        )
        normal = apps.transport([], apps.SOURCE)
        install_mock_counter(patch, httpx, mocks, fixture, normal)
        generation, _, release, source_instance, generated = apps.ready(data, style="ordered")
        phase("generate_complete")
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
        phase("source_returned")
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
        phase("extraction_release_complete")
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
        phase("cold_first_worker_start")
        try:
            worker.once()
        except G0Stop as stop:
            diagnostic = boundary.diagnostic(stop)
            diagnostic["stage_observer"] = observer.report()
            if observation is not None:
                record_candidate(diagnostic, observation)
            # Preserve the original refusal before any client/heartbeat cleanup
            # can independently fail; never truncate or overwrite this record.
            files.writer("diagnostic.json").json(
                {"event": "g0_outcome_before_cleanup", **diagnostic}
            )
        else:
            raise Boundary("Cold returned without exact G0 stop")
    except BaseException as error:
        partial = (
            "NOT_REACHED"
            if boundary.instance is None
            else dict(
                stages=boundary.instance.stages,
                run_context=boundary.instance.run_context,
                incomplete=boundary.instance.incomplete,
            )
        )
        failed = dict(
                event="failure_before_cleanup",
                classification="UNKNOWN",
                error_chain=exception_chain(error),
                partial=partial,
                g0_entered=boundary.entered,
                mock_exchanges=mocks.exchanges,
                mock_methods=mocks.methods,
                stage_observer=observer.report(),
            )
        if observation is not None:
            failed['candidate'] = observation.report()
        files.writer("diagnostic.json").json(failed)
        raise
    finally:
        if fixture is not None:
            for worker in fixture["workers"]:
                worker.stop.set()
        cleanup_errors = []
        for close in [
            *(client.close for client in reversed(clients)),
            iterator.close,
            *(store.engine.dispose for store in reversed(stores)),
        ]:
            try:
                close()
            except BaseException as error:
                cleanup_errors.append(error)
        remaining = [t for t in threading.enumerate() if t not in before_threads and t.is_alive()]
        if remaining:
            cleanup_errors.append(Boundary("owned fixture threads remain alive"))
        if cleanup_errors:
            files.writer("diagnostic.json").json(
                dict(
                    event="cleanup_errors",
                    classification="UNKNOWN",
                    errors=[exception_chain(error) for error in cleanup_errors],
                )
            )
            raise Boundary("fixture cleanup incomplete") from cleanup_errors[0]
    diagnostic.update(
        mock_exchanges=mocks.exchanges,
        mock_methods=mocks.methods,
        source_delegates=mocks.source_sync,
        business_acceptance="INTERRUPTED",
        observer_overhead="NONZERO_NOT_COMPARABLE_TO_HISTORICAL_OBSERVER",
    )
    return diagnostic
