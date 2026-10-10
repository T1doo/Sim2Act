import pytest
def test_good():pass
def test_bad():assert False,'plain bounded failure'
@pytest.mark.skip(reason='own skip')
def test_skip():pass
