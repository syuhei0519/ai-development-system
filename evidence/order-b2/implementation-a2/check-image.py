"""Read exact OCI descriptors/layers, stamps and absence of build-only trust."""
import hashlib,io,json,os,sys,tarfile
from pathlib import Path
archive=Path(sys.argv[1]);service=sys.argv[2];head=sys.argv[3]
ca=Path(os.environ['SSL_CERT_FILE']).read_bytes()
checks=[];layers=[];binary=None;config=None
with tarfile.open(archive) as t:
 def read(name):return t.extractfile(name).read()
 def check(d):
  b=read('blobs/sha256/'+d['digest'].split(':')[1]);assert len(b)==d['size'];assert 'sha256:'+hashlib.sha256(b).hexdigest()==d['digest'];checks.append({'digest':d['digest'],'size':d['size']});return b
 index=json.loads(read('index.json'));assert len(index['manifests'])==1
 manifest=json.loads(check(index['manifests'][0]));config=json.loads(check(manifest['config']))
 assert config['config']['User']=='10001:10001'
 assert config['config']['Labels']['org.opencontainers.image.revision']==head
 assert config['config']['Entrypoint']==(['/server'] if service=='backend' else ['/order-server'])
 assert all(not x.startswith(('HTTP_PROXY=','HTTPS_PROXY=','http_proxy=','https_proxy=')) for x in config['config'].get('Env',[]))
 assert 'SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt' in config['config']['Env']
 assert all('build_ca' not in x and 'task-ca' not in x for x in config['config']['Env'])
 for d in manifest['layers']:
  raw=check(d)
  with tarfile.open(fileobj=io.BytesIO(raw),mode='r:*') as layer:
   names=[]
   for m in layer:
    assert not any(s in m.name for s in ['run/secrets','build_ca','task-ca.pem'])
    names.append(m.name)
    if m.isfile():
     b=layer.extractfile(m).read();assert not (ca and ca in b)
     if m.name.lstrip('./')==('server' if service=='backend' else 'order-server'):binary=b
   layers.append({'digest':d['digest'],'entries':names})
 assert binary and head.encode() in binary and ('0.0.0+git.'+head).encode() in binary
 # Application-added layers contain only the intended executable/migrations.
 extra=layers[-2:] if service=='backend' else layers[-1:]
 allowed={'server','migrations','migrations/','migrations/0001_create_accounts.sql','migrations/embed.go'} if service=='backend' else {'order-server'}
 assert all(n.lstrip('./') in allowed for l in extra for n in l['entries'])
print(json.dumps({'service':service,'archive_size':archive.stat().st_size,'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'descriptors':checks,'runtime_user':config['config']['User'],'stamp_present':True,'secret_paths_absent':True,'bundle_bytes_absent':True,'custom_trust_env_absent':True,'application_layer_entries':[l['entries'] for l in extra]},indent=2))
