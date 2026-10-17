from pathlib import Path
s=Path('/workspace/Sim2Act/src/sim2act/ordinary_corrections.py').read_text()
start=s.index('    frozen = (',s.index('def scope_gate('));end=s.index('    source_scope_gate(store, c, parent)',start);block=s[start:end]
block=block.replace('== parent','== rid').replace('(len(effects) == 1 and receipt_ids == [[effects[0]]])','((len(effects) == 1 if completed_parent else len(effects) <= 1) and receipt_ids == [[artifact] for artifact in effects])')
needle='    material_ids = [v["resource_id"] for v in frozen["materials"]]'
shape='''    require(isinstance(frozen["materials"], list) and 1 <= len(frozen["materials"]) <= 8
        and all(isinstance(v, dict) and isinstance(v.get("resource_id"), str) for v in frozen["materials"])
        and all(isinstance(refs, list) and all(isinstance(v, str) for v in refs)
            for refs in (header["resource_refs"], frozen["refs"]))
        and frozen["version"] in (human.VERSION, human.MD_VERSION), "Invalid evidence identifier projections")
'''
assert needle in block;block=block.replace(needle,shape+needle)
s=s[:start]+'    evidence_scope(store, c, parent, header, completed_parent=True)\n    evidence_scope(store, c, rid, child, completed_parent=False)\n'+s[end:]
s=s.replace('def scope_gate(store, c, rid):','def evidence_scope(store, c, rid, header, *, completed_parent):\n'+block+'\n\ndef scope_gate(store, c, rid):')
old='select(runs.c.principal_id, runs.c.project_id, runs.c.runtime_id).where(';assert s.count(old)==1;s=s.replace(old,'select(runs.c.id, runs.c.principal_id, runs.c.project_id, runs.c.runtime_id, runs.c.resource_refs).where(')
s=s.replace('all(header[k] == child[k] for k in child)','all(header[k] == child[k] for k in ("principal_id", "project_id", "runtime_id"))')
helper='''def scoped_request_run(store, c, user, pid, parent, key):
    rid = c.execute(select(runs.c.id).where(runs.c.principal_id == user,
        runs.c.project_id == pid, runs.c.request_key == key)).scalar()
    if rid is None:
        return None
    require(parent_hint(c, rid) == parent, "Original key belongs to a different correction source")
    from .goal_applications import source_scope_gate

    source_scope_gate(store, c, rid)
    return c.execute(select(runs).where(runs.c.id == rid)).mappings().one()


'''
s=s.replace('def submit(store, user, parent, body, limits):',helper+'def submit(store, user, parent, body, limits):')
start=s.index('        old = (',s.index('def submit('));end=s.index('        if old:',start);s=s[:start]+'        old = scoped_request_run(store, c, user, pid, parent, body["request_key"])\n'+s[end:]
start=s.index('            run = (',s.index('def mount('));end=s.index('            if run is None:',start);s=s[:start]+'            run = scoped_request_run(store, c, user, pid, rid, key)\n'+s[end:]
Path('/tmp/ordinary_corrections-postreview.py').write_text(s)
print('Prepared candidate; checkout unchanged')
