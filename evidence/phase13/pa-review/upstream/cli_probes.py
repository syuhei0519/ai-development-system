import sys,pathlib,subprocess,json,hashlib,tempfile
root=pathlib.Path(sys.argv[1]).resolve();p=pathlib.Path(sys.argv[2]).resolve();out=pathlib.Path(sys.argv[3]);results=[]
policy=p/'fixture-authorization.json';pin=hashlib.sha256(policy.read_bytes()).hexdigest()
cmd=[sys.executable,str(root/'scripts/consume_delivery.py'),'--manifest',str(p/'fixture-prepared/manifest.json'),'--publication',str(p/'fixture-prepared/publication-receipt.json'),'--authorization',str(policy),'--authorization-sha256',pin,'--consumer','knowledge-delivery-test-a1','--scope','system/phase1-3/P-A','--purpose','contract-review']
with tempfile.TemporaryDirectory() as tmp:
 t=pathlib.Path(tmp)
 for i,(name,flags) in enumerate([('wrong-consumer',['--consumer','SYNTHETIC-WRONG']),('wrong-purpose',['--purpose','implementation']),('wrong-pin',['--authorization-sha256','0'*64])]):
  dest=t/str(i);r=subprocess.run(cmd+flags+['--output',str(dest)],capture_output=True);results.append(dict(id=name,expected='exit1/no-output/no-traceback',actual_exit=r.returncode,passed=r.returncode==1 and not dest.exists() and b'Traceback' not in r.stderr))
 receipt=json.loads((p/'fixture-consumed/consumption-receipt.json').read_bytes());receipt['authority_granted']=0;(t/'badreceipt.json').write_text(json.dumps(receipt))
 r=subprocess.run(cmd+['--verify-receipt',str(t/'badreceipt.json'),'--output',str(t/'receipt-out')],capture_output=True);results.append(dict(id='receipt-false-vs-zero',expected='exit1/no-output',actual_exit=r.returncode,passed=r.returncode==1 and not (t/'receipt-out').exists()))
 (t/'link').symlink_to(policy);r=subprocess.run(cmd+['--authorization',str(t/'link'),'--output',str(t/'linkout')],capture_output=True);results.append(dict(id='local-symlink-policy',expected='exit1/no-output',actual_exit=r.returncode,passed=r.returncode==1 and not (t/'linkout').exists()))
 # Old output corruption is deliberately not an input to receipt recheck. Restore afterward.
 old=next((p/'fixture-consumed/artifacts').rglob('article.md')); original=old.read_bytes(); old.write_bytes(b'Synthetic old-output corruption\n')
 try:
  r=subprocess.run(cmd+['--verify-receipt',str(p/'fixture-consumed/consumption-receipt.json'),'--output',str(t/'fresh')],capture_output=True)
  fresh=next((t/'fresh/artifacts').rglob('article.md')) if r.returncode==0 else None
  results.append(dict(id='fresh-fetch-not-old-output-inspection',expected='exit0/fresh-original-bytes',actual_exit=r.returncode,passed=r.returncode==0 and fresh.read_bytes()==original and old.read_bytes()!=original))
 finally:old.write_bytes(original)
out.write_text(json.dumps(dict(count=len(results),passed=sum(r['passed'] for r in results),results=results),indent=2)+'\n');print(out.read_text())
