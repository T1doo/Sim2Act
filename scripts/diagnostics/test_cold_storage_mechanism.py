"""SQLite mechanism proofs only; not a production transaction/CAS design."""

import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path


class StorageMechanismUnits(unittest.TestCase):
    def setUp(self):
        root = self.enterContext(tempfile.TemporaryDirectory(prefix="g0-sql-mechanism-"))
        self.a = sqlite3.connect(Path(root) / "synthetic.db", timeout=0, isolation_level=None)
        self.addCleanup(self.a.close)
        self.b = sqlite3.connect(Path(root) / "synthetic.db", timeout=0, isolation_level=None)
        self.addCleanup(self.b.close)
        self.a.execute("create table run (version integer, fence integer, lease real, deadline real)")
        self.a.execute("insert into run values (1, 1, 30, 300)")

    def tearDown(self):
        self.assertFalse(any(k == "sim2act" or k.startswith("sim2act.") for k in sys.modules))

    def test_immediate_transaction_blocks_other_writer_even_if_only_reading(self):
        self.a.execute("begin immediate")
        self.assertEqual(self.a.execute("select version from run").fetchone(), (1,))
        with self.assertRaises(sqlite3.OperationalError) as caught:
            self.b.execute("begin immediate")
        self.assertEqual(caught.exception.sqlite_errorcode, sqlite3.SQLITE_BUSY)
        self.a.rollback()
        self.b.execute("begin immediate")
        self.b.execute("update run set lease=40 where lease>10")
        self.b.commit()
        self.assertEqual(self.a.execute("select lease from run").fetchone(), (40,))

    def test_stale_version_fence_and_original_expiry_cannot_pass_scalar_cas(self):
        # A completed short read leaves no transaction alive during computation.
        version, fence = self.a.execute("select version,fence from run").fetchone()
        self.assertFalse(self.a.in_transaction)
        self.b.execute("update run set version=2,fence=2")
        self.a.execute("begin immediate")
        sql = """update run set version=version+1
            where version=? and fence=? and lease>? and deadline>?"""
        self.assertEqual(self.a.execute(sql, (version, fence, 20, 20)).rowcount, 0)
        self.a.rollback()
        for now in (30, 301):
            self.a.execute("begin immediate")
            self.assertEqual(self.a.execute(sql, (2, 2, now, now)).rowcount, 0)
            self.a.rollback()
        self.assertEqual(self.a.execute("select version,fence,lease,deadline from run").fetchone(),
                         (2, 2, 30, 300))
        # This tests scalar predicates only, NOT complete authorization/read-set
        # coverage, phantom detection or safe reuse of the original graph guard.


if __name__ == "__main__":
    unittest.main()
