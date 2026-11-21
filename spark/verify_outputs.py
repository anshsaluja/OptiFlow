"""Validate Spark demo Parquet files and Delta transaction histories."""
import argparse
import json
import re
from pathlib import Path

TABLES = ("warehouses", "stores", "routes", "route_opportunities", "network_summary")
DELTA_COMMIT = re.compile(r"^[0-9]{20}\.json$")
ACTIONS = {"add", "remove", "metaData", "protocol", "commitInfo", "txn", "cdc", "domainMetadata", "sidecar"}


def verify(root: Path, fmt: str) -> None:
    if fmt not in {"parquet", "delta"}:
        raise ValueError(f"Unsupported format: {fmt}")
    for table in TABLES:
        directory = root / table
        if not directory.is_dir():
            raise ValueError(f"Missing {fmt} table: {directory}")
        if not any(p.is_file() and p.stat().st_size > 0 for p in directory.glob("part-*.parquet")):
            raise ValueError(f"Missing nonempty Parquet part file: {directory}")
        if fmt != "delta":
            continue
        log = directory / "_delta_log"
        if not log.is_dir():
            raise ValueError(f"Missing Delta transaction log: {log}")
        commits = sorted(p for p in log.iterdir() if p.is_file() and DELTA_COMMIT.fullmatch(p.name))
        if not commits or commits[0].name != "00000000000000000000.json":
            raise ValueError(f"Missing initial Delta commit: {log}")
        for expected, commit in enumerate(commits):
            if int(commit.stem) != expected:
                raise ValueError(f"Gap in Delta commit versions: {log}")
            try:
                lines = commit.read_text(encoding="utf-8").splitlines()
                if not lines:
                    raise ValueError("empty transaction log")
                for number, line in enumerate(lines, 1):
                    if not line.strip():
                        raise ValueError(f"blank Delta action at line {number}")
                    action = json.loads(line)
                    if not isinstance(action, dict) or len(action) != 1:
                        raise ValueError(f"expected exactly one Delta action at line {number}")
                    name, payload = next(iter(action.items()))
                    if name not in ACTIONS or not isinstance(payload, dict):
                        raise ValueError(f"invalid Delta action or payload at line {number}")
            except (UnicodeError, json.JSONDecodeError, ValueError) as exc:
                raise ValueError(f"Invalid Delta transaction commit {commit}: {exc}") from exc


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("format", choices=["parquet", "delta"])
    args = parser.parse_args()
    verify(args.root, args.format)
    print(f"Validated {len(TABLES)} {args.format} tables at {args.root}")


if __name__ == "__main__":
    main()
