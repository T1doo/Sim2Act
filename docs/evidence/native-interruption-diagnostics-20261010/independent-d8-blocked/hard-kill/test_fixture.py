import time
def test_first_failure():assert False, 'CI_KILL_EARLIER_FAILURE'
def test_active_block():time.sleep(60)
def test_never_started():raise AssertionError('not executed')
