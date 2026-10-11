#!/usr/bin/env python3
"""Independent Test A1. Synthetic local probes; no application execution.

Run: python independent_probe.py CHECKOUT RESULTS LEGACY10_CHECKOUT LEGACY11_CHECKOUT
Imports production modules only, not Implementation's tests or fixture builders.
Every adversarial document is repinned in synthetic outer records unless the
case explicitly tests a pin mismatch. Real Manager authorizations are not used.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from unittest.mock import patch

ROOT=Path(sys.argv[1]).resolve()
sys.path.insert(0,str(ROOT))
from scripts import consume_delivery as d
from scripts import delivery_candidates as t

def enc(x): return (json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n').encode()
def sha(b): return hashlib.sha256(b).hexdigest()
def oid(k,b): return hashlib.sha1(k.encode()+b' '+str(len(b)).encode()+b'\0'+b).hexdigest()
def key(r): return r['repository'],r['commit'],r.get('path')
def url(r): return 'https://github.com/'+r['repository']+('/commit/'+r['commit'] if r['object_type']=='git-commit-object' else '/blob/'+r['commit']+'/'+r['path'])
RESULTS=[]
def check(name,fn,reject=False):
    try:
        fn()
        ok=not reject
        actual='accepted'
    except (ValueError,OSError) as e:
        ok=reject
        actual=type(e).__name__+': '+str(e)
    except Exception as e:
        ok=False
        actual='unexpected '+type(e).__name__+': '+str(e)
    RESULTS.append(dict(case=name,expected='reject' if reject else 'accept',actual=actual,passed=ok))
    if not ok: print('FINDING',name,actual,flush=True)

class Memory:
    def __init__(self,b): self.b=b;self.calls=[]
    def read(self,r):
        self.calls.append(key(r))
        if key(r) not in self.b: raise ValueError('independent synthetic missing object')
        return self.b[key(r)]

class Fixture:
    def __init__(self,source=None):
        self.m=dict(schema_version='1.2',document_type='artifact_delivery',artifacts=[],knowledge_bindings=[],slot_bindings=[],candidate_bindings=[])
        self.raw={}
        self.src=self.add(b'Independent raw source\r\n','src.txt',repo='synthetic/source',commit='b'*40)
        self.candidate=dict(document_type='knowledge_candidates',publication_status='pending_manager_review',candidates=[dict(id='SYNTHETIC-C',domain='test',summary='Long independent explanation.',evidence='Synthetic evidence, no truth claim.',source=url(self.src),scope='Independent test')])
        self.owner=self.add(enc(self.candidate),'candidates.json','knowledge-candidates-v1')
        self.h=json.loads((ROOT/'examples/research-to-test/research.handoff.json').read_bytes())
        self.h['task_id']='SYNTHETIC-INDEPENDENT-PRODUCER'
        self.h['artifacts'][0].update(kind='knowledge',locator='candidates.json',revision='sha256:'+self.owner['sha256'])
        self.h['knowledge_candidates']=[dict(id='SYNTHETIC-C',domain='test',summary='Short summary.',evidence_ids=[self.h['evidence'][0]['id']],raw_locator='candidates.json',publication_safety='needs_review')]
        self.producer=self.add(enc(self.h),'producer.json','handoff-v2')
        self.m['slot_bindings']=[dict(owner=copy.deepcopy(self.producer),slot=dict(kind='artifact',id=self.h['artifacts'][0]['id']),locator='candidates.json',revision='sha256:'+self.owner['sha256'],target=dict(reference=copy.deepcopy(self.owner),format='knowledge-candidates-v1'))]
        self.m['candidate_bindings']=[dict(profile='knowledge-candidates-v1',owner=copy.deepcopy(self.owner),producer=copy.deepcopy(self.producer),producer_artifact_id=self.h['artifacts'][0]['id'],candidate_ids=['SYNTHETIC-C'],sources=[dict(candidate_id='SYNTHETIC-C',source=url(self.src),target=dict(kind='blob',reference=copy.deepcopy(self.src)))])]
    def add(self,b,path,fmt='text',repo='synthetic/producer',commit='a'*40):
        r=dict(object_type='git-commit-object' if fmt=='git-commit-object' else 'git-blob',repository=repo,commit=commit,size=len(b),sha256=sha(b))
        if path is not None:r['path']=path
        self.raw[key(r)]=b
        self.m['artifacts'].append(dict(reference=r,format=fmt,representation='original',public_classification='synthetic_sample',source_alias='SYNTHETIC-INDEPENDENT'))
        return r
    def replace_ref(self,old,new):
        def walk(x):
            if isinstance(x,dict):
                for k,v in list(x.items()):
                    if v==old:x[k]=copy.deepcopy(new)
                    else:walk(v)
            elif isinstance(x,list):
                for v in x:walk(v)
        walk(self.m)
    def document(self,which,change=None,raw=None):
        ref=self.owner if which=='candidate' else self.producer
        old=copy.deepcopy(ref);obj=json.loads(self.raw[key(ref)])
        if change:change(obj)
        b=enc(obj) if raw is None else raw
        ref.update(size=len(b),sha256=sha(b));self.raw[key(ref)]=b
        self.replace_ref(old,ref)
        if which=='candidate':
            self.document('producer',lambda h:h['artifacts'][0].update(revision='sha256:'+sha(b)))
            self.m['slot_bindings'][0]['revision']='sha256:'+sha(b)
    def records(self,policy_change=None):
        m=enc(self.m)
        p=dict(schema_version='1.2',document_type='publication_receipt',manifest_sha256=sha(m),github_state='published',artifacts=copy.deepcopy(self.m['artifacts']),observation='Independent synthetic local fixture; not actual publication.')
        a=dict(schema_version='1.2',document_type='delivery_authorization',authority='Synthetic independent test only',consumer='SYNTHETIC-TEST',scope='synthetic/local',purpose='contract-review',manifest_sha256=sha(m),valid_until='2030-01-01T00:00:00Z',public_safety_review='Synthetic',publication_approval='unverified',publication_approval_evidence='Synthetic',consumer_use_approval='approved',consumer_use_evidence='Synthetic',allowed_representations=['original'],publication_receipt_sha256=sha(enc(p)))
        if policy_change:policy_change(a)
        return m,enc(a),enc(p)
    def run(self,policy_change=None,**kw):
        m,a,p=self.records(policy_change)
        args=dict(manifest_raw=m,policy_raw=a,publication_raw=p,policy_sha256=sha(a),consumer='SYNTHETIC-TEST',scope='synthetic/local',purpose='contract-review',source=Memory(self.raw),now=datetime(2026,10,11,tzinfo=timezone.utc))
        args.update(kw)
        return d.consume(**args)

check('independent candidate producer positive; short summary/pending is not approval',lambda:Fixture().run())
for field in ('document_type','publication_status','candidates'):
    def fn(field=field):
        b=Fixture();b.document('candidate',lambda x:x.pop(field));b.run()
    check('candidate required '+field,fn,True)
for field in ('id','domain','summary','evidence','source','scope'):
    for value in (None,True,17,[],{},'', ' \t', 'z'*17000):
        def fn(field=field,value=value):
            b=Fixture();b.document('candidate',lambda x:x['candidates'][0].update({field:value}));b.run()
        check('candidate field '+field+' '+str(type(value))+' '+str(len(value) if isinstance(value,str) else value),fn,True)
    def fn(field=field):
        b=Fixture();b.document('candidate',lambda x:x['candidates'][0].pop(field));b.run()
    check('candidate missing field '+field,fn,True)
for field in ('schema_version','task_id','attempt','revision','authority','unknown'):
    def fn(field=field):
        b=Fixture();b.document('candidate',lambda x:x.update({field:'added'}));b.run()
    check('forbidden added candidate field '+field,fn,True)
for status in ('approved','accepted','adopted','public_safe','private_only'):
    def fn(status=status):
        b=Fixture();b.document('candidate',lambda x:x.update(publication_status=status));b.run()
    check('candidate status grants nothing '+status,fn,True)
for fmt in ('json','text','handoff-v2','knowledge-input-v1','knowledge-context-v1','knowledge-handoff-v1'):
    def fn(fmt=fmt):
        b=Fixture();b.m['artifacts'][1]['format']=fmt;b.run()
    check('candidate downgrade '+fmt,fn,True)
for raw in (b'{"document_type":"knowledge_unknown"}',b'{"publication_status":"pending_manager_review"}',b'{"candidates":[]}',b'{"x":{"n":1,"\\u006e":2}}',b'{"x":NaN}',b'{"x":Infinity}',b'\xef\xbb\xbf{}',b'{"x":',b'{} trailing',b'[1,'):
    for fmt in ('json','text'):
        def fn(raw=raw,fmt=fmt):
            b=Fixture();b.add(raw,'negative.data',fmt);b.run()
        check('strict content '+fmt+' '+repr(raw),fn,True)
for change,name in [(lambda x:x['candidates'].append(copy.deepcopy(x['candidates'][0])),'duplicate ID'),(lambda x:x.update(candidates=[]),'empty'),(lambda x:x['candidates'][0].update(extra='x'),'extra field'),(lambda x:x.update(document_type='knowledge_future'),'unknown type')]:
    def fn(change=change):
        b=Fixture();b.document('candidate',change);b.run()
    check('candidate '+name,fn,True)
for section in ('slot_bindings','candidate_bindings'):
    for operation in ('missing','duplicate','extra'):
        def fn(section=section,operation=operation):
            b=Fixture();items=b.m[section]
            if operation=='missing':items.clear()
            else:
                item=copy.deepcopy(items[0]);items.append(item)
                if operation=='extra':item['owner']['path']='absent.json'
            b.run()
        check(section+' '+operation,fn,True)
for section,parts in [('slot_bindings',('owner',)),('slot_bindings',('target','reference')),('candidate_bindings',('owner',)),('candidate_bindings',('producer',)),('candidate_bindings',('sources',0,'target','reference'))]:
    for field,value in [('repository','synthetic/other'),('commit','c'*40),('path','other.txt'),('size',0),('sha256','0'*64),('object_type','git-commit-object')]:
        def fn(section=section,parts=parts,field=field,value=value):
            b=Fixture();v=b.m[section][0]
            for p in parts:v=v[p]
            v[field]=value;b.run()
        check('binding exact '+section+' '+str(parts)+' '+field,fn,True)
for change,name in [(lambda c:c.update(candidate_ids=[]),'missing IDs'),(lambda c:c.update(candidate_ids=['SYNTHETIC-C','SYNTHETIC-C']),'duplicate IDs'),(lambda c:c.update(candidate_ids=['EXTRA']),'extra IDs'),(lambda c:c.update(producer_artifact_id='wrong'),'artifact ID'),(lambda c:c['sources'].clear(),'missing source'),(lambda c:c['sources'].append(copy.deepcopy(c['sources'][0])),'duplicate source'),(lambda c:c['sources'][0].update(candidate_id='EXTRA'),'extra source'),(lambda c:c.update(profile='knowledge-candidates-v2'),'profile')]:
    def fn(change=change):
        b=Fixture();change(b.m['candidate_bindings'][0]);b.run()
    check('candidate binding '+name,fn,True)
for field,value in [('id','OTHER'),('domain','OTHER'),('raw_locator','other.json')]:
    def fn(field=field,value=value):
        b=Fixture();b.document('producer',lambda x:x['knowledge_candidates'][0].update({field:value}));b.run()
    check('producer candidate '+field,fn,True)
for change,name in [(lambda h:h.update(publication='private_only'),'private'),(lambda h:h.update(knowledge_candidates=[]),'empty candidate set'),(lambda h:h['knowledge_candidates'].append(copy.deepcopy(h['knowledge_candidates'][0])),'duplicate candidate set'),(lambda h:h['artifacts'][0].update(kind='document'),'wrong artifact kind')]:
    def fn(change=change):
        b=Fixture();b.document('producer',change);b.run()
    check('producer '+name,fn,True)
baseurl=url(Fixture().src)
for u in (baseurl+'?x=1',baseurl+'#frag',baseurl+'/',baseurl.replace('https:','http:'),baseurl.replace('/blob/'+'b'*40,'/blob/main'),baseurl.replace('/blob/','/raw/'),baseurl.replace('src.txt','%73rc.txt'),baseurl.replace('github.com','github.com.evil'),baseurl.replace('synthetic/source','synthetic/other'),baseurl.replace('b'*40,'c'*40)):
    def fn(u=u):
        b=Fixture();b.document('candidate',lambda x:x['candidates'][0].update(source=u));b.m['candidate_bindings'][0]['sources'][0]['source']=u;b.run()
    check('canonical source URL '+u,fn,True)
def copy_attack():
    b=Fixture();r=b.add(b.raw[key(b.owner)],'candidates.json','knowledge-candidates-v1',repo='synthetic/copy')
    b.m['artifacts'].pop(1);b.m['slot_bindings'][0]['target']['reference']=copy.deepcopy(r);b.m['candidate_bindings'][0]['owner']=copy.deepcopy(r);b.run()
check('identical candidate copy cannot rebind relative original',copy_attack,True)
for field,value in [('valid_until','2026-10-11T00:00:00Z'),('valid_until','2030-01-01T00:00:00'),('scope','other'),('consumer','other'),('purpose','implementation'),('consumer_use_approval','pending'),('manifest_sha256','0'*64),('publication_receipt_sha256','0'*64),('allowed_representations',['edited_derivative'])]:
    check('authorization '+field,lambda field=field,value=value:Fixture().run(lambda a:a.update({field:value})),True)
check('independent authorization pin',lambda:Fixture().run(policy_sha256='0'*64),True)
for v in ('1.0','1.1'):
    check('mixed authorization '+v,lambda v=v:Fixture().run(lambda a:a.update(schema_version=v)),True)
    def fn(v=v):
        b=Fixture();b.m['schema_version']=v;b.run()
    check('legacy new format '+v,fn,True)
    def fn(v=v):
        b=Fixture();r=b.run()[0];r['schema_version']=v;b.run(receipt_raw=enc(r))
    check('mixed consumption receipt '+v,fn,True)
    def fn(v=v):
        b=Fixture();m,a,p=b.records();pub=json.loads(p);pub['schema_version']=v;p=enc(pub);auth=json.loads(a);auth['publication_receipt_sha256']=sha(p);a=enc(auth);b.run(policy_raw=a,policy_sha256=sha(a),publication_raw=p)
    check('mixed publication '+v,fn,True)
def fresh_missing():
    b=Fixture();r=b.run()[0];raw=copy.deepcopy(b.raw);raw.pop(key(b.src));b.run(source=Memory(raw),receipt_raw=enc(r))
check('fresh recheck must retrieve source',fresh_missing,True)
def fresh_altered():
    b=Fixture();r=b.run()[0];b.raw[key(b.src)]+=b'!';b.run(receipt_raw=enc(r))
check('fresh recheck changed raw bytes',fresh_altered,True)
def false_authority():
    b=Fixture();r=b.run()[0];r['authority_granted']=True;b.run(receipt_raw=enc(r))
check('receipt cannot grant authority',false_authority,True)

def commit_fixture():
    b=Fixture();raw=b'tree '+b'f'*40+b'\nauthor Synthetic <test@example.invalid> 0 +0000\ncommitter Synthetic <test@example.invalid> 0 +0000\n\nIndependent synthetic\n'
    r=b.add(raw,None,'git-commit-object',commit=oid('commit',raw))
    b.document('producer',lambda h:h['artifacts'].append(dict(id='SYNTHETIC-COMMIT',kind='commit',locator=url(r),revision=r['commit'],summary='Object exists only')))
    b.m['slot_bindings'].append(dict(owner=copy.deepcopy(b.producer),slot=dict(kind='artifact',id='SYNTHETIC-COMMIT'),locator=url(r),revision=r['commit'],target=dict(reference=copy.deepcopy(r),format='git-commit-object')))
    return b,r
check('typed commit raw bytes',lambda:commit_fixture()[0].run())
for change,name in [(lambda r:r.update(size=1),'size'),(lambda r:r.update(sha256='0'*64),'hash'),(lambda r:r.update(commit='0'*40),'OID'),(lambda r:r.update(object_type='git-blob'),'type'),(lambda r:r.update(path='commit.raw'),'forbidden path')]:
    def fn(change=change):
        b,r=commit_fixture();old=copy.deepcopy(r);raw=b.raw[key(r)];change(r);b.raw[key(r)]=raw;b.replace_ref(old,r);b.run()
    check('raw commit '+name,fn,True)
def commit_rehash():
    b,r=commit_fixture();old=copy.deepcopy(r);raw=b.raw[key(r)].replace(b'Independent',b'AlteredData');r.update(size=len(raw),sha256=sha(raw));b.raw[key(r)]=raw;b.replace_ref(old,r);b.run()
check('raw commit recompute SHA256 still requires Git OID',commit_rehash,True)

def retry_fixture():
    b=Fixture();prior=copy.deepcopy(b.h);prior.update(task_id='SYNTHETIC-INDEPENDENT-PRIOR',knowledge_candidates=[])
    prior['artifacts'][0].update(kind='document',locator=url(b.src),revision='sha256:'+b.src['sha256'])
    r=b.add(enc(prior),'prior.json','handoff-v2',commit='c'*40)
    b.m['slot_bindings'].append(dict(owner=copy.deepcopy(r),slot=dict(kind='artifact',id=prior['artifacts'][0]['id']),locator=url(b.src),revision='sha256:'+b.src['sha256'],target=dict(reference=copy.deepcopy(b.src),format='text')))
    upstream=dict(role=prior['role'],task_id=prior['task_id'],attempt=1,relationship='retry_of',handoff_locator=url(r),revision='sha256:'+r['sha256'])
    b.document('producer',lambda h:h.update(attempt=2,upstream=[upstream]))
    b.m['slot_bindings'].append(dict(owner=copy.deepcopy(b.producer),slot=dict(kind='upstream',**{k:upstream[k] for k in ('role','task_id','attempt','relationship')}),locator=url(r),revision=upstream['revision'],target=dict(reference=copy.deepcopy(r),format='handoff-v2')))
    return b
check('independent cross-commit retry dependency',lambda:retry_fixture().run())
for field,value in [('role','test'),('task_id','SYNTHETIC-WRONG'),('attempt',2)]:
    def fn(field=field,value=value):
        b=retry_fixture();b.document('producer',lambda h:h['upstream'][0].update({field:value}));b.m['slot_bindings'][-1]['slot'][field]=value;b.run()
    check('independent retry mismatch '+field,fn,True)
def retry_issue():
    b=retry_fixture();b.document('producer',lambda h:h['issue'].update(title='Different issue'));b.run()
check('independent retry Issue equality',retry_issue,True)
def supplement():
    b=retry_fixture();b.document('producer',lambda h:h['assignment']['completion_criteria'].append('Synthetic extra assigned verification'));b.run()
check('additional completion conditions retain original Issue',supplement)
for field,value in [('locator','other.json'),('revision','sha256:'+'0'*64)]:
    def fn(field=field,value=value):
        b=Fixture();b.m['slot_bindings'][0][field]=value;b.run()
    check('original slot '+field+' cannot be overwritten',fn,True)
def all_objects():
    b=Fixture();s=Memory(b.raw);receipt,raw=b.run(source=s);assert set(s.calls)==set(b.raw) and raw==b.raw and receipt['authority_granted'] is False
check('all enumerated dependencies fetched before success',all_objects)

for legacy in sys.argv[3:5]:
    def fn(legacy=legacy):
        b=Fixture();m,a,p=b.records()
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'manifest.json';path.write_bytes(m)
            code='import sys,json;sys.path.insert(0,sys.argv[1]);from scripts.consume_delivery import schema;schema("artifact-delivery",json.load(open(sys.argv[2])))'
            r=subprocess.run([sys.executable,'-c',code,legacy,str(path)],capture_output=True)
            assert r.returncode!=0 and b'ValueError' in r.stderr
    check('actual unchanged legacy validator rejects new manifest '+Path(legacy).name,fn)

with tempfile.TemporaryDirectory(prefix='independent-tree-') as tmp:
    root=Path(tmp);repo=root/'synthetic';repo.mkdir()
    def git(*args,input=None):
        return subprocess.run(['git','-C',str(repo),*args],input=input,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True).stdout
    git('init');git('config','user.name','Synthetic');git('config','user.email','test@example.invalid')
    (repo/'dir/sub').mkdir(parents=True);(repo/'dir/a').write_bytes(b'line\r\n');(repo/'dir/sub/b').write_bytes(b'\0\xffraw');(repo/'dir/run').write_bytes(b'Not executable application code\n');(repo/'dir/run').chmod(0o755)
    git('add','.');git('commit','-m','Independent synthetic tree')
    commit=git('rev-parse','HEAD').decode().strip()
    cache=root/'cache';cache.mkdir();source=d.GitSource(cache);real_git=source.git
    def local(directory,*args):
        if args[0]=='fetch':
            return subprocess.run(['git','-C',str(directory),'fetch','--no-tags',str(repo),args[-1]],stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True).stdout
        return real_git(directory,*args)
    source.git=local
    ref=dict(repository='synthetic/tree',commit=commit,path='dir')
    snap,treebytes=t.snapshot_tree(source,ref)
    def oracle():
        entries=git('ls-tree','-r','-z',commit+':dir').split(b'\0')[:-1]
        expected=[]
        for e in entries:
            hdr,path=e.split(b'\t');mode,kind,obj=hdr.split();raw=git('cat-file','blob',obj.decode())
            expected.append(dict(path=path.decode(),mode=mode.decode(),oid=obj.decode(),size=len(raw),sha256=sha(raw)))
        assert snap['files']==sorted(expected,key=lambda x:x['path'])
        assert len(snap['trees'])==1 and len(treebytes)==3
    check('tree independent recursive ls-tree oracle including binary/executable',oracle)
    def tree_fixture():
        b=Fixture();u='https://github.com/synthetic/tree/tree/'+commit+'/dir'
        b.document('candidate',lambda x:x['candidates'][0].update(source=u))
        b.m['candidate_bindings'][0]['sources'][0].update(source=u,target=dict(kind='tree',snapshot=copy.deepcopy(snap)))
        s=Memory(b.raw);s.repository=source.repository;s.git=source.git
        return b,s
    check('complete tree candidate consumer',lambda:tree_fixture()[0].run(source=tree_fixture()[1]))
    for operation in ('omit-file','extra-file','duplicate-file','omit-tree','extra-tree','duplicate-tree','reorder','oid','mode','size','sha256','root','exclude'):
        def fn(operation=operation):
            b,s=tree_fixture();v=b.m['candidate_bindings'][0]['sources'][0]['target']['snapshot']
            if operation=='omit-file':v['files'].pop()
            elif operation=='extra-file':v['files'].append(dict(v['files'][0],path='extra'))
            elif operation=='duplicate-file':v['files'].append(copy.deepcopy(v['files'][0]))
            elif operation=='omit-tree':v['trees'].clear()
            elif operation=='extra-tree':v['trees'].append(dict(path='extra',oid='0'*40))
            elif operation=='duplicate-tree':v['trees'].append(copy.deepcopy(v['trees'][0]))
            elif operation=='reorder':v['files'].reverse()
            elif operation=='root':v['oid']='0'*40
            elif operation=='exclude':v['exclusions']=['sub']
            else:v['files'][0][operation]={'oid':'0'*40,'mode':'100755','size':0,'sha256':'0'*64}[operation]
            b.run(source=s)
        check('complete tree inventory '+operation,fn,True)
    for limit,value in [('MAX_ENTRIES',1),('MAX_TREES',0),('MAX_TREE_BYTES',1),('MAX_TREE_TOTAL',1),('MAX_FILE',1),('MAX_BUNDLE',1)]:
        def fn(limit=limit,value=value):
            with patch.object(t,limit,value):t.snapshot_tree(source,ref)
        check('tree bounded '+limit,fn,True)
    for operation in ('truncate-tree','change-tree','change-blob','wrong-type','wrong-size','missing-object'):
        def fn(operation=operation):
            def fault(directory,*args):
                raw=local(directory,*args)
                if args[:2]==('cat-file','tree'):
                    if operation=='truncate-tree':return raw[:-1]
                    if operation=='change-tree':return b'X'+raw[1:]
                    if operation=='missing-object':raise ValueError('Synthetic missing tree')
                if args[:2]==('cat-file','blob') and operation=='change-blob':return b'x'*len(raw)
                if args[:2]==('cat-file','-t') and raw==b'tree\n' and operation=='wrong-type':return b'blob\n'
                if args[:2]==('cat-file','-s') and operation=='wrong-size':return b'0\n'
                return raw
            with patch.object(source,'git',fault):t.snapshot_tree(source,ref)
        check('raw tree transport '+operation,fn,True)
    for mode in ('120000','160000'):
        target=oid('blob',b'a') if mode=='120000' else commit
        if mode=='120000':git('hash-object','-w','--stdin',input=b'a')
        git('update-index','--add','--cacheinfo',mode+','+target+',dir/special');git('commit','-m','Synthetic special edge')
        special=git('rev-parse','HEAD').decode().strip()
        for path in ('dir','dir/special','dir/special/child'):
            check('tree special mode '+mode+' '+path,lambda path=path,special=special:t.snapshot_tree(source,dict(ref,commit=special,path=path)),True)
            if path!='dir':check('blob special ancestor '+mode+' '+path,lambda path=path,special=special:source.read(dict(ref,object_type='git-blob',commit=special,path=path,size=1,sha256=sha(b'a'))),True)
        git('rm','--cached','dir/special')
    empty=git('mktree',input=b'').decode().strip();root_tree=git('mktree',input=('040000 tree '+empty+'\tempty\n').encode()).decode().strip();empty_commit=git('commit-tree',root_tree,input=b'Synthetic empty\n').decode().strip()
    def empty_case():
        s,b=t.snapshot_tree(source,dict(ref,commit=empty_commit,path='empty'));assert s['oid']==empty and not s['files'] and not s['trees'] and not b
    check('explicit empty Git tree',empty_case)
    for mode,path,raw in [('100644','dir/a',b'line\r\n'),('100755','dir/run',b'Not executable application code\n')]:
        blobref=dict(ref,object_type='git-blob',path=path,size=len(raw),sha256=sha(raw))
        check('normal Git blob OID and raw bytes '+mode,lambda:source.read(blobref))
    def transport():
        with patch.object(d.subprocess,'run') as run:
            run.return_value.returncode=0;run.return_value.stdout=b''
            d.GitSource(root).git(root,'status');args,kw=run.call_args
            assert 'http.followRedirects=false' in args[0] and 'core.hooksPath=/dev/null' in args[0]
            assert kw['env']['GIT_ALLOW_PROTOCOL']=='https' and kw['env']['GIT_CONFIG_GLOBAL']==os.devnull
            assert 'GITHUB_TOKEN' not in kw['env'] and not kw.get('shell',False)
    check('isolated transport never follows redirect or ambient auth',transport)

# Exercise CLI staging/error return for late content and receipt failures. Local
# synthetic fetch substitution is confined to this process and fixture map.
for scenario in ('late-json','late-receipt','scope','pin'):
    def cli_case(scenario=scenario):
        b=Fixture()
        if scenario=='late-json':b.add(b'{"n":NaN}','late.json','json')
        m,a,p=b.records()
        with tempfile.TemporaryDirectory(prefix='independent-cli-') as tmp:
            root=Path(tmp)
            for name,raw in [('m',m),('a',a),('p',p)]: (root/name).write_bytes(raw)
            args=['consume_delivery','--manifest',str(root/'m'),'--authorization',str(root/'a'),'--publication',str(root/'p'),'--authorization-sha256',sha(a),'--consumer','SYNTHETIC-TEST','--scope','synthetic/local','--purpose','contract-review','--output',str(root/'out')]
            if scenario=='scope':args[args.index('--scope')+1]='wrong'
            if scenario=='pin':args[args.index('--authorization-sha256')+1]='0'*64
            if scenario=='late-receipt':
                r=b.run()[0];r['authority_granted']=True;(root/'r').write_bytes(enc(r));args+=['--verify-receipt',str(root/'r')]
            with patch.object(sys,'argv',args),patch.object(d,'GitSource',lambda _:Memory(b.raw)):
                rc=d.main()
            assert rc==1 and not (root/'out').exists()
            assert not list(root.glob('.delivery-*'))
    check('CLI fail closed no output/receipt '+scenario,cli_case)

out=dict(report_type='independent_synthetic_probe_results',head='4b4e9c249451881f1e5eef82efb3a3b111cacbdb',cases=RESULTS,total=len(RESULTS),passed=sum(r['passed'] for r in RESULTS),failed=sum(not r['passed'] for r in RESULTS),limits='Synthetic in-process faults are not live remote attack executions; real B1 CLI/recheck recorded separately. No production code modifications.')
Path(sys.argv[2]).write_bytes(enc(out))
print(json.dumps({k:out[k] for k in ('total','passed','failed')}))
sys.exit(bool(out['failed']))
