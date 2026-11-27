"""Inspect validated Spark output files without starting Spark or the dashboard.

Run: python3 spark/snapshot_inventory.py output/spark-delta delta
The report describes physical files, not logical row counts or decoded data.
"""
import argparse
import json
from pathlib import Path

from delta_snapshot import active_delta_files
from parquet_footer import validate_parquet_part
from verify_outputs import TABLES


def build_inventory(root: Path, fmt: str) -> dict:
    """Return a deterministic inventory of the five demo output tables."""
    if fmt not in {"parquet", "delta"}:
        raise ValueError(f"Unsupported format: {fmt}")
    root = Path(root).resolve()
    tables = []
    for table in TABLES:
        directory = root / table
        if not directory.is_dir():
            raise ValueError(f"Missing {fmt} table: {directory}")
        if fmt == "delta":
            parts = active_delta_files(directory)
        else:
            parts = sorted(p for p in directory.glob("part-*.parquet") if p.is_file())
        if not parts:
            raise ValueError(f"Missing Parquet part file: {directory}")
        files = []
        for part in parts:
            validate_parquet_part(part)
            files.append({"path": part.relative_to(directory).as_posix(),
                          "bytes": part.stat().st_size})
        tables.append({"table": table, "file_count": len(files),
                       "bytes": sum(f["bytes"] for f in files), "files": files})
    return {"format": fmt,
            "scope": "active_delta_snapshot" if fmt == "delta" else "parquet_parts",
            "table_count": len(tables),
            "file_count": sum(t["file_count"] for t in tables),
            "bytes": sum(t["bytes"] for t in tables),
            "tables": tables}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("format", choices=["parquet", "delta"])
    args = parser.parse_args()
    try:
        report = build_inventory(args.root, args.format)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Snapshot inventory failed: {exc}\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
