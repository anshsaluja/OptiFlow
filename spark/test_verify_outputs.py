import tempfile
import unittest
from pathlib import Path

from verify_outputs import TABLES, verify


class VerifyOutputsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for table in TABLES:
            folder = self.root / table
            folder.mkdir()
            (folder / 'part-00000.parquet').write_bytes(b'PAR1')
            log = folder / '_delta_log'
            log.mkdir()
            (log / '00000000000000000000.json').write_text('{"commitInfo":{}}')

    def test_valid_parquet_and_delta(self):
        verify(self.root, 'parquet')
        verify(self.root, 'delta')

    def test_missing_table(self):
        import shutil
        shutil.rmtree(self.root / TABLES[0])
        with self.assertRaisesRegex(ValueError, 'Missing parquet table'):
            verify(self.root, 'parquet')

    def test_empty_part_rejected(self):
        (self.root / TABLES[0] / 'part-00000.parquet').write_bytes(b'')
        with self.assertRaisesRegex(ValueError, 'Missing nonempty'):
            verify(self.root, 'parquet')

    def test_delta_requires_numbered_commit(self):
        log = self.root / TABLES[0] / '_delta_log'
        (log / '00000000000000000000.json').unlink()
        (log / 'notes.json').write_text('{}')
        with self.assertRaisesRegex(ValueError, 'Missing Delta transaction'):
            verify(self.root, 'delta')


if __name__ == '__main__':
    unittest.main()
