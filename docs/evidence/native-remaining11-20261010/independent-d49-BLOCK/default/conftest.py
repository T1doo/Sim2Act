from pathlib import Path
import pytest
@pytest.fixture(autouse=True)
def fx(request):
    with Path('effects.txt').open('a') as s:s.write('setup '+request.node.name+'\n')
    yield
    with Path('effects.txt').open('a') as s:s.write('teardown '+request.node.name+'\n')
