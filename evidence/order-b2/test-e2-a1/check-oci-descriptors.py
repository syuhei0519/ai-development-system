"""Inspect original OCI tar bytes without extraction or repackaging.
This also works on a synthetic probe; success does not mean application success.
Usage: python check-oci-descriptors.py ORIGINAL.oci.tar
"""
import hashlib,json,sys,tarfile
from pathlib import Path
p=Path(sys.argv[1]); raw=p.read_bytes()
with tarfile.open(p,'r:') as t:
    members=t.getmembers()
    names=[m.name for m in members]
    assert len(names)==len(set(names))
    assert all(m.isfile() or m.isdir() for m in members)
    def get(name):
        assert not name.startswith('/') and '..' not in name.split('/')
        return t.extractfile(name).read()
    checks=[]
    def check(d):
        digest=d['digest']; assert digest.startswith('sha256:')
        b=get('blobs/sha256/'+digest[7:])
        assert len(b)==d['size']
        assert 'sha256:'+hashlib.sha256(b).hexdigest()==digest
        checks.append({'digest':digest,'size':len(b),'mediaType':d['mediaType']})
        return b
    idx=json.loads(get('index.json'))
    assert len(idx['manifests'])==1
    manifest=json.loads(check(idx['manifests'][0]))
    config=json.loads(check(manifest['config']))
    for layer in manifest['layers']:check(layer)
print(json.dumps({'archive_size':len(raw),'archive_sha256':hashlib.sha256(raw).hexdigest(),'descriptors':checks,'os':config.get('os'),'architecture':config.get('architecture'),'scope':'OCI descriptor integrity only'},indent=2))
