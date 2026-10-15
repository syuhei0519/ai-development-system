"""Narrow synthetic R-B2-1/type regression. This does not verify real OCI scans.
Usage: python independent-probe.py FIXED_CHECKOUT OUTPUT_JSON
"""
import copy, datetime as dt, importlib.util, json, os
from pathlib import Path
import subprocess, sys
from unittest.mock import patch
repo=Path(sys.argv[1]).resolve(); output=Path(sys.argv[2]).resolve()
head=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
assert head=='24083aba485abd6b37bcbe71736fb543a847dcc6'
def mod(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
f=mod('independent_fixture',repo/'ci/github/order-release_test.py');results=[]
oldbytes=subprocess.check_output(['git','-C',str(repo),'show','dab0123f4fd459e12c1f64ff2305e5d28d8a41f5:ci/github/release.py'])
fx=f.Interop();fx.setUp()
try:
 oldfile=Path('old-release.py');oldfile.write_bytes(oldbytes);old=mod('prior_release',oldfile)
 with patch.object(old,'now',return_value=fx.clock):
  public=Path('.security/public');summary=public/'image-scan.json';original=summary.read_bytes()
  foreign=json.loads(original);foreign['imageIdentity'].update(service='backend',configDigest='sha256:'+'e'*64,imageDigest='sha256:'+'f'*64)
  summary.write_text(json.dumps(foreign));record=public/'release-record.json'
  old.record();assert record.exists();record.unlink()
  try:f.p.record()
  except ValueError:pass
  else:raise AssertionError('current producer accepted foreign synthetic summary')
  assert not record.exists();summary.write_bytes(original)
  results.append({'case':'synthetic foreign summary before record','prior_head':'dab0123f4fd459e12c1f64ff2305e5d28d8a41f5','prior_accepted':True,'current_refused_before_record':True})
 for filename,container in [('.validation/source-identity.json',None),('.security/public/image-scan.json','imageIdentity'),('.security/public/image-proof.json','identity')]:
  path=Path(filename);original=path.read_bytes()
  for key in ('runId','runAttempt'):
   value=json.loads(original);normal=(value[container] if container else value)[key]
   for bad in (float(normal),str(normal),True,False,None):
    value=json.loads(original);(value[container] if container else value)[key]=bad;path.write_text(json.dumps(value))
    try:f.p.record()
    except (ValueError,KeyError,TypeError):pass
    else:raise AssertionError('coerced run identity accepted')
    results.append({'file':filename,'key':key,'type':type(bad).__name__,'refused':True})
   path.write_bytes(original)
 f.p.record();assert Path('.security/public/release-record.json').exists()
 results.append({'case':'restored synthetic positive','passed':True})
finally:fx.doCleanups()
output.write_text(json.dumps({'head':head,'input_class':'synthetic; no real image/scanner assertion','checks':results,'external_effects':False},indent=2)+'\n')
print('PASS:',len(results),'narrow synthetic checks; genuine image case remains unverified')
