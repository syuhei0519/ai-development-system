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
 # Independently test Account DB identity policy after a repository substitution.
 template=repo/'charts/postgresql/templates/statefulset.yaml'
 text=template.read_text()
 # Replace the rendered image expression with a synthetic fully pinned application image.
 import re
 changed=re.sub(r'(?m)^(\s*image:) .*$',r'\1 ghcr.io/syuhei0519/backend-app:'+('a'*40)+'@sha256:'+('b'*64),text)
 assert changed!=text
 template.write_text(changed)
 render('account-db-app-image-substitution',commit(),'reject')
 run(['git','-C',str(repo),'reset','--hard',head])
(out/'render-fixture-results.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2));sys.exit(any(not r['passed'] for r in summary))
