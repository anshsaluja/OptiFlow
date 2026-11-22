"""Fast structural checks for Spark Parquet part files (not full decoding)."""
from pathlib import Path
import struct

MAGIC = b"PAR1"


def validate_parquet_part(path: Path) -> None:
    """Check Parquet's leading magic and metadata footer bounds."""
    path = Path(path)
    size = path.stat().st_size
    if size < 12:
        raise ValueError(f"Invalid Parquet part {path}: too short ({size} bytes)")
    with path.open("rb") as stream:
        if stream.read(4) != MAGIC:
            raise ValueError(f"Invalid Parquet part {path}: bad header")
        stream.seek(-8, 2)
        footer = stream.read(8)
    if footer[4:] != MAGIC:
        raise ValueError(f"Invalid Parquet part {path}: bad footer")
    metadata_length = struct.unpack("<I", footer[:4])[0]
    if not 0 < metadata_length <= size - 12:
        raise ValueError(f"Invalid Parquet part {path}: invalid metadata length {metadata_length}")


def validate_parquet_parts(directory: Path) -> None:
    parts = sorted(path for path in Path(directory).glob("part-*.parquet") if path.is_file())
    if not parts:
        raise ValueError(f"Missing Parquet part file: {directory}")
    for part in parts:
        validate_parquet_part(part)
