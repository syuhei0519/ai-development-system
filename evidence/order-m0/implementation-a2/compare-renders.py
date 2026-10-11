#!/usr/bin/env python3
"""Compare fixed existing live chart/environment bytes and Helm output; no deployment."""
import hashlib,json,subprocess,sys,tempfile
from pathlib import Path
root=Path(sys.argv[1]).resolve()
base='e039945a90625262f91382e6f71149d046e31b34'
head='82505fce911c1dbbe75fe8226a06665e582e1ff9'
def git(*args):return subprocess.check_output(['git','-C',str(root),*args])
assert git('rev-parse','HEAD').decode().strip()==head
files=git('ls-tree','-r','--name-only',base,'charts','environments').decode().splitlines()
assert files==git('ls-tree','-r','--name-only',head,'charts','environments').decode().splitlines()
rows=[]
with tempfile.TemporaryDirectory() as d:
 p=Path(d)
 for f in files:
  old=git('show',base+':'+f);new=git('show',head+':'+f);assert old==new
  dest=p/f;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(old)
 for c in ['frontend','backend','postgresql']:
  cmd=['helm','template',c,'charts/'+c,'-f','environments/local/'+c+'.yaml']
  old=subprocess.check_output(cmd,cwd=p);new=subprocess.check_output(cmd,cwd=root);assert old==new
  rows.append(dict(chart=c,bytes=len(new),sha256=hashlib.sha256(new).hexdigest(),byte_equal=True,semantic_equal=True))
result=dict(base=base,head=head,chart_files=sum(f.startswith('charts/') for f in files),environment_files=sum(f.startswith('environments/') for f in files),all_tracked_inputs_byte_equal=True,renders=rows,deployment_effect='none',limitation='Static rendered inputs only; no live workload, Argo, API, database or runtime measurement.')
Path(sys.argv[2]).write_text(json.dumps(result,indent=2)+'\n')
