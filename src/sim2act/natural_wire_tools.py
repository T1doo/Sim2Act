"""Versioned wire names only; registered tool identity and checks stay canonical."""
import copy
from .errors import DomainError

PROTOCOL='natural-checked-candidate4096.v3'
STRUCTURED_FINAL = "natural-checked-candidate4096.v9"
SUBMIT = "submit_candidate"
ALIASES={'read':'resource.read','check_candidate':'spec.check_candidate', SUBMIT: SUBMIT}


def tools(values):
    result=copy.deepcopy(values)
    inverse={v:k for k,v in ALIASES.items()}
    for value in result:
        name=value['function']['name']
        if name not in inverse:raise DomainError('PERMISSION_DENIED','Unknown generation wire tool')
        value['function']['name']=inverse[name]
    return result


def diagnostic_envelope(args):
    # A known checker may report invalid input; this never validates a candidate.
    if not isinstance(args,dict) or set(args)!={'candidate'}:
        raise DomainError('INVALID_INPUT','Closed candidate check envelope required')


def parse(raw,protocol=PROTOCOL):
    from .model import parse_response
    from .tools import validate_call
    from .pa_spec_apps import check_envelope
    checker=diagnostic_envelope if protocol in {'natural-checked-candidate4096.v5','natural-checked-candidate4096.v6','natural-checked-candidate4096.v7','natural-checked-candidate4096.v8','natural-checked-candidate4096.v9'} else check_envelope
    validators = {'read':lambda args:validate_call('resource.read',args),'check_candidate':checker}
    if protocol == STRUCTURED_FINAL:
        validators[SUBMIT] = check_envelope
    message,calls=parse_response(raw, validators)
    canonical=[]
    for call in calls:canonical.append(canonical_call(call))
    # Preserve the actual assistant reply in history and subsequent messages.
    return message,canonical


def candidate_payload(message, protocol):
    from .contracts import strict_json

    if protocol == STRUCTURED_FINAL:
        calls = message.get("tool_calls", [])
        if message.get("role") != "assistant" or len(calls) != 1 or calls[0]["function"]["name"] != SUBMIT:
            raise DomainError("INVALID_MANIFEST", "One structured candidate submission required")
        args = strict_json(calls[0]["function"]["arguments"], 16384)
        from .pa_spec_apps import check_envelope
        check_envelope(args)
        return args["candidate"]
    if set(message) != {"role", "content"} or message["role"] != "assistant":
        raise DomainError("INVALID_MANIFEST", "Content-only candidate response required")
    return strict_json(message["content"], 16384)


def canonical_call(call):
    name=call.get('function',{}).get('name')
    if name not in ALIASES:raise DomainError('MODEL_OUTPUT_INVALID','Tool name differs from frozen wire declaration')
    return {**call,'function':{**call['function'],'name':ALIASES[name]}}


def protocol_from_wire(wire):
    from .contracts import strict_json
    try:return strict_json(strict_json(wire,32768)['messages'][1]['content'],32768)['server_ids'].get('output_protocol')
    except (DomainError,KeyError,TypeError,IndexError):return None
