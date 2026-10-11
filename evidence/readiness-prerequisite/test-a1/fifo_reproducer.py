"""Synthetic nonregular artifact proof. No network, no implementation changes.
Usage: python fifo_reproducer.py HEAD_CHECKOUT OUTPUT_JSON
The independent_cases.py additionally records the writer-less FIFO timeout.
"""
import hashlib,json,os,pathlib,subprocess,sys,tempfile,time
R=pathlib.Path(sys.argv[1]).resolve();OUT=pathlib.Path(sys.argv[2]);rows=[]
with tempfile.TemporaryDirectory(prefix='fifo-proof-') as t:
 p=pathlib.Path(t);F=R/'examples/readiness'
 for name in ['preparation-ready.json','preparation-context.json']:(p/name).write_bytes((F/name).read_bytes())
 artifact=p/'preparation-artifact.txt';os.mkfifo(artifact)
 cmd=[sys.executable,str(R/'scripts/validate_readiness.py'),str(p/'preparation-ready.json'),'--context',str(p/'preparation-context.json'),'--context-sha256',hashlib.sha256((p/'preparation-context.json').read_bytes()).hexdigest(),'--at','2030-01-01T12:00:00Z']
 child=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
 deadline=time.monotonic()+5;fd=None
 try:
  while time.monotonic()<deadline and child.poll() is None:
   try:fd=os.open(artifact,os.O_WRONLY|os.O_NONBLOCK);break
   except OSError:time.sleep(.02)
  if fd is None:raise RuntimeError('reader did not open synthetic FIFO')
  os.write(fd,(F/'preparation-artifact.txt').read_bytes());os.close(fd);fd=None
  stdout,stderr=child.communicate(timeout=5)
  rows.append(dict(case='FIFO_supplied_expected_bytes',expected_exit=1,actual_exit=child.returncode,output=(stdout+stderr).replace(t,'<SYNTHETIC_ROOT>')))
 finally:
  if fd is not None:os.close(fd)
  if child.poll() is None:child.kill();child.communicate()
OUT.write_text(json.dumps({'head':'3f41a0470fd0b7a2199be0b947bb22284e993e2f','synthetic':True,'results':rows},indent=2)+'\n')
print(OUT.read_text());sys.exit(int(any(x['actual_exit']!=x['expected_exit'] for x in rows)))
