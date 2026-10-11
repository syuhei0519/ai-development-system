#!/usr/bin/env python3
"""Verify the synthetic bundle's exact bytes without rewriting the sources."""
from pathlib import Path
import hashlib
import json

root = Path(__file__).resolve().parent
manifest = json.loads((root / 'manifest.json').read_bytes())
expected_names = {entry['path'] for entry in manifest['files']} | {'manifest.json'}
assert {p.name for p in root.iterdir() if p.is_file()} == expected_names
for entry in manifest['files']:
    data = (root / entry['path']).read_bytes()
    assert len(data) == entry['size_bytes'], entry['path']
    assert hashlib.sha256(data).hexdigest() == entry['sha256'], entry['path']
    assert data.count(b'\n') == entry['lf_count'], entry['path']
    assert data.endswith(b'\n') and b'\r' not in data, entry['path']
    data.decode('utf-8')
    print('PASS bytes', entry['path'], len(data))
source = json.loads((root / 'source.json').read_bytes())
assert type(source['integer_one']) is int and source['integer_one'] == 1
assert type(source['boolean_true']) is bool and source['boolean_true'] is True
assert type(source['array'][0]) is int and type(source['array'][1]) is bool
assert source['sentinel'] == 'SYNTHETIC-END-JSON-20261011-終端'
assert source['escaped'] == '"quoted" \\backslash\nembedded LF\tembedded tab'
assert source['literal_escape'] == '\\n is two characters'
assert source['unicode'][2] != source['unicode'][3]
markdown = (root / 'source.md').read_bytes()
assert len(markdown) > 32768
assert markdown.endswith('SYNTHETIC-END-MARKDOWN-20261011-OMEGA-終端\n'.encode())
handoff = json.loads((root / 'handoff.json').read_bytes())
assert handoff['schema_version'] == '2.0' and handoff['role'] == 'research-design'
assert handoff['task_id'].startswith('SYNTHETIC-')
assert handoff['publication'] == 'synthetic_sample'
assert handoff['artifacts'][0]['revision'] == 'sha256:' + hashlib.sha256(markdown).hexdigest()
assert 'final_assessment' not in handoff
print('PASS types, escapes, Unicode, sentinels and artifact digest; not business approval')
