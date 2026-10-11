#!/usr/bin/env python3
"""Independent synthetic CLI verification. No candidate test helpers imported.
Usage: python reproducer.py CANDIDATE_CHECKOUT CANONICAL_CHECKOUT RESULT_JSON
Only HTTPS fetch is substituted with a fresh fetch from a temporary local Git
origin. All actual CLI/schema/byte/type/closure/output checks execute unchanged.
Synthetic authorizations are temporary and are never published.
"""
import copy, hashlib, json, os, pathlib, subprocess, sys, tempfile, time
from datetime import datetime, timezone
P=pathlib.Path
sha=lambda b:hashlib.sha256(b).hexdigest()
enc=lambda d:(json.dumps(d,ensure_ascii=False,indent=2)+'\n').encode()

def adapter():
    root,origin,mode=sys.argv[2:5];sys.path.insert(0,root+'/scripts')
    import consume_delivery as d
    old=d.GitSource.git
    def git(self,directory,*args):
        if args[0]=='fetch':
            return subprocess.check_output(['git','-c','core.hooksPath=/dev/null','-C',str(directory),'fetch','--no-tags',origin,args[-1]],stderr=subprocess.DEVNULL)
        return old(self,directory,*args)
    d.GitSource.git=git
    sys.argv=[mode]+sys.argv[5:]
    if mode=='prepare':
        import prepare_crossref_bundle as p
        p.main()
    else:sys.exit(d.main())

if len(sys.argv)>1 and sys.argv[1]=='--adapter':adapter();sys.exit(0)

candidate,canonical,result=map(P,sys.argv[1:4]);rows=[];start=datetime.now(timezone.utc).isoformat();t0=time.monotonic()
with tempfile.TemporaryDirectory(prefix='independent-capacity-') as tmp:
    root=P(tmp);origin=root/'origin';origin.mkdir()
    def git(*args):return subprocess.check_output(['git','-C',str(origin),*args],stderr=subprocess.DEVNULL).decode().strip()
    git('init');git('config','user.name','Synthetic Test');git('config','user.email','test@example.invalid')
    def commit():git('add','.');git('commit','-m','Synthetic capacity fixture');return git('rev-parse','HEAD')
    def handoff(name):
        return dict(schema_version='2.0',issue=dict(id='synthetic-capacity',source='synthetic',title='Synthetic',acceptance_criteria=[dict(id='S1',verbatim='Synthetic fixture only.',source='synthetic')]),role='test',task_id=name,attempt=1,upstream=[],system_status='completed',status='blocked',summary='Synthetic fixture; no product claim.',artifacts=[],evidence=[],ac_mapping=[dict(ac_id='S1',disposition='unverified',scope='synthetic',artifact_ids=[],evidence_ids=[])],block_reasons=[dict(code='OTHER',detail='Synthetic fixture.',required_action='No action.')],failure_reasons=[],knowledge_candidates=[],publication='synthetic_sample',assignment=dict(scope='synthetic',ac_ids=['S1'],completion_criteria=['Synthetic test data.']))
    def artifact(n,path,raw):return dict(id=n,kind='document',locator=path,revision='sha256:'+sha(raw),summary='Synthetic bytes.')
    prior=handoff('SYNTHETIC-PRIOR');(origin/'prior.json').write_bytes(enc(prior))
    h=handoff('SYNTHETIC-ROOT')
    for i in range(126):
        path=f'item-{i}.txt';raw=f'Synthetic {i}\r\n'.encode();(origin/path).write_bytes(raw);h['artifacts'].append(artifact(str(i),path,raw))
    h['upstream']=[dict(role='test',task_id=prior['task_id'],attempt=1,relationship='dependency',handoff_locator='prior.json',revision='sha256:'+sha(enc(prior)))]
    (origin/'root.json').write_bytes(enc(h));first=commit()
    follow=handoff('SYNTHETIC-FOLLOWUP');follow['upstream']=[dict(role='test',task_id=h['task_id'],attempt=1,relationship='dependency',handoff_locator=f'https://github.com/synthetic/capacity/blob/{first}/root.json',revision='sha256:'+sha(enc(h)))]
    (origin/'follow.json').write_bytes(enc(follow));second=commit()
    def cli(code,mode,args):
        p=subprocess.run([sys.executable,str(P(__file__).resolve()),'--adapter',str(code),str(origin),mode]+args,capture_output=True)
        return p.returncode
    def record(name,actual,expected,extra=None):
        rows.append(dict(name=name,actual=actual,expected=expected,passed=actual==expected,**(extra or {})))
        assert actual==expected,(name,actual,expected)
    def prepare(name,commit,path,raw,version,expected,code=candidate):
        dest=root/name;args=['--repository','synthetic/capacity','--commit',commit,'--handoff-path',path,'--handoff-sha256',sha(raw),'--output',str(dest)]
        if version:args+=['--delivery-version',version]
        rc=cli(code,'prepare',args);record(name,rc,expected)
        if rc==0:return json.loads((dest/'manifest.json').read_bytes())
    legacy=prepare('prepare-default128',first,'root.json',enc(h),None,0)
    large=prepare('prepare-129',second,'follow.json',enc(follow),'1.3',0)
    prepare('prepare-legacy129',second,'follow.json',enc(follow),None,1)
    def consume(name,m,expected=0,policy_change=None,code=candidate,receipt=None,pub_version=None,bad_pin=False,scope=None):
        path=root/name;path.mkdir();mr=enc(m)
        pub=dict(schema_version=pub_version or m['schema_version'],document_type='publication_receipt',manifest_sha256=sha(mr),github_state='published',artifacts=m['artifacts'],observation='Synthetic local transport only.')
        policy=dict(schema_version=m['schema_version'],document_type='delivery_authorization',authority='Synthetic test fixture only',consumer='synthetic-test',scope='synthetic',purpose='contract-review',manifest_sha256=sha(mr),publication_receipt_sha256=sha(enc(pub)),valid_until='2099-01-01T00:00:00Z',public_safety_review='Synthetic fixture only.',publication_approval='unverified',publication_approval_evidence='Synthetic fixture is not public.',consumer_use_approval='approved',consumer_use_evidence='Synthetic test harness authorization.',allowed_representations=['original'])
        policy.update(policy_change or {});pr=enc(policy)
        for f,raw in [('manifest',mr),('publication',enc(pub)),('authorization',pr)]: (path/f).write_bytes(raw)
        args=['--manifest',str(path/'manifest'),'--publication',str(path/'publication'),'--authorization',str(path/'authorization'),'--authorization-sha256','0'*64 if bad_pin else sha(pr),'--consumer','synthetic-test','--scope',scope or 'synthetic','--purpose','contract-review','--output',str(path/'out')]
        if receipt is not None:(path/'receipt').write_bytes(enc(receipt));args+=['--verify-receipt',str(path/'receipt')]
        rc=cli(code,'consume',args);record(name,rc,expected);assert (path/'out').exists()==(expected==0)
        if expected==0:
            r=json.loads((path/'out/consumption-receipt.json').read_bytes());assert r['schema_version']==m['schema_version'] and not r['authority_granted'];assert r['artifacts']==m['artifacts']
            return r,path/'out'
    r128,o128=consume('legacy128',legacy)
    r129,o129=consume('extended129',large)
    for a in legacy['artifacts']:
        ref=a['reference'];p=P('artifacts')/ref['repository']/ref['commit']/ref['path'];assert (o128/p).read_bytes()==(o129/p).read_bytes()
    record('128-original-bytes-preserved',128,128)
    consume('old-consumer-rejects13',large,1,code=canonical)
    consume('old-consumer-accepts12',legacy,code=canonical)
    bad=copy.deepcopy(large);bad['schema_version']='1.2';consume('legacy129-reject',bad,1)
    # A 256-entry closure is prepared through the real preparation CLI.
    wide=handoff('SYNTHETIC-WIDE');wide['upstream']=copy.deepcopy(follow['upstream'])
    for i in range(127):
        path=f'wide-{i}.txt';raw=f'Synthetic extra {i}\n'.encode();(origin/path).write_bytes(raw);wide['artifacts'].append(artifact(str(i),path,raw))
    (origin/'wide.json').write_bytes(enc(wide));third=commit()
    maxm=prepare('prepare256',third,'wide.json',enc(wide),'1.3',0);assert len(maxm['artifacts'])==256
    r256,o256=consume('consume256',maxm)
    consume('receipt-fresh-recheck',maxm,receipt=r256)
    bad=copy.deepcopy(r256);bad['schema_version']='1.2';consume('mixed-consumption-version',maxm,1,receipt=bad)
    (origin/'extra.txt').write_bytes(b'Synthetic extra\n');wide['artifacts'].append(artifact('extra','extra.txt',b'Synthetic extra\n'));(origin/'overflow.json').write_bytes(enc(wide));fourth=commit()
    prepare('prepare257-reject',fourth,'overflow.json',enc(wide),'1.3',1)
    def item(path,raw,fmt='text',commit=fourth):return dict(reference=dict(object_type='git-blob',repository='synthetic/capacity',commit=commit,path=path,size=len(raw),sha256=sha(raw)),format=fmt,representation='original',public_classification='synthetic_sample',source_alias='SYNTHETIC')
    bad=copy.deepcopy(maxm);bad['artifacts'].append(item('extra.txt',b'Synthetic extra\n'));consume('consume257-reject',bad,1)
    for label,change in [('missing-upstream',lambda m:m['artifacts'].__delitem__(1)),('missing-slot',lambda m:m['slot_bindings'].pop()),('duplicate-slot',lambda m:m['slot_bindings'].append(copy.deepcopy(m['slot_bindings'][0]))),('duplicate-artifact',lambda m:m['artifacts'].append(copy.deepcopy(m['artifacts'][0]))),('wrong-handoff-type',lambda m:m['artifacts'][0].update(format='json')),('hash-mismatch',lambda m:m['artifacts'][-1]['reference'].update(sha256='0'*64)),('size-mismatch',lambda m:m['artifacts'][-1]['reference'].update(size=1)),('floating-commit',lambda m:m['artifacts'][-1]['reference'].update(commit='main'))]:
        bad=copy.deepcopy(large);change(bad);consume(label,bad,1)
    for label,kw in [('unauthorized',dict(policy_change=dict(consumer_use_approval='pending'))),('scope-mismatch',dict(scope='different')),('bad-independent-pin',dict(bad_pin=True)),('expired',dict(policy_change=dict(valid_until='2000-01-01T00:00:00Z'))),('representation',dict(policy_change=dict(allowed_representations=['edited_derivative']))),('mixed-authorization',dict(policy_change=dict(schema_version='1.2'))),('mixed-publication',dict(pub_version='1.2'))]:consume(label,large,1,**kw)
    extras={'duplicate.json':b'{"a":1,"a":2}\n','nonfinite.json':b'{"a":NaN}\n','truncate.json':b'{"a":','wrong.txt':b'{"x":1}\n','tamper.txt':b'Synthetic actual\n','single.txt':b'x'*(16*1024*1024+1)}
    for path,raw in extras.items():(origin/path).write_bytes(raw)
    for i in range(4):(origin/f'big-{i}.txt').write_bytes(b'x'*(16*1024*1024))
    fifth=commit()
    for path,raw in extras.items():
        bad=copy.deepcopy(large);a=item(path,raw,'json' if path.endswith('.json') else 'text',fifth)
        if path=='tamper.txt':a['reference']['sha256']=sha(b'Synthetic forged\n')
        bad['artifacts'].append(a);consume('malicious-'+path,bad,1)
    base=dict(schema_version='1.3',document_type='artifact_delivery',artifacts=[item(f'big-{i}.txt',b'x'*(16*1024*1024),commit=fifth) for i in range(4)],knowledge_bindings=[],slot_bindings=[],candidate_bindings=[])
    consume('exact64MiB',base)
    base['artifacts'].append(item('extra.txt',b'Synthetic extra\n'));consume('over64MiB',base,1)
    # Legacy 1.0 and 1.1 use their historical reference shape.
    for version in ['1.0','1.1']:
        m=dict(schema_version=version,document_type='artifact_delivery',artifacts=[item('extra.txt',b'Synthetic extra\n')]);m['artifacts'][0]['reference'].pop('object_type')
        if version=='1.1':m['knowledge_bindings']=[]
        consume('compatibility-'+version,m)
    # Independent candidate/tree closure, using real nested Git tree bytes.
    (origin/'src/nested').mkdir(parents=True)
    (origin/'src/a.txt').write_bytes(b'Synthetic tree source\r\n')
    (origin/'src/nested/b.bin').write_bytes(b'\x00\xffSynthetic binary')
    source_commit=commit()
    source_url=f'https://github.com/synthetic/capacity/tree/{source_commit}/src'
    candidates=dict(document_type='knowledge_candidates',publication_status='pending_manager_review',candidates=[dict(id='SYNTHETIC-C1',domain='synthetic',summary='Synthetic candidate.',evidence='Synthetic evidence.',source=source_url,scope='Synthetic only.')])
    candraw=enc(candidates);(origin/'candidates.json').write_bytes(candraw)
    producer=handoff('SYNTHETIC-CANDIDATE-PRODUCER')
    ca=artifact('candidate','candidates.json',candraw);ca['kind']='knowledge';producer['artifacts']=[ca]
    producer['evidence']=[dict(id='ev',claim='Synthetic candidate.',artifact_ids=['candidate'],locator='candidates.json',observation='Synthetic only.')]
    producer['knowledge_candidates']=[dict(id='SYNTHETIC-C1',domain='synthetic',summary='Synthetic.',evidence_ids=['ev'],raw_locator='candidates.json',publication_safety='safe_synthetic')]
    (origin/'producer.json').write_bytes(enc(producer));producer_commit=commit()
    cm=prepare('prepare-candidate-tree',producer_commit,'producer.json',enc(producer),'1.3',0)
    cr,co=consume('candidate-tree-positive',cm)
    for rel in ['a.txt','nested/b.bin']:
        assert (co/'artifacts/synthetic/capacity'/source_commit/'src'/rel).read_bytes()==(origin/'src'/rel).read_bytes()
    for label in ['candidate-missing','candidate-duplicate','candidate-profile','candidate-ids','source-slot-missing','tree-file-missing','tree-file-size','tree-file-hash','tree-file-mode','tree-root-oid','tree-child-missing']:
        bad=copy.deepcopy(cm);binding=bad['candidate_bindings'][0];snap=binding['sources'][0]['target']['snapshot']
        if label=='candidate-missing':bad['candidate_bindings']=[]
        elif label=='candidate-duplicate':bad['candidate_bindings'].append(copy.deepcopy(binding))
        elif label=='candidate-profile':binding['profile']='knowledge-candidates-v2'
        elif label=='candidate-ids':binding['candidate_ids']=['SYNTHETIC-WRONG']
        elif label=='source-slot-missing':binding['sources']=[]
        elif label=='tree-file-missing':snap['files'].pop()
        elif label=='tree-file-size':snap['files'][0]['size']+=1
        elif label=='tree-file-hash':snap['files'][0]['sha256']='0'*64
        elif label=='tree-file-mode':snap['files'][0]['mode']='100755'
        elif label=='tree-root-oid':snap['oid']='0'*40
        elif label=='tree-child-missing':snap['trees']=[]
        consume(label,bad,1)
    bad=copy.deepcopy(cm)
    for a in bad['artifacts']:a['representation']='edited_derivative'
    consume('tree-original-approval-required',bad,1,policy_change=dict(allowed_representations=['edited_derivative']))
    # Outer pins and slot format also agree; candidate cannot be generic JSON.
    bad=copy.deepcopy(cm)
    for a in bad['artifacts']:
        if a['format']=='knowledge-candidates-v1':a['format']='json'
    for slot in bad['slot_bindings']:
        if slot['target']['format']=='knowledge-candidates-v1':slot['target']['format']='json'
    consume('candidate-type-downgrade',bad,1)
    # Independent exact schema comparison, including all other unchanged bounds.
    for name in ['artifact-delivery','publication-receipt','consumption-receipt','delivery-authorization']:
        old=json.loads((canonical/f'contracts/{name}-v1.2.schema.json').read_bytes())
        new=json.loads((candidate/f'contracts/{name}-v1.3.schema.json').read_bytes())
        new['$id']=old['$id'];new['properties']['schema_version']['const']='1.2'
        if 'artifacts' in new['properties']:
            assert new['properties']['artifacts']['maxItems']==256
            new['properties']['artifacts']['maxItems']=128
        record('exact-schema-delta-'+name,new==old,True)
P(result).write_bytes(enc(dict(observed_at=start,completed_at=datetime.now(timezone.utc).isoformat(),duration_seconds=round(time.monotonic()-t0,3),transport='Fresh local Git fetch adapter only; actual CLI validators unchanged; no network synthetic fixture.',cases=rows)))
print(json.dumps({'cases':len(rows),'passed':all(x['passed'] for x in rows),'seconds':round(time.monotonic()-t0,3)}))
