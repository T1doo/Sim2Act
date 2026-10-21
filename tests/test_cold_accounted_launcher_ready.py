"""Profile/metadata/local SQLite units only; no grant, prefix, Mock or G0."""

import copy
import hashlib
import json
from contextlib import contextmanager
from types import SimpleNamespace

import pytest
from test_cold_accounted_mock_wiring import ROOT, script
from test_cold_accounted_native import native_segment
from test_cold_accounted_sqlite import (
    forbid_execution as forbid_execution,
)
from test_cold_accounted_sqlite import (
    sql_facts as sql_facts,
)

from sim2act import _cold_accounted_native as native
from sim2act import cold_accounted as owned
from sim2act._cold_accounted_budget import _Limits
from sim2act.errors import DomainError


@pytest.fixture
def launcher(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / 'scripts/diagnostics'))
    return script('g0_bounded')


def description(launcher):
    profile = launcher.candidate_profile()
    return dict(scope=launcher.SCOPE + '-native-accounted-v1', candidate_profile=profile,
                candidate_profile_sha256=hashlib.sha256(launcher.canonical(profile).encode()).hexdigest())


def test_profile_derives_joint_work_and_strictly_binds_all_config(launcher):
    d = description(launcher)
    p, b = d['candidate_profile'], d['candidate_profile']['bounds']
    upper = 8 * (2 * b['nodes'] + 2 * b['edges'] + 2 * b['encoded_bytes'] + 1) ** 4
    assert p['work_derivation']['classify_upper'] == upper
    assert p['limits']['work'] == 2 * upper and p['limits']['integer_bits'] == 16000
    config = launcher.candidate_config(d)
    assert config.limits.work == 2 * upper
    assert config.limits.resident == 512 * 1024**2 and config.limits.peak == 1024**3
    assert launcher.candidate_config({'scope': launcher.SCOPE}) is None
    # In-memory schema samples only, never an execution grant/file.
    grant = dict(d, expires_at=2, grant_id='unit-profile-only')
    launcher.validate_grant(grant, d, 1)
    for value in (True, 10**10, 10**40):
        bad = copy.deepcopy(d)
        bad['candidate_profile']['limits']['work'] = value
        with pytest.raises(launcher.Boundary):
            launcher.candidate_config(bad)
        with pytest.raises(launcher.Boundary):
            launcher.validate_grant(dict(grant, candidate_profile=bad['candidate_profile']), d, 1)
    with pytest.raises(launcher.Boundary):
        launcher.candidate_config(dict(d, candidate_profile=None))
    with pytest.raises(launcher.Boundary):
        launcher.canonical(float('nan'))


def test_required_capability_failure_and_cli_remain_pre_execution(launcher, monkeypatch, capsys):
    assert launcher.protection_profile()['native_vfs_required'] is False
    with monkeypatch.context() as m:
        m.setattr(launcher.sys, 'addaudithook', None)
        with pytest.raises(launcher.Boundary, match='protections unavailable'):
            launcher.protection_profile()
    calls = []
    monkeypatch.setattr(launcher, 'describe', lambda **kw: calls.append(kw) or {'unit_only': True})
    monkeypatch.setattr(launcher, 'execute', lambda *a, **kw: pytest.fail('not authorized'))
    monkeypatch.setattr(launcher.sys, 'argv', ['g0_bounded.py', '--describe', '--candidate'])
    assert launcher.main() == 0 and calls == [{'candidate': True}]
    assert json.loads(capsys.readouterr().out) == {'unit_only': True}
    monkeypatch.setattr(launcher.sys, 'argv', ['g0_bounded.py', '--candidate'])
    with pytest.raises(SystemExit) as error:
        launcher.main()
    assert error.value.code == 2


@pytest.mark.parametrize('legacy', [False, True])
def test_real_local_selection_budget_reason_survives_scope_close(sql_facts, launcher, legacy):
    f = sql_facts
    limits = _Limits(**launcher.candidate_profile()['limits'])
    if legacy:
        limits = limits._replace(resident=1)
    with f.store.tx() as c, native_segment(f, c, limits=limits) as s:
        candidate = s.candidate
        report = candidate.selection_record()
        assert report['route'] == ('LEGACY' if legacy else 'OWNED')
        assert report['budget']['peak'] <= limits.peak
        assert report['budget']['work'] <= limits.work
        if legacy:
            assert report['reason'] == 'resident' and report['phase'] == 'capture:scaffolding'
            assert report['after_scope']['active'] is False
        else:
            assert report['reason'] is None and report['phase'] == 'native:issuance'
            assert report['budget']['resident'] > 0
    closed = candidate.selection_record()['after_scope']
    assert closed['active'] is False and closed['live'] == closed['resident'] == 0


@pytest.mark.parametrize('route', ['OWNED', 'LEGACY'])
def test_scalar_trace_requires_two_original_returns_and_full_context_exit(launcher, route):
    prefix = script('g0_prefix')
    observation = prefix.CandidateObservation()
    trial = SimpleNamespace(authority_record=None, authority_record_key=None,
        accounted_candidate=SimpleNamespace(selection_record=lambda: dict(route=route,
            phase='local-only', reason=None, budget={}, after_scope=dict(active=False, live=0, resident=0))))

    @contextmanager
    def context():
        yield trial

    def commit(current, boundary):
        current.authority_record = {'deadlines': (123.0, 456.0)}
        current.authority_record_key = boundary.key + ':trial-output'
        return current

    observed = observation.wrap_commit(commit)
    with observation.context(context) as current:
        for key in ('commit:first', 'commit:second'):
            assert observed(current, SimpleNamespace(key=key)) is current
        assert observation.report()['final_deadline_check'] == 'NOT_PROVEN'
    diagnostic = {'classification': 'G0_COMPLETED_NO_W5'}
    prefix.record_candidate(diagnostic, observation)
    expected = 'G0_COMPLETED_NO_W5' if route == 'OWNED' else 'G0_COMPLETED_LEGACY_NO_W5'
    assert diagnostic['classification'] == expected
    summary = json.loads(json.dumps(diagnostic['candidate']))
    assert launcher.candidate_completion(summary, expected)
    for field in ('complete', 'trace_valid', 'both_commits_returned', 'original_scope_returned'):
        assert not launcher.candidate_completion(dict(summary, **{field: False}), expected)
    damaged = copy.deepcopy(summary)
    damaged['commits'][0]['returned'] = False
    assert not launcher.candidate_completion(damaged, expected)
    assert not launcher.candidate_completion(summary, 'UNKNOWN')


def test_original_context_exit_error_keeps_failure_and_cannot_complete(launcher):
    prefix = script('g0_prefix')
    observation = prefix.CandidateObservation()
    trial = SimpleNamespace(accounted_candidate=None)
    error = DomainError('VERSION_CONFLICT', 'local original final deadline')

    @contextmanager
    def context():
        yield trial
        raise error

    with pytest.raises(DomainError) as caught:
        with observation.context(context):
            pass
    assert caught.value is error
    diagnostic = {'classification': 'UNKNOWN'}
    prefix.record_candidate(diagnostic, observation)
    assert diagnostic['classification'] == 'UNKNOWN'
    assert diagnostic['candidate']['original_scope_returned'] is False
    assert diagnostic['candidate']['final_deadlines'] is None


@pytest.mark.parametrize('legacy', [False, True])
def test_budget_observation_failure_cannot_change_selection_or_cleanup(sql_facts, launcher, monkeypatch, legacy):
    def broken(*args):
        raise RuntimeError('local diagnostic fault')
    monkeypatch.setattr(native._NativeCandidate, 'budget_record', broken)
    limits = _Limits(**launcher.candidate_profile()['limits'])
    if legacy:
        limits = limits._replace(resident=1)
    with sql_facts.store.tx() as c, native_segment(sql_facts, c, limits=limits) as s:
        assert s.cohort.route == ('LEGACY' if legacy else 'OWNED')
        candidate = s.candidate
        assert candidate.selection_record()['diagnostic_incomplete'] is True
    assert not candidate.diagnostic_ledger.active
    assert candidate.diagnostic_ledger.live == candidate.diagnostic_ledger.resident == 0


def test_error_observation_fault_keeps_exact_original_error_and_cleanup(sql_facts, launcher, monkeypatch):
    captured = {}
    error = DomainError('VERSION_CONFLICT', 'local original rejection')
    def reject(mode, budget, completed, *, native):
        captured['candidate'] = native
        raise error
    def broken(*args):
        raise RuntimeError('local diagnostic fault')
    monkeypatch.setattr(native._NativeCandidate, 'budget_record', broken)
    monkeypatch.setattr(owned._OwnedPrewriteMode, '_select_completed', reject)
    with pytest.raises(DomainError) as caught, sql_facts.store.tx() as c:
        with native_segment(sql_facts, c, limits=_Limits(**launcher.candidate_profile()['limits'])):
            pytest.fail('original rejection yielded')
    assert caught.value is error
    candidate = captured['candidate']
    assert not candidate.diagnostic_ledger.active
    assert candidate.diagnostic_ledger.live == candidate.diagnostic_ledger.resident == 0


def test_commit_observation_fault_never_replaces_original_return_or_error(launcher):
    prefix = script('g0_prefix')
    observation = prefix.CandidateObservation()
    class Trial:
        accounted_candidate = None
        @property
        def authority_record(self):
            raise RuntimeError('local output-read diagnostic fault')
    trial = Trial()
    observation.trial = trial
    result = object()
    assert observation.wrap_commit(lambda *args: result)(trial, SimpleNamespace(key='commit:first')) is result
    assert not observation.valid
    error = DomainError('VERSION_CONFLICT', 'local original body rejection')
    class BrokenList(list):
        def append(self, value):
            raise RuntimeError('local recording fault')
    observation.commits = BrokenList()
    def reject(*args):
        raise error
    with pytest.raises(DomainError) as caught:
        observation.wrap_commit(reject)(trial, SimpleNamespace(key='commit:first'))
    assert caught.value is error
    diagnostic = {'classification': 'G0_COMPLETED_NO_W5'}
    prefix.record_candidate(diagnostic, observation)
    assert diagnostic['classification'] == 'UNKNOWN'
