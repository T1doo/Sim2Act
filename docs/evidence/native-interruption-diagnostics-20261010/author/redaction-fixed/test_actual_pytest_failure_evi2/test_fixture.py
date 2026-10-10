
def test_failure():
    assert False, "diagnostic assertion; postgresql+psycopg://fixture:fake-db-secret@localhost/db; Bearer fake-bearer-secret; authorization='Basic fake-basic-secret'; password='first fake-spaced-password'; secret='first\\' fake-escaped-secret'; authorization=Basic fake-unquoted-secret"

def test_pass():
    assert True

