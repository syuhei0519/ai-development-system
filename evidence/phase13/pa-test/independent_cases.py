"""Synthetic independent probes. Usage: python independent_cases.py FIXED_CHECKOUT OUTPUT.json
Uses the repository's fixture builder only; expected outcomes and mutations authored by independent Test.
"""
import sys,json,copy,hashlib,datetime,pathlib
root=pathlib.Path(sys.argv[1]).resolve(); sys.path.insert(0,str(root))
from scripts import consume_delivery as c
from scripts.prepare_knowledge_fixture import fixture_manifest
enc=lambda x:(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n').encode()
results=[]
class Bundle:
 def __init__(self):
  self.m=fixture_manifest('example/repo','a'*40)
  self.files={a['reference']['path']:(root/a['reference']['path']).read_bytes() for a in self.m['artifacts']}
  self.p=json.loads((root/'examples/delivery/synthetic.authorization.json').read_bytes());self.p.update(schema_version='1.1',allowed_representations=['original']);self.kw={}; self.receipt=None
 def item(self,n):return next(a for a in self.m['artifacts'] if a['reference']['path'].endswith('/'+n))
 def get(self,n):return json.loads(self.files[self.item(n)['reference']['path']])
 def put(self,n,d):self.files[self.item(n)['reference']['path']]=enc(d)
 def edit(self,n,path,v):
  d=self.get(n);o=d
  for k in path[:-1]:o=o[k]
  o[path[-1]]=v;self.put(n,d)
 def run(self):
  for a in self.m['artifacts']:
   r=a['reference'];raw=self.files[r['path']];r.update(size=len(raw),sha256=c.digest(raw))
  mr=enc(self.m); pub=dict(schema_version=self.m['schema_version'],document_type='publication_receipt',manifest_sha256=c.digest(mr),github_state='published',artifacts=copy.deepcopy(self.m['artifacts']),observation='Synthetic independent test')
  if hasattr(self,'pubedit'):self.pubedit(pub)
  pr=enc(pub);self.p.update(manifest_sha256=c.digest(mr),publication_receipt_sha256=c.digest(pr));pol=enc(self.p)
  args=dict(manifest_raw=mr,policy_raw=pol,publication_raw=pr,policy_sha256=c.digest(pol),consumer=self.p['consumer'],scope=self.p['scope'],purpose=self.p['purpose'],source=self,now=datetime.datetime(2026,10,11,tzinfo=datetime.timezone.utc));args.update(self.kw)
  if self.receipt:
   receipt,_=c.consume(**args);self.receipt(receipt);args['receipt_raw']=enc(receipt)
  return c.consume(**args)
 def read(self,ref):return self.files[ref['path']]
def case(name,change=lambda b:None,expected='reject'):
 b=Bundle();change(b)
 try:b.run();actual='accept';detail='accepted'
 except Exception as e:actual='reject' if isinstance(e,(ValueError,OSError)) else 'crash';detail=type(e).__name__+': '+str(e)
 results.append(dict(id=name,expected=expected,actual=actual,passed=actual==expected,detail=detail,reproducer='python independent_cases.py FIXED_CHECKOUT OUTPUT.json; case '+name))
case('normal-full',expected='accept')
for n in ('input.json','handoff.json'):
 for v in (True,False,'1',None):case('attempt-type-'+n+'-'+repr(v),lambda b,n=n,v=v:b.edit(n,['attempt'],v))
 for path in (['assignment','scope'],['raw_findings',0,'observation'],['knowledge_references',0,'applicability'],['task_id']):
  case('immutable-'+n+'-'+'-'.join(map(str,path)),lambda b,n=n,path=path:b.edit(n,path,'synthetic changed'))
for n in ('input.json','handoff.json','context.json'):
 for kind in ('json','text','handoff-v2','knowledge-input-v9'):
  case('dispatch-'+n+'-'+kind,lambda b,n=n,kind=kind:b.item(n).__setitem__('format',kind))
 for field,v in [('document_type',None),('schema_version','1.1'),('publication','private_only')]:case('identity-'+n+'-'+field,lambda b,n=n,field=field,v=v:b.edit(n,[field],v))
 for suffix,raw in [('duplicate',b'{"x":0,"\\u0078":1}'),('nan',b'{"x":NaN}'),('infinity',b'{"x":Infinity}'),('bom',b'\xef\xbb\xbf{}'),('truncated',b'{"document_type":'),('scalar',b'false')]:
  case('parse-'+n+'-'+suffix,lambda b,n=n,raw=raw:b.files.__setitem__(b.item(n)['reference']['path'],raw))
 for locator in ('../source-1.md','https://github.com/example/repo/blob/'+'a'*40+'/source.md','a%2fb','a/.git/x','a//b','a\n--help','missing.md'):
  case('locator-'+n+'-'+repr(locator),lambda b,n=n,locator=locator:b.edit(n,['knowledge_references',0,'sources',0,'locator'],locator))
case('raw-order',lambda b:b.edit('handoff.json',['raw_findings'],list(reversed(b.get('handoff.json')['raw_findings']))))
case('reference-order',lambda b:b.edit('handoff.json',['knowledge_references',0,'sources'],list(reversed(b.get('handoff.json')['knowledge_references'][0]['sources']))))
for n in ('input.json','source-1.md','source-2.md','article.md'):
 case('unlisted-'+n,lambda b,n=n:b.m['artifacts'].remove(b.item(n)))
case('source-resealed-tamper',lambda b:b.files.__setitem__(b.item('source-1.md')['reference']['path'],b'Synthetic changed source\n'))
case('context-revision',lambda b:b.edit('context.json',['knowledge_references',0,'revision'],'sha256:'+'0'*64))
case('coverage',lambda b:b.edit('handoff.json',['decisions',0,'raw_finding_ids'],['SYNTHETIC-RAW-1']))
case('adopted-no-article',lambda b:b.edit('handoff.json',['decisions',0,'article_artifact_ids'],[]))
for v in (0,1,True,None):case('receipt-authority-'+repr(v),lambda b,v=v:setattr(b,'receipt',lambda r:r.__setitem__('authority_granted',v)))
for k in ('consumer','scope','purpose'):case('approval-'+k,lambda b,k=k:b.kw.__setitem__(k,'SYNTHETIC-WRONG'))
case('approval-pin',lambda b:b.kw.__setitem__('policy_sha256','0'*64))
for value in ('2026-10-11T00:00:00Z','2020-01-01T00:00:00Z','2030-01-01'):
 case('expiry-'+value,lambda b,value=value:b.p.__setitem__('valid_until',value))
case('approval-pending',lambda b:b.p.__setitem__('consumer_use_approval','pending'))
case('authorization-old-version',lambda b:b.p.__setitem__('schema_version','1.0'))
case('publication-old-version',lambda b:setattr(b,'pubedit',lambda p:p.__setitem__('schema_version','1.0')))
case('manifest-downgrade',lambda b:b.m.__setitem__('schema_version','1.0'))
case('receipt-scope-tamper',lambda b:setattr(b,'receipt',lambda r:r.__setitem__('scope','other')))
case('publication-artifact-missing',lambda b:setattr(b,'pubedit',lambda p:p['artifacts'].pop()))
case('duplicate-binding',lambda b:b.m['knowledge_bindings'].append(copy.deepcopy(b.m['knowledge_bindings'][0])))
case('no-binding',lambda b:b.m.__setitem__('knowledge_bindings',[]))
def empty_article(b):
 raw=b' \t\r\n';b.files[b.item('article.md')['reference']['path']]=raw
 for n in ('input.json','handoff.json','context.json'):
  d=b.get(n);d['knowledge_references'][0]['revision']='sha256:'+c.digest(raw)
  if n=='handoff.json':d['artifacts'][0]['revision']='sha256:'+c.digest(raw)
  b.put(n,d)
case('whitespace-article-resealed',empty_article)
for outcome in ('deferred','rejected'):
 def mutation(b,outcome=outcome):
  d=b.get('handoff.json');d['decisions'][0].update(outcome=outcome,article_artifact_ids=[]);b.put('handoff.json',d)
 case('normal-'+outcome,mutation,'accept')
def unsupported_handoff(b,kind):
 d=json.loads((root/'examples/research-to-test/research.handoff.json').read_bytes())
 d['artifacts'][0].update(kind='commit',locator='https://github.com/example/other/commit/'+'b'*40,revision='b'*40)
 if kind=='upstream':
  d['artifacts'][0].update(kind='document',locator='article.md',revision='sha256:'+c.digest(b.files[b.item('article.md')['reference']['path']]))
  d['upstream']=[dict(role='research-design',task_id='SYNTHETIC-PRIOR',attempt=1,handoff_locator='https://github.com/example/other/blob/'+'b'*40+'/handoff.json',revision='sha256:'+'0'*64,relationship='dependency')]
 b.m['artifacts']=[b.item('handoff.json'),b.item('article.md')];b.item('handoff.json')['format']='handoff-v2';b.put('handoff.json',d);b.m['knowledge_bindings']=[]
case('unsupported-commit-url',lambda b:unsupported_handoff(b,'commit'))
case('unsupported-cross-repo-upstream-url',lambda b:unsupported_handoff(b,'upstream'))
pathlib.Path(sys.argv[2]).write_bytes(enc(dict(count=len(results),passed=sum(r['passed'] for r in results),results=results)))
print(json.dumps(dict(count=len(results),passed=sum(r['passed'] for r in results),failures=[r for r in results if not r['passed']]),indent=2))
