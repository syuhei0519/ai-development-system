#!/usr/bin/env python3
"""Review R-1 reproducer: valid blob URLs with a /tree/ substring.
Usage: python preparation_probe.py CHECKOUT RESULTS_JSON
Real local synthetic Git objects; only fetch transport is substituted. No app
execution, external writes, production patch, or Test/Implementation test import.
"""
import copy,hashlib,json,subprocess,sys,tempfile
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,str(Path(sys.argv[1]).resolve()))
from scripts import consume_delivery as d
from scripts.prepare_crossref_bundle import Preparation
def enc(v):return (json.dumps(v,separators=(',',':'))+'\n').encode()
def sha(v):return hashlib.sha256(v).hexdigest()
results=[]
with tempfile.TemporaryDirectory(prefix='review-preparation-') as tmp:
 root=Path(tmp);repo=root/'origin';repo.mkdir()
 def git(*args):return subprocess.check_output(['git','-C',str(repo),*args],stderr=subprocess.DEVNULL)
 git('init');git('config','user.name','Synthetic');git('config','user.email','synthetic@example.invalid')
 (repo/'docs/tree').mkdir(parents=True)
 for path in ('docs/note.txt','docs/tree/note.txt'):(repo/path).write_bytes(b'Synthetic review source\r\n')
 git('add','.');git('commit','-m','Synthetic source');source_commit=git('rev-parse','HEAD').decode().strip()
 scenarios=[('control','synthetic/source','docs/note.txt'),('nested-tree','synthetic/source','docs/tree/note.txt'),('repository-tree','synthetic/tree','docs/note.txt')]
 for name,repository,path in scenarios:
  directory=repo/name;directory.mkdir()
  url=f'https://github.com/{repository}/blob/{source_commit}/{path}'
  c=dict(document_type='knowledge_candidates',publication_status='pending_manager_review',candidates=[dict(id='SYNTHETIC-C',domain='synthetic',summary='Synthetic',evidence='Synthetic',source=url,scope='Synthetic')])
  raw=enc(c);(directory/'candidate.json').write_bytes(raw)
  h=json.loads((Path(sys.argv[1])/'examples/research-to-test/research.handoff.json').read_bytes())
  h['task_id']='SYNTHETIC-PREPARATION-'+name;h['artifacts'][0].update(kind='knowledge',locator='candidate.json',revision='sha256:'+sha(raw))
  h['knowledge_candidates']=[dict(id='SYNTHETIC-C',domain='synthetic',summary='Synthetic',evidence_ids=[h['evidence'][0]['id']],raw_locator='candidate.json',publication_safety='needs_review')]
  (directory/'handoff.json').write_bytes(enc(h))
 git('add','.');git('commit','-m','Synthetic producer');producer_commit=git('rev-parse','HEAD').decode().strip()
 for name,repository,path in scenarios:
  cache=root/(name+'-cache');cache.mkdir();source=d.GitSource(cache);original=source.git
  def local(directory,*args):
   if args[0]=='fetch':return subprocess.check_output(['git','-C',str(directory),'fetch','--no-tags',str(repo),args[-1]],stderr=subprocess.DEVNULL)
   return original(directory,*args)
  source.git=local;p=Preparation(source);producer=p.add('synthetic/producer',producer_commit,name+'/handoff.json')
  try:
   manifest=p.finish();observed='accepted';error=None
  except ValueError as e:
   observed='rejected';error=str(e)
   # Independent manifest oracle, not a production fix: explicitly declare the
   # canonical blob target and the already verified unchanged producer bytes.
   owner=p.items[('synthetic/producer',producer_commit,name+'/candidate.json')]
   target=p.add(repository,source_commit,path)
   p.manifest['candidate_bindings'].append(dict(profile='knowledge-candidates-v1',owner=copy.deepcopy(owner['reference']),producer=copy.deepcopy(producer['reference']),producer_artifact_id=h['artifacts'][0]['id'],candidate_ids=['SYNTHETIC-C'],sources=[dict(candidate_id='SYNTHETIC-C',source=f'https://github.com/{repository}/blob/{source_commit}/{path}',target=dict(kind='blob',reference=copy.deepcopy(target['reference'])))]))
   manifest=p.manifest
  m=enc(manifest);pub=enc(dict(schema_version='1.2',document_type='publication_receipt',manifest_sha256=sha(m),github_state='published',artifacts=manifest['artifacts'],observation='Synthetic only'))
  auth=enc(dict(schema_version='1.2',document_type='delivery_authorization',authority='Synthetic',consumer='SYNTHETIC',scope='synthetic',purpose='contract-review',manifest_sha256=sha(m),valid_until='2030-01-01T00:00:00Z',public_safety_review='Synthetic',publication_approval='unverified',publication_approval_evidence='Synthetic',consumer_use_approval='approved',consumer_use_evidence='Synthetic',allowed_representations=['original'],publication_receipt_sha256=sha(pub)))
  receipt,blobs=d.consume(m,auth,pub,sha(auth),'SYNTHETIC','synthetic','contract-review',source,now=datetime(2026,10,11,tzinfo=timezone.utc))
  results.append(dict(case=name,source_repository=repository,source_path=path,expected_preparation='accepted',actual_preparation=observed,error=error,consumer_with_explicit_canonical_blob_manifest='PASS',objects=len(blobs),passed=observed=='accepted'))
out=dict(report_type='independent_review_preparation_reproducer',finding='R-1',cases=results,total=3,passed=sum(r['passed'] for r in results),failed=sum(not r['passed'] for r in results),production_modified=False,limits='Synthetic local Git fetch routing only; no application source execution or public operation.')
Path(sys.argv[2]).write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2));sys.exit(bool(out['failed']))
