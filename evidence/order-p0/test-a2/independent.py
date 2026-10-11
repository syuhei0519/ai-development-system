#!/usr/bin/env python3
"""Independent Test attempt2 synthetic CLI fixture. Never executes real kubectl."""
import copy,json,pathlib,subprocess,os,time,concurrent.futures,hashlib
from datetime import datetime,timezone
ROOT=pathlib.Path(__file__).parent
OUT=ROOT/'results'; CASES=ROOT/'synthetic-cases'; CASES.mkdir(exist_ok=True)
A='b'*40; O='a'*40
names=['postgresql','backend','frontend','order-postgresql','order']
def fixture(name):
    rev=O if name.startswith('order') else A
    src=dict(repoURL='https://github.com/syuhei0519/application-manifest.git',path='charts/'+name,targetRevision=rev if name.startswith('order') else 'main',helm=dict(releaseName=name,valueFiles=['../../environments/local/'+name+'.yaml']))
    dest=dict(server='https://kubernetes.default.svc',namespace='account')
    hook=name+'-migration' if name in ['backend','order'] else None
    return dict(apiVersion='argoproj.io/v1alpha1',kind='Application',metadata=dict(name='lab-local-'+name,namespace='argocd'),spec=dict(project='lab-account',source=src,destination=dest),status=dict(sync=dict(status='Synced',revision=rev,comparedTo=dict(source=copy.deepcopy(src),destination=copy.deepcopy(dest))),health=dict(status='Healthy'),resources=[dict(group='apps',kind='StatefulSet' if 'postgresql' in name else 'Deployment',name=name,namespace='account',status='Synced',health=dict(status='Healthy'))],operationState=dict(phase='Succeeded',syncResult=dict(revision=rev,source=copy.deepcopy(src),resources=[] if not hook else [dict(kind='Job',name=hook,namespace='account',hookType='Sync',hookPhase='Succeeded')]))))
DELETE=object()
def put(obj,path,value):
    keys=path.split('.')
    for key in keys[:-1]: obj=obj[int(key)] if isinstance(obj,list) else obj.setdefault(key,{})
    key=int(keys[-1]) if isinstance(obj,list) else keys[-1]
    if value is DELETE: del obj[key]
    else: obj[key]=copy.deepcopy(value)
cases=[]
def add(label, changes=[], expected=1,enabled=True,mode='normal',timeout='900ms',extra=[]):
    data={name:fixture(name) for name in names}
    for name,path,value in changes: put(data[name],path,value)
    cases.append(dict(label=label,data=data,expected=expected,enabled=enabled,mode=mode,timeout=timeout,extra=extra))
add('enabled-baseline',expected=0);add('disabled-baseline',expected=0,enabled=False)
roots=['spec.source','status.sync.comparedTo.source','status.operationState.syncResult.source']
for target in names[3:]:
    for root in roots:
        for suffix,value in [('repoURL','https://example.invalid/repo.git'),('path','charts/backend'),('targetRevision',A),('chart','other'),('ref','values'),('name','other'),('plugin',{}),('directory',{}),('kustomize',{}),('unknownInput',False),('helm.releaseName','other'),('helm.valueFiles',[]),('helm.parameters',[dict(name='enabled',value='false')]),('helm.fileParameters',[dict(name='x',path='y')]),('helm.values','enabled: false'),('helm.valuesObject',dict(enabled=False)),('helm.namespace','other'),('helm.version','3'),('helm.kubeVersion','1.30'),('helm.apiVersions',['v1']),('helm.passCredentials',True),('helm.ignoreMissingValueFiles',True),('helm.skipCrds',True),('helm.skipTests',True),('helm.skipSchemaValidation',True),('helm.unknownInput',False)]:
            add(target+'/'+root+'/'+suffix,[(target,root+'.'+suffix,value)])
        for label,value in [('missing',DELETE),('null',None),('array',[]),('string','bad'),('number',1)]:
            add(target+'/'+root+'/'+label,[(target,root,value)])
            add(target+'/'+root+'/helm-'+label,[(target,root+'.helm',value)])
        for suffix in ['repoURL','targetRevision','path','helm.releaseName','helm.valueFiles']:
            for label,value in [('missing',DELETE),('null',None),('wrong-type',42)]:
                add(target+'/'+root+'/'+suffix+'-'+label,[(target,root+'.'+suffix,value)])
    for path,value in [('metadata.name','lab-local-backend'),('metadata.namespace','other'),('spec.project','default'),('spec.project',None),('spec.project',DELETE),('spec.project',{}),('spec.destination.server','https://other.invalid'),('spec.destination.namespace','other'),('spec.destination.name','other'),('spec.destination.unknown',False),('status.sync.comparedTo.destination.server','https://other.invalid'),('status.sync.comparedTo.destination.namespace','other'),('status.sync.comparedTo.destination',None),('status.sync.comparedTo',DELETE),('spec.sources',[{}]),('status.sync.comparedTo.sources',[{}]),('status.operationState.syncResult.sources',[{}]),('status.operationState.syncResult.revisions',[O]),('spec.ignoreDifferences',[{}]),('status.sync.comparedTo.ignoreDifferences',[{}]),('spec.sourceHydrator',{}),('status.sync.revision',A),('status.operationState.syncResult.revision',A),('status.resources',[]),('status.resources.0.namespace','other'),('status.resources.0.health.status','Unknown'),('status.resources.0.status','OutOfSync')]:
        add(target+'/'+path+'/'+str(value),[(target,path,value)])
    for suffix,value in [('helm.valuesObject',dict(enabled=False)),('repoURL','https://example.invalid/x.git'),('path','charts/backend')]:
        add(target+'/mutually-wrong/'+suffix,[(target,root+'.'+suffix,value) for root in roots])
    neutral=dict(parameters=[],fileParameters=None,apiVersions=[],values='',valuesObject={},version='',namespace='',kubeVersion='',passCredentials=False,ignoreMissingValueFiles=False,skipCrds=False,skipTests=False,skipSchemaValidation=False)
    changes=[(target,root+'.helm.'+key,value) for root in roots for key,value in neutral.items()]
    changes += [(target,root+'.'+key,value) for root in roots for key,value in dict(chart='',ref='',name='',kustomize=None,directory=None,plugin=None).items()]
    changes += [(target,'metadata.deletionTimestamp',None),(target,'metadata.finalizers',['resources-finalizer.argocd.argoproj.io']),(target,'spec.destination.name',''),(target,'status.sync.comparedTo.destination.name','')]
    add(target+'/all-neutral',changes,expected=0)
for target in names:
    for path in ['status.sync.status','status.health.status','status.operationState.phase']:
        for value in ['Unknown','Progressing','Failed','',None,42]: add(target+'/'+path+'/'+str(value),[(target,path,value)])
    for label,value in [('timestamp','2026-10-11T00:00:00Z'),('empty',''),('false',False),('object',{}),('number',0)]:
        add(target+'/deletion-'+label,[(target,'metadata.deletionTimestamp',value)])
    add(target+'/pending-operation',[(target,'operation',{})])
for target in names[:3]:
    changes=[]
    for name in names[:3]:
        changes.extend([(name,'spec',DELETE),(name,'metadata',DELETE),(name,'status.sync.comparedTo',DELETE),(name,'status.operationState.syncResult.source',DELETE)])
    add('legacy-status-only/'+target,changes,expected=0,enabled=False)
    add('legacy-deleting/'+target,changes+[(target,'metadata.deletionTimestamp','2026-10-11T00:00:00Z')],enabled=False)
for target in ['backend','order']:
    for path,value in [('status.operationState.syncResult.resources',[]),('status.operationState.syncResult.resources.0.hookPhase','Failed'),('status.operationState.syncResult.resources.0.hookType','PreSync'),('status.operationState.syncResult.resources.0.name','wrong'),('status.operationState.syncResult.resources.0.namespace','other')]: add(target+'/'+path,[(target,path,value)])
for mode in ['missing','malformed','null','blocked-read']: add(mode,mode=mode)
add('earlier-db-degrades-during-wait',mode='degrade',timeout='2600ms')
add('missing-order-revision',extra=['-order-revision',''],expected=2)
add('disabled-with-revision',enabled=False,extra=['-order-revision',O],expected=2)
add('zero-timeout',extra=['-timeout','0s'],expected=2)
add('floating-order-revision',extra=['-order-revision','main'],expected=2)
# Missing comparedTo project, operation project/destination and observedGeneration are intentional:
# Argo CD v3.5.2 snapshots do not provide these; no invented success fields.
fake=ROOT/'fake-kubectl.py'
fake.write_text('''#!/usr/bin/env python3
import json,os,pathlib,sys,time
root=pathlib.Path(os.environ['TEST_FIXTURE']); name=sys.argv[sys.argv.index('application')+1]
with (root/'calls').open('a') as f: f.write(json.dumps(sys.argv[1:])+'\\n')
mode=(root/'mode').read_text()
if mode=='blocked-read': time.sleep(30)
if mode=='missing' and name=='lab-local-order': sys.exit(1)
if mode=='malformed': print('{bad');sys.exit(0)
if mode=='null': print('null');sys.exit(0)
data=json.loads((root/name).read_text())
if mode=='degrade':
 calls=(root/'calls').read_text()
 if name=='lab-local-order': data['status']['health']['status']='Progressing'
 if name=='lab-local-postgresql' and calls.count('lab-local-postgresql')>1: data['status']['health']['status']='Degraded'
print(json.dumps(data))
''');fake.chmod(0o700)
def run(pair):
    index,case=pair; folder=CASES/str(index);folder.mkdir(exist_ok=True)
    for name,obj in case['data'].items(): (folder/('lab-local-'+name)).write_text(json.dumps(obj))
    (folder/'mode').write_text(case['mode']);(folder/'calls').write_text('')
    args=[str(ROOT/'observer-new'),'-context','synthetic-no-cluster','-revision',A,'-kubectl',str(fake),'-timeout',case['timeout']]
    if case['enabled']: args+=['-order-enabled','-order-revision',O]
    args+=case['extra']; start=time.monotonic()
    p=subprocess.run(args,env=dict(os.environ,TEST_FIXTURE=str(folder)),capture_output=True,text=True,timeout=5)
    calls=[json.loads(line) for line in (folder/'calls').read_text().splitlines()]
    return dict(case=case['label'],expected=case['expected'],exit=p.returncode,matched=p.returncode==case['expected'],elapsed=round(time.monotonic()-start,3),calls=calls,stdout=p.stdout,stderr=p.stderr,fixture=str(folder.relative_to(ROOT)))
started=datetime.now(timezone.utc).isoformat()
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool: results=list(pool.map(run,enumerate(cases)))
out=dict(document_type='independent_synthetic_test',head='5c7ed4c53d1fa05534987dc3c08b8dfbd2c6645e',started_at=started,completed_at=datetime.now(timezone.utc).isoformat(),binary_sha256=hashlib.sha256((ROOT/'observer-new').read_bytes()).hexdigest(),cases=results)
(OUT/'independent-observer.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(total=len(results),passed=sum(x['matched'] for x in results),failures=[x['case'] for x in results if not x['matched']]),ensure_ascii=False))
