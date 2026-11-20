"""Validate Spark demo output structure for Parquet and Delta Lake formats."""
from pathlib import Path
import argparse
import re

TABLES = ('warehouses', 'stores', 'routes', 'route_opportunities', 'network_summary')
DELTA_COMMIT = re.compile(r'^\d{20}\.json$')


def verify(root: Path, fmt: str) -> None:
    if fmt not in {'parquet', 'delta'}:
        raise ValueError(f'Unsupported format: {fmt}')
    for table in TABLES:
        directory = root / table
        if not directory.is_dir():
            raise ValueError(f'Missing {fmt} table: {directory}')
        if not any(p.is_file() and p.stat().st_size > 0 for p in directory.glob('part-*.parquet')):
            raise ValueError(f'Missing nonempty Parquet part file: {directory}')
        if fmt == 'delta':
            log = directory / '_delta_log'
            if not log.is_dir() or not any(p.is_file() and DELTA_COMMIT.fullmatch(p.name) and p.stat().st_size > 0 for p in log.iterdir()):
                raise ValueError(f'Missing Delta transaction commit: {log}')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('format', choices=['parquet', 'delta'])
    args = parser.parse_args()
    verify(args.root, args.format)
    print(f'Validated {len(TABLES)} {args.format} tables at {args.root}')


if __name__ == '__main__':
    main()
