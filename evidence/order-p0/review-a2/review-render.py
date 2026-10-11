#!/usr/bin/env python3
"""Read-only source and synthetic render measurements for Review2."""
import hashlib,json,pathlib,subprocess,sys,yaml
from datetime import datetime,timezone
head,base,manifest,oldmanifest,out=map(pathlib.Path,sys.argv[1:])
def digest(b):return hashlib.sha256(b).hexdigest()
def render(root,chart,local):return subprocess.check_output(['helm','template',chart,'charts/'+chart]+(['-f','environments/local/'+chart+'.yaml'] if local else []),cwd=root)
r={'document_type':'review_render_measurement','started_at':datetime.now(timezone.utc).isoformat(),'renders':[],'boundaries':[],'manifest':{'registered':[],'disabled':[]},'schema':[]}
for chart in ['root','platform','workloads']:
 for local in [False,True]:
  b=[render(p,chart,local) for p in [base,head]]
  r['renders'].append({'chart':chart,'local':local,'equal':b[0]==b[1],'sizes':list(map(len,b)),'sha256':list(map(digest,b))})
for f in ['bootstrap/namespaces.yaml','bootstrap/root-project.yaml','charts/root/templates/projects.yaml','bootstrap/argocd-values.yaml','charts/workloads/templates/applications.yaml']:
 b=[(p/f).read_bytes() for p in [base,head]];r['boundaries'].append({'path':f,'equal':b[0]==b[1],'sha256':list(map(digest,b))})
for chart in ['postgresql','backend','frontend']:
 paths=['charts/'+chart,'environments/local/'+chart+'.yaml']
 changed=subprocess.check_output(['git','diff','--name-only','bc6adaedcd645a4663c23284b977a3dd36c0796d','df8c8b5d93e48bc1f0e5ced1678bba2e27d6a1f9','--']+paths,cwd=manifest,text=True).splitlines()
 outputs=[]
 for local in [False,True]:
  procs=[subprocess.run(['helm','template',chart,'charts/'+chart]+(['-f','environments/local/'+chart+'.yaml'] if local else []),cwd=p,capture_output=True) for p in [oldmanifest,manifest]]
  b=[p.stdout for p in procs]
  outputs.append({'local':local,'equal':b[0]==b[1] and procs[0].returncode==procs[1].returncode and sorted(procs[0].stderr.splitlines())==sorted(procs[1].stderr.splitlines()),'exit':[p.returncode for p in procs],'sizes':list(map(len,b)),'sha256':list(map(digest,b)),'stderr_sha256':[digest(p.stderr) for p in procs]})
  if local: assert all(p.returncode==0 for p in procs)
 r['manifest']['registered'].append({'chart':chart,'changed_paths':changed,'renders':outputs})
for chart in ['order-postgresql','order']:
 for local in [False,True]:
  b=render(manifest,chart,local)
  r['manifest']['disabled'].append({'chart':chart,'local':local,'documents':[d for d in yaml.safe_load_all(b) if d],'bytes':len(b),'sha256':digest(b)})
for chart in ['order-postgresql','order']:
 for f in ['charts/'+chart+'/values.yaml','environments/local/'+chart+'.yaml']:
  assert yaml.safe_load((manifest/f).read_text())['enabled'] is False
O='a'*40
cases=[('default',{},0),('enabled',{'orderEnabled':True,'orderTargetRevision':O},0),('staged-disabled',{'orderEnabled':False,'orderTargetRevision':O},0)]
for rev in ['',None,False,42,[],{},'main','HEAD','v1','a'*39,'a'*41,'A'*40,'g'*40,' '+O]: cases.append(('bad-revision/'+str(rev),{'orderEnabled':True,'orderTargetRevision':rev},1))
for val in ['true','false',None,42,[],{}]: cases.append(('bad-enable/'+str(val),{'orderEnabled':val},1))
cases.extend([('unknown-key',{'orderEnable':True},1),('wrong-repo',{'applicationRepository':'other'},1),('account-not-main',{'targetRevision':O},1)])
for label,values,want in cases:
 args=['helm','template','workloads','charts/workloads']
 for k,v in values.items(): args+=['--set-json',k+'='+json.dumps(v)]
 p=subprocess.run(args,cwd=head,capture_output=True)
 r['schema'].append({'case':label,'exit':p.returncode,'expected':want,'matched':p.returncode==want})
b=subprocess.check_output(['helm','template','workloads','charts/workloads','--set','orderEnabled=true','--set-string','orderTargetRevision='+O],cwd=head)
a=list(yaml.safe_load_all(b)); default=list(yaml.safe_load_all(render(head,'workloads',False)))
assert len(a)==5 and a[:3]==default
r['topology']={'count':len(a),'existing_unchanged':a[:3]==default,'order':a[3:]}
for app,name,wave in zip(a[3:],['order-postgresql','order'],['-10','0']):
 assert app['metadata']['name']=='lab-local-'+name and app['metadata']['annotations']['argocd.argoproj.io/sync-wave']==wave
 assert app['spec']['source']=={'repoURL':'https://github.com/syuhei0519/application-manifest.git','targetRevision':O,'path':'charts/'+name,'helm':{'releaseName':name,'valueFiles':['../../environments/local/'+name+'.yaml']}}
 assert app['spec']['project']=='lab-account' and app['spec']['destination']=={'server':'https://kubernetes.default.svc','namespace':'account'}
r['manifest']['old_revision']='bc6adaedcd645a4663c23284b977a3dd36c0796d';r['manifest']['current_revision']='df8c8b5d93e48bc1f0e5ced1678bba2e27d6a1f9'
r['manifest']['current_tree']=subprocess.check_output(['git','rev-parse','HEAD^{tree}'],cwd=manifest,text=True).strip()
r['completed_at']=datetime.now(timezone.utc).isoformat();out.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
assert all(x['equal'] for x in r['renders']+r['boundaries']) and all(x['matched'] for x in r['schema'])
assert all(not x['changed_paths'] and all(y['equal'] for y in x['renders']) for x in r['manifest']['registered'])
assert all(not x['documents'] for x in r['manifest']['disabled'])
print(json.dumps({'six_renders_equal':True,'five_boundaries_equal':True,'schema_cases':len(cases),'manifest_registered_three_unchanged':True,'manifest_three_local_renders_equal':True,'manifest_default_behavior_unchanged':True,'manifest_order_four_renders_empty':True}))
