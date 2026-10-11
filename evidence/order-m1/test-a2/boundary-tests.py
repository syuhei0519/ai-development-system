"""Independent synthetic adversarial boundary tests; no deployment or release proof."""
import copy,datetime,hashlib,json,pathlib,subprocess,sys,tempfile
import yaml
r=pathlib.Path(sys.argv[1]);source=pathlib.Path(sys.argv[2]);out=pathlib.Path(sys.argv[3]);out.mkdir(exist_ok=True)
inv=r/'.build/order-inventory';scan=r/'.security/scan-gate';results=[]
docs=[d for f in ['order-synthetic.yaml','order-postgresql-synthetic.yaml'] for d in yaml.safe_load_all((source/f).read_text()) if d]
def observe(name,ds,expected_inv,expected_scan):
 start=datetime.datetime.now(datetime.timezone.utc).isoformat();raw=yaml.safe_dump_all(ds,sort_keys=False).encode()
 with tempfile.TemporaryDirectory() as td:
  p=pathlib.Path(td);(p/'fixture.yaml').write_bytes(raw)
  a=subprocess.run([str(inv)],input=raw,capture_output=True)
  b=subprocess.run([str(scan),'-check-render-only',td,'-out',str(p/'result.json')],capture_output=True)
  findings=json.loads((p/'result.json').read_text()) if (p/'result.json').exists() else {}
  results.append(dict(case=name,observed_at=start,sha256=hashlib.sha256(raw).hexdigest(),inventory_exit=a.returncode,structural_exit=b.returncode,expected_inventory=expected_inv,expected_structural=expected_scan,passed=(a.returncode==0)==expected_inv and (b.returncode==0)==expected_scan,host_findings=sum(x.get('rule')=='LOCAL-HOST-NAMESPACE' for x in findings.get('findings',[]))))
  if not results[-1]['passed']: (out/(name+'.yaml')).write_bytes(raw)
observe('positive',docs,True,True)
# All supported PodSpec forms and all three host namespace fields. Include YAML typed values,
# malformed booleans, foreign namespaces and DB identities in full original positive fixture.
base=next(d for d in docs if d['kind']=='Deployment')
for kind,api in [('Pod','v1'),('Deployment','apps/v1'),('StatefulSet','apps/v1'),('DaemonSet','apps/v1'),('ReplicaSet','apps/v1'),('ReplicationController','v1'),('Job','batch/v1'),('CronJob','batch/v1')]:
 d=copy.deepcopy(base);d['kind']=kind;d['apiVersion']=api
 spec=d['spec']['template']['spec'];meta=d['spec']['template']['metadata']
 if kind=='Pod':d['spec']=spec;d['metadata'].update(meta)
 elif kind=='CronJob':d['spec']={'jobTemplate':{'spec':{'template':{'metadata':meta,'spec':spec}}}}
 for field in ['hostNetwork','hostPID','hostIPC']:
  for n,v in enumerate([False,True,None,'false','true',0,1,[],{},'off','no']):
   m=copy.deepcopy(d)
   ps=m['spec'] if kind=='Pod' else m['spec']['jobTemplate']['spec']['template']['spec'] if kind=='CronJob' else m['spec']['template']['spec']
   ps[field]=v;observe(f'{kind}-{field}-{n}',[m],v is False,v is False)
for pos,d in enumerate(docs):
 for n,v in enumerate(['account','',None,False,0,[],{},'kube-system','account ','Account','account\n']):
  m=copy.deepcopy(docs);m[pos]['metadata']['namespace']=v
  observe(f'namespace-{pos}-{n}',m,v in ['account',''] if isinstance(v,str) else False,True)
for kind in ['StatefulSet','Job']:
 for field in ['hostNetwork','hostPID','hostIPC']:
  m=copy.deepcopy(docs);next(d for d in m if d['kind']==kind)['spec']['template']['spec'][field]=True
  observe('dedicated-'+kind+'-'+field,m,False,False)
# Hidden PodSpec and unknown kind are independently challenged.
for kind in ['ConfigMap','UnknownWorkload']:
 m=copy.deepcopy(base);m['kind']=kind
 m['spec']['template']['spec']['hostPID']=True
 observe('hidden-'+kind,[m],False,False)
(out/'boundary-results.json').write_text(json.dumps(dict(synthetic_only=True,head='41a7e9632102a8c30ff7fa57570fd85aea19adf1',results=results),indent=2)+'\n')
print('cases',len(results),'failed',sum(not x['passed'] for x in results))
sys.exit(any(not x['passed'] for x in results))
