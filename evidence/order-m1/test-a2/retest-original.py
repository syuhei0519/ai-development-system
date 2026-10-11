"""Replay original immutable Test1 fixtures through before and repaired head binaries."""
import datetime,hashlib,json,pathlib,subprocess,sys,tempfile
p=pathlib.Path(sys.argv[1]);r=pathlib.Path(sys.argv[2]);old=pathlib.Path(sys.argv[3]);o=pathlib.Path(sys.argv[4]);results=[]
for name in ['inventory-positive','pod-hostNetwork','pod-hostPID','pod-hostIPC','namespace-escape']:
 raw=(p/(name+'.yaml')).read_bytes();entry=dict(case=name,observed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),fixture_sha256=hashlib.sha256(raw).hexdigest())
 for label,binary in [('before',old/'old-inventory'),('after',r/'.build/order-inventory')]:
  a=subprocess.run([str(binary)],input=raw,capture_output=True);entry[label]=dict(exit=a.returncode,inventory_sha256=json.loads(a.stdout)['inventorySha256'] if a.returncode==0 else None)
 with tempfile.TemporaryDirectory() as td:
  d=pathlib.Path(td);(d/'fixture.yaml').write_bytes(raw)
  for label,binary in [('before',old/'old-scan'),('after',r/'.security/scan-gate')]:
   a=subprocess.run([str(binary),'-check-render-only',td,'-out',str(d/'report.json')],capture_output=True)
   entry[label]['structural_exit']=a.returncode
 results.append(entry)
o.write_text(json.dumps(results,indent=2)+'\n');print([(x['case'],x['before']['exit'],x['after']['exit']) for x in results])
