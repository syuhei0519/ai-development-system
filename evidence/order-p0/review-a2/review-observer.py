#!/usr/bin/env python3
"""Review2 independently generated synthetic observations; only fake kubectl executes.
Usage: review-observer.py checkout observer output.json
Baseline spec is extracted from the fixed head's actual synthetic Helm render.
"""
import copy,concurrent.futures,hashlib,json,os,pathlib,subprocess,sys,tempfile,time
from datetime import datetime,timezone
import yaml
checkout,binary,output=map(pathlib.Path,sys.argv[1:]); A='b'*40; O='a'*40
render=subprocess.check_output(['helm','template','workloads','charts/workloads','--set','orderEnabled=true','--set-string','orderTargetRevision='+O],cwd=checkout)
apps=list(yaml.safe_load_all(render)); names=[a['metadata']['name'] for a in apps]
for app in apps:
 n=app['metadata']['name'].removeprefix('lab-local-'); rev=O if n.startswith('order') else A
 hook=n+'-migration' if n in ['backend','order'] else None
 app['status']={'sync':{'status':'Synced','revision':rev,'comparedTo':{'source':copy.deepcopy(app['spec']['source']),'destination':copy.deepcopy(app['spec']['destination'])}},'health':{'status':'Healthy'},'resources':[{'group':'apps','kind':'StatefulSet' if 'postgresql' in n else 'Deployment','name':n,'namespace':'account','status':'Synced','health':{'status':'Healthy'}}],'operationState':{'phase':'Succeeded','syncResult':{'revision':rev,'source':copy.deepcopy(app['spec']['source']),'resources':[] if hook is None else [{'group':'batch','kind':'Job','name':hook,'namespace':'account','hookType':'Sync','hookPhase':'Succeeded'}]}}}
class Missing:
 def __repr__(self): return 'missing'
MISSING=Missing(); cases=[]
def add(label,mutations=(),want=1,enabled=True,mode='normal',extra=()): cases.append((label,list(mutations),want,enabled,mode,list(extra)))
def mutate(app,path,v):
 keys=path.split('.'); obj=app
 for key in keys[:-1]: obj=obj[int(key)] if isinstance(obj,list) else obj.setdefault(key,{})
 key=int(keys[-1]) if isinstance(obj,list) else keys[-1]
 if v is MISSING: obj.pop(key,None)
 else: obj[key]=copy.deepcopy(v)
add('enabled actual-render contract',want=0); add('default three leaves',want=0,enabled=False)
roots=['spec.source','status.sync.comparedTo.source','status.operationState.syncResult.source']
neutral={'parameters':[None,[]],'fileParameters':[None,[]],'apiVersions':[None,[]],'valuesObject':[None,{}],'values':[''],'version':[''],'namespace':[''],'kubeVersion':[''],'passCredentials':[False],'ignoreMissingValueFiles':[False],'skipCrds':[False],'skipTests':[False],'skipSchemaValidation':[False]}
for i in [3,4]:
 for root in roots:
  for field in ['repoURL','targetRevision','path','helm','helm.releaseName','helm.valueFiles']:
   for v in [MISSING,None,False,0,'',[],{},'wrong']:
    add(f'{i}/{root}/{field}/{repr(v) if v is not MISSING else "missing"}',[(i,root+'.'+field,v)])
  for field,values in neutral.items():
   for v in values: add(f'{i}/{root}/neutral/{field}/{v}',[(i,root+'.helm.'+field,v)],0)
   for v in [None,False,True,0,'',[],{},'override',[{'name':'enabled','value':'false'}],{'enabled':False}]:
    # bool/int equality in Python must not treat false as 0.
    if any(type(v)==type(n) and v==n for n in values): continue
    add(f'{i}/{root}/nonneutral/{field}/{v}',[(i,root+'.helm.'+field,v)])
  for field,v in {'chart':'','ref':'','name':'','kustomize':None,'directory':None,'plugin':None}.items():
   add(f'{i}/{root}/neutral-source/{field}',[(i,root+'.'+field,v)],0)
   add(f'{i}/{root}/active-source/{field}',[(i,root+'.'+field,{} if v is None else 'other')])
  for p in [root+'.future',root+'.helm.future']:
   for v in [None,False,'',[],{}]: add(f'{i}/unknown/{p}/{v}',[(i,p,v)])
 for root in ['spec.destination','status.sync.comparedTo.destination']:
  for field in ['server','namespace']:
   for v in [MISSING,None,False,0,'',[],{},'other']: add(f'{i}/{root}/{field}/{v}',[(i,root+'.'+field,v)])
  add(f'{i}/{root}/neutral-name',[(i,root+'.name','')],0)
  for field,v in [('name','other'),('name',None),('unknown',None)]: add(f'{i}/{root}/{field}/{v}',[(i,root+'.'+field,v)])
 for path in ['metadata.name','metadata.namespace','spec.project','status.sync.comparedTo','status.operationState.syncResult']:
  for v in [MISSING,None,False,0,'',[],{},'other']: add(f'{i}/{path}/{v}',[(i,path,v)])
 for path in ['spec.sources','status.sync.comparedTo.sources','status.operationState.syncResult.sources','status.operationState.syncResult.revisions','spec.ignoreDifferences','status.sync.comparedTo.ignoreDifferences']:
  for v in [None,[]]: add(f'{i}/{path}/neutral/{v}',[(i,path,v)],0)
  for v in [[{}],False,'',{}]: add(f'{i}/{path}/active/{v}',[(i,path,v)])
 add(f'{i}/hydrator-null',[(i,'spec.sourceHydrator',None)],0)
 for v in [{},False,'',[]]: add(f'{i}/hydrator/{v}',[(i,'spec.sourceHydrator',v)])
 for suffix,v in [('helm.valuesObject',{'enabled':False}),('helm.valueFiles',['other.yaml']),('repoURL','other'),('path','charts/backend')]:
  add(f'{i}/all-snapshots-wrong/{suffix}',[(i,r+'.'+suffix,v) for r in roots])
for i in range(5):
 for path in ['status.sync.status','status.health.status','status.operationState.phase']:
  for v in [MISSING,None,42,'','Unknown','Progressing','Failed','Error']:
   add(f'{i}/state/{path}/{v}',[(i,path,v)])
 for v in ['2026-10-11T00:00:00Z','',False,0,{},[]]:
  add(f'{i}/deleting/{v}',[(i,'metadata.deletionTimestamp',v),(i,'metadata.finalizers',['resources-finalizer.argocd.argoproj.io'])])
 add(f'{i}/finalizer-not-deleting',[(i,'metadata.deletionTimestamp',None),(i,'metadata.finalizers',['resources-finalizer.argocd.argoproj.io'])],0)
 add(f'{i}/operation-pending',[(i,'operation',{})])
for i in [3,4]:
 for path in ['status.sync.revision','status.operationState.syncResult.revision','status.resources.0.kind','status.resources.0.name','status.resources.0.namespace','status.resources.0.status','status.resources.0.health.status']:
  add(f'{i}/resource/{path}',[(i,path,'wrong')])
 add(f'{i}/missing-resource',[(i,'status.resources',[])])
for i in [1,4]:
 for key in ['kind','name','namespace','hookType','hookPhase']: add(f'{i}/hook/{key}',[(i,'status.operationState.syncResult.resources.0.'+key,'wrong')])
 add(f'{i}/no-hook',[(i,'status.operationState.syncResult.resources',[])])
legacy=[(i,p,MISSING) for i in range(3) for p in ['metadata','spec','status.sync.comparedTo','status.operationState.syncResult.source']]
add('legacy/status-only',legacy,0,False)
for i in range(3): add(f'legacy/deleting/{i}',legacy+[(i,'metadata.deletionTimestamp','2026-10-11T00:00:00Z')],enabled=False)
for mode in ['missing','malformed','null','block','regress']: add(mode,mode=mode)
for label,extra,enabled in [('missing-revision',['-order-revision',''],True),('floating',['-order-revision','main'],True),('disabled-revision',['-order-revision',O],False),('zero-time',['-timeout','0s'],True),('negative-time',['-timeout','-1s'],True),('positional',['bad'],True)]: add(label,want=2,extra=extra,enabled=enabled)
start=datetime.now(timezone.utc).isoformat()
with tempfile.TemporaryDirectory(prefix='review-synthetic-') as temp:
 root=pathlib.Path(temp)
 fake=root/'kubectl'
 fake.write_text('''#!/bin/sh
set -eu
printf '%s\\n' "$8" >> "$FIXTURE/calls"
case "$MODE" in
 block) exec sleep 20;;
 missing) if [ "$8" = lab-local-order ]; then exit 1; fi;;
 malformed) printf '{'; exit 0;;
 null) printf 'null'; exit 0;;
 regress) if [ "$8" = lab-local-order ]; then printf '{}' > "$FIXTURE/lab-local-order-postgresql"; exit 1; fi;;
esac
exec cat "$FIXTURE/$8"
''');fake.chmod(0o700)
 def run(item):
  idx,(label,changes,want,enabled,mode,extra)=item; folder=root/str(idx);folder.mkdir(); data=copy.deepcopy(apps)
  for i,p,v in changes: mutate(data[i],p,v)
  for a,n in zip(data,names): (folder/n).write_text(json.dumps(a))
  args=[str(binary),'-context','synthetic-review','-revision',A,'-kubectl',str(fake),'-timeout','2400ms' if mode=='regress' else '400ms']
  if enabled: args+=['-order-enabled','-order-revision',O]
  t=time.monotonic(); r=subprocess.run(args+extra,env=dict(os.environ,FIXTURE=str(folder),MODE=mode),capture_output=True,text=True,timeout=6)
  calls=(folder/'calls').read_text().splitlines() if (folder/'calls').exists() else []
  return {'case':label,'expected_exit':want,'exit':r.returncode,'matched':r.returncode==want,'elapsed':round(time.monotonic()-t,4),'calls':calls,'synthetic_stdout':r.stdout,'synthetic_stderr':r.stderr}
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool: results=list(pool.map(run,enumerate(cases)))
summary={'document_type':'independent_review_observer','synthetic_sample':True,'started_at':start,'completed_at':datetime.now(timezone.utc).isoformat(),'head':subprocess.check_output(['git','-C',str(checkout),'rev-parse','HEAD'],text=True).strip(),'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'render_sha256':hashlib.sha256(render).hexdigest(),'cases':results}
output.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'cases':len(results),'matched':sum(r['matched'] for r in results),'unexpected':[r['case'] for r in results if not r['matched']]}))
