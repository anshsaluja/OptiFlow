"""Conservative active-file reconstruction for basic Delta JSON logs.

Not a general-purpose Delta reader: unsupported features fail closed.
"""
import json
import re
from pathlib import Path
from urllib.parse import unquote

_COMMIT = re.compile(r"[0-9]{20}\.json\Z")
_ALLOWED = {"add", "remove", "metaData", "protocol", "commitInfo", "txn"}

def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError(f"Duplicate Delta JSON key: {key}")
        result[key] = value
    return result

def _constant(value):
    raise ValueError(f"Invalid JSON constant: {value}")

def _path(table, value):
    if not isinstance(value, str) or not value:
        raise ValueError("Delta action missing path")
    decoded = unquote(value)
    if '%' in decoded or '\\' in decoded or '\x00' in decoded:
        raise ValueError(f"Unsupported Delta path encoding: {value}")
    relative = Path(decoded)
    if relative.is_absolute() or any(p in ('', '.', '..') for p in decoded.split('/')):
        raise ValueError(f"Unsafe Delta path: {value}")
    resolved = (table / relative).resolve()
    if not resolved.is_relative_to(table.resolve()):
        raise ValueError(f"Delta path escapes table: {value}")
    if resolved.suffix != '.parquet':
        raise ValueError(f"Expected Delta Parquet path: {value}")
    return resolved

def active_delta_files(table: Path) -> list[Path]:
    """Return active Parquet paths for an uncheckpointed basic Delta table."""
    table = Path(table)
    log = table / '_delta_log'
    if not log.is_dir():
        raise ValueError(f"Missing Delta transaction log: {log}")
    if any(p.name.endswith('.checkpoint.parquet') or p.name == '_last_checkpoint'
           or '.checkpoint.' in p.name for p in log.iterdir()):
        raise ValueError('Delta checkpoints are unsupported')
    commits = sorted(p for p in log.iterdir() if _COMMIT.fullmatch(p.name))
    if not commits or commits[0].stem != '00000000000000000000':
        raise ValueError('Missing initial Delta commit')
    active = {}
    for version, commit in enumerate(commits):
        if int(commit.stem) != version:
            raise ValueError(f"Gap in Delta commit versions at {version}")
        lines = commit.read_text(encoding='utf-8').splitlines()
        if not lines:
            raise ValueError(f"Empty Delta commit: {commit}")
        for number, line in enumerate(lines, 1):
            if not line.strip():
                raise ValueError(f"Blank Delta action: {commit}:{number}")
            action = json.loads(line, object_pairs_hook=_pairs, parse_constant=_constant)
            if not isinstance(action, dict) or len(action) != 1:
                raise ValueError(f"Invalid Delta action: {commit}:{number}")
            kind, payload = next(iter(action.items()))
            if kind not in _ALLOWED or not isinstance(payload, dict):
                raise ValueError(f"Unsupported Delta action: {kind}")
            if kind == 'protocol':
                if (payload.get('minReaderVersion', 1) > 1
                        or payload.get('minWriterVersion', 2) > 2
                        or payload.get('readerFeatures') or payload.get('writerFeatures')):
                    raise ValueError('Unsupported Delta protocol/features')
            elif kind == 'metaData':
                config = payload.get('configuration') or {}
                if not isinstance(config, dict) or any(
                        k.startswith('delta.columnMapping.') or k.startswith('delta.enableDeletionVectors')
                        for k in config):
                    raise ValueError('Unsupported Delta table configuration')
            elif kind in ('add', 'remove'):
                path = _path(table, payload.get('path'))
                if kind == 'add':
                    if payload.get('deletionVector') is not None:
                        raise ValueError('Delta deletion vectors are unsupported')
                    active[path] = True
                else:
                    active.pop(path, None)
    if not active:
        raise ValueError(f"No active Delta Parquet files: {table}")
    for path in active:
        if not path.is_file():
            raise ValueError(f"Missing active Delta Parquet file: {path}")
    return sorted(active)
