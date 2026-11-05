"""Read original launcher selection; never issue or select a production permit."""
from .errors import DomainError


def read(store, settings, selected, user, pid, cid):
    result=dict(version='natural-generation-readiness.v1',project_id=pid,card_id=cid,
        availability='BLOCKED',new_runs=0,new_approvals=0,actual_model_requests=0)
    with store.tx() as c:
        store.own_project(c,user,pid)
    if selected is None:
        return {**result,'reason':'NO_LAUNCHER_SELECTION'}
    if set(selected)!={'user','project','trial','approval','account'} or selected['user']!=user or selected['project']!=pid:
        raise DomainError('PERMISSION_DENIED')
    from .launch_configuration import check_selection
    from .natural_trial_api import original_contract,existing_worker_selection
    from .db import fingerprint
    try:
        check_selection(store,settings,selected)
    except ValueError:
        raise DomainError('LIVE_BLOCKED','Selected production configuration is unavailable') from None
    contract=original_contract(store,user,pid,selected['trial'])
    recovered=existing_worker_selection(store,user,pid,selected['trial'],selected['approval'])
    first=contract.bindings[0]
    if recovered['worker_selection']!=selected or first.card_id!=cid:
        raise DomainError('VERSION_CONFLICT','Goal differs from selected generation scope')
    return {**result,'availability':'SELECTED_APPROVED_SCOPE','reason':None,
        'expected_version':first.goal_version,'expected_fingerprint':first.goal_fingerprint,
        'snapshot':first.goal_snapshot.model_dump(),'generation_request_key':contract.stage_keys.generate,
        'contract_fingerprint':fingerprint(contract.model_dump()),'approval_fingerprint':recovered['approval_fingerprint'],
        'expires_at':contract.expires_at}
