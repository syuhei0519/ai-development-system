import pathlib,subprocess,os,json,hashlib,shutil,tarfile,io
root=pathlib.Path(os.environ['PRIVATE_OUTPUT']); repo=pathlib.Path(os.environ['BACKEND_CHECKOUT'])
head='dab0123f4fd459e12c1f64ff2305e5d28d8a41f5'
svc=__import__('sys').argv[1]
work=root/('chain-'+svc);work.mkdir(mode=0o700)
source=subprocess.check_output(['git','-C',str(repo),'archive',head])
with tarfile.open(fileobj=io.BytesIO(source)) as t:t.extractall(work,filter='data')
for p in ['.oci','.security/public','.security/private','.cache/trivy']:(work/p).mkdir(parents=True,exist_ok=True)
for p in (root/'bin').iterdir():shutil.copy2(p,work/'.security'/p.name)
shutil.copyfile(root/'valid'/f'{svc}.oci.tar',work/'.oci/image.tar')
archive=hashlib.sha256((work/'.oci/image.tar').read_bytes()).hexdigest()
def run(args,out=None,env=None):
 with (work/(out or '.security/private/chain.log')).open('w' if out else 'a') as f:
  return subprocess.run(args,cwd=work,env=env,stdout=f,stderr=f,check=True)
run(['.security/github-oci-check','.oci/image.tar',archive,'.oci/layout',head,'syuhei0519/backend-app'],'.security/public/layout.json')
layout=json.loads((work/'.security/public/layout.json').read_text())
run(['.security/oci-crane-check','.oci/layout',layout['digest']],'.security/public/reader.json')
reader=json.loads((work/'.security/public/reader.json').read_text())
env=dict(os.environ,GITHUB_REPOSITORY='syuhei0519/backend-app',RELEASE_SERVICE=svc)
run(['python3','-I','ci/github/runtime.py'],env=env)
scan='''
trivy image --download-db-only --db-repository ghcr.io/aquasecurity/trivy-db:2 --db-repository public.ecr.aws/aquasecurity/trivy-db:2 --cache-dir .cache/trivy --timeout 5m --quiet > .security/private/db.log 2>&1
: > .security/private/empty-ignore
trivy image --input .oci/layout --cache-dir .cache/trivy --skip-db-update --timeout 5m --quiet --no-progress --scanners vuln,secret,misconfig --severity UNKNOWN,LOW,MEDIUM,HIGH,CRITICAL --ignorefile .security/private/empty-ignore --list-all-pkgs --format json --output .security/private/image.json > .security/private/scan.log 2>&1
.security/scan-gate -policy security/scan-policy.json -db .cache/trivy/db/metadata.json -report .security/private/image.json -out .security/public/image-scan.json -scanner-exit 0 -image-config "$IMAGE_CONFIG"
trivy convert --format cyclonedx --output .security/private/sbom.cdx.json .security/private/image.json > .security/private/sbom.log 2>&1
.security/sbom-check .security/private/sbom.cdx.json .security/private/image.json "$IMAGE_CONFIG" > .security/public/sbom-proof.json
cp .security/private/sbom.cdx.json .security/public/sbom.cdx.json
'''
run(['docker','run','--rm','--user',f'{os.getuid()}:{os.getgid()}','--mount',f'type=bind,src={work},dst=/work','--mount',f'type=bind,src={os.environ["SSL_CERT_FILE"]},dst=/etc/task-ca.pem,readonly','-w','/work','-e','SSL_CERT_FILE=/etc/task-ca.pem','-e','IMAGE_CONFIG='+reader['configDigest'],'--entrypoint','sh','aquasec/trivy:0.75.0@sha256:9db099105405c648166e6b94155eb32f8da12673cf1f455207f7385cc9a77283','-ec',scan])
assert archive==hashlib.sha256((work/'.oci/image.tar').read_bytes()).hexdigest()
(root/f'chain-{svc}-result.json').write_text(json.dumps({'service':svc,'head':head,'archive_sha256':archive,'oci_digest':layout['digest'],'config_digest':reader['configDigest'],'reader':'passed','runtime':'passed','scan':'passed','sbom':'passed','original_archive_unchanged':True,'actual_publish':False},indent=2)+'\n')
