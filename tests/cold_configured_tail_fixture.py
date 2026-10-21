"""Original configured synthetic prefix, independently restored per tail case.

Only configured's existing three qualification substitutes are used. This is a
pytest fixture composition, not the protected real-clock launcher/child entry.
"""

import hashlib
import json
import shutil
from dataclasses import replace
from types import SimpleNamespace

import httpx
import test_natural_spec_apps as apps
from conftest import env
from test_pb_spec_production_controller import prepare_pb
from test_pb_trial_dispatch import approve_stage
from test_spec_production_controller import configured

from sim2act import natural_source_archives as archive
from sim2act import natural_specs as natural
from sim2act import pa_trial_dispatch as trial
from sim2act import pb_natural_specs as pb
from sim2act import pb_natural_uses as use
from sim2act._cold_accounted_budget import _Limits
from sim2act._cold_accounted_native import _NativeConfig
from sim2act._cold_accounted_values import _Bounds
from sim2act.api import create_app
from sim2act.config import Settings
from sim2act.db import Store, fingerprint


def config():
    bounds = _Bounds(nodes=60000, edges=120000, depth=128,
        leaf_bytes=8 * 1024**2, encoded_bytes=64 * 1024**2)
    upper = 8 * (2 * (bounds.nodes + bounds.edges + bounds.encoded_bytes) + 1) ** 4
    return _NativeConfig(bounds, _Limits(resident=512 * 1024**2,
        peak=1024**3, work=2 * upper, integer_bits=16000))


class MockCap:
    """One shared prefix and at most seven independent C1 cases; no retries."""

    def __init__(self, patch):
        self.exchange_limit, self.method_limit = 13, 15
        self.exchanges = self.methods = self.delegates = 0
        self.case_exchanges = self.case_methods = 0
        self.stage = 'prefix'
        sync = httpx.MockTransport.handle_request
        asynchronous = httpx.MockTransport.handle_async_request

        def handle(transport, request):
            assert self.stage == 'source' and self.delegates < 2
            self.delegates += 1
            self.enter(False)
            return sync(transport, request)

        async def handle_async(transport, request):
            self.enter(True)
            assert len(request.content) <= 32768
            result = await asynchronous(transport, request)
            assert len(result.content) <= 32768
            return result

        def denied(*args, **kwargs):
            raise AssertionError('Real HTTP is forbidden in configured semantic regression')

        patch.setattr(httpx.MockTransport, 'handle_request', handle)
        patch.setattr(httpx.MockTransport, 'handle_async_request', handle_async)
        patch.setattr(httpx.HTTPTransport, 'handle_request', denied)
        patch.setattr(httpx.AsyncHTTPTransport, 'handle_async_request', denied)

    def enter(self, exchange):
        assert self.methods < self.method_limit and self.exchanges < self.exchange_limit
        if self.stage == 'cold':
            assert exchange and self.case_exchanges < 1 and self.case_methods < 1
            self.case_exchanges += 1
            self.case_methods += 1
        self.methods += 1
        self.exchanges += int(exchange)

    def new_case(self):
        self.stage = 'cold'
        self.case_exchanges = self.case_methods = 0


def build_prefix(root, patch, clock, cap):
    root.mkdir()
    patch.delenv('SIM2ACT_TEST_DATABASE_URL', raising=False)
    patch.delenv('SIM2ACT_RECORD_PG_CONFIG', raising=False)
    iterator = env.__wrapped__(root)
    original = next(iterator)
    clients = [original[2]]
    fixture = None
    try:
        def prepared(env, out):
            value = prepare_pb(env, out)
            clients.append(value[0][2])
            return value

        data, binding, fixture, factory = configured(original, root, patch, prepare_case=prepared)
        clients.append(data[2])
        generation, _, release, instance, sent = apps.ready(data, style='ordered')
        assert len(sent) == cap.exchanges == 3
        cap.stage = 'source'
        source_id = apps.enqueue(data, release, instance, key=binding.contract.stage_keys.source)
        approve_stage(data, binding, 'source', source_id)
        normal = apps.transport([], apps.SOURCE)
        source_bytes = []

        def source_response(request):
            raw = normal.handle_request(request).json()
            raw['archive_note'] = '合成原始正文；非真实模型'
            payload = (json.dumps(raw, ensure_ascii=False, indent=2) + '\n').encode()
            source_bytes.append((request.content, payload))
            return httpx.Response(200, content=payload)

        assert factory(data[0], data[1], goal_planner_transport=httpx.MockTransport(source_response)).once()
        assert apps.inspect(data, instance, source_id).json()['status'] == 'SUCCEEDED'
        assert (cap.exchanges, cap.methods, cap.delegates) == (5, 7, 2)
        route = f'/api/projects/{data[4]}/natural-spec-task-runs/{source_id}'
        options = data[2].get(route + '/extraction-options')
        assert options.status_code == 200
        target = binding.contract.bindings[1]
        review = dict(source_run_id=source_id,
            expected_source_proof_fingerprint=options.json()['source_proof_fingerprint'],
            expected_source_recipe_fingerprint=options.json()['recipe_fingerprint'],
            card_id=target.card_id, expected_goal_version=target.goal_version,
            expected_goal_fingerprint=target.goal_fingerprint, expected_source_hash=target.source_hash,
            recipe=binding.contract.extraction_recipe.model_dump(exclude_none=True),
            name='P-B production-shaped fixture', request_key=binding.contract.extraction_request_key)
        preview = data[2].post(route + '/extraction-reviews', json=review)
        assert preview.status_code == 200
        body = pb.ExtractInput(review=review,
            expected_review_fingerprint=preview.json()['review_fingerprint'],
            consent=pb.CONSENT, artifact_write_consent=natural.CONSENT)

        def no_send(request):
            raise AssertionError('Extraction cannot send')

        extractor = factory(data[0], data[1], goal_planner_transport=httpx.MockTransport(no_send))
        made = trial.extract_pb(extractor, data[3], source_id, body)
        assert trial.extract_pb(extractor, data[3], source_id, body) == made
        resolved = archive.resolve_trial_source(data[0], data[3], binding.contract, binding.approval_key)
        assert list(zip(resolved.request_bodies, resolved.response_bodies, strict=True)) == source_bytes
        release, instance = apps.instance(data, made['id'])
        base = '/api/internal/instances/' + instance['id']
        current = data[2].get(base).json()
        app = data[2].get('/api/apps/' + made['id']).json()
        use_review = dict(expected_revision=current['revision'],
            expected_release_fingerprint=release['fingerprint'], expected_app_fingerprint=app['fingerprint'],
            expected_recipe_fingerprint=fingerprint(binding.contract.extraction_recipe.model_dump(exclude_none=True)),
            resource_id=target.resource_id, card_id=target.card_id,
            expected_goal_version=target.goal_version, expected_goal_fingerprint=target.goal_fingerprint,
            expected_source_hash=target.source_hash, request_key=binding.contract.stage_keys.cold)
        checked = data[2].post(base + '/pb-use-reviews', json=use_review)
        assert checked.status_code == 200
        request = dict(review=use_review, expected_review_fingerprint=checked.json()['review_fingerprint'], consent=use.CONSENT)
        queued = data[2].post(base + '/pb-use-runs', json=request)
        assert queued.status_code == 202
        cold_id = queued.json()['run_id']
        approve_stage(data, binding, 'cold', cold_id)
        template = SimpleNamespace(settings=data[1], identity=data[3:],
            contract=binding.contract.model_dump(), approval_key=binding.approval_key,
            account_id=binding.account_id, cold_id=cold_id, now=clock.now(),
            prefix_receipt=resolved.public_receipt, generation=generation, source_id=source_id)
        assert cap.exchanges == 5 and len(fixture['sends']) == 5
    finally:
        if fixture is not None:
            for worker in fixture['workers']:
                worker.stop.set()
        for client in reversed(clients):
            client.close()
        clock.assert_closed()
        try:
            next(iterator)  # env's original after-yield teardown is not finally.
        except StopIteration:
            pass
        else:
            raise AssertionError('Original env fixture yielded twice')
    clock.assert_closed()
    template.path = root / 'fixture.db'
    assert not any(root.glob('fixture.db-*')), 'Template must be cold-closed without WAL/journal'
    template.sha256 = hashlib.sha256(template.path.read_bytes()).hexdigest()
    return template


def restore_case(template, root, patch, clock):
    root.mkdir()
    clock.reset(template.now)
    assert hashlib.sha256(template.path.read_bytes()).hexdigest() == template.sha256
    path = root / 'fixture.db'
    shutil.copyfile(template.path, path)
    store = Store('sqlite:///' + str(path), test_only=True)
    settings = replace(template.settings, database_url=str(store.engine.url))
    from fastapi.testclient import TestClient

    client = TestClient(create_app(store, settings))
    client.headers['Authorization'] = 'Bearer synthetic-test-A'
    data = (store, settings, client, *template.identity)

    def restored(env, out):
        # New model, fixture closure, settings, Store, client, workers and stop
        # events; only immutable contract/DB template bytes are shared.
        from sim2act.natural_live_admission import PBTrialContract
        contract = PBTrialContract.model_validate(json.loads(json.dumps(template.contract)))
        return data, SimpleNamespace(contract=contract,
            approval_key=template.approval_key, account_id=template.account_id)

    data, binding, fixture, factory = configured(data, root, patch, prepare_case=restored)
    return SimpleNamespace(data=data, binding=binding, fixture=fixture, factory=factory,
        original_client=client, store=store, root=root)


def close_case(case, clock):
    for worker in case.fixture['workers']:
        worker.stop.set()
    case.data[2].close()
    case.original_client.close()
    clock.assert_closed()
    case.store.engine.dispose()


def load_prefix(manifest, clock, cap):
    """Explicit local test checkpoint, never a received/failed Cold database.

    The metadata freezes this suite's own cold-closed, still-QUEUED prefix. It
    preserves spent requests from the failed harness attempt in the global cap.
    Normal test runs do not use this optional checkpoint input.
    """
    from pathlib import Path

    data = json.loads(Path(manifest).read_text())
    assert data['classification'] == 'THIS_TEST_CONFIGURED_PREFIX_QUEUED_NO_COLD_ATTEMPTS'
    path = Path(data['path'])
    assert hashlib.sha256(path.read_bytes()).hexdigest() == data['sha256']
    assert not any(path.parent.glob(path.name + '-*'))
    settings = dict(data['settings'])
    settings['data_dir'] = Path(settings['data_dir'])
    data['settings'] = Settings(**settings)
    data['path'] = path
    cap.exchanges, cap.methods, cap.delegates = data.pop('prior_mock_counts')
    assert cap.exchanges <= 7 and cap.methods <= 9 and cap.delegates == 2
    cap.checkpoint_prior = cap.exchanges, cap.methods
    clock.reset(data['now'])
    return SimpleNamespace(**data)
