"""Versioned wire names only; registered tool identity and checks stay canonical."""
import copy
from .errors import DomainError

PROTOCOL='natural-checked-candidate4096.v3'
ALIASES={'read':'resource.read','check_candidate':'spec.check_candidate'}


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
    checker=diagnostic_envelope if protocol in {'natural-checked-candidate4096.v5','natural-checked-candidate4096.v6'} else check_envelope
    message,calls=parse_response(raw,{'read':lambda args:validate_call('resource.read',args),'check_candidate':checker})
    canonical=[]
    for call in calls:canonical.append(canonical_call(call))
    # Preserve the actual assistant reply in history and subsequent messages.
    return message,canonical


def canonical_call(call):
    name=call.get('function',{}).get('name')
    if name not in ALIASES:raise DomainError('MODEL_OUTPUT_INVALID','Tool name differs from frozen wire declaration')
    return {**call,'function':{**call['function'],'name':ALIASES[name]}}


def protocol_from_wire(wire):
    from .contracts import strict_json
    try:return strict_json(strict_json(wire,32768)['messages'][1]['content'],32768)['server_ids'].get('output_protocol')
    except (DomainError,KeyError,TypeError,IndexError):return None
