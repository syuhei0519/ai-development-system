#!/usr/bin/env python3
"""Independent synthetic Review fixtures. No cluster access; fake kubectl only.
Usage: python3 reproduce.py HEAD_CHECKOUT BASE_CHECKOUT OBSERVER OUTPUT_JSON
Build OBSERVER from the fixed head's tools/bootstrap before running.
"""
import copy, hashlib, json, os, pathlib, subprocess, sys, tempfile, time
from datetime import datetime, timezone
head, base, observer, output = map(pathlib.Path, sys.argv[1:])
assert subprocess.check_output(['git','-C',str(head),'rev-parse','HEAD'],text=True).strip()=='e01882d8a2c4ac4eadad5b081c1b5c69e5599776'
assert subprocess.check_output(['git','-C',str(base),'rev-parse','HEAD'],text=True).strip()=='b989e29b8addbd6396c5c2b4833b969bc15fc8fa'
A='b'*40; O='a'*40
names=['postgresql','backend','frontend','order-postgresql','order']
def observation(name):
 rev=O if name.startswith('order') else A
 hook={'backend':'backend-migration','order':'order-migration'}.get(name)
 kind='StatefulSet' if 'postgresql' in name else 'Deployment'
 source={'repoURL':'https://github.com/syuhei0519/application-manifest.git','targetRevision':rev if name.startswith('order') else 'main','path':'charts/'+name,'helm':{'releaseName':name,'valueFiles':['../../environments/local/'+name+'.yaml']}}
 return {'apiVersion':'argoproj.io/v1alpha1','kind':'Application','metadata':{'name':'lab-local-'+name,'namespace':'argocd'},'spec':{'project':'lab-account','destination':{'server':'https://kubernetes.default.svc','namespace':'account'},'source':source},'status':{'sync':{'status':'Synced','revision':rev,'comparedTo':{'source':copy.deepcopy(source),'destination':{'server':'https://kubernetes.default.svc','namespace':'account'}}},'health':{'status':'Healthy'},'resources':[{'group':'apps','kind':kind,'name':name,'namespace':'account','status':'Synced','health':{'status':'Healthy'}}],'operationState':{'phase':'Succeeded','syncResult':{'revision':rev,'source':copy.deepcopy(source),'resources':[] if not hook else [{'group':'batch','kind':'Job','name':hook,'namespace':'account','hookType':'Sync','hookPhase':'Succeeded'}]}}}}
def setpath(x,path,v):
 keys=path.split('.')
 for k in keys[:-1]: x=x[int(k)] if isinstance(x,list) else x[k]
 x[keys[-1]]=v
results={'document_type':'review_reproductions','synthetic_sample':True,'started_at':datetime.now(timezone.utc).isoformat(),'renders':[],'observer':[],'schema':[]}
for chart in ['root','platform','workloads']:
 for local in [False,True]:
  blobs=[]
  for root in [base,head]:
   args=['helm','template',chart,'charts/'+chart]+(['-f','environments/local/'+chart+'.yaml'] if local else [])
   blobs.append(subprocess.check_output(args,cwd=root))
  results['renders'].append({'chart':chart,'values':'local' if local else 'default','equal':blobs[0]==blobs[1],'sizes':list(map(len,blobs)),'sha256':[hashlib.sha256(b).hexdigest() for b in blobs]})
# Exercise Helm's schema boundary independently, without cluster APIs.
for label,args,expected in [('default',[],0),('enabled',['--set','orderEnabled=true','--set-string','orderTargetRevision='+O],0),('enabled-empty',['--set','orderEnabled=true'],1),('enabled-floating',['--set','orderEnabled=true','--set-string','orderTargetRevision=main'],1),('flag-string',['--set-string','orderEnabled=false'],1),('unknown-key',['--set','orderEnable=true'],1),('disabled-staged',['--set-string','orderTargetRevision='+O],0)]:
 p=subprocess.run(['helm','template','workloads','charts/workloads']+args,cwd=head,capture_output=True)
 results['schema'].append({'case':label,'exit':p.returncode,'expected':expected,'matched':p.returncode==expected})
cases=[('baseline-enabled',None,None,None,0,True),('baseline-disabled',None,None,None,0,False)]
for target in ['order-postgresql','order']:
 for label,path,value in [('wrong-project','spec.project','default'),('wrong-namespace','spec.destination.namespace','other'),('wrong-cluster','spec.destination.server','https://example.invalid'),('wrong-source-path','spec.source.path','charts/other'),('wrong-repository','spec.source.repoURL','https://github.com/example/other.git'),('changed-helm-values','spec.source.helm.parameters',[{'name':'enabled','value':'false'}]),('deleting-application','metadata.deletionTimestamp','2026-10-11T00:00:00Z'),('source-drift','spec.source.targetRevision',A),('operation-drift','status.operationState.syncResult.revision',A),('unknown-phase','status.operationState.phase','NewUnknownState'),('unhealthy-resource','status.resources.0.health',{'status':'Degraded'}),('wrong-resource-namespace','status.resources.0.namespace','other')]:
  cases.append((target+'/'+label,target,path,value,1,True))
cases.append(('order/failed-hook','order','status.operationState.syncResult.resources.0.hookPhase','Failed',1,True))
with tempfile.TemporaryDirectory() as tmp:
 root=pathlib.Path(tmp)
 fake=root/'kubectl';fake.write_text('#!/usr/bin/env python3\nimport os,sys,pathlib\np=pathlib.Path(os.environ["REVIEW_FIXTURES"])\nname=sys.argv[sys.argv.index("application")+1]\nwith (p/"calls").open("a") as f: f.write(name+"\\n")\nsys.stdout.write((p/name).read_text())\n');fake.chmod(0o700)
 for label,target,path,value,expected,enabled in cases:
  for name in names:
   obj=observation(name)
   if name==target:
    setpath(obj,path,value)
    if path=="metadata.deletionTimestamp": obj["metadata"]["finalizers"]=["resources-finalizer.argocd.argoproj.io"]
   (root/('lab-local-'+name)).write_text(json.dumps(obj))
  (root/'calls').write_text('')
  args=[str(observer),'-context','synthetic-unused','-revision',A,'-kubectl',str(fake),'-timeout','600ms']
  if enabled: args+=['-order-enabled','-order-revision',O]
  start=time.monotonic();p=subprocess.run(args,env=dict(os.environ,REVIEW_FIXTURES=tmp),capture_output=True,text=True,timeout=5)
  results['observer'].append({'case':label,'mutation':None if target is None else {'application':'lab-local-'+target,'path':path,'value':value},'expected_exit':expected,'actual_exit':p.returncode,'matched':p.returncode==expected,'elapsed_seconds':round(time.monotonic()-start,3),'calls':(root/'calls').read_text().splitlines(),'synthetic_stdout':p.stdout,'synthetic_stderr':p.stderr})
results['completed_at']=datetime.now(timezone.utc).isoformat()
output.write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'render_equal':sum(x['equal'] for x in results['renders']),'schema_matched':sum(x['matched'] for x in results['schema']),'observer_cases':len(results['observer']),'unexpected_success':[x['case'] for x in results['observer'] if not x['matched']]}))
