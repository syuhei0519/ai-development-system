"""Independent Test attempt 2 route boundaries; synthetic Git data only.
Usage: python boundary_probe.py CHECKOUT RESULT_JSON
Only fetch transport is substituted. No Implementation tests are imported.
"""
import json,sys,subprocess,tempfile,hashlib
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,str(Path(sys.argv[1]).resolve()))
from scripts import consume_delivery as d
from scripts.prepare_crossref_bundle import Preparation
def enc(v):return (json.dumps(v,ensure_ascii=False,separators=(',',':'))+'\n').encode()
results=[]
with tempfile.TemporaryDirectory() as temp:
 root=Path(temp); origin=root/'origin';origin.mkdir()
 def git(*args):return subprocess.check_output(['git','-C',str(origin),*args],stderr=subprocess.DEVNULL)
 git('init');git('config','user.name','Synthetic');git('config','user.email','synthetic@example.invalid')
 (origin/'tree/blob/tree').mkdir(parents=True)
 (origin/'tree/blob/tree/commit.txt').write_bytes(b'Independent source CRLF\r\n')
 git('add','.');git('commit','-m','Synthetic data')
 sha=git('rev-parse','HEAD').decode().strip()
 cases=[]
 for repo in ('tree/tree','blob/blob','tree/blob','blob/tree','synthetic/tree.git'):
  for kind,path in [('blob','tree/blob/tree/commit.txt'),('tree','tree/blob')]:
   cases.append((repo+' '+kind,f'https://github.com/{repo}/{kind}/{sha}/{path}',True,kind))
 u=f'https://github.com/tree/tree/blob/{sha}/tree/blob/tree/commit.txt'
 mutations=[
 ('scheme','http://'+u[8:]),('host-case',u.replace('github.com','GitHub.com')),
 ('host-suffix',u.replace('github.com','github.com.evil.invalid')),
 ('userinfo',u.replace('github.com','github.com@evil.invalid')),
 ('password',u.replace('github.com','user:pass@github.com')),
 ('port',u.replace('github.com','github.com:443')),('protocol-relative',u[6:]),
 ('extra-separator',u.replace('github.com/','github.com//')),
 ('route-raw',u.replace('/blob/'+sha,'/raw/'+sha)),
 ('route-commit',u.replace('/blob/'+sha,'/commit/'+sha)),
 ('route-case',u.replace('/blob/'+sha,'/BLOB/'+sha)),
 ('route-encoded',u.replace('/blob/'+sha,'/%62lob/'+sha)),
 ('route-empty',u.replace('/blob/'+sha,'//'+sha)),
 ('oid-main',u.replace(sha,'main')),('oid-short',u.replace(sha,sha[:39])),
 ('oid-long',u.replace(sha,sha+'0')),('oid-uppercase',u.replace(sha,sha.upper())),
 ('query-empty',u+'?'),('query',u+'?raw=1'),('fragment-empty',u+'#'),('fragment',u+'#tree'),
 ('suffix-slash',u+'/'),('dot',u.replace('/commit.txt','/./commit.txt')),
 ('dotdot',u.replace('/commit.txt','/../commit.txt')),
 ('encoded-slash',u.replace('/commit.txt','%2Fcommit.txt')),
 ('encoded-dot',u.replace('/commit.txt','/%2e/commit.txt')),
 ('git-directory',u.replace('/commit.txt','/.git/commit.txt')),
 ('empty-component',u.replace('/commit.txt','//commit.txt')),
 ('backslash',u.replace('/commit.txt',chr(92)+'commit.txt')),
 ('newline',u+'\n'),('tab',u+'\t'),('nul',u+'\0'),
 ('unicode-host',u.replace('github.com','gıthub.com')),
 ('path-space',u.replace('commit.txt','commit .txt')),
 ('missing-path',u[:u.index('/tree/blob/tree/commit.txt')]),
 ('empty',''),('nonstring-null',None),('nonstring-array',[]),('nonstring-bool',True)]
 cases.extend((n,v,False,None) for n,v in mutations)
 for i,(name,url,accept,kind) in enumerate(cases):
  p=origin/str(i);p.mkdir()
  c=dict(document_type='knowledge_candidates',publication_status='pending_manager_review',
         candidates=[dict(id='SYNTHETIC-C',domain='test',summary='Synthetic',evidence='Synthetic',source=url,scope='Test')])
  (p/'c.json').write_bytes(enc(c))
  h=json.loads((Path(sys.argv[1])/'examples/research-to-test/research.handoff.json').read_bytes())
  h['task_id']='SYNTHETIC-BOUNDARY-'+str(i)
  h['artifacts'][0].update(kind='knowledge',locator='c.json',revision='sha256:'+d.digest(enc(c)))
  h['knowledge_candidates']=[dict(id='SYNTHETIC-C',domain='test',summary='Synthetic',evidence_ids=[h['evidence'][0]['id']],raw_locator='c.json',publication_safety='needs_review')]
  (p/'h.json').write_bytes(enc(h))
 git('add','.');git('commit','-m','Synthetic producers')
 producer_sha=git('rev-parse','HEAD').decode().strip()
 for i,(name,url,accept,kind) in enumerate(cases):
  cache=root/('cache'+str(i));cache.mkdir();source=d.GitSource(cache);original=source.git
  def local(directory,*args):
   if args[0]=='fetch':return subprocess.check_output(['git','-C',str(directory),'fetch','--no-tags',str(origin),args[-1]],stderr=subprocess.DEVNULL)
   return original(directory,*args)
  source.git=local
  try:
   p=Preparation(source,'synthetic_sample');p.add('synthetic/producer',producer_sha,str(i)+'/h.json');m=p.finish()
   if not accept:actual='accepted';passed=False
   else:
    assert m['candidate_bindings'][0]['sources'][0]['target']['kind']==kind
    mr=enc(m);pr=enc(dict(schema_version='1.2',document_type='publication_receipt',manifest_sha256=d.digest(mr),github_state='published',artifacts=m['artifacts'],observation='Synthetic'))
    ar=enc(dict(schema_version='1.2',document_type='delivery_authorization',authority='Synthetic',consumer='SYNTHETIC',scope='synthetic',purpose='contract-review',manifest_sha256=d.digest(mr),valid_until='2030-01-01T00:00:00Z',public_safety_review='Synthetic',publication_approval='unverified',publication_approval_evidence='Synthetic',consumer_use_approval='approved',consumer_use_evidence='Synthetic',allowed_representations=['original'],publication_receipt_sha256=d.digest(pr)))
    args=(mr,ar,pr,d.digest(ar),'SYNTHETIC','synthetic','contract-review',source)
    receipt,blobs=d.consume(*args,now=datetime(2026,10,11,tzinfo=timezone.utc))
    assert receipt['authority_granted'] is False
    assert b'Independent source CRLF\r\n' in blobs.values()
    assert d.consume(*args,receipt_raw=enc(receipt),now=datetime(2026,10,11,tzinfo=timezone.utc))[0]==receipt
    actual='accepted; canonical kind and Consumer/fresh checks passed';passed=True
  except ValueError:
   actual='rejected';passed=not accept
  except Exception as e:
   actual='unexpected '+type(e).__name__;passed=False
  results.append(dict(case=name,expected='accept' if accept else 'reject',actual=actual,passed=passed))
out=dict(record_type='independent_test_attempt2_boundaries',head=subprocess.check_output(['git','-C',sys.argv[1],'rev-parse','HEAD']).decode().strip(),cases=results,total=len(results),passed=sum(r['passed'] for r in results),failed=sum(not r['passed'] for r in results))
Path(sys.argv[2]).write_bytes(enc(out));print(out['total'],out['passed'],out['failed']);sys.exit(bool(out['failed']))
