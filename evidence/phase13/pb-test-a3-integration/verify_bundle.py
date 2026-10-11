"""Verify local integration supplement bytes, explicit bindings and typed closure; no authority."""
import os,sys,json,hashlib
from pathlib import Path
sys.path.insert(0,os.environ['PB_CANONICAL'])
from scripts.consume_delivery import verify_handoffs
root=Path(__file__).resolve().parent
inventory=json.loads((root/'inventory.json').read_bytes());artifacts=[];blobs={}
actual={str(p.relative_to(root)) for p in root.rglob('*') if p.is_file() and p!=root/'inventory.json' and '__pycache__' not in p.parts}
assert actual=={x['path'] for x in inventory['files']}
for item in inventory['files']:
 raw=(root/item['path']).read_bytes();assert len(raw)==item['size'] and hashlib.sha256(raw).hexdigest()==item['sha256']
 # Local synthetic reference keys do not claim publication or grant authority.
 ref=dict(repository='synthetic/pb-test',commit='a'*40,path=item['path'],size=len(raw),sha256=item['sha256'])
 artifacts.append(dict(reference=ref,format=item['format'],representation='edited_derivative',public_classification='public_safe',source_alias='PUBLIC-PB-TEST-A3-INTEGRATION'))
 blobs[ref['repository'],ref['commit'],ref['path']]=raw
verify_handoffs(artifacts,blobs,'1.0')
supplement=json.loads((root/'integration-supplement.json').read_bytes())
for item in supplement['bindings'].values():
 raw=(root/item['path']).read_bytes();assert len(raw)==item['size'] and hashlib.sha256(raw).hexdigest()==item['sha256']
prior=json.loads((root/'prior-test/handoff.json').read_bytes())
assert prior['role']==supplement['role']=='test' and prior['attempt']==supplement['attempt']==3
assert prior['assignment']['scope']==supplement['scope'] and prior['status']==supplement['status']=='completed'
assert {x['ac_id'] for x in supplement['pb_results']}==set(prior['assignment']['ac_ids'])
print('PASS all bytes/types/schema/Handoff/retry closure and same-attempt integration bindings')
