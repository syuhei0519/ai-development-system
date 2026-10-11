#!/usr/bin/env python3
"""Reproduce synthetic verification without editing source or using the network."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('head',type=Path);p.add_argument('output',type=Path)
p.add_argument('--base',type=Path);p.add_argument('--before',type=Path)
a=p.parse_args();root=Path(__file__).resolve().parent;out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
def revision(path,expected):
    actual=subprocess.check_output(['git','-C',str(path),'rev-parse','HEAD'],text=True).strip()
    if actual!=expected:raise SystemExit('wrong checkout revision')
revision(a.head,'b6d446ceb072e3a6d137318175bb672155d9b206')
if a.base:revision(a.base,'b1e606544174481b7b6904f811e857f80978c287')
if a.before:revision(a.before,'591f896d30fde5630d49f99a4ea7544ff90f53a4')
rows=[]
def run(label,args,cwd):
    r=subprocess.run(args,cwd=cwd,capture_output=True,text=True)
    (out/(label+'.log')).write_text(r.stdout+r.stderr)
    rows.append({'label':label,'exit':r.returncode,'passed':r.returncode==0})
run('head-unit',[sys.executable,'-m','unittest','discover','-s','tests','-v'],a.head)
if a.base:run('base-unit',[sys.executable,'-m','unittest','discover','-s','tests','-v'],a.base)
helper=root/'upstream/independent_cases.py'
run('independent',[sys.executable,str(helper),str(a.head.resolve()),str(out/'independent')],root)
probe=json.loads((out/'independent/results.json').read_bytes())
rows[-1]['passed'] &= probe['total']==130 and all(x['passed'] for x in probe['cases'])
run('boundaries',[sys.executable,str(root/'boundary_cases.py'),str(a.head.resolve()),str(helper),str(out/'boundaries')],root)
if a.before:run('baseline',[sys.executable,str(root/'boundary_cases.py'),str(a.before.resolve()),str(helper),str(out/'baseline'),'baseline'],root)
for i,row in enumerate(json.loads((root/'results.json').read_bytes())['cli']):
    run('cli-'+str(i),[sys.executable]+row['command'][1:],a.head)
(out/'summary.json').write_text(json.dumps(rows,indent=2)+'\n')
print(json.dumps(rows,indent=2));sys.exit(0 if all(r['passed'] for r in rows) else 1)
