"""New-profile projection and byte-compatible legacy scope, not dispatch IO."""
import json
import pytest
from pydantic import ValidationError
from test_natural_trial_preparation import prepared_data,scope
from sim2act import natural_live_admission as gate
from sim2act.natural_generation_budget import PROFILE,output_limit
from sim2act.db import fingerprint
from sim2act.errors import DomainError
from test_production_trial_policy import kernel


def test_new_profile_changes_only_generation_projection_and_scope_fingerprint(prepared_data):
    _,_,_,receipt=scope(prepared_data)
    original=receipt['contract'];legacy=gate.parse_contract(original)
    assert legacy.model_dump()==original and 'generation_profile' not in legacy.model_dump()
    new=gate.parse_contract({**original,'generation_profile':PROFILE})
    assert fingerprint(new.model_dump())!=fingerprint(original)
    assert new.caps==legacy.caps and new.expires_at==legacy.expires_at
    assert [output_limit(legacy,s) for s in ('generate','source','cold')]==[1024]*3
    assert [output_limit(new,s) for s in ('generate','source','cold')]==[4096,1024,1024]
    assert gate.parse_contract(json.loads(new.model_dump_json())).model_dump()==new.model_dump()
    with pytest.raises(ValidationError):gate.parse_contract({**original,'generation_profile':'unapproved'})
    with pytest.raises(DomainError):output_limit(new,'other')
    from sim2act.production_evidence import requirements_for
    assert requirements_for(new.principal_id,new,'synthetic-approval').generation_profile==PROFILE
    assert 'generation_profile' not in requirements_for(legacy.principal_id,legacy,'synthetic-approval').model_dump()


def test_profile_ledger_uses_conservative_generate_envelope_and_keeps_total_output(kernel):
    import time
    from sim2act import production_trial_policy as policy
    _,_,_,_,scope,_,identity,_,_,_,_=kernel
    extended=scope.model_copy(update={'generation_profile':PROFILE})
    identity=identity.model_copy(update={'requirements_fingerprint':fingerprint(extended.model_dump())})
    assert policy._envelope(extended,identity)==identity.wire_bytes+4096
    assert policy._envelope(scope,identity)==identity.wire_bytes+1024
    assert policy._envelope(extended,identity.model_copy(update={'stage':'source'}))==identity.wire_bytes+1024
    result=policy.Outcome(outcome='RECEIVED',response_sha256='a'*64,response_ascii_bytes=100,prompt_tokens=1,completion_tokens=2048,total_tokens=2049)
    slot=policy.Slot(identity=identity,reserved_at=time.time(),attempted=True,settlement=result,accepted=True)
    ledger=policy.Ledger(scope=extended,account_id=identity.account_id,slots=(slot,))
    assert policy._ledger(ledger)==ledger
    old_identity=identity.model_copy(update={'requirements_fingerprint':fingerprint(scope.model_dump())})
    with pytest.raises(DomainError):policy._ledger(ledger.model_copy(update={'scope':scope,'slots':(slot.model_copy(update={'identity':old_identity}),)}))
    large=result.model_copy(update={'completion_tokens':4000,'total_tokens':4001})
    one=slot.model_copy(update={'settlement':large})
    two=one.model_copy(update={'reserved_at':one.reserved_at+60,'identity':identity.model_copy(update={'attempt_id':'attempt_'+'b'*32})})
    with pytest.raises(DomainError):policy._ledger(ledger.model_copy(update={'slots':(one,two)}))
