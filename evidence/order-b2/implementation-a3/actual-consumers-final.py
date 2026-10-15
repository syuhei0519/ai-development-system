# Reviewed public edited derivative of completed Implementation self-verification; delivery-only preparation, no new measurement. Private originals retained; no private-original equivalence certification.
import pathlib,json,importlib.util,copy,os
r=pathlib.Path(os.environ['REPRO_ROOT']);checks=[]
def module(path):
 s=importlib.util.spec_from_file_location('consumer',path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
for service in ('backend','order'):
 data=json.loads((r/'final'/f'{service}-publish-binding.json').read_bytes());record=data['mocked_published_record'];assert record['imagePolicyPassed'] and data['actual_registry_or_github_writes'] is False
 for version in ('m0','m1'):
  m=module(r/version/'ci/github/release.py');args=(record['repository'],record['sourceCommit'],1,2,service)
  m.validate_record(record,*args)
  cases={'sourceCommit':'b'*40,'repository':'other/backend-app','runId':2,'runAttempt':3,'configDigest':'invalid','imageDigest':'invalid','imageRepository':'ghcr.io/other/backend-app','imagePolicyPassed':False,'validUntil':'2000-01-01T00:00:00Z'}
  if service=='order':cases.update(service='backend',extra=True)
  for key,value in cases.items():
   try:m.validate_record({**record,key:value},*args)
   except (ValueError,KeyError,TypeError):pass
   else:raise AssertionError((version,service,key))
  path=r/version/'environments/local'/f'{service}.yaml'
  if path.exists():
   before=path.read_text();after=m.patch_values(before,record['repository'],record['sourceCommit'],record,{'release-record.json':'synthetic','sbom.cdx.json':'synthetic'},'0'*64)
   assert record['imageDigest'] in after
   if service=='order':assert '\nenabled: false\n' in '\n'+after
  checks.append({'consumer':version,'service':service,'real_producer_record_accepted':True,'negative_cases':len(cases),'actual_values_checked':path.exists()})
(r/'actual-consumers-final.json').write_text(json.dumps({'checks':checks,'publication_transport':'mock only; actual OCI and policy inputs'},indent=2)+'\n');print('PASS actual producer output / both fixed consumers')
