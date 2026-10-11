#!/usr/bin/env python3
"""Review boundary reproduction with an external Go overlay; no source edits.
Use Go 1.27.1, local Docker and the preloaded pinned PostgreSQL image.
Only fresh disposable fixtures are created. Do not supply a live database DSN.
"""
import argparse,json,os,pathlib,subprocess,tempfile
p=argparse.ArgumentParser();p.add_argument('checkout',type=pathlib.Path);a=p.parse_args();repo=a.checkout.resolve()
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()=='7b54f55cf1a652ee127528877b3bb9034b75b311'
assert not subprocess.check_output(['git','status','--porcelain'],cwd=repo,text=True).strip()
env=os.environ.copy()
for k in list(env):
 if k.startswith(('PG','PE_')) or k in ['DATABASE_URL','KUBECONFIG','TEST_COLLECTOR_ENDPOINT']:env.pop(k)
env['ORDER_DISPOSABLE_TEST']='1'
with tempfile.TemporaryDirectory(prefix='order-review-overlay-') as d:
 overlay=pathlib.Path(d)/'overlay.json';overlay.write_text(json.dumps({'Replace':{str(repo/'internal/store/orderpostgres/review_boundary_test.go'):str(pathlib.Path(__file__).resolve().with_name('review_boundary_test.go'))}})+'\n')
 result=subprocess.run(['go','test','-overlay',str(overlay),'-race','-v','./internal/store/orderpostgres','-run','^TestReview','-count=1'],cwd=repo,env=env)
 assert not subprocess.check_output(['git','status','--porcelain'],cwd=repo,text=True).strip()
 raise SystemExit(result.returncode)
