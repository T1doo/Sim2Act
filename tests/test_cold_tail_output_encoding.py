"""No DB/model/Mock: exact diagnostic representation of complete native rows."""

import json

from sqlalchemy.sql.elements import quoted_name
from test_cold_configured_semantic_tail import exact_output


def test_complete_output_row_keys_bytes_and_container_types_are_serializable():
    raw = {quoted_name('id', None): 'run', quoted_name('created_at', False): 123.0,
        'archive': (b'original bytes', [True, 1, 1.0, None])}
    encoded = exact_output(raw)
    assert json.loads(json.dumps(encoded)) == encoded
    assert ['quoted-name', 'id', None] in [pair[0] for pair in encoded[1]]
    assert ['quoted-name', 'created_at', False] in [pair[0] for pair in encoded[1]]
    assert ['str', 'archive'] in [pair[0] for pair in encoded[1]]
