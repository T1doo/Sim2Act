import ast, difflib, hashlib, json, pathlib
repo=pathlib.Path('/workspace/Sim2Act')
out=pathlib.Path('/workspace/local-record-ui-independent-review-20261018')
paths=['tests/test_local_record_apps_ui.py','tests/local_record_apps_ui.cjs']
original={name:(repo/name).read_text() for name in paths}
py=original[paths[0]]
def replace_once(text,before,after):
 assert text.count(before)==1,(before[:100],text.count(before))
 return text.replace(before,after,1)
py=replace_once(py,'from sqlalchemy import select','from sqlalchemy import select, update')
py=replace_once(py,'from sim2act.db import Store, attempts, reservations, runs','from sim2act.db import Store, attempts, fingerprint, grants, reservations, runs')
py=replace_once(py,'@pytest.mark.parametrize("scenario", ["flow-recovery", "navigation"])','@pytest.mark.parametrize("scenario", ["flow-recovery", "navigation", "revocation"])')
py=replace_once(py,'    stores = []\n','    stores = []\n    revocation_log, revocation_grant = [], None\n')
start=py.index('        if scenario == "navigation":\n')
end=py.index('        before_identity = snapshot',start)
py=py[:start]+'''        if scenario in {"navigation", "revocation"}:
            data = ready(env)
            first = execute(env, data, create_body(current(env, data)))
            info.update(app=data["app"]["id"], instance=data["instance"]["id"],
                iid=data["instance"]["id"], release=data["release"]["id"],
                seed_run=first["run"]["id"], seed_request_key=first["prepared"]["request_key"])
            if scenario == "navigation":
                second = ok(env[2].post(f"/api/internal/record-releases/{data['release']['id']}/instances", json=dict(
                    expected_release_fingerprint=data["release"]["fingerprint"], request_key="page-navigation-empty-instance")), 201)["instance"]
                info["second_instance"] = second["id"]
            else:
                info["seed_artifact"] = first["run"]["output"]["resource_id"]
                with env[0].tx() as connection:
                    matching = connection.execute(select(grants).where(
                        grants.c.principal_id == env[3], grants.c.project_id == env[5],
                        grants.c.resource_id == info["seed_artifact"], grants.c.tool_ref == "resource.read",
                        grants.c.revoked.is_(False))).mappings().all()
                    assert len(matching) == 1, "Exactly one known owner-read grant for the synthetic seed artifact"
                    revocation_grant = dict(matching[0])
''' +py[end:]
py=replace_once(py,'                if request.get("command") == "worker":\n','                if request.get("command") == "worker":\n                    assert scenario == "flow-recovery", "Read-only page scenarios cannot invoke Worker"\n')
py=replace_once(py,'                else:\n                    assert "command" not in request, request\n', '''                elif request.get("command") == "revoke_seed_artifact_read":
                    # Fixture-only authority mutation. The page cannot select a Grant,
                    # principal, project or arbitrary resource through this bridge.
                    assert scenario == "revocation" and revocation_grant is not None and not revocation_log
                    assert set(request) == {"id", "command", "run", "resource"}
                    assert request["run"] == info["seed_run"] and request["resource"] == info["seed_artifact"]
                    with env[0].tx() as connection:
                        actual = dict(connection.execute(select(grants).where(
                            grants.c.id == revocation_grant["id"], grants.c.principal_id == env[3],
                            grants.c.project_id == env[5], grants.c.resource_id == info["seed_artifact"],
                            grants.c.tool_ref == "resource.read")).mappings().one())
                        assert actual == revocation_grant and not actual["revoked"]
                        changed = connection.execute(update(grants).where(
                            grants.c.id == actual["id"], grants.c.principal_id == env[3],
                            grants.c.project_id == env[5], grants.c.resource_id == info["seed_artifact"],
                            grants.c.tool_ref == "resource.read", grants.c.revoked.is_(False),
                            grants.c.revision == actual["revision"]).values(
                                revoked=True, revision=actual["revision"] + 1)).rowcount
                        assert changed == 1
                        after_grant = dict(connection.execute(select(grants).where(
                            grants.c.id == actual["id"])).mappings().one())
                    revocation_log.append(dict(before=actual, after=after_grant,
                        run_id=info["seed_run"], resource_id=info["seed_artifact"],
                        classification="EXPLICIT_SYNTHETIC_FIXTURE_GRANT_REVOCATION"))
                    answer = dict(status=200, text=json.dumps(dict(
                        revoked=True, resource_id=info["seed_artifact"], run_id=info["seed_run"])))
                else:
                    assert "command" not in request, request
                    if scenario == "revocation":
                        assert request["method"] == "GET", "Revocation page must never POST"
''')
py=replace_once(py,'        else:\n            assert page["classification"] == "ACTUAL_HTTP_JSDOM_LOCAL_RECORD_NAVIGATION_NO_WORKER"', '''        elif scenario == "revocation":
            assert page["classification"] == "ACTUAL_HTTP_JSDOM_LOCAL_RECORD_REVOCATION_NO_WORKER"
            assert worker_log == [] and len(revocation_log) == 1
            after_page = snapshot(env[0])
            assert before_page.keys() == after_page.keys()
            for table in before_page:
                if table != "grants":
                    assert before_page[table] == after_page[table], table
            expected = {row["id"]: row for row in before_page["grants"]}
            actual = {row["id"]: row for row in after_page["grants"]}
            assert expected.keys() == actual.keys()
            grant_id = revocation_grant["id"]
            expected[grant_id] = {**revocation_grant, "revoked": True, "revision": revocation_grant["revision"] + 1}
            assert actual == expected
            assert before_page["runs"] == after_page["runs"], "Original accepted Run must remain unchanged"
            write_json(tmp_path / "actual-revocation-proof.json", dict(
                scenario=scenario, fixture_grant_mutations=revocation_log,
                changed_tables=[name for name in before_page if before_page[name] != after_page[name]],
                database_before_fingerprint=fingerprint(before_page),
                database_after_fingerprint=fingerprint(after_page),
                only_exact_known_grant_changed=True, all_other_rows_unchanged=True,
                original_run_rows_unchanged=True, page_worker_calls=0, page_post_count=0))
            proof.update(page_worker_calls=0, fixture_worker_calls=1, actual_no_model_runs=1,
                fixture_grant_mutations=1, page_post_count=0, original_run_rows_unchanged=True,
                page_creation_release_instance_covered=False)
        else:
            assert page["classification"] == "ACTUAL_HTTP_JSDOM_LOCAL_RECORD_NAVIGATION_NO_WORKER"''')
py=replace_once(py,'        write_json(tmp_path / "worker-log.json", worker_log)\n','        write_json(tmp_path / "worker-log.json", worker_log)\n        write_json(tmp_path / "fixture-revocation-log.json", revocation_log)\n')
py=replace_once(py,'                    "ipc.json", "worker-log.json", "run-summary.json"):', '                    "ipc.json", "worker-log.json", "run-summary.json", "actual-revocation-proof.json",\n                    "fixture-revocation-log.json"):')
js=original[paths[1]]
scene='''async function revocation(){
 await open();
 await select('local-records-run-select',info.seed_run);await click('local-records-run-read');
 check(view().run?.id===info.seed_run&&view().run.status==='SUCCEEDED','seed same-Run result is genuinely re-read before revocation');
 await select('local-records-recovery-stage','RUN');input('local-records-recovery-key',info.seed_request_key);await click('local-records-recover');
 check($('local-records-current').textContent.includes(info.title_a)&&$('local-records-recovery-proof').textContent.includes(info.details_a)&&$('local-records-details').value===info.details_a,'real original-key recovery visibly restores seed body and form before denial');
 check(posts().length===0,'pre-revocation instance and original-key reads perform zero POST');
 const revoked=await rpc({command:'revoke_seed_artifact_read',run:info.seed_run,resource:info.seed_artifact});assert.equal(revoked.status,200,revoked.text);
 const cleared=label=>{
  for(const id of ['local-records-current','local-records-history','local-records-run-proof','local-records-preview-proof','local-records-preview-summary','local-records-recovery-proof'])check(!$(id).textContent,label+' clears '+id);
  for(const id of ['local-records-title','local-records-details','local-records-reason'])check(!$(id).value,label+' clears form '+id);
  check(!view().instance&&!view().preview&&!view().run&&$('local-records-confirm').disabled,label+' clears current claims and blocks confirmation');
  check($('local-records-recovery-key').value===info.seed_request_key&&$('local-records-recovery-stage').value==='RUN',label+' preserves exact original key and stage');
  check(!view().panel.textContent.includes(info.title_a)&&!view().panel.textContent.includes(info.details_a),label+' leaves no seed record text in any panel node');
 };
 let offset=actions.length;await click('local-records-refresh');
 let reads=actions.slice(offset);check(reads.length===1&&reads[0].method==='GET'&&reads[0].path===base()&&reads[0].status===403,'manual refresh receives one actual authorization 403 without automatic follow-up');cleared('refresh 403');
 offset=actions.length;await click('local-records-recover');
 reads=actions.slice(offset);check(reads.length===1&&reads[0].method==='GET'&&reads[0].path===original(info.seed_request_key)&&reads[0].status===403,'explicit original-key recovery receives actual 403 with zero automatic requests');cleared('recovery 403');
 check(posts().length===0,'the entire revocation page performs zero POST and invokes no page Worker');
}
'''
js=replace_once(js,'(async()=>{\n',scene+'(async()=>{\n')
js=replace_once(js,"try{await boot();if(info.scenario==='navigation')await navigation();else await flow();status='PASS';}","try{await boot();if(info.scenario==='navigation')await navigation();else if(info.scenario==='revocation')await revocation();else await flow();status='PASS';}")
js=replace_once(js,"classification:info.scenario==='navigation'?'ACTUAL_HTTP_JSDOM_LOCAL_RECORD_NAVIGATION_NO_WORKER':'ACTUAL_HTTP_JSDOM_LOCAL_RECORD_FLOW'", "classification:info.scenario==='navigation'?'ACTUAL_HTTP_JSDOM_LOCAL_RECORD_NAVIGATION_NO_WORKER':info.scenario==='revocation'?'ACTUAL_HTTP_JSDOM_LOCAL_RECORD_REVOCATION_NO_WORKER':'ACTUAL_HTTP_JSDOM_LOCAL_RECORD_FLOW'")
modified={paths[0]:py,paths[1]:js}
patch=''
manifest={}
for name in paths:
 base=out/('original-'+pathlib.Path(name).name)
 base.write_text(original[name])
 target=out/pathlib.Path(name).name
 target.write_text(modified[name])
 patch+=''.join(difflib.unified_diff(original[name].splitlines(keepends=True),modified[name].splitlines(keepends=True),fromfile='a/'+name,tofile='b/'+name))
 manifest[name]={'base_sha256':hashlib.sha256(original[name].encode()).hexdigest(),'proposed_sha256':hashlib.sha256(modified[name].encode()).hexdigest(),'base_copy':str(base),'proposed_copy':str(target)}
ast.parse(py)
(out/'revocation-scene.patch').write_text(patch)
(out/'revocation-patch-manifest.json').write_text(json.dumps({'execution':'AST parsed and node --check only; no fixture/Worker/pytest run by independent reviewer','scope':'test-only proposed third scenario; root remains sole repository writer','files':manifest},indent=2)+'\n')
print(json.dumps(manifest,indent=2))
print('patch_sha256',hashlib.sha256(patch.encode()).hexdigest())
