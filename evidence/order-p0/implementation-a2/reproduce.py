#!/usr/bin/env python3
"""Implementation self-check reproduction, synthetic observations only.
Requires Go 1.27.1, Helm 4.2.4, Python 3, three fixed clean Git checkouts,
and the canonically consumed (unmodified) Review reproduce.py. No cluster calls.
Usage: reproduce.py OLD_CHECKOUT BASE_CHECKOUT REPAIRED_CHECKOUT REVIEW_SCRIPT NEW_OUTPUT
The Review script remains pinned to OLD; the explicitly supplied observer binary
is built separately from OLD or REPAIRED. Render OLD comparisons in those results
are historical. Repaired render/5-boundary checks are measured separately here.
"""
import hashlib, json, os, pathlib, subprocess, sys
old, base, repaired, review_script, out = map(lambda x:pathlib.Path(x).resolve(), sys.argv[1:])
revs=['e01882d8a2c4ac4eadad5b081c1b5c69e5599776','b989e29b8addbd6396c5c2b4833b969bc15fc8fa','5c7ed4c53d1fa05534987dc3c08b8dfbd2c6645e']
for root, rev in zip([old,base,repaired], revs):
 assert subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()==rev
assert hashlib.sha256(review_script.read_bytes()).hexdigest()=='d7910d86cdfcc5ef6e68b38d41cd5ca02ae80c84af6e8b3af8a302a5d90ebe43'
out.mkdir(exist_ok=False)
for label,root in [('old',old),('new',repaired)]:
 binary=out/('observer-'+label)
 subprocess.run(['go','build','-trimpath','-o',str(binary),'.'],cwd=root/'tools/bootstrap',env=os.environ|{'CGO_ENABLED':'0'},check=True)
 subprocess.run([sys.executable,str(review_script),str(old),str(base),str(binary),str(out/(label+'-reproductions.json'))],check=True)
 data=json.loads((out/(label+'-reproductions.json')).read_bytes())
 misses=[c['case'] for c in data['observer'] if not c['matched']]
 assert len(misses)==(14 if label=='old' else 0),misses
renders=[];boundaries=[]
for chart in ['root','platform','workloads']:
 for local in [False,True]:
  blobs=[subprocess.check_output(['helm','template',chart,'charts/'+chart]+(['-f','environments/local/'+chart+'.yaml'] if local else []),cwd=root) for root in [base,old,repaired]]
  renders.append(dict(chart=chart,values='local' if local else 'default',equal=len(set(blobs))==1,sha256=[hashlib.sha256(b).hexdigest() for b in blobs]))
for path in ['bootstrap/namespaces.yaml','bootstrap/root-project.yaml','bootstrap/argocd-values.yaml','charts/root/templates/projects.yaml','charts/workloads/templates/applications.yaml']:
 blobs=[(root/path).read_bytes() for root in [base,old,repaired]]
 boundaries.append(dict(path=path,equal=len(set(blobs))==1,sha256=hashlib.sha256(blobs[0]).hexdigest()))
assert all(x['equal'] for x in renders+boundaries)
(out/'boundaries.json').write_text(json.dumps(dict(renders=renders,boundaries=boundaries),indent=2)+'\n')
subprocess.run(['bash','ci/github/test.sh'],cwd=repaired,check=True)
for module in ['bootstrap','scan-gate']:
 for args in [['go','test','-race','-count=1','./...'],['go','vet','./...'],['go','build','-trimpath','-o',str(out/module),'.']]:
  subprocess.run(args,cwd=repaired/'tools'/module,check=True)
subprocess.run(['sh','ci/validate.sh'],cwd=repaired,check=True)
subprocess.run([str(repaired/'.build/bootstrap-test'),'-test.run','TestObservabilityContract|TestCollectorContract|TestGrafanaProvisioningBoundary|TestOrderWorkloadsContract','-test.v'],cwd=repaired,env=os.environ|{'PE_OBSERVABILITY_RENDER_DIR':'.rendered'},check=True)
# Schema/security use the pinned images/commands from .github/workflows/ci.yml.
# In environments with a managed TLS CA, mount the existing trust bundle read-only
# and set SSL_CERT_FILE. Never disable certificate verification or change policy.
print('PASS self-checks only; run pinned schema/security CI separately. No product or independent Test/Review claim.')
