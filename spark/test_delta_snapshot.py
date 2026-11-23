"""Regression tests for conservative Delta active snapshot reconstruction."""
import json
import tempfile
import unittest
from pathlib import Path
from delta_snapshot import active_delta_files

class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.table = Path(self.tmp.name)
        (self.table / '_delta_log').mkdir()
        (self.table / 'part-0.parquet').write_bytes(b'PAR1')
        self.commit(0, {'protocol': {'minReaderVersion': 1, 'minWriterVersion': 2}},
                    {'add': {'path': 'part-0.parquet'}})

    def commit(self, n, *actions):
        (self.table / '_delta_log' / f'{n:020d}.json').write_text(
            ''.join(json.dumps(a) + '\n' for a in actions))

    def test_initial(self):
        self.assertEqual([self.table / 'part-0.parquet'], active_delta_files(self.table))

    def test_removed_historical_file(self):
        (self.table / 'part-1.parquet').write_bytes(b'PAR1')
        self.commit(1, {'remove': {'path': 'part-0.parquet'}},
                    {'add': {'path': 'part-1.parquet'}})
        (self.table / 'part-0.parquet').unlink()
        self.assertEqual([self.table / 'part-1.parquet'], active_delta_files(self.table))

    def test_missing_active(self):
        (self.table / 'part-0.parquet').unlink()
        with self.assertRaisesRegex(ValueError, 'Missing active'):
            active_delta_files(self.table)

    def test_gap(self):
        self.commit(2, {'commitInfo': {}})
        with self.assertRaisesRegex(ValueError, 'Gap'):
            active_delta_files(self.table)

    def test_traversal(self):
        self.commit(1, {'add': {'path': '%2e%2e/outside.parquet'}})
        with self.assertRaisesRegex(ValueError, 'Unsafe'):
            active_delta_files(self.table)

    def test_protocol(self):
        self.commit(1, {'protocol': {'minReaderVersion': 3}})
        with self.assertRaisesRegex(ValueError, 'protocol'):
            active_delta_files(self.table)

    def test_checkpoint(self):
        (self.table / '_delta_log' / '_last_checkpoint').write_text('{}')
        with self.assertRaisesRegex(ValueError, 'checkpoints'):
            active_delta_files(self.table)

    def test_duplicate_keys(self):
        (self.table / '_delta_log' / '00000000000000000001.json').write_text(
            '{"add":{"path":"a.parquet","path":"b.parquet"}}\n')
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            active_delta_files(self.table)

    def test_deletion_vector(self):
        self.commit(1, {'add': {'path': 'part-0.parquet', 'deletionVector': {'x': 1}}})
        with self.assertRaisesRegex(ValueError, 'deletion vectors'):
            active_delta_files(self.table)

if __name__ == '__main__':
    unittest.main()
