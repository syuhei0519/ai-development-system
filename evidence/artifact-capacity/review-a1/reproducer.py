#!/usr/bin/env python3
"""Independent Review adversarial CLI fixture. No Test/Implementation helpers.
python reproducer.py CANDIDATE CANONICAL RESULT
Only GitSource.repository is adapted to a temporary synthetic local Git origin;
actual Git object/path reads, preparation, Consumer main and schemas are unchanged.
No real bundle, credentials or network is used by these cases.
"""
import copy, hashlib, json, pathlib, subprocess, sys, tempfile
from datetime import datetime, timezone
P=pathlib.Path
enc=lambda x:(json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode()
sha=lambda x:hashlib.sha256(x).hexdigest()
if len(sys.argv)>1 and sys.argv[1]=='--cli':
    code,origin,mode=sys.argv[2:5];sys.path.insert(0,code+'/scripts')
    import consume_delivery as d
    def repository(self,ref):
        d.check_reference(ref)
        d.require(self.git(origin,'cat-file','-t',ref['commit']).strip()==b'commit','fixed local commit')
        return P(origin)
    d.GitSource.repository=repository
    sys.argv=[mode]+sys.argv[5:]
    if mode=='prepare':
        import prepare_crossref_bundle as p
        p.main()
    else:sys.exit(d.main())
    sys.exit(0)
candidate,canonical,result=map(P,sys.argv[1:]);rows=[]
started=datetime.now(timezone.utc).isoformat()
with tempfile.TemporaryDirectory(prefix='review-capacity-') as tmp:
    root=P(tmp);origin=root/'origin';origin.mkdir()
    def git(*a):return subprocess.check_output(['git','-C',str(origin),*a],stderr=subprocess.DEVNULL).decode().strip()
    git('init');git('config','user.name','Synthetic Review');git('config','user.email','review@example.invalid')
    def commit():git('add','.');git('commit','-m','Synthetic review fixture');return git('rev-parse','HEAD')
    def h(name):return dict(schema_version='2.0',issue=dict(id='synthetic',source='synthetic',title='Synthetic review',acceptance_criteria=[dict(id='S1',verbatim='Synthetic fixture only.',source='synthetic')]),role='review',task_id=name,attempt=1,upstream=[],system_status='completed',status='blocked',summary='Synthetic fixture.',artifacts=[],evidence=[],ac_mapping=[dict(ac_id='S1',disposition='unverified',scope='synthetic',artifact_ids=[],evidence_ids=[])],block_reasons=[dict(code='OTHER',detail='Synthetic fixture.',required_action='None.')],failure_reasons=[],knowledge_candidates=[],publication='synthetic_sample',assignment=dict(scope='synthetic',ac_ids=['S1'],completion_criteria=['Synthetic.']))
    prior=h('SYNTHETIC-PRIOR')
    for i in range(127):
        name=f'f{i}.txt';raw=f'Synthetic {i}\r\n'.encode();(origin/name).write_bytes(raw)
        prior['artifacts'].append(dict(id=f'f{i}',kind='document',locator=name,revision='sha256:'+sha(raw),summary='Synthetic.'))
    (origin/'prior.json').write_bytes(enc(prior));c1=commit()
    follow=h('SYNTHETIC-FOLLOW');follow['upstream']=[dict(role='review',task_id=prior['task_id'],attempt=1,relationship='dependency',handoff_locator=f'https://github.com/synthetic/review/blob/{c1}/prior.json',revision='sha256:'+sha(enc(prior)))]
    (origin/'follow.json').write_bytes(enc(follow));c2=commit()
    wide=copy.deepcopy(follow);wide['task_id']='SYNTHETIC-WIDE';wide['artifacts']=copy.deepcopy(prior['artifacts'])
    (origin/'wide.json').write_bytes(enc(wide))
    evil={'partial.data':b'{"publication_status":"pending_manager_review"}', 'candidate.data':enc(dict(document_type='knowledge_candidates',publication_status='pending_manager_review',candidates=[])), 'identity.data':b'{"task_id":"SYNTHETIC"}', 'nan.data':b'{"x":NaN}', 'dupe.data':b'{"x":1,"\\u0078":2}', 'bom.data':b'\xef\xbb\xbf{}', 'null.data':b'null', 'cut.data':b'{"x":'}
    for n,b in evil.items():(origin/n).write_bytes(b)
    (origin/'link.txt').symlink_to('f0.txt');c3=commit()
    def check(name,ok):
        rows.append(dict(name=name,passed=bool(ok)));assert ok,name
    def cli(code,mode,args):return subprocess.run([sys.executable,str(P(__file__).resolve()),'--cli',str(code),str(origin),mode]+args,capture_output=True).returncode
    def prep(name,c,path,raw,version=None,expected=0,code=candidate):
        dest=root/name;a=['--repository','synthetic/review','--commit',c,'--handoff-path',path,'--handoff-sha256',sha(raw),'--output',str(dest)]
        if version:a+=['--delivery-version',version]
        rc=cli(code,'prepare',a);check(name,rc==expected and dest.exists()==(expected==0))
        if rc==0:return json.loads((dest/'manifest.json').read_bytes())
    old=prep('prepare-default128',c1,'prior.json',enc(prior))
    m=prep('prepare129',c2,'follow.json',enc(follow),'1.3')
    full=prep('prepare256',c3,'wide.json',enc(wide),'1.3')
    prep('prepare129-legacy-rejected',c2,'follow.json',enc(follow),expected=1)
    prep('prepare-unknown-rejected',c1,'prior.json',enc(prior),'1.4',2)
    def item(path,raw,fmt='text'):
        return dict(reference=dict(object_type='git-blob',repository='synthetic/review',commit=c3,path=path,size=len(raw),sha256=sha(raw)),format=fmt,representation='original',public_classification='synthetic_sample',source_alias='SYNTHETIC')
    def run(name,manifest,expected=1,policy_change=None,pub_change=None,receipt=None,code=candidate,output_symlink=False):
        d=root/name;d.mkdir();mr=enc(manifest)
        pub=dict(schema_version=manifest['schema_version'],document_type='publication_receipt',manifest_sha256=sha(mr),github_state='published',artifacts=copy.deepcopy(manifest['artifacts']),observation='Synthetic fixture.')
        if pub_change:pub_change(pub)
        auth=dict(schema_version=manifest['schema_version'],document_type='delivery_authorization',authority='Synthetic fixture',consumer='synthetic',scope='synthetic',purpose='contract-review',manifest_sha256=sha(mr),publication_receipt_sha256=sha(enc(pub)),valid_until='2099-01-01T00:00:00Z',public_safety_review='Synthetic.',publication_approval='unverified',publication_approval_evidence='Synthetic.',consumer_use_approval='approved',consumer_use_evidence='Synthetic.',allowed_representations=['original'])
        if policy_change:auth.update(policy_change)
        for n,b in [('manifest',mr),('publication',enc(pub)),('authorization',enc(auth))]:(d/n).write_bytes(b)
        out=d/'out'
        if output_symlink:out.symlink_to(d/'missing')
        args=['--manifest',str(d/'manifest'),'--publication',str(d/'publication'),'--authorization',str(d/'authorization'),'--authorization-sha256',sha(enc(auth)),'--consumer','synthetic','--scope','synthetic','--purpose','contract-review','--output',str(out)]
        if receipt is not None:(d/'receipt').write_bytes(enc(receipt));args+=['--verify-receipt',str(d/'receipt')]
        rc=cli(code,'consume',args);check(name,rc==expected and out.exists()==(expected==0))
        if rc==0:return json.loads((out/'consumption-receipt.json').read_bytes()),out
    r128,o128=run('consume128',old,0)
    r129,o129=run('consume129',m,0)
    check('original128-byte-equality',all((o128/'artifacts'/a['reference']['repository']/a['reference']['commit']/a['reference']['path']).read_bytes()==(o129/'artifacts'/a['reference']['repository']/a['reference']['commit']/a['reference']['path']).read_bytes() for a in old['artifacts']))
    r256,_=run('consume256',full,0);run('receipt-fresh',full,0,receipt=r256)
    run('old-consumer-rejects13',m,code=canonical);run('old-consumer-accepts12',old,0,code=canonical)
    run('receipt12-cannot-authorize13',m,receipt=r128)
    bad=copy.deepcopy(r129);bad['authority_granted']=True;run('receipt-cannot-grant-authority',m,receipt=bad)
    run('dangling-output-symlink',m,output_symlink=True)
    for version in ['1.0','1.1','1.2','1.4']:
        run('authorization-version-'+version,m,policy_change={'schema_version':version})
        run('publication-version-'+version,m,pub_change=lambda p,v=version:p.update(schema_version=v))
    for label,change in [('manifest-downgrade',lambda x:x.update(schema_version='1.2')),('257',lambda x:x['artifacts'].append(item('partial.data',evil['partial.data'],'json'))),('missing-closure',lambda x:x['artifacts'].pop(1)),('missing-slot',lambda x:x['slot_bindings'].pop()),('extra-slot',lambda x:x['slot_bindings'].append(copy.deepcopy(x['slot_bindings'][0]))),('duplicate-blob',lambda x:x['artifacts'].__setitem__(-1,copy.deepcopy(x['artifacts'][0]))),('wrong-owner-size',lambda x:x['slot_bindings'][0]['owner'].update(size=1)),('wrong-target-type',lambda x:x['slot_bindings'][0]['target'].update(format='json')),('tamper',lambda x:x['artifacts'][-1]['reference'].update(sha256='0'*64)),('wrong-handoff-format',lambda x:x['artifacts'][0].update(format='json'))]:
        bad=copy.deepcopy(full);change(bad);run(label,bad)
    for n,b in evil.items():
        bad=copy.deepcopy(m);bad['artifacts'].append(item(n,b,'json' if n in ('partial.data','candidate.data','identity.data') else 'text'));run('type-'+n,bad)
    bad=copy.deepcopy(m);bad['artifacts'].append(item('link.txt',b'Synthetic 0\r\n'));run('symlink-blob',bad)
    for k,v in [('consumer_use_approval','pending'),('scope','other'),('purpose','implementation'),('allowed_representations',['edited_derivative']),('valid_until','2000-01-01T00:00:00Z')]:run('auth-'+k,m,policy_change={k:v})
    run('publication-artifact-order',m,pub_change=lambda p:p['artifacts'].reverse())
    for name in ['artifact-delivery','publication-receipt','consumption-receipt','delivery-authorization']:
        a=json.loads((canonical/f'contracts/{name}-v1.2.schema.json').read_bytes());b=json.loads((candidate/f'contracts/{name}-v1.3.schema.json').read_bytes())
        b['$id']=a['$id'];b['properties']['schema_version']['const']='1.2'
        if 'artifacts' in b['properties']:check(name+'-256',b['properties']['artifacts']['maxItems']==256);b['properties']['artifacts']['maxItems']=128
        check(name+'-exact-delta',a==b)
        for v in ['','-v1.1','-v1.2']:check(name+v+'-unchanged',(canonical/f'contracts/{name}{v}.schema.json').read_bytes()==(candidate/f'contracts/{name}{v}.schema.json').read_bytes())
P(result).write_bytes(enc(dict(observed_at=started,completed_at=datetime.now(timezone.utc).isoformat(),cases=rows,passed=all(r['passed'] for r in rows),transport='Synthetic local repository adapter; no network. Incoming public delivery verified separately.')))
print(json.dumps({'cases':len(rows),'passed':all(r['passed'] for r in rows)}))
