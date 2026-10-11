"""Synthetic independent B2 cases; no credentials, network or publication.
Usage: python independent-negative.py FIXED_BACKEND_CHECKOUT FIXED_M0_CHECKOUT
Existing fixture setup supplies data only; new mutations/assertions are below.
"""
import sys, importlib.util, unittest, copy, json, os, shutil, subprocess
from pathlib import Path
from unittest.mock import patch
BACKEND=Path(sys.argv.pop(1)).resolve(); M0=Path(sys.argv.pop(1)).resolve()
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
fixtures=module('fixture_setup',BACKEND/'ci/github/order-release_test.py')
p=fixtures.p; a=fixtures.a;c=module('fresh_fixed_consumer',M0/'ci/github/release.py')
class Independent(unittest.TestCase):
 def setUp(self):
  self.f=fixtures.Interop();self.f.setUp();self.addCleanup(self.f.doCleanups)
  self.clock=patch.object(c,'now',return_value=self.f.clock);self.clock.start();self.addCleanup(self.clock.stop)
 def write(self,path,value):Path(path).write_text(json.dumps(value))
 def matrix(self):
  p.record();original=p.load('.security/public/release-record.json');root=Path('.checked');root.mkdir()
  for service in ('backend','order'):
   dest=root/('checked-image-'+('order-' if service=='order' else '')+'2');pub=dest/'.security/public';pub.mkdir(parents=True);(dest/'.oci').mkdir()
   data=('synthetic archive '+service).encode();(dest/'.oci/image.tar').write_bytes(data)
   record=copy.deepcopy(original);record['archiveSha256']=p.sha(data)
   if service=='backend':
    record.pop('service');record['schema']=p.SCHEMA;record['imageRepository']='ghcr.io/'+self.f.repo
    record['imageDigest']='sha256:'+'d'*64;record['configDigest']='sha256:'+'e'*64
   for name in ('source-scan.json','source-identity.json','image-scan.json','sbom.cdx.json'):(pub/name).write_bytes((p.PUBLIC/name).read_bytes())
   self.write(pub/'release-record.json',record)
   self.write(pub/'runtime.json',dict(service=service,digest=record['imageDigest'],archiveSha256=record['archiveSha256'],configDigest=record['configDigest'],passed=True,readOnly=True,capDrop='ALL',network='internal'))
  a.check(root);return root
 def test_matrix_extra_missing_and_collision(self):
  root=self.matrix();order=root/'checked-image-order-2'
  for name in ('checked-image-order-3','checked-image-3','unexpected'):
   order.rename(root/name)
   with self.subTest(name=name),self.assertRaises(ValueError):a.check(root)
   (root/name).rename(order)
  shutil.copytree(order,root/'extra')
  with self.assertRaises(ValueError):a.check(root)
  shutil.rmtree(root/'extra');shutil.rmtree(order)
  with self.assertRaises(ValueError):a.check(root)
 def test_matrix_byte_tampering(self):
  root=self.matrix();base=root/'checked-image-order-2'
  for name in ('.oci/image.tar','.security/public/sbom.cdx.json','.security/public/image-scan.json','.security/public/source-scan.json'):
   path=base/name;raw=path.read_bytes();path.write_bytes(raw+b'\n')
   with self.subTest(file=name),self.assertRaises(ValueError):a.check(root)
   path.write_bytes(raw)
 def test_matrix_identity_runtime_and_policy(self):
  root=self.matrix();public=root/'checked-image-order-2/.security/public';path=public/'release-record.json';raw=path.read_bytes()
  mutations={'runId':999,'runAttempt':1,'sourceCommit':'b'*40,'repository':'other/backend-app','workflowRef':'other','service':'backend','schema':p.SCHEMA,'imageRepository':'ghcr.io/other/backend-app-order','published':True,'deploymentAuthorized':True,'sourcePolicyPassed':False,'imagePolicyPassed':False,'sbomValidated':False,'isolatedRuntimePassed':False,'configDigest':'sha256:'+'0'*64,'imageDigest':'sha256:'+'0'*64}
  for key,value in mutations.items():
   self.write(path,{**p.decode(raw),key:value})
   with self.subTest(field=key),self.assertRaises(ValueError):a.check(root)
  path.write_bytes(raw)
  runtime=public/'runtime.json';raw=runtime.read_bytes()
  for key,value in [('readOnly',False),('capDrop','NET_ADMIN'),('network','bridge'),('service','backend'),('passed',False)]:
   self.write(runtime,{**p.decode(raw),key:value})
   with self.subTest(runtime=key),self.assertRaises(ValueError):a.check(root)
  runtime.write_bytes(raw)
 def test_publish_tamper_before_side_effects(self):
  p.record()
  for name in ('.oci/image.tar','.security/public/sbom.cdx.json','.security/public/image-scan.json'):
   path=Path(name);raw=path.read_bytes();path.write_bytes(raw+b'corruption')
   with self.subTest(file=name),patch.object(p,'api') as api,patch.object(p,'run') as run,self.assertRaises(ValueError):p.publish()
   api.assert_not_called();run.assert_not_called();path.write_bytes(raw)
 def test_producer_records_real_fixed_consumer(self):
  record=self.f.published();c.validate_record(record,self.f.repo,self.f.commit,123,2,'order')
  for key,value in [('service','unknown'),('repository','other/backend-app'),('imageRepository','ghcr.io/other/backend-app-order'),('runId',124),('runAttempt',3),('sourceCommit','b'*40),('validUntil','2000-01-01T00:00:00Z'),('published',False),('protectedMain',False),('deploymentAuthorized',True)]:
   with self.subTest(field=key),self.assertRaises(ValueError):c.validate_record({**record,key:value},self.f.repo,self.f.commit,123,2,'order')
  self.assertEqual(p.tag_for(self.f.commit,123,2,'backend'),c.tag_for(self.f.commit,123,2,'backend'))
  self.assertNotEqual(p.tag_for(self.f.commit,123,2,'backend'),p.tag_for(self.f.commit,123,2,'order'))
 def test_proposal_missing_order_values_has_no_writes(self):
  record=self.f.published();calls=[]
  def api(path,method='GET',**kw):
   calls.append((path,method));self.assertEqual(method,'GET')
   if '/git/ref/heads/main' in path:return {'object':{'sha':self.f.commit}}
   self.assertIn('/application-manifest/contents/environments/local/order.yaml?ref=',path)
   raise FileNotFoundError('synthetic missing Order values')
  with patch.object(p,'release_data',return_value=(record,{},'0'*64)),patch.object(p,'api',side_effect=api),self.assertRaises(FileNotFoundError):p.propose()
  self.assertEqual(len(calls),3)
 def test_ci_required_job_status_fail_closed(self):
  # Execute the exact workflow gate shell before its separate artifact checker.
  workflow=(BACKEND/'.github/workflows/ci.yml').read_text();shell=workflow.split('      - name: Required check\n',1)[1].split('        run: |\n',1)[1]
  shell='\n'.join(line[10:] for line in shell.splitlines())
  shell=shell.replace('python3 -I ci/github/matrix-result.py','true')
  env={**os.environ,'DOCS':'false','CLASSIFY':'success','DOCS_RESULT':'skipped','VALIDATE':'success','IMAGE':'success'}
  self.assertEqual(subprocess.run(['bash','-e','-c',shell],env=env,capture_output=True).returncode,0)
  for field in ('CLASSIFY','VALIDATE','IMAGE'):
   for value in ('failure','skipped','cancelled',''):
    with self.subTest(field=field,value=value):self.assertNotEqual(subprocess.run(['bash','-e','-c',shell],env={**env,field:value},capture_output=True).returncode,0)
  self.assertIn('fail-fast: false',workflow)
if __name__=='__main__':unittest.main(verbosity=2)
