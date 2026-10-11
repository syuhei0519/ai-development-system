"""Independent M1 review probes. Synthetic only; no cluster/OCI/release access.
Usage: python reproduce.py HEAD BASE PLATFORM INVENTORY SCAN_GATE OUTPUT
Requires Helm 4.2.4 in PATH and PyYAML. Binaries must be built from fixed HEAD.
"""
import copy, hashlib, json, pathlib, subprocess, sys, tempfile
from datetime import datetime, timezone
import yaml

head, base, platform, inventory, scanner, output = map(pathlib.Path, sys.argv[1:])
output.mkdir(parents=True, exist_ok=True)
cases = []
def run(args, cwd=head, data=None):
    return subprocess.run(list(map(str,args)),cwd=cwd,input=data,capture_output=True)
def check(name, passed, detail=None):
    cases.append(dict(name=name,passed=bool(passed),detail=detail))
def render(chart, root=head, fixture=None, local=False):
    args=['helm','template',chart,'charts/'+chart,'--namespace','account']
    if local: args+=['-f','environments/local/'+chart+'.yaml']
    if fixture: args+=['-f','ci/fixtures/order/'+fixture]
    p=run(args,root); assert p.returncode==0,p.stderr
    return p.stdout
def inv(docs):
    return run([inventory],data=yaml.safe_dump_all(docs).encode())
def scan(docs):
    with tempfile.TemporaryDirectory() as d:
        p=pathlib.Path(d); (p/'synthetic.yaml').write_text(yaml.safe_dump_all(docs))
        return run([scanner,'-check-render-only',p,'-out',p/'result.json'])
def spec(d): return d['spec']['template']['spec']
fixed='41a7e9632102a8c30ff7fa57570fd85aea19adf1'
check('head',run(['git','rev-parse','HEAD']).stdout.decode().strip()==fixed)
check('tree',run(['git','rev-parse','HEAD^{tree}']).stdout.decode().strip()=='47ea076ac6f481fdf6a1588abcfd0aaf07c4e25d')
paths=run(['git','ls-tree','-r','--name-only','HEAD','charts','environments/local'],base).stdout.decode().splitlines()
check('existing32files',len(paths)==32 and all((head/p).read_bytes()==(base/p).read_bytes() for p in paths),{'count':len(paths)})
for chart in ['frontend','backend','postgresql']:
    a,b=render(chart,head,local=True),render(chart,base,local=True)
    check('existing-render/'+chart,a==b,{'sha256':hashlib.sha256(a).hexdigest()})
for chart in ['order','order-postgresql']:
    for local in [False,True]: check(f'disabled/{chart}/{local}',not render(chart,local=local).strip())
pr=run(['helm','template','workloads','charts/workloads','-f','environments/local/workloads.yaml'],platform)
assert pr.returncode==0
apps=list(yaml.safe_load_all(pr.stdout))
check('fixed-platform-three-apps',len(apps)==3 and {x['metadata']['name'] for x in apps}=={'lab-local-postgresql','lab-local-backend','lab-local-frontend'})
check('fixed-platform-existing-paths',all(x['spec']['destination']['namespace']=='account' and x['spec']['source']['path'] in ['charts/backend','charts/frontend','charts/postgresql'] for x in apps))
raw=render('order',fixture='enabled.yaml')+b'\n---\n'+render('order-postgresql',fixture='postgresql-enabled.yaml')
(output/'synthetic.yaml').write_bytes(raw)
docs=[x for x in yaml.safe_load_all(raw) if x is not None]; by={(x['kind'],x['metadata']['name']):x for x in docs}
dep=by['Deployment','order']; job=by['Job','order-migration']; db=by['StatefulSet','order-postgresql']
check('eleven-resources-three-podspecs',len(docs)==11 and sum(x['kind'] in ['Deployment','Job','StatefulSet'] for x in docs)==3)
check('positive-inventory',inv(docs).returncode==0)
check('positive-scanner',scan(docs).returncode==0)
check('same-image',spec(dep)['containers'][0]['image']==spec(job)['containers'][0]['image'])
check('no-secret-namespace-appproject',not any(x['kind'] in ['Secret','Namespace','AppProject','Application'] for x in docs))
for x in [dep,job]:
    p=spec(x); c=p['containers'][0]
    check(x['kind']+'/security',p['automountServiceAccountToken'] is False and p['securityContext']['runAsUser']==10001 and c['securityContext']['readOnlyRootFilesystem'] is True and c['securityContext']['capabilities']=={'drop':['ALL']})
    refs=[v['valueFrom']['secretKeyRef'] for v in c['env'] if 'valueFrom' in v]
    check(x['kind']+'/app-credentials',refs==[{'name':'order-db','key':'app-username'},{'name':'order-db','key':'app-password'}])
for svc,workload in [('order',dep),('order-postgresql',db),('order-postgresql-headless',db)]:
    sel=by['Service',svc]['spec']['selector']; labels=workload['spec']['template']['metadata']['labels']
    check('selector/'+svc,all(labels.get(k)==v for k,v in sel.items()) and sel['app.kubernetes.io/name'] in ['order','order-postgresql'])
check('migration-budget',job['spec']['activeDeadlineSeconds']==180 and job['spec']['backoffLimit']==1 and spec(job)['restartPolicy']=='Never' and spec(job)['containers'][0]['args']==['migrate'])
check('dedicated-data',any(v.get('persistentVolumeClaim',{}).get('claimName')=='order-postgresql-data' for v in spec(db)['volumes']))
check('pvc-retention',by['PersistentVolumeClaim','order-postgresql-data']['metadata']['annotations']['argocd.argoproj.io/sync-options']=='Prune=false,Delete=false')
check('stateful-retention',db['metadata']['annotations']['argocd.argoproj.io/sync-options']=='Prune=confirm,Delete=confirm')
for kind in ['Pod','Deployment','StatefulSet','DaemonSet','ReplicaSet','ReplicationController','Job','CronJob']:
    p=copy.deepcopy(spec(dep)); meta={'name':'synthetic'}
    api='v1' if kind in ['Pod','ReplicationController'] else 'batch/v1' if kind in ['Job','CronJob'] else 'apps/v1'
    if kind=='Pod': shape=p
    elif kind=='CronJob': shape={'jobTemplate':{'spec':{'template':{'metadata':{},'spec':p}}}}
    else: shape={'template':{'metadata':{},'spec':p}}
    obj={'apiVersion':api,'kind':kind,'metadata':meta,'spec':shape}
    for field in ['hostNetwork','hostPID','hostIPC']:
        for value in [False,True,None,'false',0,[],{}]:
            p[field]=value
            check(f'host-inventory/{kind}/{field}/{value!r}',(inv([obj]).returncode==0)==(value is False))
            check(f'host-scanner/{kind}/{field}/{value!r}',(scan([obj]).returncode==0)==(value is False))
        del p[field]
    for ns in ['account','','kube-system',None,False,[],{}]:
        meta['namespace']=ns
        check(f'namespace/{kind}/{ns!r}',(inv([obj]).returncode==0)==(ns in ['account','']))
for index,obj in enumerate(docs):
    mutated=copy.deepcopy(docs); mutated[index]['metadata']['namespace']='escape'
    check('all-resources-namespace/'+obj['metadata']['name'],inv(mutated).returncode!=0)
for kind in ['ConfigMap','UnknownWorkload']:
    hidden={'apiVersion':'v1','kind':kind,'metadata':{'name':'hidden'},'spec':{'containers':copy.deepcopy(spec(dep)['containers']),'hostPID':True}}
    check('hidden-inventory/'+kind,inv(docs+[hidden]).returncode!=0)
    check('hidden-scanner/'+kind,scan([hidden]).returncode!=0)
for chart,fixture in [('order','enabled.yaml'),('order-postgresql','postgresql-enabled.yaml')]:
    overrides=['enabled=invalid','replicaCount=2','securityContext.privileged=true','podSecurityContext.runAsUser=0','secrets.existingSecret=account-db','imagePullSecrets[0].name=other','extra=1','service.port=80','resources.limits.extra=1']
    if chart=='order': overrides+=['image.tag=latest','release.service=backend','release.runId=999','release.sourceCommit='+('a'*40),'migration.backoffLimit=2']
    else: overrides+=['persistence.enabled=false','persistence.size=1Gi','image.tag=latest','config.dbName=account']
    for value in overrides:
        p=run(['helm','template',chart,'charts/'+chart,'-f','ci/fixtures/order/'+fixture,'--set',value])
        check('schema/'+chart+'/'+value,p.returncode!=0)
result={'observed_at':datetime.now(timezone.utc).isoformat(),'scope':'synthetic independent review','cases':cases,'passed':sum(x['passed'] for x in cases),'failed':sum(not x['passed'] for x in cases)}
(output/'results.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='cases'}))
sys.exit(bool(result['failed']))
