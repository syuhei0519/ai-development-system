"""Offline candidate bytes and typed closure verification; no publication or authority."""
import os,sys,json,hashlib
from pathlib import Path
base=Path(os.environ['PB_BASE']);sys.path.insert(0,str(base))
from scripts.consume_delivery import verify_handoffs
root=Path(__file__).resolve().parent
inv=json.loads((root/'inventory.json').read_bytes())
listed={x['path'] for x in inv['files']}
actual={str(p.relative_to(root)) for p in root.rglob('*') if p.is_file() and p != root/'inventory.json' and '__pycache__' not in p.parts}
assert listed==actual,(listed-actual,actual-listed)
artifacts=[];blobs={}
# Synthetic local keys exercise production closure validation; these are not published refs.
for item in inv['files']:
 raw=(root/item['path']).read_bytes();assert len(raw)==item['size'] and hashlib.sha256(raw).hexdigest()==item['sha256'],item['path']
 ref=dict(repository='synthetic/pb-test',commit='a'*40,path=item['path'],size=len(raw),sha256=item['sha256'])
 artifacts.append(dict(reference=ref,format=item['format'],representation='edited_derivative',public_classification='public_safe',source_alias='PUBLIC-PB-TEST-A3'))
 blobs[ref['repository'],ref['commit'],ref['path']]=raw
verify_handoffs(artifacts,blobs,'1.0')
print('PASS all candidate bytes, types, Handoff/retry transitive closure; no publication authority')
