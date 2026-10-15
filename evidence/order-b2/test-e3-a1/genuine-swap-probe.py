# Independent Test adaptation of fixed upstream probe; historical Implementation annotation replaced for this execution.
"""Independent Test: genuine image inputs, all external effects mocked."""
import os,json,pathlib,hashlib,importlib.util,subprocess,tempfile,shutil
from unittest.mock import patch
P=pathlib.Path
root=P(os.environ['PRIVATE_OUTPUT']);head=subprocess.check_output(['git','-C',os.environ['BACKEND_CHECKOUT'],'rev-parse','HEAD'],text=True).strip()
def mod(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def sha(b):return hashlib.sha256(b).hexdigest()
results=[]
for service,other in [('backend','order'),('order','backend')]:
 w=root/('chain-'+service);os.chdir(w);m=mod('release_'+service,w/'ci/github/release.py');matrix=mod('matrix_'+service,w/'ci/github/matrix-result.py')
 env={'GITHUB_REPOSITORY':'syuhei0519/backend-app','GITHUB_SHA':head,'GITHUB_RUN_ID':'1','GITHUB_RUN_ATTEMPT':'2','GITHUB_WORKFLOW_REF':'syuhei0519/backend-app/.github/workflows/ci.yml@refs/heads/main','GITHUB_EVENT_NAME':'push','GITHUB_REF':'refs/heads/main','GITHUB_REF_PROTECTED':'true','RELEASE_SERVICE':service}
 public=w/'.security/public';scan=public/'image-scan.json';record=public/'release-record.json';good=scan.read_bytes();goodrecord=record.read_bytes()
 foreign=(root/('chain-'+other)/'.security/public/image-scan.json').read_bytes()
 assert json.loads(good)['imageIdentity']['configDigest']!=json.loads(foreign)['imageIdentity']['configDigest']
 variants={'foreign-proof-only':{'image-proof.json':(root/('chain-'+other)/'.security/public/image-proof.json').read_bytes()},'foreign-summary':{'image-scan.json':foreign},'foreign-summary-and-proof':{'image-scan.json':foreign,'image-proof.json':(root/('chain-'+other)/'.security/public/image-proof.json').read_bytes()}}
 for label,changes in variants.items():
  original={n:(public/n).read_bytes() for n in changes}
  try:
   for n,b in changes.items():(public/n).write_bytes(b)
   record.unlink()
   with patch.dict(os.environ,env):
    try:m.record()
    except (ValueError,KeyError,FileNotFoundError):pass
    else:raise AssertionError('foreign scan accepted by record')
   assert not record.exists()
   # Simulate the old minting flaw by rehashing the substituted scan into a record.
   forged=json.loads(goodrecord);forged['imageScanSha256']=sha(scan.read_bytes());record.write_text(json.dumps(forged))
   matrixroot=root/'production-matrix';target=matrixroot/('checked-image-'+('order-' if service=='order' else '')+'2')/'.security/public'
   save={n:(target/n).read_bytes() for n in [*changes,'release-record.json']}
   try:
    for n in save:(target/n).write_bytes((public/n).read_bytes())
    with patch.dict(os.environ,env):
     try:matrix.check(matrixroot)
     except (ValueError,KeyError,FileNotFoundError):pass
     else:raise AssertionError('foreign scan accepted by matrix')
   finally:
    for n,b in save.items():(target/n).write_bytes(b)
   with tempfile.TemporaryDirectory(dir=root,prefix='publish-probe-') as temp:
    temp=P(temp);shutil.copytree(public,temp/'.security/public');(temp/'.oci').mkdir();shutil.copyfile(w/'.oci/image.tar',temp/'.oci/image.tar');os.chdir(temp)
    calls=[]
    def local(args,**kw):
     assert args[0]=='github-oci-check';calls.append(args[0]);return subprocess.run([str(root/'bin/github-oci-check'),*args[1:]],capture_output=True,check=True).stdout
    with patch.dict(os.environ,env),patch.object(m,'api') as api,patch.object(m,'run',side_effect=local):
     try:m.publish()
     except (ValueError,KeyError,FileNotFoundError):pass
     else:raise AssertionError('foreign scan accepted by publish')
     api.assert_not_called()
    assert calls==['github-oci-check']
   os.chdir(w)
   results.append({'target':service,'foreign':other,'case':label,'record_refused_before_mint':True,'matrix_refused_rehashed_scan':True,'publish_refused_before_api_registry':True,'real_original_oci_rechecked':True})
  finally:
   os.chdir(w)
   for n,b in original.items():(public/n).write_bytes(b)
   record.write_bytes(goodrecord)
 # Swap raw scanner JSON before the trusted producer. It must not bless it.
 policy=mod('policy_'+service,w/'ci/github/image-policy.py');raw=w/'.security/private/image.json';before=raw.read_bytes()
 saved={f.name:f.read_bytes() for f in public.iterdir() if f.is_file()}
 try:
  raw.write_bytes((root/('chain-'+other)/'.security/private/image.json').read_bytes())
  with patch.dict(os.environ,env):
   try:policy.check()
   except ValueError:pass
   else:raise AssertionError('foreign raw scan accepted')
  assert not (public/'image-proof.json').exists() and not scan.exists()
  results.append({'target':service,'case':'foreign-raw-before-producer','refused':True,'prior_proof_removed':True})
 finally:
  raw.write_bytes(before)
  for n,b in saved.items():(public/n).write_bytes(b)
(root/'scan-swap-fixed.json').write_text(json.dumps({'head':head,'measurements':results,'external_operations':False},indent=2)+'\n')
print('PASS: bidirectional real summary/proof/raw swaps refused at producer/record/matrix/publish boundaries')
