"""Fixed persisted Metadata error ownership; no model/worker execution."""

import copy
import math

import pytest
from sqlalchemy import insert, select, update
from test_cold_extract_parse import local_origin as local_origin
from test_cold_extract_parse import malformed_extract as malformed_extract
from test_cold_extract_parse import no_external_transport as no_external_transport
from test_cold_release_stages import read_scope

from sim2act import delivery_graph_apps as graph
from sim2act import pa_spec_apps as spec
from sim2act import pb_natural_specs as pb
from sim2act import pb_natural_uses as use
from sim2act.db import delivery_graph_requests, fingerprint, new_id, task_extractions
from sim2act.errors import DomainError


@pytest.fixture
def malformed_metadata(malformed_extract):
    f = malformed_extract
    with f.store.tx() as c:
        stored = c.execute(select(delivery_graph_requests).where(
            delivery_graph_requests.c.app_id == f.draft["id"],
            delivery_graph_requests.c.kind == pb.EXTRACT)).mappings().one()
        request = copy.deepcopy(stored["snapshot"]["request"])
        request["expected_review_fingerprint"] = "b" * 64
        pb.ExtractInput.model_validate(request)
        snapshot = dict(request=request, response={})
        c.execute(update(delivery_graph_requests).where(
            delivery_graph_requests.c.app_id == f.draft["id"],
            delivery_graph_requests.c.kind.in_((pb.EXTRACT, pb.EXTRACT + "_seal"))).values(
                request_fingerprint=fingerprint(request), snapshot=snapshot,
                fingerprint=fingerprint(snapshot)))
        c.execute(update(task_extractions).where(task_extractions.c.app_id == f.draft["id"])
            .values(request_fingerprint=fingerprint(request)))
        metadata = dict(app_id=f.draft["id"], principal_id=f.user,
            project_id=f.draft["project_id"], runtime_id=f.draft["runtime_id"],
            resource_id=f.origin[2]["resource_id"], source_run_id=request["review"]["source_run_id"])
        pb.Metadata.model_validate(metadata)
        del metadata["resource_id"]
        snapshot = dict(request=metadata, response={})
        for kind in (pb.META, pb.META + "_seal"):
            c.execute(insert(delivery_graph_requests).values(app_id=f.draft["id"],
                principal_id=f.user, kind=kind, request_key="scope",
                request_fingerprint=fingerprint(metadata), snapshot=snapshot,
                fingerprint=fingerprint(snapshot)))
    return f


def test_owned_malformed_metadata_pair_matches_old_public_error(malformed_metadata, monkeypatch):
    f, parsed = malformed_metadata, []
    parser = pb._persisted_pair_input

    def owned_parser(expected, value):
        parsed.append(expected)
        return parser(expected, value)

    monkeypatch.setattr(pb, "_persisted_pair_input", owned_parser)
    with f.store.tx() as c:
        with pytest.raises(DomainError) as old:
            pb.verify(f.store, c, f.user, f.draft, f.limits)
    with f.store.tx() as c, pb._source_reads(f.store, c):
        with pytest.raises(DomainError) as strict:
            with read_scope(f, c) as guard:
                pb._cold_verify_prefix(f.store, c, f.user, f.draft, f.limits, guard, "cold")
        assert not guard.active
    assert strict.value.public() == old.value.public()
    assert strict.value.code == "VERSION_CONFLICT"
    assert strict.value.message == "Malformed persisted DeliveryGraph binding"
    assert parsed == [pb.ExtractInput, pb.Metadata]


def test_external_checked_valueerror_keeps_identity_before_metadata_parser(
        malformed_metadata, monkeypatch):
    f, parsed, checked_kinds = malformed_metadata, [], []
    checked, parser = graph.checked, pb._persisted_pair_input
    original = ValueError("synthetic external checked callback")

    def external_checked(row):
        checked_kinds.append(row["kind"])
        if row["kind"] == pb.META:
            raise original
        return checked(row)

    def owned_parser(expected, value):
        parsed.append(expected)
        return parser(expected, value)

    monkeypatch.setattr(graph, "checked", external_checked)
    monkeypatch.setattr(pb, "_persisted_pair_input", owned_parser)
    with f.store.tx() as c, pb._source_reads(f.store, c):
        with pytest.raises(ValueError) as caught:
            with read_scope(f, c) as guard:
                pb._cold_verify_prefix(f.store, c, f.user, f.draft, f.limits, guard, "cold")
        assert not guard.active
    assert caught.value is original
    assert checked_kinds == [pb.EXTRACT, pb.EXTRACT + "_seal", pb.META]
    assert parsed == [pb.ExtractInput]


@pytest.mark.parametrize('nonfinite', [float('nan'), float('inf')],
    ids=['nested-nan', 'nested-inf'])
def test_owned_nested_nonfinite_snapshot_matches_old_error_in_three_collectors(
        local_origin, monkeypatch, nonfinite):
    """Actual SQLite corruption; no full scope/trial proof or model is produced."""
    f = local_origin
    assert f.store.test_only and f.store.sqlite
    rid = new_id('run')
    request = spec.RunScopeInput(app_id=f.draft['id'], principal_id=f.user,
        project_id=f.draft['project_id'], runtime_id=f.draft['runtime_id'],
        resource_id=f.origin[2]['resource_id'], run_id=rid,
        instance_id=new_id('instance'), app_run_id=new_id('apprun'),
        release_id=new_id('release')).model_dump()
    finite = dict(request=request, response=dict(audit=dict(values=[0.0])))
    corrupted = copy.deepcopy(finite)
    corrupted['response']['audit']['values'][0] = nonfinite
    with f.store.tx() as c:
        for kind in (spec.RUN_META, spec.RUN_META + '_seal'):
            c.execute(insert(delivery_graph_requests).values(app_id=rid,
                principal_id=f.user, kind=kind, request_key='accepted',
                request_fingerprint=fingerprint(request), snapshot=finite,
                fingerprint=fingerprint(finite)))
        # Keep the finite original seal hash. An invalid canonical JSON value
        # cannot have a new allow_nan=False fingerprint; it is corruption.
        c.execute(update(delivery_graph_requests).where(
            delivery_graph_requests.c.app_id == rid,
            delivery_graph_requests.c.kind.in_((spec.RUN_META, spec.RUN_META + '_seal')))
            .values(snapshot=corrupted))
    with f.store.tx() as c:
        saved = c.execute(select(delivery_graph_requests.c.snapshot).where(
            delivery_graph_requests.c.app_id == rid,
            delivery_graph_requests.c.kind == spec.RUN_META)).scalar_one()
        actual = saved['response']['audit']['values'][0]
        assert type(actual) is float and not math.isfinite(actual)
        old_pair = graph.controlled(spec.pair)
        with pytest.raises(DomainError) as old:
            old_pair(c, f.user, rid, spec.RUN_META, 'accepted', spec.RunScopeInput)
    original_finite = spec._persisted_snapshot_finite
    seen, checked = [], []

    def finite_leaf(snapshot):
        assert type(snapshot) is dict
        assert not math.isfinite(snapshot['response']['audit']['values'][0])
        seen.append(snapshot)
        return original_finite(snapshot)

    def forbidden_checked(row):
        checked.append(row)
        pytest.fail('Known nonfinite JSON reached the unmapped checked callback')

    monkeypatch.setattr(spec, '_persisted_snapshot_finite', finite_leaf)
    monkeypatch.setattr(graph, 'checked', forbidden_checked)

    def scope_pair(c, guard):
        return spec._cold_scope_pair(f.store, c, f.user, rid, guard, run_scope=True)

    def pb_pair(c, guard):
        return pb._cold_persisted_pair(f.store, c, f.user, rid, spec.RUN_META,
            'accepted', spec.RunScopeInput, guard)

    def use_pair(c, guard):
        return use._use_pair(c, f.user, rid, spec.RUN_META, 'accepted',
            spec.RunScopeInput, _graph_read=guard)

    for reader in (scope_pair, pb_pair, use_pair):
        with f.store.tx() as c, pb._source_reads(f.store, c):
            with pytest.raises(DomainError) as strict:
                with read_scope(f, c) as guard:
                    try:
                        reader(c, guard)
                    except DomainError:
                        assert not guard.active
                        raise
        assert strict.value.public() == old.value.public()
        assert strict.value.code == 'VERSION_CONFLICT'
        assert strict.value.message == 'Malformed persisted DeliveryGraph binding'
    assert len(seen) == 3 and checked == []


def test_owned_unpaired_surrogate_matches_original_canonical_error():
    snapshot = {'request': {}, 'response': {'audit': ['\ud800']}}

    @graph.controlled
    def original_checked():
        return fingerprint(snapshot)

    with pytest.raises(DomainError) as old:
        original_checked()
    with pytest.raises(DomainError) as strict:
        spec._persisted_snapshot_finite(snapshot)
    assert strict.value.public() == old.value.public()
    assert strict.value.message == 'Malformed persisted DeliveryGraph binding'
