"""Small actual-SQLite storage-class order boundary; no Worker/model execution."""

import sqlite3

from sim2act import natural_spec_runtime as runtime


def test_cold_attempt_order_matches_actual_sqlite_mixed_storage_classes():
    # Typeless raw columns retain corrupt storage classes instead of applying
    # affinity before the comparison. Sort actual driver readback values.
    pairs = [
        (None, None), (None, -1), (None, 0.5), (None, "2"), (None, b"2"),
        (-7, "low"), (-3.5, "real"), (0, "zero"), (2, "integer"), (2.0, "real-tie"),
        (4, None), (4, -2), (4, 0.5), (4, "0"), (4, b"\x00"),
        ("10", "lexical"), ("2", "numeric-looking-text"), ("é", "unicode"),
        ("𝄞", "astral"), (b"\x00", "blob-low"), (b"\xff", "blob-high"),
    ]
    with sqlite3.connect(":memory:") as connection:
        connection.execute("CREATE TABLE raw_order (seq INTEGER PRIMARY KEY, created_at, attempt_id)")
        connection.executemany("INSERT INTO raw_order VALUES (?, ?, ?)",
            [(index, created, aid) for index, (created, aid) in enumerate(pairs)])
        raw = connection.execute("SELECT seq, created_at, attempt_id FROM raw_order").fetchall()
        expected = connection.execute(
            "SELECT seq FROM raw_order ORDER BY created_at ASC, attempt_id ASC").fetchall()
    rows = [dict(seq=seq, created_at=created, id=aid) for seq, created, aid in raw]
    actual = sorted(rows, key=runtime._cold_attempt_order)
    assert [row["seq"] for row in actual] == [row[0] for row in expected]
    assert len(actual) == len(rows) == len(pairs)
    # Explicit scalar-key composition must agree with the fixed Attempt key.
    assert actual == sorted(rows, key=lambda row: (
        runtime._cold_sqlite_order(row["created_at"]), runtime._cold_sqlite_order(row["id"])))
