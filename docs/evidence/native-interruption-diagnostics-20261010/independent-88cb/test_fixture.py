import pytest
MESSAGES=["authorization='Basic CI_ORIGINAL_BASIC' password='first CI_ORIGINAL_SPACED'", 'password="first\\" CI_ESCAPED_QUOTE \\\\ CI_ESCAPED_SLASH"', 'authorization=Basic CI_UNQUOTED_BASIC tail CI_UNQUOTED_TAIL', "password='first CI_MULTILINE_FIRST\nsecond CI_MULTILINE_SECOND'\nordinary diagnostic survives", '{"api_key": "first CI_JSON_API second", "secret": "CI_JSON_SECRET"}', 'POSTGRESQL+psycopg://ciuser:CI_UPPER_DB@127.0.0.1/db\nBearer CI_BEARER_VALUE']
@pytest.mark.parametrize("index",range(len(MESSAGES)))
def test_material(index):
    assert False, MESSAGES[index]
