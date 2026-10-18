"""Two actual HTTP/JSDOM closure flows; no page Worker/model execution.

The existing new backend module owns one fresh shared source seed. This module
imports its fixture and clone helper without running the older cold-page seed.
"""

import copy
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

import pytest
from test_pa_natural_spec_ui import _PageObserver
from test_pb_cold_recovery_ui import assert_assets, assert_one_extraction
from test_pb_extraction_close import (
    CloseCase,
    assert_only_terminal,
    assert_terminal,
    identity_for,
    sha,
    source_header,
    sources,
)
from test_pb_extraction_close import (
    pb_extraction_close_seed as _shared_source_seed,
)
from test_spec_app_operations import snapshot

from sim2act import natural_specs as natural
from sim2act import pb_natural_specs as pb
from sim2act.db import fingerprint

pb_extraction_close_seed = _shared_source_seed


def page_sources(root):
    value = sources()
    paths = [Path(__file__).resolve(), Path(__file__).with_name("pb_extraction_close_ui.cjs").resolve(),
        root / "tests/durable_browser.cjs", root / "tests/test_pb_cold_recovery_ui.py"]
    for path in paths:
        label = str(path.relative_to(root)) if path.is_relative_to(root) else str(path)
        value[label] = dict(bytes=path.stat().st_size, sha256=sha(path))
    return value


def committed_body(review):
    return dict(review=copy.deepcopy(review["request"]),
        expected_review_fingerprint=review["review_fingerprint"], consent=pb.CONSENT,
        artifact_write_consent=natural.CONSENT)


def only(rows, predicate, label):
    matches = [row for row in rows if predicate(row)]
    assert len(matches) == 1, (label, matches)
    return matches[0]


@pytest.mark.parametrize("scenario", ["preaccept-close", "accepted-refuse"])
def test_pb_unknown_extraction_close_visible_actual_http(pb_extraction_close_seed, tmp_path, scenario):
    root = Path.cwd().resolve()
    seed = pb_extraction_close_seed
    with _PageObserver(tmp_path, "PB_CLOSE_PAGE_" + scenario) as observer:
        with CloseCase(seed, tmp_path / "case", observer) as case:
            before_sources = page_sources(root)
            observer.save("page-source-before.json", before_sources)
            initial = snapshot(case.store)
            readonly, closed_rows = initial, None
            original_identity = original_commit = terminal_receipt = extraction = None
            reviews, http, ipc, checkpoints = {}, [], [], []
            deferred_dispatches = 0
            process = None
            proof = dict(status="NOT_COMPLETED", scenario=scenario,
                classification="ACTUAL_HTTP_JSDOM_PB_EXTRACTION_CLOSE",
                page_worker_calls=0, page_model_requests=0, real_model_requests=0,
                shared_seed=str(seed["seed_folder"]), shared_seed_sha256=seed["seed_sha256"],
                fixture_generation_mock_requests=3, fixture_source_mock_requests=1,
                fixture_source_worker_calls=1, mock_request_scope="ONE_FRESH_SEED_PER_PYTEST_PROCESS",
                expected_mock_requests_if_backend_and_ui_run_as_separate_processes=8,
                native_browser="NOT_RUN", windows="NOT_RUN", pg="NOT_RUN", remote_ci="NOT_RUN",
                real_semantic_acceptance="NOT_RUN", actual_network_concurrency="NOT_RUN",
                actual_database_concurrency="BACKEND_SUITE_SCOPE")
            # Forward only the page's actual Authorization header. An authenticated
            # TestClient default must never hide a missing production-page header.
            bridge = case.new_client(case.store)
            bridge.headers.pop("Authorization", None)
            case.extra_clients.append(bridge)

            def identity_from_actual_review(value):
                key = value["request_key"]
                assert key in reviews, "An actual successful read-only preview must precede a ticket"
                reviewed = reviews[key]
                expected_commit = committed_body(reviewed)
                assert identity_for(reviewed, expected_commit) == value
                return expected_commit

            try:
                info = dict(case.info, scenario=scenario, output=str(tmp_path / "page-result.json"),
                    storage_path=str(tmp_path / "durable-storage.json"))
                observer.save("info.json", info)
                process = subprocess.Popen(["node", str(Path(__file__).with_name("pb_extraction_close_ui.cjs")),
                    str(tmp_path / "info.json")], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                    stderr=observer.driver, text=True, env={**os.environ,
                        "NODE_PATH": str(root / "scripts/engineering-ci/node_modules")})
                observer.own_node(process)
                with (tmp_path / "node.stdout").open("w", encoding="utf-8") as stdout:
                    for line in process.stdout:
                        stdout.write(line)
                        stdout.flush()
                        observer.event("node_stdout", raw_line=line)
                        request = json.loads(line)
                        ipc.append(dict(direction="NODE_TO_PYTHON", value=request))
                        if request.get("done"):
                            assert request["status"] == "PASS", request
                            break
                        command = request.get("command")
                        with observer.phase("rpc", rpc_id=request["id"], command=command):
                            if command in {"zero-effects-checkpoint", "closure-checkpoint", "extraction-accepted-checkpoint"}:
                                value = request["identity"]
                                candidate_commit = identity_from_actual_review(value)
                                if original_identity is None:
                                    original_identity, original_commit = copy.deepcopy(value), candidate_commit
                                    case.identity, case.commit = copy.deepcopy(value), copy.deepcopy(candidate_commit)
                                assert value == original_identity
                                current = snapshot(case.store)
                                if command == "zero-effects-checkpoint":
                                    assert scenario == "preaccept-close" and extraction is None
                                    assert current == readonly
                                    if request["phase"] == "before-api-original-attempt-only":
                                        assert closed_rows is None and current == initial
                                        assert not [row for row in http if row["path"] == case.path + "/extractions"]
                                    else:
                                        assert request["phase"] == "late-original-post-rejected" and closed_rows is not None
                                        assert deferred_dispatches == 1
                                        late = only(http, lambda row: row.get("transport_phase") ==
                                            "DEFERRED_ORIGINAL_POST_AFTER_CLIENT_DELIVERY_FAILURE", "One original deferred wire")
                                        assert late["status"] == 409 and late["response"]["error"]["code"] == "VERSION_CONFLICT"
                                        assert late["body"] == original_commit
                                elif command == "closure-checkpoint":
                                    assert scenario == "preaccept-close" and closed_rows is None and extraction is None
                                    assert request["close_body"] == case.close_body()
                                    terminal_receipt = assert_terminal(request["receipt"], case)
                                    close_row = only(http, lambda row: row["method"] == "POST" and
                                        row["path"] == case.by_key() + "/close", "One actual close POST")
                                    assert close_row["status"] == 200 and close_row["body"] == case.close_body()
                                    assert close_row["response"] == terminal_receipt
                                    assert_only_terminal(initial, current, case)
                                    closed_rows = copy.deepcopy(current)
                                    readonly = current
                                else:
                                    assert extraction is None, "Each page case accepts exactly one application"
                                    if scenario == "preaccept-close":
                                        assert closed_rows is not None and deferred_dispatches == 1
                                        new_key = request["new_request_key"]
                                        assert new_key != original_identity["request_key"] and new_key in reviews
                                        expected_commit = committed_body(reviews[new_key])
                                        accepted_baseline = closed_rows
                                    else:
                                        assert closed_rows is None
                                        new_key, expected_commit, accepted_baseline = value["request_key"], original_commit, initial
                                    accepted = only(http, lambda row: row["method"] == "POST" and
                                        row["path"] == case.path + "/extractions" and row["status"] == 201,
                                        "One actual accepted extraction")
                                    assert accepted["body"] == expected_commit
                                    assert accepted["body"]["review"]["request_key"] == new_key
                                    extraction = assert_one_extraction(accepted_baseline, current, case.info)
                                    assert request["app_id"] == extraction["app"]["id"] == accepted["response"]["id"]
                                    assert extraction["marker"]["request_key"] == new_key
                                    assert extraction["marker"]["request_fingerprint"] == fingerprint(expected_commit)
                                    assert accepted["response"]["request"] == expected_commit
                                    assert accepted["response"]["reviewed"] == reviews[new_key]
                                    assert accepted["response"]["candidate_fingerprint"] == fingerprint(extraction["app"]["candidate"])
                                    if scenario == "preaccept-close":
                                        assert extraction["app"]["id"] != original_identity["app_id"]
                                    readonly = current
                                checkpoints.append(dict(command=command, phase=request["phase"],
                                    identity=copy.deepcopy(value), all_expected_rows_verified=True))
                                answer = dict(status=200, text="{}")
                            elif command == "readonly-checkpoint":
                                assert snapshot(case.store) == readonly
                                checkpoints.append(dict(command=command, phase=request["phase"], all_rows_identical=True))
                                answer = dict(status=200, text="{}")
                            else:
                                assert command is None, "No Worker/model or arbitrary fixture mutation RPC is supported"
                                method, path = request["method"], request["path"]
                                headers = request.get("headers", {})
                                if path.startswith("/api/"):
                                    assert {key.lower(): value for key, value in headers.items()}.get("authorization") == "Bearer synthetic-test-A"
                                kwargs = dict(headers=headers)
                                raw_body = b""
                                if "body_text" in request:
                                    assert isinstance(request["body_text"], str)
                                    raw_body = request["body_text"].encode("utf-8")
                                    assert json.loads(raw_body) == request["body"]
                                    kwargs["content"] = raw_body
                                else:
                                    assert request.get("body") is None and method == "GET"
                                if request.get("transport_phase"):
                                    assert scenario == "preaccept-close" and closed_rows is not None and extraction is None
                                    assert request["transport_phase"] == "DEFERRED_ORIGINAL_POST_AFTER_CLIENT_DELIVERY_FAILURE"
                                    assert method == "POST" and path == case.path + "/extractions"
                                    assert request["body"] == original_commit
                                    deferred_dispatches += 1
                                    assert deferred_dispatches == 1
                                reply = bridge.request(method, path, **kwargs)
                                assert reply.request.content == raw_body, "The actual transport must preserve exact original bytes"
                                try:
                                    response_value = reply.json()
                                except ValueError:
                                    response_value = None
                                row = dict(rpc_id=request["id"], method=method, path=path,
                                    headers=dict(reply.request.headers), body=request.get("body"),
                                    body_text=request.get("body_text"), body_bytes=len(raw_body),
                                    body_sha256=hashlib.sha256(raw_body).hexdigest(), status=reply.status_code,
                                    response=response_value, response_text=reply.text,
                                    transport_phase=request.get("transport_phase"))
                                http.append(row)
                                observer.save("actual-http.json", http)
                                if method == "POST" and path == case.path + "/extraction-reviews" and reply.status_code == 200:
                                    key = response_value["request"]["request_key"]
                                    assert key not in reviews and response_value["request"] == request["body"]
                                    assert response_value["review_fingerprint"] == fingerprint({key: value
                                        for key, value in response_value.items() if key != "review_fingerprint"})
                                    reviews[key] = copy.deepcopy(response_value)
                                answer = dict(status=reply.status_code, text=reply.text,
                                    content_type=reply.headers.get("content-type"))
                            answer["id"] = request["id"]
                            ipc.append(dict(direction="PYTHON_TO_NODE", value=answer))
                            process.stdin.write(json.dumps(answer) + "\n")
                            process.stdin.flush()
                process.stdin.close()
                code = process.wait(timeout=20)
                proof["node_exit_code"] = code
                assert code == 0, observer.stderr_text()
                page = json.loads((tmp_path / "page-result.json").read_text(encoding="utf-8"))
                assert page["status"] == "PASS" and page["checks"] and page["actions"], page
                assert page["classification"] == "ACTUAL_HTTP_JSDOM_PB_EXTRACTION_CLOSE"
                assert page["scenario"] == scenario and page["worker_calls"] == 0 and not page["page_errors"]
                assert original_identity and original_commit and extraction and snapshot(case.store) == readonly
                assert_assets(root, page)
                expected_assets = {"/", "/app.css", *re.findall(r'<script[^>]+src="([^"]+)"',
                    (root / "src/sim2act/web/index.html").read_text(encoding="utf-8"))}
                assert len(expected_assets) == 27
                assert all(len([row for row in page["static_resource_loads"] if row["boot"] == boot]) == 27
                    for boot in range(1, page["boots"] + 1))
                close = only(http, lambda row: row["method"] == "POST" and row["path"] == case.by_key() + "/close", "One actual close")
                assert close["status"] == (200 if scenario == "preaccept-close" else 409)
                if scenario == "preaccept-close":
                    assert deferred_dispatches == 1 and page["closed_identity"] == original_identity
                    assert page["terminal"] == terminal_receipt
                    assert_only_terminal(initial, closed_rows, case)
                    wire = only(http, lambda row: row.get("transport_phase") is not None, "One exact late original wire")
                    assert page["deferred_body_text_sha256"] == wire["body_sha256"]
                    captured = only(page["transport"], lambda row: row["phase"] == "CAPTURE_ORIGINAL_WIRE_BEFORE_API", "Captured deferred request")
                    assert captured["wire"]["body_text"].encode("utf-8") == wire["body_text"].encode("utf-8")
                    assert captured["wire"]["body"] == original_commit
                    assert page["deferred_wire_sha256"] == fingerprint(captured["wire"])
                    digest, = page["terminal_digest_observations"]
                    unsigned = {key: value for key, value in terminal_receipt.items()
                        if key != "receipt_fingerprint"}
                    assert json.loads(digest["input_utf8"]) == unsigned
                    assert bytes.fromhex(digest["input_utf8_hex"]) == digest["input_utf8"].encode("utf-8")
                    assert digest["actual_digest_hex"] == fingerprint(unsigned)
                    assert digest["actual_result_computed_before_hold"] and digest["released"] and digest["delivered"]
                    assert digest["events"] == ["HOLD_ALREADY_COMPUTED_ACTUAL_SHA_RESULT",
                        "USER_EXPLICITLY_CLOSES_OLD_REVIEW_PANEL", "RELEASE_ACTUAL_SHA_RESULT",
                        "DELIVER_UNMODIFIED_ACTUAL_SHA_RESULT"]
                    assert json.loads(Path(str(tmp_path / "page-result.json") + ".terminal-digest.json").read_text()) == [digest]
                    captured_file = json.loads(Path(str(tmp_path / "page-result.json") + ".deferred-wire.json").read_text())
                    assert captured_file["server_received"] is False
                    assert captured_file["body_text"].encode("utf-8") == wire["body_text"].encode("utf-8")
                    assert bytes.fromhex(captured_file["body_text_utf8_hex"]) == wire["body_text"].encode("utf-8")
                    assert captured_file["body_text_sha256"] == wire["body_sha256"]
                    assert page["new_request_key"] == extraction["marker"]["request_key"]
                    assert page["new_request_key"] != original_identity["request_key"]
                else:
                    assert deferred_dispatches == 0 and closed_rows is None and page["original_identity"] == original_identity
                    assert page["original_request_key"] == extraction["marker"]["request_key"]
                assert page["app_id"] == extraction["app"]["id"]
                assert not observer.sent and not observer.runtime_sent
                assert page_sources(root) == before_sources
                proof.update(status="PASS", accepted_extractions=1, app_id=extraction["app"]["id"],
                    runtime_id=extraction["app"]["runtime_id"], original_identity=original_identity,
                    accepted_request_key=extraction["marker"]["request_key"],
                    terminal_metadata_rows=2 if scenario == "preaccept-close" else 0,
                    extraction_journal_rows=4, derived_runtime_grants=2,
                    actual_deferred_original_posts=deferred_dispatches,
                    deferred_request_bytes_preserved=bool(deferred_dispatches),
                    no_automatic_release_instance_run_or_business_artifact=True,
                    all_27_assets_verified_each_boot=True)
            finally:
                if process is not None:
                    observer.kill_owned_node("PAGE_BRIDGE_FINALLY")
                    if process.poll() is None:
                        process.wait(timeout=10)
                observer.save("proof.json", proof)
                observer.save("ipc.json", ipc)
                observer.save("checkpoints.json", checkpoints)
                observer.save("actual-http.json", http)
                observer.save("actual-reviews.json", reviews)
                observer.save("page-source-after.json", page_sources(root))
                observer.save("source-worker-finally.json", source_header(case.store, case.info["source_run"]))
                observer.save("page-final-rows.json", snapshot(case.store))
