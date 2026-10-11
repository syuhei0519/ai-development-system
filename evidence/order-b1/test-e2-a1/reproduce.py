#!/usr/bin/env python3
"""Run independent B1 supplement with a temporary Go overlay, leaving Git files unchanged.
Requires Go 1.27.1, Docker local Unix socket and the fixed PostgreSQL image already loaded.
Output is private test evidence; no GitHub write, deployment or external DB connection.
"""
import argparse, json, os, pathlib, subprocess, tempfile
HEAD='7b54f55cf1a652ee127528877b3bb9034b75b311'
p=argparse.ArgumentParser();p.add_argument('checkout',type=pathlib.Path);args=p.parse_args()
repo=args.checkout.resolve();helper=pathlib.Path(__file__).resolve().with_name('supplement_test.go')
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()==HEAD,'wrong fixed head'
assert not subprocess.check_output(['git','status','--porcelain'],cwd=repo,text=True).strip(),'checkout must be clean'
env=os.environ.copy()
for k in list(env):
 if k.startswith(('PG','PE_')) or k in ['DATABASE_URL','KUBECONFIG','TEST_COLLECTOR_ENDPOINT']:
  env.pop(k)
env['ORDER_DISPOSABLE_TEST']='1'
with tempfile.TemporaryDirectory(prefix='b1-independent-overlay-') as d:
 overlay=pathlib.Path(d)/'overlay.json'
 overlay.write_text(json.dumps({'Replace':{str(repo/'internal/store/orderpostgres/independent_supplement_test.go'):str(helper)}})+'\n')
 result=subprocess.run(['go','test','-overlay',str(overlay),'-race','-v','./internal/store/orderpostgres','-run','^TestIndependent','-count=1'],cwd=repo,env=env)
 assert not subprocess.check_output(['git','status','--porcelain'],cwd=repo,text=True).strip(),'source worktree changed'
 raise SystemExit(result.returncode)
