#!/usr/bin/env python3
"""Independent Review probes. Synthetic data only; no application execution.
Usage: python review_probe.py CHECKOUT RESULT_JSON
Does not import Implementation tests or the independent Test harness.
"""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from datetime import datetime, timezone
from unittest.mock import patch

sys.path.insert(0, str(Path(sys.argv[1]).resolve()))
from scripts import consume_delivery as d
from scripts import delivery_candidates as t

def enc(x): return (json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n').encode()
def sha(b): return hashlib.sha256(b).hexdigest()
def oid(kind,b): return hashlib.sha1(kind.encode()+b' '+str(len(b)).encode()+b'\0'+b).hexdigest()
def key(r): return r['repository'],r['commit'],r.get('path')
def url(r): return f"https://github.com/{r['repository']}/blob/{r['commit']}/{r['path']}"
RESULTS=[]
def check(name,fn,reject=False):
    try:
        fn(); actual='accepted'; passed=not reject
    except ValueError as e:
        actual='rejected: '+str(e);passed=reject
    except Exception as e:
        actual='unexpected '+type(e).__name__+': '+str(e);passed=False
    RESULTS.append(dict(case=name,expected='reject' if reject else 'accept',actual=actual,passed=passed))

class Objects:
    def __init__(self): self.objects={};self.blobs={};self.calls=[]
    def add(self,kind,raw):
        k=oid(kind,raw);self.objects[k]=(kind,raw);return k
    def tree(self,entries):
        return self.add('tree',b''.join(m.encode()+b' '+n.encode()+b'\0'+bytes.fromhex(o) for m,n,o in entries))
    def repository(self,ref): d.check_reference(ref);return 'synthetic'
    def git(self,directory,*args):
        assert args[0]=='cat-file'
        kind,raw=self.objects[args[2]];self.calls.append(args)
        if args[1]=='-t':return kind.encode()+b'\n'
        if args[1]=='-s':return str(len(raw)).encode()+b'\n'
        assert args[1]==kind
        return raw
    def read(self,r): return self.blobs[key(r)]

class Fixture:
    def __init__(self):
        self.s=Objects()
        self.m=dict(schema_version='1.2',document_type='artifact_delivery',artifacts=[],knowledge_bindings=[],slot_bindings=[],candidate_bindings=[])
        self.src=self.add(b'Synthetic review source\r\n','source.txt','text','synthetic/source','b'*40)
        self.c=dict(document_type='knowledge_candidates',publication_status='pending_manager_review',candidates=[dict(id=i,domain='review',summary='Synthetic candidate',evidence='Synthetic only',source=url(self.src),scope='Review transport') for i in ('C1','C2')])
        self.owner=self.add(enc(self.c),'candidate.json','knowledge-candidates-v1')
        self.h=dict(schema_version='2.0',issue=dict(id='SYNTHETIC-REVIEW',source='synthetic',title='Synthetic',acceptance_criteria=[dict(id='AC',verbatim='Synthetic only',source='synthetic')]),role='review',task_id='SYNTHETIC-PRODUCER',attempt=1,upstream=[],system_status='completed',status='completed',summary='Synthetic only',assignment=dict(scope='synthetic',ac_ids=['AC'],completion_criteria=['Synthetic']),artifacts=[dict(id='C',kind='knowledge',locator='candidate.json',revision='sha256:'+self.owner['sha256'],summary='Synthetic')],evidence=[dict(id='E',claim='Synthetic',artifact_ids=['C'],locator='candidate.json',observation='Synthetic')],ac_mapping=[dict(ac_id='AC',disposition='covered',scope='Synthetic',artifact_ids=['C'],evidence_ids=['E'])],block_reasons=[],failure_reasons=[],knowledge_candidates=[dict(id=i,domain='review',summary='Synthetic',evidence_ids=['E'],raw_locator='candidate.json',publication_safety='needs_review') for i in ('C1','C2')],publication='synthetic_sample')
        self.producer=self.add(enc(self.h),'producer.json','handoff-v2');self.bind()
    def add(self,raw,path,fmt,repo='synthetic/owner',commit='a'*40):
        r=dict(object_type='git-blob',repository=repo,commit=commit,path=path,size=len(raw),sha256=sha(raw))
        self.s.blobs[key(r)]=raw
        self.m['artifacts'].append(dict(reference=r,format=fmt,representation='original',public_classification='synthetic_sample',source_alias='SYNTHETIC-REVIEW'))
        return r
    def update(self):
        raw=enc(self.c);self.owner.update(size=len(raw),sha256=sha(raw));self.s.blobs[key(self.owner)]=raw
        self.h['artifacts'][0]['revision']='sha256:'+sha(raw)
        raw=enc(self.h);self.producer.update(size=len(raw),sha256=sha(raw));self.s.blobs[key(self.producer)]=raw
        self.bind()
    def bind(self):
        self.m['slot_bindings']=[dict(owner=copy.deepcopy(self.producer),slot=dict(kind='artifact',id='C'),locator=self.h['artifacts'][0]['locator'],revision=self.h['artifacts'][0]['revision'],target=dict(reference=copy.deepcopy(self.owner),format='knowledge-candidates-v1'))]
        self.m['candidate_bindings']=[dict(profile='knowledge-candidates-v1',owner=copy.deepcopy(self.owner),producer=copy.deepcopy(self.producer),producer_artifact_id='C',candidate_ids=[c['id'] for c in self.c['candidates']],sources=[dict(candidate_id=c['id'],source=c['source'],target=dict(kind='blob',reference=copy.deepcopy(self.src))) for c in self.c['candidates']])]
    def records(self):
        m=enc(self.m);p=enc(dict(schema_version='1.2',document_type='publication_receipt',manifest_sha256=sha(m),github_state='published',artifacts=self.m['artifacts'],observation='Synthetic only'))
        a=dict(schema_version='1.2',document_type='delivery_authorization',authority='Synthetic',consumer='SYNTHETIC',scope='synthetic',purpose='contract-review',manifest_sha256=sha(m),valid_until='2026-10-18T00:00:00Z',public_safety_review='Synthetic',publication_approval='unverified',publication_approval_evidence='Synthetic',consumer_use_approval='approved',consumer_use_evidence='Synthetic',allowed_representations=['original'],publication_receipt_sha256=sha(p))
        return m,a,p
    def run(self,auth=None,**kw):
        m,a,p=self.records()
        if auth:auth(a)
        raw=enc(a)
        return d.consume(m,raw,p,sha(raw),'SYNTHETIC','synthetic','contract-review',self.s,now=datetime(2026,10,11,tzinfo=timezone.utc),**kw)

check('two candidate IDs share one fully checked blob',lambda:Fixture().run())
def mutate(fn):
    b=Fixture();fn(b);return b.run()
check('candidate and producer order are set based',lambda:mutate(lambda b:(b.c['candidates'].reverse(),b.update())))
check('absolute producer locator and raw_locator bind same owner',lambda:mutate(lambda b:(b.h['artifacts'][0].update(locator=url(b.owner)),[c.update(raw_locator=url(b.owner)) for c in b.h['knowledge_candidates']],b.update())))
for member,value in [('size',True),('size',-1),('sha256','F'*64),('commit','b'*39),('path','x/../source.txt'),('repository','synthetic/source.git?x')]:
    check('schema/reference rejects '+member+' '+repr(value),lambda member=member,value=value:mutate(lambda b:b.m['artifacts'][0]['reference'].update({member:value})),True)
for section in ('candidate_bindings','slot_bindings','knowledge_bindings'):
    check('binding JSON type '+section,lambda section=section:mutate(lambda b:b.m.update({section:{}})),True)
for field in ('producer_artifact_id','profile','owner','producer','candidate_ids','sources'):
    check('required outer candidate field '+field,lambda field=field:mutate(lambda b:b.m['candidate_bindings'][0].pop(field)),True)
def second_producer():
    b=Fixture();h=copy.deepcopy(b.h);h['task_id']='SYNTHETIC-SECOND';r=b.add(enc(h),'second.json','handoff-v2')
    slot=copy.deepcopy(b.m['slot_bindings'][0]);slot['owner']=r;b.m['slot_bindings'].append(slot);b.run()
check('second producer cannot silently claim bound candidates',second_producer,True)
check('publication remains unverified with read-only approval',lambda:Fixture().run())
check('exact expiry is rejected',lambda:Fixture().run(auth=lambda a:a.update(valid_until='2026-10-11T00:00:00Z')),True)
check('current representation restriction applies on recheck',lambda:Fixture().run(auth=lambda a:a.update(allowed_representations=['edited_derivative'])),True)
for raw in (b'{"x":{"a":1,"\\u0061":2}}',b'{"document_type":"knowledge_unrecognized"}',b'{"publication":"private_only"}',b'[1,2',b'{}null'):
    check('strict extra artifact '+repr(raw),lambda raw=raw:mutate(lambda b:b.add(raw,'payload.data','json')),True)

def tree_fixture(mode='100644',name='leaf',duplicate=False):
    b=Fixture();s=b.s;blob=s.add('blob',b'\0\xffsynthetic\r\n');empty=s.tree([])
    entries=[(mode,name,blob),('40000','empty',empty)]
    if duplicate:entries.append((mode,name,blob))
    sub=s.tree(entries);root=s.tree([('40000','dir',sub)])
    commit=s.add('commit',b'tree '+root.encode()+b'\nauthor Synthetic <s@example.invalid> 0 +0000\ncommitter Synthetic <s@example.invalid> 0 +0000\n\nSynthetic\n')
    ref=dict(repository='synthetic/tree',commit=commit,path='dir')
    snap=dict(profile='git-tree-snapshot-v1',**ref,oid=sub,trees=[dict(path='empty',oid=empty)],files=[dict(path=name,mode=mode,oid=blob,size=len(s.objects[blob][1]),sha256=sha(s.objects[blob][1]))])
    u=f'https://github.com/synthetic/tree/tree/{commit}/dir';b.c['candidates'][1]['source']=u;b.update()
    b.m['candidate_bindings'][0]['sources'][1].update(source=u,target=dict(kind='tree',snapshot=snap))
    return b,ref
check('independently assembled raw tree with binary leaf and empty subtree',lambda:tree_fixture()[0].run())
for mode in ('120000','160000','100664'):
    check('raw tree mode '+mode,lambda mode=mode:tree_fixture(mode)[0].run(),True)
check('duplicate raw Git tree name',lambda:tree_fixture(duplicate=True)[0].run(),True)
for name in ('.git','..','bad/name','bad\\name','bad\tname'):
    check('unsafe raw tree name '+repr(name),lambda name=name:tree_fixture(name=name)[0].run(),True)
for which in ('files','trees'):
    def omit(which=which):
        b,r=tree_fixture();b.m['candidate_bindings'][0]['sources'][1]['target']['snapshot'][which]=[];b.run()
    check('full raw enumeration prevents omitted '+which,omit,True)
def tree_recheck():
    b,r=tree_fixture();receipt,raw=b.run();s=b.s
    leaf=next(k for k,(kind,v) in s.objects.items() if kind=='blob');s.objects[leaf]=('blob',b'altered')
    b.run(receipt_raw=enc(receipt))
check('fresh tree recheck detects changed actual leaf bytes',tree_recheck,True)
def tree_budget():
    b,r=tree_fixture()
    with patch.object(t,'MAX_BUNDLE',sum(len(x) for x in b.s.blobs.values())):b.run()
check('combined explicit plus tree bytes bound',tree_budget,True)
def transport():
    with tempfile.TemporaryDirectory() as tmp,patch.dict('os.environ',{'GIT_CONFIG_COUNT':'1','GIT_CONFIG_KEY_0':'core.sshCommand','GIT_CONFIG_VALUE_0':'malicious','GITHUB_TOKEN':'SYNTHETIC'}):
        with patch.object(d.subprocess,'run') as run:
            run.return_value.returncode=0;run.return_value.stdout=b'';d.GitSource(tmp).git(tmp,'status')
            args,kw=run.call_args
            assert kw['env']['GIT_ALLOW_PROTOCOL']=='https' and kw['env']['GIT_NO_REPLACE_OBJECTS']=='1'
            assert not any(k in kw['env'] for k in ('GIT_CONFIG_COUNT','GITHUB_TOKEN','GIT_SSH_COMMAND'))
            assert 'http.followRedirects=false' in args[0] and not kw.get('shell')
check('ambient injection variables excluded from Git subprocess',transport)
def no_overwrite():
    b=Fixture();r,raw=b.run()
    with tempfile.TemporaryDirectory() as tmp:
        out=Path(tmp)/'out';d.write_bundle(out,r,raw);sentinel=(out/'sentinel');sentinel.write_bytes(b'unchanged')
        try:d.write_bundle(out,r,raw)
        except ValueError:pass
        else:raise AssertionError('overwrite accepted')
        assert sentinel.read_bytes()==b'unchanged' and not list(Path(tmp).glob('.delivery-*'))
check('existing output preserved and temporary staging cleaned',no_overwrite)
result=dict(report_type='independent_review_probes',cases=RESULTS,total=len(RESULTS),passed=sum(x['passed'] for x in RESULTS),failed=sum(not x['passed'] for x in RESULTS),limits='Synthetic fixtures and mocked Git object transport supplement actual B1 CLI; no application execution.')
Path(sys.argv[2]).write_bytes(enc(result));print(json.dumps({k:result[k] for k in ('total','passed','failed')}))
for x in RESULTS:
    if not x['passed']:print(x)
sys.exit(bool(result['failed']))
