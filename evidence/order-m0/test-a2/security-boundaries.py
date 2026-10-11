#!/usr/bin/env python3
"""Independent synthetic effective-security tests. No network or deployment."""
import copy,json,subprocess,sys
from pathlib import Path
import yaml
root=Path(sys.argv[1]);out=Path(sys.argv[2]);results=[]
raw=subprocess.check_output(['helm','template','postgresql',str(root/'charts/postgresql'),'-f',str(root/'environments/local/postgresql.yaml')]).decode()
for name in ['postgresql','order-postgresql']:
 docs=list(yaml.safe_load_all(raw.replace('postgresql',name)))
 def check(label,expected,mutate):
  v=copy.deepcopy(docs);s=next(x for x in v if x['kind']=='StatefulSet')['spec']['template']['spec'];mutate(v,s,s['containers'][0])
  p=subprocess.run([str(root/'.security/inventory')],input=yaml.safe_dump_all(v).encode(),capture_output=True)
  actual='accept' if p.returncode==0 else 'reject'
  results.append(dict(case=name+'/'+label,expected=expected,actual=actual,passed=actual==expected,exit_code=p.returncode))
 check('inherit','accept',lambda d,s,c:None)
 legal={'runAsUser':999,'runAsGroup':999,'runAsNonRoot':True,'seccompProfile':{'type':'RuntimeDefault'}}
 check('all-equivalent','accept',lambda d,s,c:c['securityContext'].update(legal))
 for k,value in legal.items():
  check('partial-'+k,'accept',lambda d,s,c,k=k,value=value:c['securityContext'].update({k:value}))
 for k in legal:
  for label,v in [('null',None),('list',[]),('object',{}),('string','999'),('unknown','UNKNOWN'),('float',999.0)]:
   check(k+'/'+label,'reject',lambda d,s,c,k=k,v=v:c['securityContext'].update({k:v}))
 for v in [False,0,1,'true']:
  check('nonroot/'+repr(v),'reject',lambda d,s,c,v=v:c['securityContext'].update(runAsNonRoot=v))
 for v in [{'type':None},{'type':[]},{'type':'Unknown'},{'type':'Localhost','localhostProfile':'synthetic'},{'type':'Unconfined'}]:
  check('seccomp/'+repr(v),'reject',lambda d,s,c,v=v:c['securityContext'].update(seccompProfile=v))
 for role in ['containers','initContainers','ephemeralContainers']:
  for unsafe in [False,True]:
   def add(d,s,c,role=role,unsafe=unsafe):
    side=copy.deepcopy(c);side['name']='synthetic-sidecar'
    if unsafe:side['securityContext'].update(runAsUser=0,runAsNonRoot=False)
    s.setdefault(role,[]).append(side)
   check(role+'/pg-sidecar/'+str(unsafe),'reject',add)
 for key in ['containers','initContainers','ephemeralContainers']:
  for value in [None,{},'invalid']:
   check(key+'/type/'+repr(value),'reject',lambda d,s,c,key=key,value=value:s.update({key:value}))
 check('missing-pvc','reject',lambda d,s,c:d.__setitem__(slice(None),[x for x in d if x['kind']!='PersistentVolumeClaim']))
 check('unknown-resource','reject',lambda d,s,c:d.append({'apiVersion':'unknown/v1','kind':'Unknown','metadata':{'name':'synthetic'}}))
 check('unscanned-podspec','reject',lambda d,s,c:d.append({'apiVersion':'v1','kind':'ConfigMap','metadata':{'name':'synthetic'},'spec':{'containers':[copy.deepcopy(c)]}}))
 check('app-image-as-db','reject',lambda d,s,c:c.update(image='ghcr.io/syuhei0519/backend-app-order:'+('a'*40)+'@sha256:'+('b'*64)))
out.write_text(json.dumps({'synthetic':True,'target':subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD']).decode().strip(),'results':results},indent=2)+'\n')
print(json.dumps({'cases':len(results),'failed':[x for x in results if not x['passed']]}));sys.exit(any(not x['passed'] for x in results))
