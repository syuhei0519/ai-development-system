"""Offline full-byte/type/Handoff closure check for the Review candidate; no authority."""
import hashlib
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, os.environ['PB_BASE'])
from scripts.consume_delivery import verify_handoffs

root = Path(__file__).resolve().parent
inventory = json.loads((root / 'inventory.json').read_bytes())
actual = {str(f.relative_to(root)) for f in root.rglob('*')
          if f.is_file() and '__pycache__' not in f.parts and f != root / 'inventory.json'}
assert actual == {item['path'] for item in inventory['files']}
artifacts, blobs = [], {}
for item in inventory['files']:
    path = root / item['path']
    assert not path.is_symlink()
    raw = path.read_bytes()
    assert len(raw) == item['size']
    assert hashlib.sha256(raw).hexdigest() == item['sha256'], item['path']
    ref = dict(repository='synthetic/pb-review', commit='a' * 40, path=item['path'],
               size=len(raw), sha256=item['sha256'])
    artifacts.append(dict(reference=ref, format=item['format'], representation='edited_derivative',
                          public_classification='public_safe', source_alias='PUBLIC-PB-REVIEW-A1'))
    blobs[ref['repository'], ref['commit'], ref['path']] = raw
verify_handoffs(artifacts, blobs, '1.0')
supplement=json.loads((root/'integration-supplement.json').read_bytes())
for ref in supplement['bindings'].values():
    raw=(root/ref['path']).read_bytes()
    assert len(raw)==ref['size'] and hashlib.sha256(raw).hexdigest()==ref['sha256']
assert supplement['status']=='completed' and supplement['head']=='5e1980eff37107bca7089aca7c457180d00ff020'
print('PASS full bytes/types/Handoff/retry and Test supplement closure; no authority')
