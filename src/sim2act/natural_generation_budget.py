"""Explicit new P-A profile only; old caps and Source/Cold limits stay intact.

Projection alone is not send permission. Dispatch must still validate original
consent, stage, wire, account, ledger, lease and absolute budget.
"""
from . import natural_live_admission as gate


PROFILE='pa-natural-output4096.v1'


def envelope_limit(profile,stage):
    """Conservative ledger envelope; not an execution permission."""
    gate.require(profile in (None,PROFILE) and stage in {'generate','source','cold'})
    return 4096 if profile==PROFILE and stage=='generate' else 1024


def output_limit(contract,stage):
    gate.require(stage in {'generate','source','cold'})
    if (gate._contract_kind(contract) is gate.TrialContractV2
            and contract.generation_profile==PROFILE and stage=='generate'):
        return 4096
    return contract.caps.max_output_tokens


def wire_output_limit(contract,stage,tools):
    gate.require(type(tools) is list)
    cap=output_limit(contract,stage)
    if cap==4096 and tools and not (len(tools)==1 and type(tools[0]) is dict and type(tools[0].get('function')) is dict and tools[0]['function'].get('name')=='spec.check_candidate'):
        return contract.caps.max_output_tokens
    return cap
