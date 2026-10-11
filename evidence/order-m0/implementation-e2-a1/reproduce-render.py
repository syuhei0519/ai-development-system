#!/usr/bin/env python3
"""Implementation self-test derivative of verified Test2; fixed target updated.
Synthetic-only Git fixtures; bounded trusted renderer; no remote writes or deployment."""
import hashlib,json,os,subprocess,sys,tempfile
from pathlib import Path
root=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(exist_ok=True)
head='e5e6de38cf6ee22ba2f10c9f5fcf05c87004a8e4';base='e039945a90625262f91382e6f71149d046e31b34'
def run(args,**kw):return subprocess.run(args,capture_output=True,check=True,**kw).stdout
summary=[]
with tempfile.TemporaryDirectory(prefix='m0-synthetic-') as d:
 repo=Path(d)/'fixture';run(['git','clone','--no-hardlinks','--no-checkout',str(root),str(repo)])
 run(['git','-C',str(repo),'checkout','--detach',head])
 def commit():
  run(['git','-C',str(repo),'add','charts','environments'])
  run(['git','-C',str(repo),'-c','user.name=Synthetic Test','-c','user.email=synthetic@example.invalid','commit','-m','Synthetic fixture only'])
  return run(['git','-C',str(repo),'rev-parse','HEAD']).decode().strip()
 def render(label,source,expect,identity_change=None):
  result=out/(label+'.json')
  p=subprocess.run(['python3','-I',str(root/'ci/trusted-render.py'),'--repo',str(repo),'--target',base,'--source',source,'--verifier',head,'--producer-job-id','0','--test-only','--output',str(result)],capture_output=True)
  actual='accept' if p.returncode==0 else 'reject'
  record=dict(case=label,expected=expect,actual=actual,passed=actual==expect,synthetic=True)
  if p.returncode==0:
   report=json.loads(result.read_bytes());record.update(provenanceRequired=report['provenanceRequired'],eligible=report['eligibleForAuthenticatedVerification'],entries=len(report['renders']['candidate']['inventory']['entries']))
  summary.append(record)
 # Override effective container security via synthetic Helm values only.
 values=repo/'environments/local/postgresql.yaml'
 values.write_text(values.read_text()+'\nsecurityContext:\n  runAsUser: 0\n  runAsNonRoot: false\n  seccompProfile: {type: Unconfined}\n')
 render('effective-security-bypass',commit(),'reject')
 run(['git','-C',str(repo),'reset','--hard',head])
 # Future chart names both present, default disabled, then enabled CI fixture.
 pg=run(['helm','template','postgresql',str(root/'charts/postgresql'),'-f',str(root/'environments/local/postgresql.yaml')]).decode().replace('postgresql','order-postgresql')
 pod='apiVersion: v1\nkind: Pod\nmetadata: {name: order, namespace: account}\nspec:\n  containers:\n  - name: order\n    image: ghcr.io/syuhei0519/backend-app-order:'+'a'*40+'@sha256:'+'b'*64+'\n'
 for name,body in [('order',pod),('order-postgresql',pg)]:
  chart=repo/'charts'/name;(chart/'templates').mkdir(parents=True)
  (chart/'Chart.yaml').write_text('apiVersion: v2\nname: '+name+'\nversion: 0.1.0\n')
  (chart/'values.yaml').write_text('enabled: false\n')
  (chart/'templates/fixture.yaml').write_text('{{ if .Values.enabled }}\n'+body+'\n{{ end }}\n')
  (repo/'environments/local'/str(name+'.yaml')).write_text('enabled: false\n')
 render('optional-disabled',commit(),'accept')
 for name in ['order','order-postgresql']:(repo/'environments/local'/str(name+'.yaml')).write_text('enabled: true\n')
 render('optional-enabled',commit(),'accept')
 # An enabled synthetic Order DB must still reject broken retention.
 f=repo/'charts/order-postgresql/templates/fixture.yaml';f.write_text(f.read_text().replace('Prune=false,Delete=false','Prune=true,Delete=true'))
 render('enabled-invalid-pvc',commit(),'reject')
(out/'render-fixture-results.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2));sys.exit(any(not r['passed'] for r in summary))
