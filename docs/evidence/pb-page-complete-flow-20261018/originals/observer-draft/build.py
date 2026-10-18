from pathlib import Path
r=Path('/workspace/pb-page-observer-draft-20261018');s=(r/'base/test_pb_natural_product_flow.py').read_text()
s=s.replace('import subprocess\n','import subprocess\nfrom contextlib import nullcontext\n',1)
s=s.replace('from test_pb_natural_specs import drive_to_success\n','from test_pa_natural_spec_ui import _PageObserver\nfrom test_pb_natural_specs import drive_to_success\n',1)
start=s.index('def test_successful_source_to_pb_directory_and_new_material(')
end=s.index('\ndef test_pb_product_navigation_synthesized_api(',start)
original=s[start:end];head,body=original.split('\n',1)
body=body.replace('    data = setup(env)\n','    with observer.phase("fixture_setup"):\n        data = setup(env)\n',1)
body=body.replace('    _, source_app, source_release, source_instance, generation_wire = ready(data, "single")\n','    with observer.phase("fixture_generation_and_ready"):\n        _, source_app, source_release, source_instance, generation_wire = ready(data, "single")\n    generation_returned = True\n    observer.sent = generation_wire\n    observer.save("source-generation-wire.json", generation_wire)\n    observer.event("fixture_generation_wire_exported", request_count=len(generation_wire))\n',1)
body=body.replace('    source_wire = []\n','',1)
body=body.replace('    drive_to_success(data, source_run, transport(source_wire, SOURCE))\n','    with observer.phase("worker", command="fixture-source-worker", run_id=source_run):\n        drive_to_success(data, source_run, transport(source_wire, SOURCE))\n',1)
body=body.replace('    source_app_reply = client.get("/api/apps/" + source_app)\n','    with observer.phase("http", method="GET", path="/api/apps/" + source_app):\n        source_app_reply = client.get("/api/apps/" + source_app)\n        observer.http_response(dict(method="GET", path="/api/apps/" + source_app), source_app_reply)\n',1)
body=body.replace('    source_artifact = client.get(f"/api/internal/app-run-jobs/{source_run}/spec-artifact")\n','    with observer.phase("http", method="GET", path=f"/api/internal/app-run-jobs/{source_run}/spec-artifact"):\n        source_artifact = client.get(f"/api/internal/app-run-jobs/{source_run}/spec-artifact")\n        observer.http_response(dict(method="GET", path=f"/api/internal/app-run-jobs/{source_run}/spec-artifact"), source_artifact)\n',1)
body=body.replace('    runtime_wire, checkpoints, boundary_receipts = [], [], []\n','',1)
body=body.replace('    stderr = tmp_path / "node.stderr"\n','    stderr = tmp_path / "node.stderr"\n    observer.driver.close()\n    observer.driver = stderr.open("w", encoding="utf-8")\n',1)
body=body.replace('    with stderr.open("w", encoding="utf-8") as err:\n','    with nullcontext(observer.driver) as err:\n',1)
body=body.replace('        try:\n            for line in process.stdout:\n                request = json.loads(line)\n','        observer.own_node(process)\n        try:\n            for line in process.stdout:\n                observer.event("node_stdout", raw_line=line)\n                request = json.loads(line)\n',1)
# Add the original per-line body under a logging-only RPC context.
loop_start=body.index('                if request.get("done"):\n')
loop_end=body.index('            process.stdin.close()\n',loop_start)
loop=body[loop_start:loop_end]
loop=loop.replace('                    break\n','                    observer.event("rpc_done", rpc_id=request.get("id"))\n                    break\n',1)
worker_start=loop.index('                    assert not runtime_wire\n')
worker_end=loop.index('                elif command == "revoke-source-read":\n',worker_start)
worker_body=loop[worker_start:worker_end]
worker_wrapped='                    with observer.phase("worker", rpc_id=request["id"], command=command, run_id=request["run_id"]):\n'+''.join('    '+line if line.strip() else line for line in worker_body.splitlines(True))
loop=loop[:worker_start]+worker_wrapped+loop[worker_end:]
loop=loop.replace('                    listed = active_client.get(f"/api/projects/{project}/grants")\n','                    with observer.phase("http", rpc_id=request["id"], method="GET", path=f"/api/projects/{project}/grants"):\n                        listed = active_client.get(f"/api/projects/{project}/grants")\n                        observer.http_response(dict(id=request["id"], method="GET", path=f"/api/projects/{project}/grants"), listed)\n',1)
loop=loop.replace('                    revoked = active_client.post(revoke_path, json=body)\n','                    with observer.phase("http", rpc_id=request["id"], method="POST", path=revoke_path):\n                        revoked = active_client.post(revoke_path, json=body)\n                        observer.http_response(dict(id=request["id"], method="POST", path=revoke_path, body=body), revoked)\n',1)
# Keep the original two boundary receipts, and checkpoint them as soon as available.
loop=loop.replace('                    readonly_baseline = snapshot(cold or store)\n                    source_unchanged(readonly_baseline)\n                    answer = dict(id=request["id"], status=200, text=json.dumps(dict(selected_grant=revoked_grant, receipt=revoked.json())))\n','                    observer.save("boundary-receipts.json", boundary_receipts)\n                    readonly_baseline = snapshot(cold or store)\n                    source_unchanged(readonly_baseline)\n                    answer = dict(id=request["id"], status=200, text=json.dumps(dict(selected_grant=revoked_grant, receipt=revoked.json())))\n',1)
http_start=loop.index('                    reply = (cold_client or client).request(')
http_end=loop.index('                process.stdin.write',http_start)
http_body=loop[http_start:http_end]
http_body=http_body.replace('                    answer = dict(', '                    observer.http_response(request, reply)\n                    answer = dict(',1)
http_wrapped='                    with observer.phase("http", rpc_id=request["id"], method=request["method"], path=request["path"]):\n'+''.join('    '+line if line.strip() else line for line in http_body.splitlines(True))
loop=loop[:http_start]+http_wrapped+loop[http_end:]
loop=loop.replace('                process.stdin.write(json.dumps(answer) + "\\n")','                observer.event("rpc_reply", rpc_id=answer["id"], status=answer["status"],\n                    text_sha256=hashlib.sha256(answer["text"].encode()).hexdigest())\n                process.stdin.write(json.dumps(answer) + "\\n")',1)
body=body[:loop_start]+'                with observer.phase("rpc", request=request):\n'+''.join('    '+line if line.strip() else line for line in loop.splitlines(True))+body[loop_end:]
# Always preserve the PB-specific original evidence names, even before Popen/setup completion.
prefix='''    with _PageObserver(tmp_path, "test_successful_source_to_pb_directory_and_new_material") as observer:
        generation_wire = []
        generation_returned = False
        source_wire = observer.observed_list("source-worker")
        runtime_wire = observer.runtime_sent
        checkpoints = observer.observed_list("checkpoints")
        boundary_receipts = []
        try:
'''
wrapped=''.join('        '+line if line.strip() else line for line in body.splitlines(True))
suffix='''        finally:
            for name, value in [("source-generation-wire.json", generation_wire),
                                ("source-worker-wire.json", source_wire),
                                ("runtime-wire.json", runtime_wire), ("checkpoints.json", checkpoints),
                                ("boundary-receipts.json", boundary_receipts)]:
                observer.save(name, value)
            observer.save("fixture-generation-observation.json", dict(
                ready_returned=generation_returned, exported_requests=len(generation_wire),
                partial_wire_before_ready_return="NOT_EXPORTED_BY_ORIGINAL_HELPER",
                exported_count_is_not_attempt_count_if_ready_failed=not generation_returned))
            if not generation_returned:
                observer.event("fixture_generation_wire_unavailable",
                    reason="Original ready helper did not return; partial generation wire is not exported")

'''
new=head+'\n'+prefix+wrapped+suffix
s=s[:start]+new+s[end:]
(r/'tests/test_pb_natural_product_flow.py').write_text(s)
