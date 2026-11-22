import struct
import tempfile
import unittest
from pathlib import Path
from parquet_footer import validate_parquet_part, validate_parquet_parts


def envelope(metadata=b'\x00'):
    return b'PAR1' + metadata + struct.pack('<I', len(metadata)) + b'PAR1'


class ParquetFooterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.part = self.root / 'part-00000.parquet'

    def test_valid_envelope(self):
        self.part.write_bytes(envelope())
        validate_parquet_part(self.part)

    def test_four_byte_placeholder_rejected(self):
        self.part.write_bytes(b'PAR1')
        with self.assertRaisesRegex(ValueError, 'too short'):
            validate_parquet_part(self.part)

    def test_truncated_footer_rejected(self):
        self.part.write_bytes(envelope()[:-2])
        with self.assertRaises(ValueError):
            validate_parquet_part(self.part)

    def test_invalid_header_rejected(self):
        self.part.write_bytes(b'NOPE' + envelope()[4:])
        with self.assertRaisesRegex(ValueError, 'header'):
            validate_parquet_part(self.part)

    def test_invalid_footer_rejected(self):
        self.part.write_bytes(envelope()[:-4] + b'NOPE')
        with self.assertRaisesRegex(ValueError, 'footer'):
            validate_parquet_part(self.part)

    def test_zero_metadata_rejected(self):
        self.part.write_bytes(b'PAR1' + struct.pack('<I', 0) + b'PAR1')
        with self.assertRaisesRegex(ValueError, 'metadata length'):
            validate_parquet_part(self.part)

    def test_metadata_overflow_rejected(self):
        self.part.write_bytes(b'PAR1' + b'\x00' + struct.pack('<I', 100) + b'PAR1')
        with self.assertRaisesRegex(ValueError, 'metadata length'):
            validate_parquet_part(self.part)

    def test_missing_parts_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Missing Parquet'):
            validate_parquet_parts(self.root)

    def test_two_valid_parts(self):
        self.part.write_bytes(envelope())
        (self.root / 'part-00001.parquet').write_bytes(envelope(b'\x00\x01'))
        validate_parquet_parts(self.root)

    def test_corrupt_second_part_rejected(self):
        self.part.write_bytes(envelope())
        (self.root / 'part-00001.parquet').write_bytes(b'PAR1')
        with self.assertRaisesRegex(ValueError, 'too short'):
            validate_parquet_parts(self.root)


if __name__ == '__main__':
    unittest.main()
