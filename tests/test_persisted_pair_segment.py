"""Private pair arithmetic keeps original errors and a late complete boundary."""

import pytest
from test_cold_extract_parse import local_origin as local_origin
from test_cold_extract_parse import no_external_transport as no_external_transport

from sim2act import _cold_policy_segment as segment
from sim2act import pa_spec_apps as spec
from sim2act import pb_natural_specs as pb
from sim2act.db import fingerprint
from sim2act.errors import DomainError
from sim2act.text_logic_reuse import require


def rows(request=None):
    if request is None:
        request = dict(
            app_id="a",
            principal_id="u",
            project_id="p",
            runtime_id="r",
            resource_id="material",
            source_run_id="source",
        )
    value = dict(request=request, response={"retained": ["original"]})
    return [
        dict(
            snapshot=value, fingerprint=fingerprint(value), request_fingerprint=fingerprint(request)
        )
        for _ in range(2)
    ]


def read(values, pin=lambda: None):
    return segment._persisted_pair_value(
        values, spec.Metadata, spec._persisted_snapshot_finite, require, pin=pin
    )


def test_same_original_parser_and_private_response_late_pin():
    source = rows()
    pins = []
    body, response = read(source, lambda: pins.append("late"))
    assert (
        body.model_dump()
        == spec._persisted_scope_metadata(source[0]["snapshot"]["request"]).model_dump()
    )
    assert pins == ["late"]
    response["retained"].append("private change")
    assert source[0]["snapshot"]["response"]["retained"] == ["original"]


def test_fixed_malformed_parser_has_original_error_mapping():
    request = rows()[0]["snapshot"]["request"]
    del request["resource_id"]
    with pytest.raises(DomainError) as old:
        spec._persisted_scope_metadata(request)
    with pytest.raises(DomainError) as fast:
        read(rows(request))
    assert fast.value.public() == old.value.public()


def test_late_boundary_rejects_before_any_result_is_published():
    sentinel = DomainError("VERSION_CONFLICT", "complete graph changed")

    def pin():
        raise sentinel

    with pytest.raises(DomainError) as caught:
        read(rows(), pin)
    assert caught.value is sentinel


def test_unknown_serializer_falls_back_without_callback(monkeypatch):
    calls = []
    monkeypatch.setattr(spec.Metadata, "model_dump", lambda *a, **kw: calls.append(1))
    assert read(rows()) is segment._UNSUITABLE
    assert calls == []


def test_changed_module_fingerprint_keeps_original_path(monkeypatch):
    monkeypatch.setattr(spec, "fingerprint", lambda value: "changed")
    assert not spec._scope_pair_code_current()
    monkeypatch.setattr(pb, "fingerprint", lambda value: "changed")
    assert pb.fingerprint is not pb._PAIR_FINGERPRINT_FUNCTION


def test_unknown_graph_copy_module_falls_back(monkeypatch):
    from types import SimpleNamespace

    monkeypatch.setattr(segment._pair_graph, "copy", SimpleNamespace(deepcopy=lambda value: value))
    assert read(rows()) is segment._UNSUITABLE


def test_real_sqlite_pair_uses_two_sql_pins_and_late_full_pin(local_origin, monkeypatch):
    from sqlalchemy import event, insert
    from test_cold_release_stages import read_scope

    from sim2act import natural_spec_runtime as runtime
    from sim2act.db import delivery_graph_requests, new_id

    f = local_origin
    entity = new_id("app")
    request = rows()[0]["snapshot"]["request"]
    saved = dict(request=request, response={"retained": ["original"]})
    with f.store.tx() as c:
        for kind in (spec.META, spec.META + "_seal"):
            c.execute(
                insert(delivery_graph_requests).values(
                    app_id=entity,
                    principal_id=f.user,
                    kind=kind,
                    request_key="scope",
                    request_fingerprint=fingerprint(request),
                    snapshot=saved,
                    fingerprint=fingerprint(saved),
                )
            )
    original = segment._persisted_pair_value
    encode = runtime._cold_graph_bytes
    counts = []
    reports = []

    def counted(value):
        counts.append(1)
        return encode(value)

    monkeypatch.setattr(runtime, "_cold_graph_bytes", counted)
    for fast in (False, True):
        monkeypatch.setattr(
            segment,
            "_persisted_pair_value",
            original if fast else lambda *a, **kw: segment._UNSUITABLE,
        )
        queries = []

        def sql(*args, queries=queries):
            queries.append(1)

        with f.store.tx() as c, pb._source_reads(f.store, c), read_scope(f, c) as guard:
            event.listen(c, "before_cursor_execute", sql)
            start = len(counts)
            result = spec._cold_scope_pair(f.store, c, f.user, entity, guard)
            reports.append((len(counts) - start, len(queries), result[0].model_dump(), result[1]))
            event.remove(c, "before_cursor_execute", sql)
    assert reports[0][1:] == reports[1][1:]
    assert reports[0][0] == 10 and reports[1][0] == 4
