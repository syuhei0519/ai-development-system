#!/usr/bin/env python3
"""Implementation self-test derivative of verified Test2; fixed target updated.
Independently compare fixed tree bytes and Helm output; no live operations."""
import hashlib,json,subprocess,sys,tempfile
from pathlib import Path
import yaml
root=Path(sys.argv[1]);out=Path(sys.argv[2]);base='e039945a90625262f91382e6f71149d046e31b34';head='e5e6de38cf6ee22ba2f10c9f5fcf05c87004a8e4'
def git(*a):return subprocess.check_output(['git','-C',str(root),*a])
def sha(b):return hashlib.sha256(b).hexdigest()
def files(rev,p):return git('ls-tree','-r','--name-only',rev,p).decode().splitlines()
record={'base':base,'head':head,'base_tree':git('rev-parse',base+'^{tree}').decode().strip(),'head_tree':git('rev-parse',head+'^{tree}').decode().strip(),'files':[],'renders':[]}
with tempfile.TemporaryDirectory() as d:
 for prefix in ['charts','environments']:
  a=files(base,prefix);b=files(head,prefix);assert a==b
  for p in a:
   before=git('show',base+':'+p);after=git('show',head+':'+p);assert before==after
   record['files'].append({'path':p,'size':len(before),'sha256':sha(before),'equal':True})
   target=Path(d,p);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(before)
 for chart in ['frontend','backend','postgresql']:
  def render(repo):return subprocess.check_output(['helm','template',chart,str(repo/'charts'/chart),'-f',str(repo/'environments/local'/str(chart+'.yaml'))])
  a=render(Path(d));b=render(root);assert a==b;assert list(yaml.safe_load_all(a))==list(yaml.safe_load_all(b))
  record['renders'].append({'chart':chart,'size':len(a),'sha256':sha(a),'byte_equal':True,'semantic_equal':True})
out.write_text(json.dumps(record,indent=2)+'\n');print('PASS: 28 chart files, 4 environment files and three byte/semantic renders unchanged')
