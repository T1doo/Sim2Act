
def test_failure():
    assert False, "diagnostic assertion; postgresql+psycopg://fixture:fake-db-secret@localhost/db; Bearer fake-bearer-secret"

def test_pass():
    assert True

def test_interrupted():
    raise KeyboardInterrupt

def test_never_started():
    assert False, "unexecuted fixture"
