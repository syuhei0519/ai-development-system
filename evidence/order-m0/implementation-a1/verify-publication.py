#!/usr/bin/env python3
"""Publisher's fresh byte/type/closure check; does not issue Consumer authority.
Usage: python verify-publication.py FIXED_SYSTEM_CHECKOUT MANIFEST
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

root=Path(sys.argv[1]).resolve()
expected='0083151aa2f6b2aaf0e1db64ada3f196ed766e48'
actual=subprocess.check_output(['git','-C',str(root),'rev-parse',expected]).decode().strip()
assert actual==expected
# The supplied checkout may be on an evidence branch; trusted scripts must still
# have exactly the canonical fixed-System bytes, including transitive imports.
for directory in ('scripts','contracts'):
 for path in (root/directory).rglob('*'):
  if not path.is_file() or '__pycache__' in path.parts:continue
  relative=str(path.relative_to(root))
  canonical=subprocess.check_output(['git','-C',str(root),'show',expected+':'+relative])
  assert canonical==path.read_bytes()
sys.path.insert(0,str(root/'scripts'))
from consume_delivery import GitSource, schema, reference_key, verify_handoffs, check_reference, parse
manifest_raw=Path(sys.argv[2]).read_bytes();manifest=parse(manifest_raw)
schema('artifact-delivery',manifest)
with tempfile.TemporaryDirectory(prefix='m0-publication-') as temp:
 source=GitSource(temp);blobs={}
 for item in manifest['artifacts']:
  ref=item['reference'];check_reference(ref);raw=source.read(ref)
  assert len(raw)==ref['size'] and hashlib.sha256(raw).hexdigest()==ref['sha256']
  key=reference_key(ref);assert key not in blobs;blobs[key]=raw
 tree=verify_handoffs(manifest['artifacts'],blobs,'1.2',manifest['knowledge_bindings'],manifest['slot_bindings'],manifest['candidate_bindings'],source)
 print(json.dumps({'result':'pass','manifest_sha256':hashlib.sha256(manifest_raw).hexdigest(),
  'explicit_objects':len(blobs),'tree_objects':len(tree),'total_unique_objects':len(set(blobs)|set(tree)),
  'authority_granted':False},sort_keys=True))
