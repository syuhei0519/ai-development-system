"""Independent M1 synthetic preparation verification. No cluster or release claims."""
import copy, datetime, hashlib, json, pathlib, subprocess, sys
import yaml, jsonschema
R=pathlib.Path(sys.argv[1]); B=pathlib.Path(sys.argv[2]); O=pathlib.Path(sys.argv[3]); O.mkdir(exist_ok=True)
H='41a7e9632102a8c30ff7fa57570fd85aea19adf1'; BASE='bc6adaedcd645a4663c23284b977a3dd36c0796d'
results=[]
def run(cmd,cwd=R,input=None): return subprocess.run(cmd,cwd=cwd,input=input,capture_output=True,text=True)
def check(name, ok, detail=''):
 results.append({'case':name,'pass':bool(ok),'detail':detail})
def render(root,chart,fixture=None,extra=[]):
 args=['helm','template',chart,'charts/'+chart,'--namespace','account']
 if fixture: args+=['-f',fixture]
 return run(args+extra,root)
def digest(b):return hashlib.sha256(b).hexdigest()
check('fixed-head',run(['git','rev-parse','HEAD']).stdout.strip()==H)
check('fixed-tree',run(['git','rev-parse','HEAD^{tree}']).stdout.strip()=='47ea076ac6f481fdf6a1588abcfd0aaf07c4e25d')
paths=run(['git','ls-tree','-r','--name-only',BASE,'charts','environments/local']).stdout.splitlines()
check('32-existing-files',len(paths)==32)
for p in paths:check('unchanged:'+p,(B/p).read_bytes()==(R/p).read_bytes(),digest((R/p).read_bytes()))
for chart in ['frontend','backend','postgresql']:
 a=render(B,chart,'environments/local/'+chart+'.yaml'); b=render(R,chart,'environments/local/'+chart+'.yaml')
 check('unchanged-render:'+chart,a.returncode==b.returncode==0 and a.stdout==b.stdout,digest(b.stdout.encode()))
 (O/(chart+'-baseline.yaml')).write_text(a.stdout)
for chart,fx in [('order','enabled.yaml'),('order-postgresql','postgresql-enabled.yaml')]:
 for f in [None,'environments/local/'+chart+'.yaml']:
  a=render(R,chart,f);check('empty:'+chart+':'+str(f),a.returncode==0 and not a.stdout.strip())
 s=json.loads((R/'charts'/chart/'values.schema.json').read_text()); values=yaml.safe_load((R/'charts'/chart/'values.yaml').read_text())
 for state in [False,True]:
  v=copy.deepcopy(values);v.update(yaml.safe_load((R/'ci/fixtures/order'/fx).read_text()) if state else {})
  check('schema-positive:'+chart+':'+str(state),not list(jsonschema.Draft7Validator(s).iter_errors(v)))
  for key in s['required']:
   m=copy.deepcopy(v);del m[key];check('schema-missing:'+chart+':'+str(state)+':'+key,bool(list(jsonschema.Draft7Validator(s).iter_errors(m))))
  for bad in ['false',0,1,None,[],{}]:
   m=copy.deepcopy(v);m['enabled']=bad;check('schema-enabled-type:'+chart+':'+str(state)+':'+repr(bad),bool(list(jsonschema.Draft7Validator(s).iter_errors(m))))
 for override in ['enabled=null','enabled=oops','securityContext.allowPrivilegeEscalation=true','podSecurityContext.seccompProfile.type=Unconfined','serviceAccount.name=backend','imagePullSecrets[0].name=secret','config.dbName=account','secrets.existingSecret=account-db','replicaCount=0','securityContext.capabilities.add[0]=SYS_ADMIN']:
  for state in ['false','true']:
   a=render(R,chart,'ci/fixtures/order/'+fx,['--set','enabled='+state,'--set',override]); check('helm-reject:'+chart+':'+state+':'+override,a.returncode!=0)
 a=render(R,chart,'ci/fixtures/order/'+fx);check('enabled-render:'+chart,a.returncode==0);(O/(chart+'-synthetic.yaml')).write_text(a.stdout)
# Independent value/release mutations, not release authentication.
for val in ['image.digest=sha256:bad','image.tag=latest','release.sourceCommit='+('b'*40),'release.runId=0','release.runAttempt=0','release.recordSha256='+('a'*63),'release.service=backend','migration.activeDeadlineSeconds=179','migration.backoffLimit=0','probes.readiness.path=/livez']:
 check('release-reject:'+val,render(R,'order','ci/fixtures/order/enabled.yaml',['--set',val]).returncode!=0)
# Disabled placeholder fields intentionally are not authenticated.
check('disabled-placeholder-digest',render(R,'order',None,['--set','image.digest=placeholder']).returncode==0)
docs=list(yaml.safe_load_all((O/'order-synthetic.yaml').read_text()))+list(yaml.safe_load_all((O/'order-postgresql-synthetic.yaml').read_text()))
docs=[d for d in docs if d]
check('11-resources',len(docs)==11)
check('no-extra-sensitive-resource',all(d['kind'] not in ['Secret','Namespace','AppProject','Application'] for d in docs))
by={(d['kind'],d['metadata']['name']):d for d in docs};dep=by['Deployment','order'];job=by['Job','order-migration'];db=by['StatefulSet','order-postgresql'];pvc=by['PersistentVolumeClaim','order-postgresql-data']
def ps(d):return d['spec']['template']['spec']
dc=ps(dep)['containers'][0];jc=ps(job)['containers'][0];dbc=ps(db)['containers'][0]
check('migration-image-equality',dc['image']==jc['image'] and '@sha256:' in dc['image'])
check('migration-command',jc['args']==['migrate'] and job['spec']['activeDeadlineSeconds']==180 and job['spec']['backoffLimit']==1 and ps(job)['restartPolicy']=='Never')
for d in [dep,db]:
 sel=d['spec']['selector']['matchLabels'];labels=d['spec']['template']['metadata']['labels'];check('selector:'+d['kind'],all(labels.get(k)==v for k,v in sel.items()))
for name,target in [('order',dep),('order-postgresql',db),('order-postgresql-headless',db)]:
 sel=by['Service',name]['spec']['selector'];labels=target['spec']['template']['metadata']['labels'];check('service-selector:'+name,all(labels.get(k)==v for k,v in sel.items()))
check('app-db-distinct',dep['spec']['selector']!=db['spec']['selector'])
for probe,path in [('startupProbe','/livez'),('livenessProbe','/livez'),('readinessProbe','/readyz')]:check(probe,dc[probe]['httpGet']['path']==path)
check('pvc-retained',pvc['metadata']['annotations']['argocd.argoproj.io/sync-options']=='Prune=false,Delete=false')
check('sts-protected',db['metadata']['annotations']['argocd.argoproj.io/sync-options']=='Prune=confirm,Delete=confirm' and 'volumeClaimTemplates' not in db['spec'])
# Additional independently constructed PodSpec/resource attacks against unchanged inventory.
raw=yaml.safe_dump_all(docs,sort_keys=False)
inv=str(R/'.build/order-inventory')
if pathlib.Path(inv).exists():
 def invcase(name,m,expected):
  payload=yaml.safe_dump_all(m,sort_keys=False); r=run([inv],input=payload);check(name,(r.returncode==0)==expected,r.stderr.strip());(O/(name+'.yaml')).write_text(payload)
 invcase('inventory-positive',docs,True)
 mutations=[]
 for kind in ['Secret','Namespace','AppProject']:
  mutations.append(('extra-'+kind,docs+[{'apiVersion':'v1','kind':kind,'metadata':{'name':'synthetic-forbidden'}}]))
 for typ in ['initContainers','ephemeralContainers']:
  m=copy.deepcopy(docs);d=next(d for d in m if d['kind']=='Deployment');ps(d)[typ]=[{'name':'injected','image':'untrusted:latest'}];mutations.append(('extra-'+typ,m))
 for field,value in [('hostNetwork',True),('hostPID',True),('hostIPC',True)]:
  m=copy.deepcopy(docs);ps(next(d for d in m if d['kind']=='Deployment'))[field]=value;mutations.append(('pod-'+field,m))
 m=copy.deepcopy(docs);next(d for d in m if d['kind']=='Deployment')['metadata']['namespace']='kube-system';mutations.append(('namespace-escape',m))
 m=copy.deepcopy(docs);ps(next(d for d in m if d['kind']=='StatefulSet'))['volumes'][0]['persistentVolumeClaim']['claimName']='postgresql-data';mutations.append(('account-pvc',m))
 m=copy.deepcopy(docs);next(d for d in m if d['kind']=='PersistentVolumeClaim')['metadata']['annotations']={};mutations.append(('pvc-no-protection',m))
 for name,m in mutations:invcase(name,m,False)
(O/'independent-results.json').write_text(json.dumps({'synthetic_only':True,'observed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'results':results},indent=2)+'\n')
print('cases',len(results),'failed',sum(not r['pass'] for r in results))
for r in results:
 if not r['pass']:print('FAIL',r)
sys.exit(any(not r['pass'] for r in results))
