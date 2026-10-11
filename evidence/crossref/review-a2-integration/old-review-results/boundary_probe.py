#!/usr/bin/env python3
"""Review attempt 2 independent route-boundary fixtures; only synthetic Git data.
Usage: python boundary_probe.py CHECKOUT RESULT_JSON
No Implementation/Test test modules are imported. No application execution.
"""
import copy, hashlib, json, subprocess, sys, tempfile
from pathlib import Path
from datetime import datetime, timezone
sys.path.insert(0, str(Path(sys.argv[1]).resolve()))
from scripts import consume_delivery as d
from scripts.prepare_crossref_bundle import Preparation
def enc(v): return (json.dumps(v,ensure_ascii=False,separators=(',',':'))+'\n').encode()
cases=[]
with tempfile.TemporaryDirectory(prefix='synthetic-review-a2-') as tmp:
 root=Path(tmp);origin=root/'origin';origin.mkdir()
 def git(*args): return subprocess.check_output(['git','-C',str(origin),*args],stderr=subprocess.DEVNULL)
 git('init');git('config','user.name','Synthetic');git('config','user.email','synthetic@example.invalid')
 for path in ('docs/tree/blob/note.txt','docs/blob/tree/note.txt','docs/commit/note.txt'):
  p=origin/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'Synthetic source\r\n')
 git('add','.');git('commit','-m','Synthetic source');oid=git('rev-parse','HEAD').decode().strip()
 scenarios=[]
 for repo in ('tree/tree','blob/blob','commit/tree','tree/commit'):
  for route,path in [('blob','docs/tree/blob/note.txt'),('blob','docs/blob/tree/note.txt'),('tree','docs/tree'),('tree','docs/blob')]:
   scenarios.append((f'https://github.com/{repo}/{route}/{oid}/{path}',True,route))
 u=f'https://github.com/tree/tree/blob/{oid}/docs/tree/blob/note.txt'
 bad=[u.replace('/blob/'+oid,'/'+r+'/'+oid) for r in ('raw','blobs','trees','commit','Blob','TREE','%62lob','blob;tree','blob%2ftree','blob\\tree')]
 bad += [u+s for s in ('?','#','?route=tree','#/tree/','\r','\n','\t','\x00','/','//')]
 bad += [u.replace('github.com',s) for s in ('github.com:443','github.com.','github.com.evil','user@github.com','GITHUB.COM')]
 bad += [u.replace('https://',s) for s in ('http://','https:////','//','file://',' https://')]
 bad += [u.replace(oid,s) for s in ('main',oid[:12],oid.upper(),oid+'0')]
 bad += [u.replace('docs/tree/blob/note.txt',s) for s in ('docs//tree/note.txt','docs/../tree/note.txt','docs/%74ree/note.txt','docs/.git/tree/note.txt','docs/tree/note.txt?x','docs/tree/./note.txt','docs/tree\\note.txt')]
 scenarios += [(v,False,None) for v in bad]
 for i,(url,valid,route) in enumerate(scenarios):
  c={'document_type':'knowledge_candidates','publication_status':'pending_manager_review','candidates':[dict(id='SYNTHETIC-C',domain='synthetic',summary='Synthetic',evidence='Synthetic',scope='Synthetic',source=url)]}
  raw=enc(c);folder=origin/str(i);folder.mkdir();(folder/'candidate.json').write_bytes(raw)
  h=json.loads((Path(sys.argv[1])/'examples/research-to-test/research.handoff.json').read_bytes())
  h['task_id']='SYNTHETIC-REVIEW-A2-'+str(i);h['artifacts'][0].update(kind='knowledge',locator='candidate.json',revision='sha256:'+d.digest(raw))
  h['knowledge_candidates']=[dict(id='SYNTHETIC-C',domain='synthetic',summary='Synthetic',evidence_ids=[h['evidence'][0]['id']],raw_locator='candidate.json',publication_safety='needs_review')]
  (folder/'handoff.json').write_bytes(enc(h))
 git('add','.');git('commit','-m','Synthetic producers');producer_oid=git('rev-parse','HEAD').decode().strip()
 for i,(url,valid,route) in enumerate(scenarios):
  cache=root/('cache-'+str(i));cache.mkdir();source=d.GitSource(cache);original=source.git
  def local(directory,*args):
   if args[0]=='fetch': return subprocess.check_output(['git','-C',str(directory),'fetch','--no-tags',str(origin),args[-1]],stderr=subprocess.DEVNULL)
   return original(directory,*args)
  source.git=local
  try:
   p=Preparation(source,'synthetic_sample');p.add('synthetic/producer',producer_oid,str(i)+'/handoff.json');m=p.finish()
   assert m['candidate_bindings'][0]['sources'][0]['target']['kind']==route
   mr=enc(m);pub=enc(dict(schema_version='1.2',document_type='publication_receipt',manifest_sha256=d.digest(mr),github_state='published',artifacts=m['artifacts'],observation='Synthetic only'))
   auth=enc(dict(schema_version='1.2',document_type='delivery_authorization',authority='Synthetic',consumer='SYNTHETIC',scope='synthetic',purpose='contract-review',manifest_sha256=d.digest(mr),valid_until='2030-01-01T00:00:00Z',public_safety_review='Synthetic',publication_approval='unverified',publication_approval_evidence='Synthetic',consumer_use_approval='approved',consumer_use_evidence='Synthetic',allowed_representations=['original'],publication_receipt_sha256=d.digest(pub)))
   r,b=d.consume(mr,auth,pub,d.digest(auth),'SYNTHETIC','synthetic','contract-review',source,now=datetime(2026,10,11,tzinfo=timezone.utc))
   assert not r['authority_granted'] and all(b[k]==v for k,v in p.raw.items())
   actual='accepted';passed=valid
  except ValueError as e: actual='rejected: '+str(e);passed=not valid
  except Exception as e: actual='unexpected '+type(e).__name__+': '+str(e);passed=False
  cases.append(dict(case=i,url=url,expected='accept' if valid else 'reject',actual=actual,passed=passed))
result=dict(report_type='independent_review_a2_route_boundaries',cases=cases,total=len(cases),passed=sum(c['passed'] for c in cases),failed=sum(not c['passed'] for c in cases),limits='Synthetic local Git; only fetch transport redirected to the fixture. Complete Consumer used for positive cases. Not live hostile network testing.')
Path(sys.argv[2]).write_bytes(enc(result));print(json.dumps({k:result[k] for k in ('total','passed','failed')}));sys.exit(bool(result['failed']))
