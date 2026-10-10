from pathlib import Path
import pytest
@pytest.fixture(autouse=True)
def lifecycle(request):
    with Path('fixture-effects.txt').open('a') as stream:stream.write('setup '+request.node.name+'\n')
    yield
    with Path('fixture-effects.txt').open('a') as stream:stream.write('teardown '+request.node.name+'\n')
