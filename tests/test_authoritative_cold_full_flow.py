"""Manual large original-30 acceptance, actual SQLite and fixed Mock transport.

No business clock or worker method replacement. All original controller goal,
archive, two model settlements, saved-result and readback assertions remain.
"""
import json
from dataclasses import replace
from types import SimpleNamespace

import test_pb_spec_production_controller as original
from sim2act import natural_live_admission as gate
from sim2act.db import fingerprint


def test_large_original_thirty_authoritative_flow(env, tmp_path, monkeypatch):
    def prepare(data, out):
        data = original.apps.setup(data)
        account = "synthetic-pb-production-shape"
        subject = original.admission.canonical_quota_subject(account)
        data = (data[0], replace(data[1], quota_subject=subject), *data[2:])
        data[0].initialize(quota_subject=subject)
        baseline, consent = original.frozen(data, ttl=1800)
        contract = gate.PBTrialContract(**(baseline.model_dump() | dict(
            quota_subject=subject, caps=gate.TrialCaps().model_dump())), path="P-B",
            extraction_request_key="original-pb-production-extraction",
            extraction_recipe=original.apps.recipe("ordered"))
        consent = consent.model_copy(update=dict(expected_contract_fingerprint=fingerprint(contract.model_dump())))
        gate.approve(data[0], data[3], contract, consent)
        return data, SimpleNamespace(contract=contract, approval_key=consent.request_key, account_id=account)
    monkeypatch.setattr(original, "prepare_pb", prepare)
    original.test_pb_production_original_source_extraction_explicit_use_and_cold(
        env, tmp_path, monkeypatch, _authoritative=True)
    proof = json.loads((tmp_path / "pb-controller-proof.json").read_text())
    assert proof["result"]["status"] == "SUCCEEDED"
    assert len((tmp_path / "mock-exchanges.jsonl").read_text().splitlines()) == 7
