from pathlib import Path
import difflib

out=Path('/tmp/csv-full-report-negative-sql-observer-20261017')
source=Path('/tmp/test_csv_full_report_instances_negative.py')
text=source.read_text()
text=text.replace('from sqlalchemy import event, select, update', 'from sqlalchemy import event, func, select, update', 1)
marker='@pytest.mark.parametrize("target", ["source-csv", "source-md", "runtime-save"])\n'
helper='''# Exact existing family discovery SELECT, not a broad journal exemption.
_EMPTY_PA_PROBE_SQL = (
    "select delivery_graph_requests.app_id, delivery_graph_requests.principal_id, "
    "delivery_graph_requests.kind, delivery_graph_requests.request_key, "
    "delivery_graph_requests.request_fingerprint, delivery_graph_requests.snapshot, "
    "delivery_graph_requests.fingerprint from delivery_graph_requests where "
    "delivery_graph_requests.app_id = ? and delivery_graph_requests.principal_id = ? and "
    "delivery_graph_requests.kind = ? and delivery_graph_requests.request_key = ?"
)


def _count_exact_empty_pa_probes(store, user, run_ids):
    counts = {}
    with store.tx() as connection:
        for run_id in sorted(set(run_ids)):
            for kind in ("pa_spec_run_scope", "pa_spec_run_scope_seal"):
                identity = (run_id, user, kind, "accepted")
                count = connection.execute(select(func.count()).select_from(delivery_graph_requests).where(
                    delivery_graph_requests.c.app_id == run_id,
                    delivery_graph_requests.c.principal_id == user,
                    delivery_graph_requests.c.kind == kind,
                    delivery_graph_requests.c.request_key == "accepted")).scalar_one()
                assert count == 0, ("PA discovery exemption requires an independently empty exact identity", identity, count)
                counts[identity] = count
    return counts


def _probe_counts_json(counts):
    return [dict(run_id=key[0], principal_id=key[1], kind=key[2], request_key=key[3], existing_rows=value)
            for key, value in sorted(counts.items())]


def _known_empty_pa_probe(statement, parameters, empty_probes, executemany):
    if executemany or not isinstance(parameters, (tuple, list)) or len(parameters) != 4:
        return False
    if not all(type(value) is str for value in parameters):
        return False
    identity = tuple(parameters)
    if identity not in empty_probes or empty_probes[identity] != 0:
        return False
    sql = re.sub(r'["`\\[\\]]', "", statement).lower()
    sql = re.sub(r"\\s+", " ", sql).strip()
    return sql == _EMPTY_PA_PROBE_SQL


'''
assert text.count(marker)==1
text=text.replace(marker,helper+marker,1)
old='''    selected = []

    def observe(connection, cursor, statement, parameters, context, executemany):
        if _private_body(statement):
            selected.append({"sql": statement, "parameters": repr(parameters)})

    _readonly(env, "GET", "/api/runs/" + rid, {200}, evidence, "positive_private_read", sql=observe)
    evidence["positive_sql_control"] = list(selected)
    assert selected, "positive SQL control must see a protected full body"
    selected.clear()
'''
new='''    selected, empty_discoveries = [], []
    probe_runs = {rid, original["id"]}
    empty_probes = _count_exact_empty_pa_probes(env[0], env[3], probe_runs)
    evidence["exact_empty_pa_family_probe_precounts"] = _probe_counts_json(empty_probes)

    def observe(connection, cursor, statement, parameters, context, executemany):
        if _private_body(statement):
            item = {"sql": statement, "parameters": repr(parameters)}
            if _known_empty_pa_probe(statement, parameters, empty_probes, executemany):
                empty_discoveries.append({**item, "independent_exact_row_count": 0})
            else:
                selected.append(item)

    _readonly(env, "GET", "/api/runs/" + rid, {200}, evidence, "positive_private_read", sql=observe)
    evidence["positive_sql_control"] = list(selected)
    evidence["positive_exact_empty_pa_family_discoveries"] = list(empty_discoveries)
    assert selected, "positive control must see a real protected full body after exact empty probes are excluded"
    selected.clear()
    empty_discoveries.clear()
'''
assert text.count(old)==1
text=text.replace(old,new,1)
old='''    evidence["denied_private_body_reads"] = list(selected)
    assert selected == [], selected
'''
new='''    evidence["denied_private_body_reads"] = list(selected)
    evidence["denied_exact_empty_pa_family_discoveries"] = list(empty_discoveries)
    final_probe_counts = _count_exact_empty_pa_probes(env[0], env[3], probe_runs)
    evidence["exact_empty_pa_family_probe_postcounts"] = _probe_counts_json(final_probe_counts)
    assert final_probe_counts == empty_probes
    assert selected == [], selected
'''
assert text.count(old)==1
text=text.replace(old,new,1)
target=out/'test_csv_full_report_instances_negative_sqlbarrier.py'
target.write_text(text)
patch=''.join(difflib.unified_diff(source.read_text().splitlines(True),text.splitlines(True),fromfile='a/tests/test_csv_full_report_instances_negative.py',tofile='b/tests/test_csv_full_report_instances_negative.py'))
(out/'observer-only.patch').write_text(patch)
print(str(target))
