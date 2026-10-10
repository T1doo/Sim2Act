import pytest
def test_selected_pass():pass
def test_selected_fail():assert False, 'own bounded failure'
def test_unselected():raise AssertionError('must not be selected')
@pytest.mark.skip(reason='own expected skip')
def test_selected_skip():pass
