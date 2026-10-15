# Reviewed public edited derivative of completed Implementation self-verification; delivery-only preparation, no new measurement. Private originals retained; no private-original equivalence certification.
"""Implementation self-verification measurements. Local private output; external writes always mocked.
source ROOT: scan exact archive context using pinned Trivy and existing trust.
image ROOT SERVICE: byte-compare OCI transport and inspect loaded runtime config.
consumer BACKEND M0 M1: actual fixed consumer compatibility and disabled values.
"""
import sys,os,json,pathlib,subprocess,hashlib,tarfile,io,gzip,importlib.util,secrets
from unittest.mock import patch
P=pathlib.Path
HEAD='24083aba485abd6b37bcbe71736fb543a847dcc6'
def sha(b): return hashlib.sha256(b).hexdigest()
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def run(args,**kw):return subprocess.run(args,check=True,capture_output=True,**kw).stdout
mode=sys.argv[1]
if mode=='build':
 sys.argv=[sys.argv[0],*sys.argv[2:]]
 import os,json,pathlib,subprocess,time,hashlib,sys,tempfile
 # Self-verification reproducer: existing proxy/CA only; keep output private.
 # Use a pristine git archive of 24083aba485abd6b37bcbe71736fb543a847dcc6.
 # Invoke separately with valid, missing, invalid; do not overlap on one worker.
 # Two explicit security options require the task owner's authorization.
 root=pathlib.Path(sys.argv[1]).resolve()
 context=pathlib.Path(sys.argv[2]).resolve()
 priv=root
 priv.mkdir(mode=0o700,parents=True,exist_ok=True)
 mode=sys.argv[3] if len(sys.argv)>3 else 'valid'
 assert mode in ('valid','missing','invalid','empty','nonexistent')
 image='moby/buildkit@sha256:586cf37ba4bafd151058aa9c857fe06036942a2a765d7dc5630098cf31834200'
 name='order-b2-test-'+os.urandom(8).hex()
 def run(args,**kw): return subprocess.run(args,check=True,**kw)
 cfg=json.loads((pathlib.Path(os.environ.get('DOCKER_CONFIG',str(pathlib.Path.home()/'.docker')))/'config.json').read_text())
 endpoint=os.environ.get('DOCKER_HOST','unix:///var/run/docker.sock')
 proxy=cfg.get('proxies',{}).get(endpoint,cfg.get('proxies',{}).get('default',{}))
 env={}
 for key,var in [('httpProxy','HTTP_PROXY'),('httpsProxy','HTTPS_PROXY'),('noProxy','NO_PROXY')]:
     value=proxy.get(key)
     if value is not None: env[var]=env[var.lower()]=value
 assert env.get('HTTPS_PROXY')
 ca=os.environ['SSL_CERT_FILE']
 assert pathlib.Path(ca).is_file()
 envfile=priv/'buildkit.env'
 envfile.write_text(''.join(k+'='+v+'\n' for k,v in env.items())+'SSL_CERT_FILE=/etc/task-ca.pem\n')
 envfile.chmod(0o600)
 before=run(['docker','image','ls','-q','--no-trunc'],capture_output=True,text=True).stdout.splitlines()
 image_present=subprocess.run(['docker','image','inspect',image],capture_output=True).returncode==0
 (priv/'images-before.json').write_text(json.dumps(before))
 log=open(priv/'buildkit-private.log','w')
 try:

  if not image_present: run(['docker','pull',image],stdout=log,stderr=log)
  run(['docker','create','--name',name,'--network','bridge','--security-opt','seccomp=unconfined','--security-opt','systempaths=unconfined','--env-file',str(envfile),'--mount',f'type=bind,src={ca},dst=/etc/task-ca.pem,readonly','--mount',f'type=bind,src={context},dst=/diagnosis,readonly',image],stdout=log,stderr=log)
  inspect=json.loads(run(['docker','inspect',name],capture_output=True,text=True).stdout)[0]
  h=inspect['HostConfig']; c=inspect['Config']
  assert h['NetworkMode']=='bridge' and h['Privileged']==False and not h['CapAdd']
  assert c['User']=='1000:1000' and not inspect['AppArmorProfile']
  assert h['SecurityOpt']==['seccomp=unconfined'] and h['MaskedPaths']==[] and h['ReadonlyPaths']==[]
  (priv/'buildkit-boundary.json').write_text(json.dumps({'network':h['NetworkMode'],'privileged':h['Privileged'],'cap_add':h['CapAdd'],'user':c['User'],'apparmor':inspect['AppArmorProfile'],'security_opt':h['SecurityOpt'],'masked_paths':h['MaskedPaths'],'readonly_paths':h['ReadonlyPaths']}))
  run(['docker','start',name],stdout=log,stderr=log)
  ctl=['docker','exec',name,'buildctl','--addr','unix:///run/user/1000/buildkit/buildkitd.sock']
  for i in range(20):
   p=subprocess.run(ctl+['debug','workers'],stdout=log,stderr=log)
   if p.returncode==0: break
   time.sleep(1)
  else: raise RuntimeError('worker unavailable')
  run(['docker','exec',name,'sh','-c',"printf 'synthetic invalid CA fixture\\n' > /tmp/invalid.pem"],stdout=log,stderr=log)
  run(['docker','exec',name,'sh','-c',': > /tmp/empty.pem'],stdout=log,stderr=log)
  results=[]
  for service,df in [('backend','Dockerfile'),('order','Dockerfile.order')]:
   start=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
   args=ctl+['build','--frontend','dockerfile.v0','--no-cache','--local','context=/diagnosis','--local','dockerfile=/diagnosis','--opt','filename='+df,'--opt','platform=linux/amd64','--opt','build-arg:VCS_REF=24083aba485abd6b37bcbe71736fb543a847dcc6','--opt','build-arg:VCS_SOURCE=https://github.com/syuhei0519/backend-app','--output',f'type=oci,dest=/tmp/{service}.oci.tar,oci-mediatypes=true']
   if mode=='valid': args+=['--secret','id=build_ca,src=/etc/task-ca.pem']
   if mode=='invalid': args+=['--secret','id=build_ca,src=/tmp/invalid.pem']
   if mode=='empty': args+=['--secret','id=build_ca,src=/tmp/empty.pem']
   if mode=='nonexistent': args+=['--secret','id=build_ca,src=/tmp/does-not-exist.pem']
   for k,v in env.items(): args+=['--opt',f'build-arg:{k}={v}']
   with open(priv/f'build-{service}.log','w') as f:
    p=subprocess.run(args,stdout=f,stderr=f,timeout=900)
   result={'service':service,'dockerfile':df,'started_at':start,'ended_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'exit_code':p.returncode}
   if p.returncode==0:
    dest=priv/f'{service}.oci.tar'
    run(['docker','cp',f'{name}:/tmp/{service}.oci.tar',str(dest)],stdout=log,stderr=log)
    result.update(size=dest.stat().st_size,sha256=hashlib.sha256(dest.read_bytes()).hexdigest())
   results.append(result)
   (priv/'image-build-results.json').write_text(json.dumps(results,indent=2)+'\n')
 finally:
  subprocess.run(['docker','logs',name],stdout=log,stderr=log)
  subprocess.run(['docker','rm','-fv',name],stdout=log,stderr=log)
  if not image_present:
   subprocess.run(['docker','image','rm',image],stdout=log,stderr=log)
  envfile.unlink(missing_ok=True)
  log.close()

elif mode=='chain':
 sys.argv=[sys.argv[0],*sys.argv[2:]]
 import pathlib,subprocess,os,json,hashlib,shutil,tarfile,io
 root=pathlib.Path(os.environ['PRIVATE_OUTPUT']); repo=pathlib.Path(os.environ['BACKEND_CHECKOUT'])
 head='24083aba485abd6b37bcbe71736fb543a847dcc6'
 svc=__import__('sys').argv[1]
 work=root/('chain-'+svc);work.mkdir(mode=0o700)
 source=subprocess.check_output(['git','-C',str(repo),'archive',head])
 with tarfile.open(fileobj=io.BytesIO(source)) as t:t.extractall(work,filter='data')
 for p in ['.oci','.security/public','.security/private','.cache/trivy']:(work/p).mkdir(parents=True,exist_ok=True)
 for p in (root/'bin').iterdir():shutil.copy2(p,work/'.security'/p.name)
 shutil.copyfile(root/'valid'/f'{svc}.oci.tar',work/'.oci/image.tar')
 archive=hashlib.sha256((work/'.oci/image.tar').read_bytes()).hexdigest()
 def run(args,out=None,env=None):
  with (work/(out or '.security/private/chain.log')).open('w' if out else 'a') as f:
   return subprocess.run(args,cwd=work,env=env,stdout=f,stderr=f,check=True)
 run(['.security/github-oci-check','.oci/image.tar',archive,'.oci/layout',head,'syuhei0519/backend-app'],'.security/public/layout.json')
 layout=json.loads((work/'.security/public/layout.json').read_text())
 run(['.security/oci-crane-check','.oci/layout',layout['digest']],'.security/public/reader.json')
 reader=json.loads((work/'.security/public/reader.json').read_text())
 env=dict(os.environ,GITHUB_REPOSITORY='syuhei0519/backend-app',RELEASE_SERVICE=svc)
 run(['python3','-I','ci/github/runtime.py'],env=env)
 scan='''
 trivy image --download-db-only --db-repository ghcr.io/aquasecurity/trivy-db:2 --db-repository public.ecr.aws/aquasecurity/trivy-db:2 --cache-dir .cache/trivy --timeout 5m --quiet > .security/private/db.log 2>&1
 : > .security/private/empty-ignore
 trivy image --input .oci/layout --cache-dir .cache/trivy --skip-db-update --timeout 5m --quiet --no-progress --scanners vuln,secret,misconfig --severity UNKNOWN,LOW,MEDIUM,HIGH,CRITICAL --ignorefile .security/private/empty-ignore --list-all-pkgs --format json --output .security/private/image.json > .security/private/scan.log 2>&1
 trivy convert --format cyclonedx --output .security/private/sbom.cdx.json .security/private/image.json > .security/private/sbom.log 2>&1
 '''
 run(['docker','run','--rm','--user',f'{os.getuid()}:{os.getgid()}','--mount',f'type=bind,src={work},dst=/work','--mount',f'type=bind,src={os.environ["SSL_CERT_FILE"]},dst=/etc/task-ca.pem,readonly','-w','/work','-e','SSL_CERT_FILE=/etc/task-ca.pem','-e','IMAGE_CONFIG='+reader['configDigest'],'--entrypoint','sh','aquasec/trivy:0.75.0@sha256:9db099105405c648166e6b94155eb32f8da12673cf1f455207f7385cc9a77283','-ec',scan])
 (work/'.validation').mkdir()
 source=(root/'source-scan/source-scan.json').read_bytes();(work/'.validation/source-scan.json').write_bytes(source)
 (work/'.validation/source-identity.json').write_text(json.dumps({'repository':'syuhei0519/backend-app','sourceCommit':head,'runId':1,'runAttempt':2,'sourceScanSha256':sha(source)}))
 env.update(GITHUB_SHA=head,GITHUB_RUN_ID='1',GITHUB_RUN_ATTEMPT='2')
 run(['python3','-I','ci/github/image-policy.py'],env=env)
 assert archive==hashlib.sha256((work/'.oci/image.tar').read_bytes()).hexdigest()
 (root/f'chain-{svc}-result.json').write_text(json.dumps({'service':svc,'head':head,'archive_sha256':archive,'oci_digest':layout['digest'],'config_digest':reader['configDigest'],'reader':'passed','runtime':'passed','scan':'passed','sbom':'passed','original_archive_unchanged':True,'actual_publish':False},indent=2)+'\n')

elif mode=='source':
 root=P(sys.argv[2]);out=root/'source-scan';out.mkdir();(out/'scan-gate').write_bytes((root/'bin/scan-gate').read_bytes());(out/'scan-gate').chmod(0o700)
 script='''trivy image --download-db-only --db-repository ghcr.io/aquasecurity/trivy-db:2 --db-repository public.ecr.aws/aquasecurity/trivy-db:2 --cache-dir .cache --timeout 5m --quiet
: > empty-ignore
trivy fs --cache-dir .cache --skip-db-update --timeout 5m --quiet --no-progress --include-dev-deps --scanners vuln,secret,misconfig --severity UNKNOWN,LOW,MEDIUM,HIGH,CRITICAL --ignorefile empty-ignore --list-all-pkgs --format json --output raw.json /source
./scan-gate -policy /source/security/scan-policy.json -db .cache/db/metadata.json -report raw.json -out source-scan.json -scanner-exit 0'''
 with (out/'private.log').open('wb') as log:
  subprocess.run(['docker','run','--rm','--user',f'{os.getuid()}:{os.getgid()}','--mount',f'type=bind,src={root}/context,dst=/source,readonly','--mount',f'type=bind,src={out},dst=/out','--mount',f'type=bind,src={os.environ["SSL_CERT_FILE"]},dst=/etc/task-ca.pem,readonly','-e','SSL_CERT_FILE=/etc/task-ca.pem','-w','/out','--entrypoint','sh','aquasec/trivy:0.75.0@sha256:9db099105405c648166e6b94155eb32f8da12673cf1f455207f7385cc9a77283','-ec',script],check=True,stdout=log,stderr=log)
elif mode=='leak':
 import re
 root=P(sys.argv[2]);svc=sys.argv[3];archive=root/'valid'/f'{svc}.oci.tar';bundle=P(os.environ['SSL_CERT_FILE']).read_bytes();files=[];configs=[]
 certs=lambda b:set(re.findall(rb'-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----',b,re.S))
 with tarfile.open(archive) as t:
  ix=json.loads(t.extractfile('index.json').read());man=json.loads(t.extractfile('blobs/sha256/'+ix['manifests'][0]['digest'][7:]).read());configs.append(t.extractfile('blobs/sha256/'+man['config']['digest'][7:]).read())
  for d in man['layers']:
   raw=t.extractfile('blobs/sha256/'+d['digest'][7:]).read()
   with tarfile.open(fileobj=io.BytesIO(raw)) as layer:
    for f in layer:
     if f.isfile():files.append((f.name,layer.extractfile(f).read()))
 standard=next(b for n,b in files if n.lstrip('./')=='etc/ssl/certs/ca-certificates.crt');custom=certs(bundle)-certs(standard);assert custom
 cfg=json.loads((P(os.environ.get('DOCKER_CONFIG',str(P.home()/'.docker')))/'config.json').read_bytes());endpoint=os.environ.get('DOCKER_HOST','unix:///var/run/docker.sock');proxies=cfg.get('proxies',{}).get(endpoint,cfg.get('proxies',{}).get('default',{}))
 sourcepath=os.environ['SSL_CERT_FILE'].encode()
 # Host and distroless may share this standard path; actual custom bytes are checked separately.
 sourcepaths=[] if sourcepath==b'/etc/ssl/certs/ca-certificates.crt' else [sourcepath]
 forbidden=[bundle,*custom,*sourcepaths,b'/run/secrets/build_ca',b'/etc/task-ca.pem',*[v.encode() for v in proxies.values() if len(v)>8]]
 for b in [*configs,*[b for n,b in files]]:
  assert not any(x and x in b for x in forbidden)
 (root/(svc+'-trust-leak.json')).write_text(json.dumps({'service':svc,'custom_certificates_distinguished_from_standard':True,'custom_pem_material_absent':True,'full_bundle_absent':True,'custom_secret_source_path_absent':True,'standard_path_alias_not_a_leak':True,'secret_target_paths_absent':True,'actual_proxy_values_absent':True,'all_runtime_layer_files_and_config_checked':True,'standard_runtime_trust_retained':True},indent=2)+'\n')
elif mode=='image':
 root=P(sys.argv[2]);svc=sys.argv[3];w=root/('chain-'+svc);layout=json.loads((w/'.security/public/layout.json').read_bytes());reader=json.loads((w/'.security/public/reader.json').read_bytes());tag='docker.io/local/order-b2-test-'+secrets.token_hex(10)+':checked';name='order-b2-test-'+secrets.token_hex(10);tar=w/'.oci/transport-independent.tar'
 run([str(root/'bin/oci-runtime-export'),str(w/'.oci/layout'),layout['digest'],str(tar),tag]);loaded=False;created=False
 try:
  with tarfile.open(tar) as t:
   mf=json.loads(t.extractfile('manifest.json').read());assert len(mf)==1;mf=mf[0]
   config=t.extractfile(mf['Config']).read();assert 'sha256:'+sha(config)==reader['configDigest'];assert config==(w/'.oci/layout/blobs/sha256'/reader['configDigest'][7:]).read_bytes()
   om=json.loads((w/'.oci/layout/blobs/sha256'/layout['digest'][7:]).read_bytes());cfg=json.loads(config);layers=[]
   assert len(om['layers'])==len(mf['Layers'])
   for i,(d,n) in enumerate(zip(om['layers'],mf['Layers'])):
    before=(w/'.oci/layout/blobs/sha256'/d['digest'][7:]).read_bytes();after=t.extractfile(n).read();assert before==after
    plain=gzip.decompress(after) if after[:2]==b'\x1f\x8b' else after;assert 'sha256:'+sha(plain)==cfg['rootfs']['diff_ids'][i]
    layers.append({'compressed_digest':d['digest'],'uncompressed_digest':'sha256:'+sha(plain),'exact_bytes':True})
  run(['docker','load','--input',str(tar)]);loaded=True
  image=json.loads(run(['docker','image','inspect',tag]))[0];assert image['Id']==reader['configDigest']
  run(['docker','create','--name',name,'--pull=never','--network','none','--read-only','--cap-drop=ALL','--security-opt=no-new-privileges','--user','10001:10001',tag]);created=True
  ins=json.loads(run(['docker','inspect',name]))[0];h=ins['HostConfig'];assert h['ReadonlyRootfs'] and h['CapDrop']==['ALL'];assert 'no-new-privileges' in h['SecurityOpt'];assert ins['Config']['User']=='10001:10001';assert ins['Image']==reader['configDigest']
  # Known wrong digest must be rejected by the real exporter.
  bad=subprocess.run([str(root/'bin/oci-runtime-export'),str(w/'.oci/layout'),'sha256:'+'0'*64,str(w/'.oci/refused.tar'),tag],capture_output=True);assert bad.returncode!=0
  (root/(svc+'-transport.json')).write_text(json.dumps({'service':svc,'config_bytes_equal':True,'layers':layers,'loaded_id':image['Id'],'container_image':ins['Image'],'read_only':h['ReadonlyRootfs'],'cap_drop':h['CapDrop'],'security_opt':h['SecurityOpt'],'user':ins['Config']['User'],'wrong_digest_rejected':True,'real_runtime_result':json.loads((w/'.security/public/runtime.json').read_bytes())},indent=2)+'\n')
 finally:
  if created:run(['docker','rm','-v',name])
  if loaded:run(['docker','image','rm',tag])
  tar.unlink(missing_ok=True)
elif mode=='consumer':
 backend,m0,m1=map(P,sys.argv[2:]);f=module('fixtures',backend/'ci/github/order-release_test.py');fixture=f.Interop();fixture.setUp()
 try:
  p=f.p;record=fixture.published();checks=[]
  assert not (m0/'environments/local/order.yaml').exists()
  for version,root in [('M0',m0),('M1',m1)]:
   c=module('consumer'+version,root/'ci/github/release.py')
   with patch.object(c,'now',return_value=fixture.clock):
    c.validate_record(record,fixture.repo,fixture.commit,123,2,'order')
    account=c.load(root/'ci/github/fixtures/backend-record.json');c.validate_record(account,fixture.repo,fixture.commit,123,2,'backend');p.validate_record(account,fixture.repo,fixture.commit,123,2,'backend')
    for service in ('backend','order'):
     path=root/f'environments/local/{service}.yaml'
     if not path.exists():continue
     text=path.read_text();r=record if service=='order' else account;urls={'release-record.json':'synthetic-record','sbom.cdx.json':'synthetic-sbom'}
     a=p.patch_values(text,fixture.repo,fixture.commit,r,urls,'0'*64);b=c.patch_values(text,fixture.repo,fixture.commit,r,urls,'0'*64);assert a==b
     if service=='order':assert '\nenabled: false\n' in '\n'+a
     checks.append(version+'-'+service+'-actual-values')
  print(json.dumps({'status':'passed','producer_to_fixed_consumers':True,'account_v1':True,'m0_order_values_absent':True,'m1_order_values_disabled_preserved':True,'actual_values_checks':checks,'external_operations':'none; synthetic release identity'}))
 finally:fixture.doCleanups()
elif mode=='matrix':
 import shutil
 root=P(sys.argv[2]);w=root/'production-matrix';w.mkdir();os.chdir(w)
 for svc in ('backend','order'):
  dest=w/('checked-image-'+('order-' if svc=='order' else '')+'2');dest.mkdir();(dest/'.oci').mkdir();shutil.copy2(root/f'chain-{svc}/.oci/image.tar',dest/'.oci/image.tar');shutil.copytree(root/f'chain-{svc}/.security/public',dest/'.security/public')
 m=module('matrix',root/'context/ci/github/matrix-result.py');env={'GITHUB_REPOSITORY':'syuhei0519/backend-app','GITHUB_SHA':HEAD,'GITHUB_RUN_ID':'1','GITHUB_RUN_ATTEMPT':'2','GITHUB_WORKFLOW_REF':'syuhei0519/backend-app/.github/workflows/ci.yml@refs/heads/main'}
 with patch.dict(os.environ,env):m.check(w)
 (root/'production-matrix.json').write_text(json.dumps({'status':'passed','identity':'synthetic run 1 attempt 2','both_actual_oci_archives':True,'distinct_archive_config_image':True,'same_measured_source_scan':True,'real_ci_execution':False})+'\n')
elif mode=='publish':
 root=P(sys.argv[2]);svc=sys.argv[3];w=root/('chain-'+svc);os.chdir(w);m=module('production_release',w/'ci/github/release.py');repo='syuhei0519/backend-app'
 env={'GITHUB_REPOSITORY':repo,'GITHUB_SHA':HEAD,'GITHUB_RUN_ID':'1','GITHUB_RUN_ATTEMPT':'2','GITHUB_WORKFLOW_REF':repo+'/.github/workflows/ci.yml@refs/heads/main','GITHUB_EVENT_NAME':'push','GITHUB_REF':'refs/heads/main','GITHUB_REF_PROTECTED':'true','RELEASE_SERVICE':svc,'GITHUB_ACTOR':'synthetic','GH_TOKEN':'synthetic-no-credential'}
 (w/'.validation').mkdir(exist_ok=True);source=(root/'source-scan/source-scan.json').read_bytes();(w/'.validation/source-scan.json').write_bytes(source)
 (w/'.validation/source-identity.json').write_text(json.dumps({'repository':repo,'sourceCommit':HEAD,'runId':1,'runAttempt':2,'sourceScanSha256':sha(source)}))
 with patch.dict(os.environ,env):
  m.record();record=m.load(m.PUBLIC/'release-record.json');original=(m.PUBLIC/'release-record.json').read_bytes();calls=[];assets={};real_run=subprocess.run
  config=(w/'.oci/layout/blobs/sha256'/record['configDigest'][7:]).read_bytes()
  def command(args,**kw):
   calls.append(args)
   if args[0]=='github-oci-check':return real_run([str(root/'bin/github-oci-check'),*args[1:]],check=True,capture_output=True).stdout
   assert args[0]=='crane'
   if args[1]=='digest':return record['imageDigest'].encode()
   if args[1]=='config':return config
   assert args[1] in ('auth','push');return b''
  def api(path,method='GET',body=None,raw=None,upload=False):
   if path.endswith('/git/ref/heads/main'):return {'object':{'sha':HEAD}}
   if method=='POST' and path.endswith('/releases'):return {'id':1}
   if raw is not None:assets[path.split('name=')[1]]=raw
   return {}
  def probe(args,**kw):
   assert args[:2]==['crane','digest'];return subprocess.CompletedProcess(args,1,b'',b'404 Not Found')
  # Corrupt actual bytes: reject before all registry/API effects.
  negatives=[]
  for name in ('.oci/image.tar','.security/public/sbom.cdx.json','.security/public/image-scan.json'):
   f=P(name);raw=f.read_bytes();f.write_bytes(raw+b'corruption')
   try:
    with patch.object(m,'api') as a,patch.object(m,'run') as r:
     try:m.publish();raise AssertionError('tampered input accepted')
     except ValueError:pass
     a.assert_not_called();r.assert_not_called()
   finally:f.write_bytes(raw)
   negatives.append(name)
  with patch.object(m,'run',side_effect=command),patch.object(m,'api',side_effect=api),patch.object(m.subprocess,'run',side_effect=probe):m.publish()
  published=m.decode(assets['release-record.json'])
  for v in ('m0','m1'):
   c=module('published_'+v,root/v/'ci/github/release.py');c.validate_record(published,repo,HEAD,1,2,svc)
  assert ['crane','push','.oci/publish-layout',record['imageRepository']+':'+HEAD] in calls
  assert all('build' not in arg for call in calls for arg in call)
  assert sha(P('.oci/image.tar').read_bytes())==record['archiveSha256']
  (m.PUBLIC/'release-record.json').write_bytes(original)
  (root/(svc+'-publish-binding.json')).write_text(json.dumps({'service':svc,'identity':'synthetic run 1 attempt 2; not GitHub CI','real_source_scan':True,'local_record':record,'mocked_published_record':published,'actual_registry_or_github_writes':False,'fixed_consumers':['M0','M1'],'same_original_archive':True,'negative_tampering_rejected':negatives,'real_local_validator_calls':sum(c[0]=='github-oci-check' for c in calls),'rebuild':False},indent=2)+'\n')
else:raise ValueError('mode')
