#!/usr/bin/env python3
"""Reproduce P0 self-validation from the clean fixed checkout; no cluster operations.
Requires Go 1.27.1, Docker and network for pinned public charts/schema/images.
Use --host-ca only where containers need the existing host CA bundle.
Security scanning is optional and distinctly reported; it uses the existing policy.
"""
import argparse
import os
from pathlib import Path
import subprocess

HEAD = 'e01882d8a2c4ac4eadad5b081c1b5c69e5599776'
BASE = 'b989e29b8addbd6396c5c2b4833b969bc15fc8fa'
HELM = 'alpine/helm:4.2.4@sha256:76c375eed56144c68d6197c55bc5a4552fb42002190b796729901cbab3ae6e51'
KUBE = 'ghcr.io/yannh/kubeconform:v0.7.0-alpine@sha256:8f0eeaaa96ba27ba1500b0e4b1c215acc358d159c62a7ecae58d7a03403287b0'
TRIVY = 'aquasec/trivy:0.75.0@sha256:9db099105405c648166e6b94155eb32f8da12673cf1f455207f7385cc9a77283'
SCHEMA = 'https://raw.githubusercontent.com/datreeio/CRDs-catalog/ad3b08c5045129d7bb1eeffd8e61719b2c8dd1e2/argoproj.io/'
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('checkout', type=Path)
p.add_argument('--host-ca', action='store_true')
p.add_argument('--security', action='store_true')
a = p.parse_args()
root = a.checkout.resolve()
def run(args, cwd=root, env=None):
    print('+', ' '.join(args), flush=True)
    subprocess.run(args, cwd=cwd, env=env, check=True)
def capture(args):
    return subprocess.check_output(args, cwd=root, text=True).strip()
assert capture(['git','rev-parse','HEAD']) == HEAD, 'wrong HEAD'
assert not capture(['git','status','--porcelain','--untracked-files=no']), 'tracked modifications'
assert capture(['git','merge-base',HEAD,BASE]) == BASE, 'wrong base ancestry'
assert capture(['go','version']).startswith('go version go1.27.1 '), 'use fixed CI Go version'
run(['bash','ci/github/test.sh'])
for module in ['tools/bootstrap','tools/scan-gate']:
    run(['go','test','-race','./...'],root/module)
    run(['go','vet','./...'],root/module)
run(['git','diff','--check'])
container = ['docker','run','--rm','--user',f'{os.getuid()}:{os.getgid()}','-e','HOME=/tmp','-v',str(root)+':/work','-w','/work']
if a.host_ca:
    container += ['-v','/etc/ssl/certs:/etc/ssl/certs:ro']
run(container + ['--entrypoint','sh',HELM,'-ec','sh ci/validate.sh'])
env = os.environ.copy(); env['PE_OBSERVABILITY_RENDER_DIR'] = '.rendered'
run(['.build/bootstrap-test','-test.run','TestObservabilityContract|TestCollectorContract|TestGrafanaProvisioningBoundary|TestOrderWorkloadsContract','-test.v'],env=env)
run(['.security/scan-gate','-check-render-only','.rendered','-out','.security/public/pre-render.json'])
run(container + [KUBE,'-strict','-summary','-kubernetes-version','1.36.0'] + ['.rendered/'+name+'.yaml' for name in ['runner-foundation','gitlab-runner','observability-foundation','prometheus','argocd-pods','collector-disabled','collector-enabled','grafana']])
for name, schema in [('applications','application'),('projects','appproject')]:
    run(container + [KUBE,'-strict','-summary','-schema-location',SCHEMA+schema+'_v1alpha1.json','.rendered/'+name+'.yaml'])
if a.security:
    run(container + ['-e','SECURITY_RENDER_REQUIRED=true','--entrypoint','sh',TRIVY,'-ec','git config --global --add safe.directory /work; sh ci/source-scan.sh'])
else:
    print('Security scanner NOT RUN; pass --security for the existing source/render policy gates.')
print('P0 self-validation complete. Independent Test/Review, real Service/digest, T6/T7 and P1 remain unverified.')
