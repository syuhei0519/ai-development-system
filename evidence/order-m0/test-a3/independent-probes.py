#!/usr/bin/env python3
"""Synthetic independent M0 boundaries. Run with fixed checkout and result path.
Requires prepared helm, PyYAML and checkout/.security/inventory. No live APIs.
"""
import copy,importlib.util,json,subprocess,sys,tempfile
from pathlib import Path
from unittest.mock import patch
import yaml
root=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]);results=[]
assert subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD']).decode().strip()=='e5e6de38cf6ee22ba2f10c9f5fcf05c87004a8e4'
def observe(case,expected,fn):
 try: fn(); actual='accept'
 except Exception: actual='reject'
 results.append(dict(case=case,expected=expected,actual=actual,passed=expected==actual))
def inventory(docs):
 p=subprocess.run([str(root/'.security/inventory')],input=yaml.safe_dump_all(docs).encode(),capture_output=True)
 if p.returncode:raise ValueError('rejected')
 return json.loads(p.stdout)
raw=subprocess.check_output(['helm','template','postgresql',str(root/'charts/postgresql'),'-f',str(root/'environments/local/postgresql.yaml')]).decode()
for name in ['postgresql','order-postgresql']:
 for namespace in [None,'account','synthetic-other']:
  docs=list(yaml.safe_load_all(raw.replace('postgresql',name)))
  for d in docs:
   if namespace is None:d['metadata'].pop('namespace',None)
   else:d['metadata']['namespace']=namespace
  label=name+'/'+str(namespace)
  observe(label+'/fixed-db','accept',lambda:inventory(docs))
  bad=copy.deepcopy(docs)
  next(d for d in bad if d['kind']=='PersistentVolumeClaim')['metadata']['namespace']='mismatch'
  observe(label+'/wrong-pvc-namespace','reject',lambda:inventory(bad))
  for image in ['ghcr.io/syuhei0519/backend-app','ghcr.io/syuhei0519/backend-app-order','ghcr.io/syuhei0519/frontend-app']:
   bad=copy.deepcopy(docs)
   next(d for d in bad if d['kind']=='StatefulSet')['spec']['template']['spec']['containers'][0]['image']=image+':'+'a'*40+'@sha256:'+'b'*64
   observe(label+'/'+image+'/db-substitution','reject',lambda:inventory(bad))
# Legal application inventory remains accepted; not a release approval.
app={'apiVersion':'v1','kind':'Pod','metadata':{'name':'synthetic-app'},'spec':{'containers':[{'name':'app','image':'ghcr.io/syuhei0519/backend-app:'+'a'*40+'@sha256:'+'b'*64}]}}
observe('ordinary-app-inventory','accept',lambda:inventory([app]))
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
r=load('independent_render',root/'ci/trusted-render.py')
t=load('independent_release_tests',root/'ci/github/release_test.py')
# Existing positive complete selection, now explicitly under synthetic token-bearing environment.
def token_boundary():
 case=t.OrderContract();case.setUp()
 try:
  with patch.dict(t.m.os.environ,{k:'synthetic-not-a-secret' for k in ['GH_TOKEN','GITHUB_TOKEN','EVIDENCE_READ_TOKEN','ACTIONS_RUNTIME_TOKEN']}):
   case.test_complete_selection_and_anonymous_registry()
 finally:case.doCleanups()
observe('token-bearing-github-environment-anonymous-registry','accept',token_boundary)
# Snapshot refuses symlink bytes before any chart interpretation.
with tempfile.TemporaryDirectory() as temp:
 repo=Path(temp)/'repo';repo.mkdir()
 def git(*args):return subprocess.check_output(['git','-C',str(repo),*args],stderr=subprocess.DEVNULL)
 git('init','-q');(repo/'charts/x').mkdir(parents=True);(repo/'charts/x/Chart.yaml').symlink_to('/etc/passwd')
 git('add','charts');git('-c','user.name=Synthetic','-c','user.email=synthetic@example.invalid','commit','-qm','Synthetic boundary fixture')
 rev=git('rev-parse','HEAD').decode().strip();dest=Path(temp)/'snapshot';dest.mkdir()
 observe('git-symlink-chart-rejected','reject',lambda:r.snapshot(repo,rev,dest,('charts',)))
# Shell metacharacter inventory cannot enter the fixed render loop.
base={p:{} for n in r.ACTIVE_CHARTS for p in ['charts/'+n+'/Chart.yaml','environments/local/'+n+'.yaml']}
for name in ['order;false','order$(false)','order`false`','../order','unknown']:
 observe('chart-name/'+name,'reject',lambda name=name:r.chart_inventory({**base,'charts/'+name+'/Chart.yaml':{},'environments/local/'+name+'.yaml':{}}))
out.write_text(json.dumps({'synthetic':True,'results':results},indent=2)+'\n')
print(json.dumps({'cases':len(results),'failures':[v for v in results if not v['passed']]}))
sys.exit(any(not v['passed'] for v in results))
