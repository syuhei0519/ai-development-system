#!/usr/bin/env python3
"""Independent synthetic M0 probes. No deployment, network API or source writes.
Usage: python3 reproduce.py FIXED_CHECKOUT OUTPUT_JSON
Requires Helm, Go-built inventory and scan-gate supplied in CHECKOUT/.security.
Exit 1 records contract failures, exit 0 all expectations satisfied.
"""
import copy, datetime as dt, hashlib, importlib.util, io, json, os
from pathlib import Path
import stat, subprocess, sys, tempfile, zipfile
from unittest.mock import patch
root=Path(sys.argv[1]).resolve(); output=Path(sys.argv[2]).resolve()
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path); m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
m=module('release_independent',root/'ci/github/release.py')
r=module('render_independent',root/'ci/trusted-render.py')
results=[]
def observe(name,expected,fn):
 try: fn(); actual='accept'
 except Exception as e: actual='reject'
 results.append(dict(case=name,expected=expected,actual=actual,passed=actual==expected))
def reject_unless(value):
 if not value:raise ValueError('rejected')
fixture=root/'ci/github/fixtures'
order=json.loads((fixture/'order-record.json').read_bytes()); account=json.loads((fixture/'backend-record.json').read_bytes())
with patch.object(m,'now',return_value=dt.datetime(2030,1,1,1,tzinfo=dt.timezone.utc)):
 def validate(v,svc='order'):m.validate_record(v,order['repository'],order['sourceCommit'],123,2,svc)
 observe('v2-positive','accept',lambda:validate(order))
 observe('v1-backend-positive','accept',lambda:validate(account,'backend'))
 front={**account,'repository':'syuhei0519/frontend-app','imageRepository':'ghcr.io/syuhei0519/frontend-app','workflowRef':'syuhei0519/frontend-app/.github/workflows/ci.yml@refs/heads/main'}
 observe('v1-frontend-positive','accept',lambda:m.validate_record(front,front['repository'],front['sourceCommit'],123,2,'frontend'))
 for field in order:
  v=copy.deepcopy(order);del v[field]
  observe('record-missing-'+field,'reject',lambda v=v:validate(v))
 for field,val in [('schema',m.SCHEMA),('service','backend'),('service','unknown'),('repository','syuhei0519/backend-app-order'),('sourceCommit','0'*40),('runId',124),('runId',True),('runId','123'),('runAttempt',1),('runAttempt',2.0),('workflowRef',order['workflowRef'].replace('main','feature')),('workflowRef',order['workflowRef'].replace('ci.yml','evil.yml')),('imageRepository','ghcr.io/syuhei0519/backend-app'),('imageDigest','sha256:bad'),('configDigest','bad'),('archiveSha256','bad'),('sbomSha256','bad'),('sourceScanSha256','bad'),('imageScanSha256','bad'),('scannedAt','2030-01-01T01:00:01Z'),('createdAt','2029-12-30T00:00:00Z'),('dbUpdatedAt','2030-01-01T00:00:00'),('validUntil','2030-01-01T01:00:00Z'),('validUntil','2030-01-02T00:00:01Z'),('published',1),('protectedMain','true'),('deploymentAuthorized',True),('unknown',True)]:
  observe('record-invalid-'+field+'-'+str(val),'reject',lambda field=field,val=val:validate({**order,field:val}))
 for svc in ['backend','frontend']:
  observe('v1-service-spoof-'+svc,'reject',lambda svc=svc:m.validate_record({**account,'service':'order'},account['repository'],account['sourceCommit'],123,2,svc))
 for raw in [b'{"a":1,"a":2}',b'{"a":{"x":1,"\\u0078":2}}',b'{"x":NaN}',b'{"x":Infinity}',b'{}junk',b'{']:
  observe('JSON-'+repr(raw),'reject',lambda raw=raw:m.decode(raw))
 for names in [['release-record.json'],['../release-record.json'],['/release-record.json'],['dir/release-record.json'],['release-record.json','extra'],['release-record.json','release-record.json']]:
  import warnings
  with warnings.catch_warnings():
   warnings.simplefilter('ignore');s=io.BytesIO()
   with zipfile.ZipFile(s,'w') as z:
    for n in names:z.writestr(n,b'{}')
  data=s.getvalue()
  observe('ZIP-'+str(names),'accept' if names==['release-record.json'] else 'reject',lambda data=data:m.artifact_record_bytes(data,'sha256:'+m.sha(data)))
 for mode in [stat.S_IFLNK,stat.S_IFDIR,stat.S_IFIFO,stat.S_IFREG]:
  s=io.BytesIO(); zi=zipfile.ZipInfo('release-record.json');zi.external_attr=(mode|0o600)<<16
  with zipfile.ZipFile(s,'w') as z:z.writestr(zi,b'{}')
  data=s.getvalue();observe('ZIP-mode-'+str(mode),'accept' if mode==stat.S_IFREG else 'reject',lambda data=data:m.artifact_record_bytes(data,'sha256:'+m.sha(data)))
 jobs=[dict(name=n,run_id=123,head_sha=order['sourceCommit'],status='completed',conclusion='success') for n in ['validate','image (backend)','image (order)','ci-result']]
 artifacts=[dict(name=n,expired=False,workflow_run=dict(id=123,head_sha=order['sourceCommit']),digest='sha256:'+'1'*64) for n in ['checked-image-2','checked-image-order-2','published-evidence-2','published-evidence-order-2']]
 def matrix(j,a):
  with patch.object(m,'api',side_effect=[dict(jobs=j),dict(artifacts=a)]):m.verify_order_matrix(order['repository'],order['sourceCommit'],123,2)
 observe('matrix-positive','accept',lambda:matrix(jobs,artifacts))
 for i in range(4):
  observe('matrix-missing-job-'+str(i),'reject',lambda i=i:matrix(jobs[:i]+jobs[i+1:],artifacts))
  observe('matrix-missing-artifact-'+str(i),'reject',lambda i=i:matrix(jobs,artifacts[:i]+artifacts[i+1:]))
  j=copy.deepcopy(jobs);j[i]['conclusion']='failure';observe('matrix-failed-job-'+str(i),'reject',lambda j=j:matrix(j,artifacts))
  a=copy.deepcopy(artifacts);a[i]['expired']=True;observe('matrix-expired-artifact-'+str(i),'reject',lambda a=a:matrix(jobs,a))
 observe('matrix-duplicate-job','reject',lambda:matrix(jobs+[jobs[0]],artifacts))
 observe('matrix-duplicate-artifact','reject',lambda:matrix(jobs,artifacts+[artifacts[0]]))
# Fixed inventory set: optional chart+values, unknown names, partial pairs and removal.
def files(names):return {p:{} for n in names for p in ['charts/'+n+'/Chart.yaml','environments/local/'+n+'.yaml']}
base=files(r.ACTIVE_CHARTS)
observe('inventory-optional-absent','accept',lambda:r.chart_inventory(base))
for n in r.INACTIVE_CHARTS:
 observe('inventory-optional-present-'+n,'accept',lambda n=n:r.chart_inventory(files((*r.ACTIVE_CHARTS,n)),list(r.ACTIVE_CHARTS)))
 observe('inventory-missing-values-'+n,'reject',lambda n=n:r.chart_inventory({**base,'charts/'+n+'/Chart.yaml':{}}))
 observe('inventory-missing-chart-'+n,'reject',lambda n=n:r.chart_inventory({**base,'environments/local/'+n+'.yaml':{}}))
 observe('inventory-removed-baseline-'+n,'reject',lambda n=n:r.chart_inventory(base,[*r.ACTIVE_CHARTS,n]))
observe('inventory-unknown-chart','reject',lambda:r.chart_inventory(files((*r.ACTIVE_CHARTS,'rogue'))))
for n in r.ACTIVE_CHARTS:observe('inventory-active-removed-'+n,'reject',lambda n=n:r.chart_inventory(files([x for x in r.ACTIVE_CHARTS if x!=n])))
# Render real fixed chart, then synthetic-only mutations of rendered bytes.
p=subprocess.run(['helm','template','postgresql',str(root/'charts/postgresql'),'-f',str(root/'environments/local/postgresql.yaml')],capture_output=True,check=True)
pg=p.stdout.decode()
mutations={'baseline':pg,'root-override':pg.replace('          securityContext: \n','          securityContext: \n            runAsUser: 0\n            runAsNonRoot: false\n'),'seccomp-override':pg.replace('          securityContext: \n','          securityContext: \n            seccompProfile: {type: Unconfined}\n'),'uid-override':pg.replace('          securityContext: \n','          securityContext: \n            runAsUser: 10001\n'),'gid-override':pg.replace('          securityContext: \n','          securityContext: \n            runAsGroup: 0\n'),'pod-root':pg.replace('runAsUser: 999','runAsUser: 0'),'writable-root':pg.replace('readOnlyRootFilesystem: true','readOnlyRootFilesystem: false'),'pvc-retention':pg.replace('Prune=false,Delete=false','Prune=true,Delete=true'),'stateful-retention':pg.replace('Prune=confirm,Delete=confirm','Prune=true,Delete=true'),'wrong-image':pg.replace('17.10-bookworm','latest'),'hidden-podspec':pg+'\n---\napiVersion: v1\nkind: ConfigMap\nmetadata: {name: hidden}\nspec:\n  containers: [{name: hidden, image: anything}]\n'}
for service in ['postgresql','order-postgresql']:
 for label,data in mutations.items():
  if label!='baseline':assert data!=pg
  data=data.replace('postgresql',service)
  def check(data=data):
   p=subprocess.run([str(root/'.security/inventory')],input=data.encode(),capture_output=True)
   reject_unless(p.returncode==0)
  observe(service+'-'+label,'accept' if label=='baseline' else 'reject',check)
  if label in ['baseline','root-override','seccomp-override','uid-override','gid-override']:
   with tempfile.TemporaryDirectory() as d:
    Path(d,'fixture.yaml').write_text(data)
    p=subprocess.run([str(root/'.security/scan-gate'),'-check-render-only',d,'-out',d+'/scan.json'],capture_output=True)
    results.append(dict(case=service+'-'+label+'-scan-observation',exit_code=p.returncode,expectation='observation only; inventory must enforce fixed effective security'))
output.write_text(json.dumps(dict(target='82505fce911c1dbbe75fe8226a06665e582e1ff9',synthetic=True,results=results),indent=2)+'\n')
failed=[x for x in results if x.get('passed') is False]
print(json.dumps(dict(cases=len(results),failed=failed),indent=2))
sys.exit(bool(failed))
