#!/usr/bin/env python3
"""Generate and validate a fictional 1.1 bundle; no live result or authority."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT/'tests')]
from preparation_completion_fixture import build_preparation
from scripts.validate_issue_completion import validate_files, instant

root = Path(sys.argv[1]).absolute()
root.mkdir(parents=True, exist_ok=False)
a, c = build_preparation(root)
print(validate_files(root/'completion.json', root/'context.json', a['context_sha256'],
                     root/'handoff.json', now=instant('2030-01-03T12:00:00Z')))
print('SYNTHETIC REPLAY context SHA-256:', a['context_sha256'])
