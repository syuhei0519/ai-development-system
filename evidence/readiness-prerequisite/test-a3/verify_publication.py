"""Fresh public typed closure check using baseline primitives; no Consumer authorization.
Usage: python verify_publication.py BASELINE MANIFEST PUBLICATION OUTPUT_JSON
This creates a publication observation, never a Consumption Receipt or permission.
"""
import datetime,json,pathlib,sys,tempfile
base,mp,pp,out=map(pathlib.Path,sys.argv[1:]);sys.path.insert(0,str(base.resolve()))
from scripts.consume_delivery import GitSource,parse,schema,reference_key,digest,require,check_reference,verify_handoffs,MAX_BUNDLE
mraw=mp.read_bytes();m=parse(mraw);p=parse(pp.read_bytes())
schema('artifact-delivery',m);schema('publication-receipt',p)
require(m['schema_version']==p['schema_version']=='1.2','version mismatch')
require(p['manifest_sha256']==digest(mraw) and p['artifacts']==m['artifacts'],'publication bindings mismatch')
with tempfile.TemporaryDirectory(prefix='publication-fresh-') as t:
 source=GitSource(t);blobs={}
 for item in m['artifacts']:
  ref=item['reference'];check_reference(ref);key=reference_key(ref)
  require(key not in blobs,'duplicate artifact');raw=source.read(ref)
  require(len(raw)==ref['size'] and digest(raw)==ref['sha256'],'bytes/size/hash mismatch');blobs[key]=raw
 require(sum(map(len,blobs.values()))<=MAX_BUNDLE,'bundle bound')
 trees=verify_handoffs(m['artifacts'],blobs,'1.2',m['knowledge_bindings'],m['slot_bindings'],m['candidate_bindings'],source)
 result=dict(document_type='publication_verification_observation',observed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),result='pass',baseline_revision='0083151aa2f6b2aaf0e1db64ada3f196ed766e48',manifest_sha256=digest(mraw),publication_receipt_sha256=digest(pp.read_bytes()),artifacts=len(m['artifacts']),slots=len(m['slot_bindings']),payload_bytes=sum(map(len,blobs.values())),tree_member_count=len(trees),verification='fresh isolated Git; all raw bytes size/hash/object types/JSON/Handoff/upstream/retry/structural slots; no Consumer authorization',authority_granted=False)
 out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
