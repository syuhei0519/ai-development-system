import os,json,pathlib,subprocess,time,hashlib,sys,tempfile
# Reproducer: existing proxy/CA only; raw logs and env remain private.
# Two explicit security options require the task owner's authorization.
root=pathlib.Path(sys.argv[1]).resolve()
context=pathlib.Path(sys.argv[2]).resolve()
priv=root
priv.mkdir(mode=0o700,parents=True,exist_ok=True)
mode=sys.argv[3] if len(sys.argv)>3 else 'application'
assert mode in ('application','synthetic')
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
 run(['docker','pull',image],stdout=log,stderr=log)
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
 results=[]
 for service,df in ([('synthetic','Dockerfile')] if mode=='synthetic' else [('backend','Dockerfile'),('order','Dockerfile.order')]):
  start=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
  args=ctl+['build','--frontend','dockerfile.v0','--local','context=/diagnosis','--local','dockerfile=/diagnosis','--opt','filename='+df,'--opt','platform=linux/amd64','--opt','build-arg:VCS_REF=65885af3fd648ce7010fa4a06470b273b995d418','--opt','build-arg:VCS_SOURCE=https://github.com/syuhei0519/backend-app','--output',f'type=oci,dest=/tmp/{service}.oci.tar,oci-mediatypes=true']
  if mode=='synthetic': args+=['--secret','id=ca,src=/etc/task-ca.pem']
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
