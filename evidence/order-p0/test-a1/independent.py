#!/usr/bin/env python3
"""Synthetic samples only; uses a fake kubectl, never accesses a cluster.
Run: python independent.py HEAD_CHECKOUT BASE_CHECKOUT OBSERVER_BINARY OUTPUT_JSON
Requires Helm 4.2.4 and PyYAML/jsonschema. No source edits.
"""
import sys,os,json,subprocess,tempfile,pathlib,hashlib,copy,time,datetime
import yaml,jsonschema
head,base,binary,out=map(pathlib.Path,sys.argv[1:]); head=head.resolve();base=base.resolve();binary=binary.resolve()
results=[]
def record(name,passed,**detail):
 results.append(dict(name=name,passed=passed,**detail))
def run(args,**kw): return subprocess.run(list(map(str,args)),capture_output=True,**kw)
def render(root,chart,extra=[]):return run(['helm','template',chart,root/'charts'/chart]+extra)
for chart in ['root','platform','workloads']:
 for mode in ['default','local']:
  outputs=[render(root,chart,[] if mode=='default' else ['-f',root/'environments/local'/f'{chart}.yaml']) for root in [base,head]]
  record(f'render/{chart}/{mode}',all(p.returncode==0 for p in outputs) and outputs[0].stdout==outputs[1].stdout,hashes=[hashlib.sha256(p.stdout).hexdigest() for p in outputs],sizes=[len(p.stdout) for p in outputs])
for path in ['bootstrap/namespaces.yaml','bootstrap/argocd-values.yaml','charts/root/templates/projects.yaml','charts/workloads/templates/applications.yaml']:
 a=base/path;b=head/path
 if not a.exists(): continue
 record('source/'+path,a.read_bytes()==b.read_bytes(),sha256=hashlib.sha256(b.read_bytes()).hexdigest())
A='1234567890abcdef1234567890abcdef12345678'; O='abcdef1234567890abcdef1234567890abcdef12'
def docs(p):return [x for x in yaml.safe_load_all(p.stdout) if x]
p=render(head,'workloads'); before=docs(p)
record('disabled-three-main',len(before)==3 and all(x['spec']['source']['targetRevision']=='main' for x in before) and not any('order' in x['metadata']['name'] for x in before))
p=render(head,'workloads',['--set','orderEnabled=true','--set-string','orderTargetRevision='+O]); enabled=docs(p)
record('enabled-preserve-existing',p.returncode==0 and enabled[:3]==before and len(enabled)==5)
for app,name,wave in zip(enabled[3:],['order-postgresql','order'],['-10','0']):
 spec=app['spec']; src=spec['source'];meta=app['metadata']
 record('enabled/'+name,meta=={'name':'lab-local-'+name,'namespace':'argocd','annotations':{'argocd.argoproj.io/sync-wave':wave,'argocd.argoproj.io/sync-options':'Prune=confirm'}} and spec['project']=='lab-account' and src=={'repoURL':'https://github.com/syuhei0519/application-manifest.git','targetRevision':O,'path':'charts/'+name,'helm':{'releaseName':name,'valueFiles':['../../environments/local/'+name+'.yaml']}} and spec['destination']=={'server':'https://kubernetes.default.svc','namespace':'account'} and spec['syncPolicy']=={'automated':{'prune':True,'selfHeal':True,'allowEmpty':False},'syncOptions':['PruneLast=true','FailOnSharedResource=true']})
schema=json.loads((head/'charts/workloads/values.schema.json').read_text()); values=yaml.safe_load((head/'charts/workloads/values.yaml').read_text())
for key in values:
 v=values.copy();del v[key]
 try:jsonschema.validate(v,schema);ok=False
 except jsonschema.ValidationError:ok=True
 record('schema-missing/'+key,ok)
cases=[]
for v in [None,'true','false','yes','unknown',0,1,{},[]]:cases.append(('flag/'+repr(v),{'orderEnabled':v},False))
for v in ['',None,'main','HEAD','v1.2.3',O[:39],O+'0',O.upper(),'g'*40,' '+O,O+'\n',1,True,{},[]]:cases.append(('revision/'+repr(v),{'orderEnabled':True,'orderTargetRevision':v},False))
cases += [('valid-enabled',{'orderEnabled':True,'orderTargetRevision':O},True),('disabled-staged-fixed',{'orderEnabled':False,'orderTargetRevision':O},True),('disabled-floating',{'orderEnabled':False,'orderTargetRevision':'main'},False),('unknown-key',{'orderTargetRevison':O},False),('account-floating',{'targetRevision':O},False),('repository-drift',{'applicationRepository':'https://example.invalid/repo.git'},False)]
with tempfile.TemporaryDirectory() as t:
 f=pathlib.Path(t)/'values.json'
 for name,v,want in cases:
  f.write_text(json.dumps(v));p=render(head,'workloads',['-f',f]);record('render-boundary/'+name,(p.returncode==0)==want,exit=p.returncode,expected_accept=want)
# fake kubectl validates command shape and permits only synthetic Application reads.
names=['lab-local-postgresql','lab-local-backend','lab-local-frontend','lab-local-order-postgresql','lab-local-order']
def observation(i):
 rev=A if i<3 else O; hooks=[]
 if i in [1,4]:hooks=[dict(kind='Job',name='backend-migration' if i==1 else 'order-migration',namespace='account',hookType='Sync',hookPhase='Succeeded')]
 resources=[] if i<3 else [dict(kind='StatefulSet' if i==3 else 'Deployment',name='order-postgresql' if i==3 else 'order',namespace='account',status='Synced',health={'status':'Healthy'})]
 return dict(spec={'source':{'targetRevision':'main' if i<3 else rev}},status={'sync':{'status':'Synced','revision':rev},'health':{'status':'Healthy'},'resources':resources,'operationState':{'phase':'Succeeded','syncResult':{'revision':rev,'resources':hooks}}})
def setpath(d,path,v):
 parts=path.split('.')
 for k in parts[:-1]:d=d[int(k)] if isinstance(d,list) else d[k]
 k=parts[-1]
 if isinstance(d,list):d[int(k)]=v
 else:d[k]=v
fake='''#!/usr/bin/env python3
import json,os,sys,pathlib
p=pathlib.Path(os.environ['P0_SYNTHETIC_DIR']);a=sys.argv[1:]
assert a[:7]==['--context','synthetic-unused','--request-timeout=8s','-n','argocd','get','application'] and a[8:]==['-o','json']
name=a[7]; calls=p/'calls';old=calls.read_text().splitlines() if calls.exists() else []
with calls.open('a') as f:f.write(name+'\\n')
s=json.loads((p/'state.json').read_text()); obj=s['objects'].get(name)
if s.get('dynamic') and name==s['dynamic']['trigger'] and name not in old:sys.exit(1)
if s.get('dynamic') and s['dynamic']['trigger'] in old and name==s['dynamic']['victim']:obj=s['dynamic']['replacement']
if obj is None:sys.exit(1)
print(json.dumps(obj))
'''
def cli(name,objects=None,options=None,want=1,dynamic=None,disabled=False,target=None):
 with tempfile.TemporaryDirectory() as t:
  p=pathlib.Path(t);f=p/'fake-kubectl';f.write_text(fake);f.chmod(0o700)
  (p/'state.json').write_text(json.dumps({'objects':objects or {n:observation(i) for i,n in enumerate(names)},'dynamic':dynamic}))
  args=[binary,'-context','synthetic-unused','-revision',A,'-kubectl',f,'-timeout','3s' if dynamic else ('5s' if want==0 else '650ms')]
  if not disabled:args+=['-order-enabled','-order-revision',O]
  if options:args+=options
  env=os.environ.copy();env['P0_SYNTHETIC_DIR']=str(p)
  start=time.monotonic();r=run(args,env=env,timeout=7);elapsed=time.monotonic()-start
  calls=(p/'calls').read_text().splitlines() if (p/'calls').exists() else []
  ok=r.returncode==want and elapsed<6
  if target:ok=ok and target in calls
  if want==2:ok=ok and not calls
  if want==0:ok=ok and calls==names[:3 if disabled else 5]
  if dynamic:ok=ok and calls.count(dynamic['victim'])>=2
  record('observer/'+name,ok,exit=r.returncode,expected_exit=want,elapsed_seconds=round(elapsed,3),calls=calls)
cli('default-success',disabled=True,want=0);cli('enabled-success',want=0)
for i,n in enumerate(names):
 variations=[('missing',None,None),('pending','operation',{}),('unknown-phase','status.operationState.phase','FuturePhase'),('missing-phase','status.operationState.phase',''),('failed','status.operationState.phase','Failed'),('running','status.operationState.phase','Running'),('synced-only','status.health.status',''),('healthy-only','status.sync.status',''),('health-stale-progress','status.health.status','Progressing'),('status-revision','status.sync.revision','f'*40),('operation-incomplete','status.operationState',{})]
 if i>=3:variations += [('spec-revision','spec.source.targetRevision',A),('operation-revision','status.operationState.syncResult.revision',A),('resource-absent','status.resources',[]),('resource-health','status.resources.0.health.status','Progressing'),('resource-sync','status.resources.0.status','Unknown'),('resource-namespace','status.resources.0.namespace','other')]
 if i in [1,4]:variations += [('hook-missing','status.operationState.syncResult.resources',[]),('hook-stale-revision','status.operationState.syncResult.revision','f'*40),('hook-failed','status.operationState.syncResult.resources.0.hookPhase','Failed'),('hook-unknown','status.operationState.syncResult.resources.0.hookPhase','Unknown'),('hook-presync','status.operationState.syncResult.resources.0.hookType','PreSync'),('hook-wrong-namespace','status.operationState.syncResult.resources.0.namespace','other')]
 for label,path,val in variations:
  objects={n:observation(j) for j,n in enumerate(names)}
  if path:setpath(objects[n],path,val)
  else:objects[n]=None
  cli(n+'/'+label,objects=objects,target=n,disabled=i<3)
for label,args,disabled in [('invalid-bool',['-order-enabled=maybe'],False),('floating-order',['-order-revision=main'],False),('empty-order',['-order-revision='],False),('uppercase-order',['-order-revision='+O.upper()],False),('disabled-conflict',['-order-revision='+O],True),('missing-context',['-context='],False),('zero-timeout',['-timeout=0s'],False),('unknown-flag',['-nonexistent'],False),('positional',['ignored'],False),('short-account',['-revision=abc'],False)]:cli(label,options=args,disabled=disabled,want=2)
for victim in [names[0],names[3]]:
 for mode in ['degraded','revision-changed']:
  i=names.index(victim);obj=observation(i)
  setpath(obj,'status.health.status' if mode=='degraded' else 'status.sync.revision','Degraded' if mode=='degraded' else 'f'*40)
  cli('repoll/'+victim+'/'+mode,dynamic={'trigger':names[4],'victim':victim,'replacement':obj})
data={'synthetic_sample':True,'observed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'tests':results,'passed':all(x['passed'] for x in results),'count':len(results)}
out.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'count':len(results),'failures':[x for x in results if not x['passed']]}));sys.exit(0 if data['passed'] else 1)
