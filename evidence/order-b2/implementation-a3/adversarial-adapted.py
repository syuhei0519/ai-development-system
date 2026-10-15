# Reviewed public edited derivative of completed Implementation self-verification; delivery-only preparation, no new measurement. Private originals retained; no private-original equivalence certification.
"""Implementation rerun of adapted independent Review adversarial probes. All publication transports are mocked.
Usage: python adversarial.py BACKEND_CHECKOUT
Synthetic fixture identities are not real CI evidence.
"""
import sys, pathlib, importlib.util, json, os, copy, unittest
from unittest.mock import patch
ROOT=pathlib.Path(sys.argv.pop(1)).resolve()
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
f=module('review_fixture',ROOT/'ci/github/order-release_test.py');p=f.p
class Review(unittest.TestCase):
 def setUp(self):
  self.fx=f.Interop();self.fx.setUp();self.addCleanup(self.fx.doCleanups)
 def test_no_side_effects_for_event_ref_protection_combinations(self):
  for event in ['pull_request','workflow_dispatch','push']:
   for ref in ['refs/heads/main','refs/heads/feature','refs/tags/main']:
    for protected in ['true','false','True','']:
     if (event,ref,protected)==('push','refs/heads/main','true'):continue
     with self.subTest(event=event,ref=ref,protected=protected),patch.dict(os.environ,GITHUB_EVENT_NAME=event,GITHUB_REF=ref,GITHUB_REF_PROTECTED=protected),patch.object(p,'api') as a,patch.object(p,'run') as r:
      for op in [p.publish,p.propose]:
       with self.assertRaises(ValueError):op()
      a.assert_not_called();r.assert_not_called()
 def test_v2_scalar_types_are_not_coerced(self):
  good=self.fx.published()
  for key in ['runId','runAttempt']:
   for value in [True,False,0,-1,'123',123.0,None]:
    with self.subTest(key=key,value=value),self.assertRaises((ValueError,TypeError)):
     p.validate_record({**good,key:value},self.fx.repo,self.fx.commit,123,2,'order')
  for key in ['published','protectedMain','deploymentAuthorized','sourcePolicyPassed','imagePolicyPassed','sbomValidated','isolatedRuntimePassed']:
   for value in [0,1,'true',None]:
    with self.subTest(key=key,value=value),self.assertRaises((ValueError,TypeError)):
     p.validate_record({**good,key:value},self.fx.repo,self.fx.commit,123,2,'order')
 def test_config_service_swap_and_runtime_extra_fields(self):
  good=json.loads(self.fx.config);path=pathlib.Path('.oci/layout/blobs/sha256');path.mkdir(parents=True,exist_ok=True)
  for change in [{'architecture':'arm64'},{'os':'windows'},{'config':{**good['config'],'Entrypoint':['/server']}},{'config':{**good['config'],'User':'0'}}]:
   raw=json.dumps({**good,**change}).encode();digest='sha256:'+p.sha(raw);(path/digest[7:]).write_bytes(raw)
   with self.assertRaises(ValueError):p.check_config(path.parents[1],digest,'order')
  proofpath=p.PUBLIC/'runtime.json';original=p.load(proofpath)
  proofpath.write_text(json.dumps({**original,'extra':True}))
  with self.assertRaises(ValueError):p.record()
 def test_stale_source_and_image_fail_independently(self):
  for name in ['.validation/source-scan.json','.security/public/image-scan.json']:
   path=pathlib.Path(name);raw=path.read_bytes();good=json.loads(raw)
   for key,value in [('pass',False),('scannedAt','2000-01-01T00:00:00Z'),('dbUpdatedAt','2000-01-01T00:00:00Z'),('trivyVersion','0.1')]:
    path.write_text(json.dumps({**good,key:value}))
    with self.assertRaises(ValueError):p.record()
   path.write_bytes(raw)
 def test_wrong_config_secret_material_never_reaches_publish_api(self):
  p.record();record=p.load(p.PUBLIC/'release-record.json')
  def validator(args,**kw):
   assert args[0]=='github-oci-check'
   path=pathlib.Path(args[3])/'blobs/sha256';path.mkdir(parents=True,exist_ok=True)
   (path/record['imageDigest'][7:]).write_bytes(self.fx.manifest)
   (path/record['configDigest'][7:]).write_bytes(b'wrong config bytes')
   return json.dumps(self.fx.layout).encode()
  with patch.object(p,'run',side_effect=validator),patch.object(p,'api') as a,self.assertRaises(ValueError):p.publish()
  a.assert_not_called()


def probe_scan_swap(output):
 import pathlib,importlib.util,os,json,hashlib,shutil,tempfile,subprocess
 from unittest.mock import patch
 r=pathlib.Path(output).resolve();w=r/'chain-backend';other=r/'chain-order/.security/public/image-scan.json'
 if not other.exists():raise SystemExit('order scan pending')
 s=importlib.util.spec_from_file_location('probe',w/'ci/github/release.py');p=importlib.util.module_from_spec(s);s.loader.exec_module(p)
 env={'GITHUB_REPOSITORY':'syuhei0519/backend-app','GITHUB_SHA':'dab0123f4fd459e12c1f64ff2305e5d28d8a41f5','GITHUB_RUN_ID':'1','GITHUB_RUN_ATTEMPT':'2','GITHUB_WORKFLOW_REF':'syuhei0519/backend-app/.github/workflows/ci.yml@refs/heads/main','GITHUB_EVENT_NAME':'push','GITHUB_REF':'refs/heads/main','GITHUB_REF_PROTECTED':'true','RELEASE_SERVICE':'backend'}
 os.chdir(w);scan=p.PUBLIC/'image-scan.json';record=p.PUBLIC/'release-record.json';before=scan.read_bytes();old=record.read_bytes();foreign=other.read_bytes();assert before!=foreign
 try:
  scan.write_bytes(foreign)
  with patch.dict(os.environ,env):p.record()
  new=json.loads(record.read_bytes());accepted=new['imageScanSha256']==hashlib.sha256(foreign).hexdigest() and new['imagePolicyPassed'] is True
  assert accepted
  with tempfile.TemporaryDirectory(dir=r,prefix='scan-swap-') as tmp:
   tmp=pathlib.Path(tmp)
   shutil.copytree(w/'.security/public',tmp/'.security/public');(tmp/'.oci').mkdir();shutil.copy2(w/'.oci/image.tar',tmp/'.oci/image.tar')
   os.chdir(tmp);calls=[]
   class ReachedAPI(Exception):pass
   def local(args,**kw):
    assert args[0]=='github-oci-check';return subprocess.run([str(r/'bin/github-oci-check'),*args[1:]],capture_output=True,check=True).stdout
   def api(*args,**kw):calls.append(args);raise ReachedAPI()
   try:
    with patch.dict(os.environ,env),patch.object(p,'run',side_effect=local),patch.object(p,'api',side_effect=api):p.publish()
   except ReachedAPI:pass
   assert len(calls)==1
  os.chdir(w)
  matrixroot=r/'production-matrix'
  if matrixroot.exists():
   msp=importlib.util.spec_from_file_location('matrix_probe',w/'ci/github/matrix-result.py');m=importlib.util.module_from_spec(msp);msp.loader.exec_module(m)
   target=matrixroot/'checked-image-2/.security/public';a=target/'image-scan.json';b=target/'release-record.json';ar=a.read_bytes();br=b.read_bytes()
   try:
    a.write_bytes(foreign);b.write_bytes(record.read_bytes())
    with patch.dict(os.environ,env):m.check(matrixroot)
   finally:a.write_bytes(ar);b.write_bytes(br)
  else:raise RuntimeError('normal actual matrix must pass first')
  result={'probe':'actual cross-service image-scan summary replacement before record','source_service':'order','target_service':'backend','accepted':accepted,'all_local_publish_guards_passed':True,'actual_matrix_accepted_mixed_scan':True,'own_scan_sha256':hashlib.sha256(before).hexdigest(),'foreign_scan_sha256':hashlib.sha256(foreign).hexdigest(),'config_digest':new['configDigest'],'archive_sha256':new['archiveSha256'],'image_digest':new['imageDigest'],'sbom_sha256':new['sbomSha256'],'no_registry_or_api_operations':True}
  (r/'scan-swap-probe.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
 finally:os.chdir(w);scan.write_bytes(before);record.write_bytes(old)

if __name__=='__main__':
 if len(sys.argv)>1 and sys.argv[1]=='--scan-swap':probe_scan_swap(sys.argv[2])
 else:unittest.main(verbosity=2)
