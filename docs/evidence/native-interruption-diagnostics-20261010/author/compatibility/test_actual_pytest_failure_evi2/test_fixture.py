
def test_failure():
    assert False, "diagnostic assertion; postgresql+psycopg://fixture:fake-db-secret@localhost/db; Bearer fake-bearer-secret"

def test_pass():
    assert True

