"""Old persisted protocol must remain readable/confirmable after new policy default."""
from test_goal_text_applications import setup,generate,confirm,release_instance
from sim2act import goal_applications


def test_legacy_generation_can_be_confirmed_after_policy_default_changes(env,monkeypatch):
    data=setup(env)
    original=goal_applications.policy
    # Create a genuinely absent discriminator using the old policy shape, not
    # an edited persisted receipt or resigned candidate.
    with monkeypatch.context() as patch:
        def legacy(*args,**kwargs):
            value=original(*args,**kwargs)
            value.pop('output_protocol',None)
            return value
        patch.setattr(goal_applications,'policy',legacy)
        rid,result,sent=generate(data)
    assert result['status']=='PARTIAL'
    assert all('thinking_mode' not in request for request in sent)
    assert 'output_protocol' not in result['contract']['snapshot']['application_generation']
    # Back on the new policy factory, use the original stored receipt.
    application,_=confirm(data,rid,result)
    release,instance=release_instance(data,application)
    assert release['id']==instance['release_id']
