#!/usr/bin/env python3
"""Run preserved Test reproduction and independent Review probes; no network or source edits."""
import argparse,json,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('head',type=Path);p.add_argument('output',type=Path)
p.add_argument('--base',type=Path,required=True);p.add_argument('--before',type=Path,required=True)
a=p.parse_args();root=Path(__file__).resolve().parent;out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
rows=[]
for name,args in [('upstream',[str(root/'upstream/reproduce.py'),str(a.head.resolve()),str(out/'upstream'),'--base',str(a.base.resolve()),'--before',str(a.before.resolve())]),('review',[str(root/'review_probes.py'),str(a.head.resolve()),str(out/'review')])]:
 r=subprocess.run([sys.executable]+args,capture_output=True,text=True)
 (out/(name+'.log')).write_text(r.stdout+r.stderr)
 rows.append({'suite':name,'exit':r.returncode,'passed':r.returncode==0})
(out/'summary.json').write_text(json.dumps(rows,indent=2)+'\n')
print(json.dumps(rows,indent=2));sys.exit(0 if all(x['passed'] for x in rows) else 1)
