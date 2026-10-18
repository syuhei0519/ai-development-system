"""Synthetic v1.2 transport tests. No application execution or acceptance claims."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts.consume_delivery import (
    ROOT, GitSource, consume, digest, parse, schema, reference_key,
    artifact_slot, upstream_slot, verify_handoffs, write_bundle,
)
from scripts.prepare_knowledge_fixture import fixture_manifest


def encode(data):
    return (json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode()


class Source:
    def __init__(self, blobs):
        self.blobs = blobs
        self.calls = []

    def read(self, ref):
        self.calls.append(reference_key(ref))
        return self.blobs[reference_key(ref)]


class Bundle:
    def __init__(self):
        self.manifest = dict(schema_version='1.3', document_type='artifact_delivery',
                             artifacts=[], knowledge_bindings=[], slot_bindings=[])
        self.blobs = {}

    def add(self, raw, path, fmt='text', repo='synthetic/one', commit='a'*40):
        ref = dict(repository=repo, commit=commit, size=len(raw), sha256=digest(raw),
                   object_type='git-blob')
        if fmt == 'git-commit-object':
            ref['object_type'] = fmt
            ref['commit'] = hashlib.sha1(b'commit '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
        else:
            ref['path'] = path
        item = dict(reference=ref, format=fmt, representation='original',
                    public_classification='synthetic_sample', source_alias='SYNTHETIC-CROSSREF')
        self.manifest['artifacts'].append(item)
        self.blobs[reference_key(ref)] = raw
        return item

    def slot(self, owner, slot, locator, revision, target):
        binding = dict(owner=deepcopy(owner['reference']), slot=slot, locator=locator,
                       revision=revision, target={k:deepcopy(target[k]) for k in ('reference','format')})
        self.manifest['slot_bindings'].append(binding)
        return binding

    def records(self):
        raw = encode(self.manifest)
        pub = dict(schema_version=self.manifest['schema_version'], document_type='publication_receipt',
                   manifest_sha256=digest(raw), github_state='published',
                   artifacts=deepcopy(self.manifest['artifacts']), observation='Synthetic fixture only.')
        policy = parse((ROOT/'examples/delivery/current.authorization.json').read_bytes())
        policy.update(schema_version=self.manifest['schema_version'], manifest_sha256=digest(raw),
                      publication_receipt_sha256=digest(encode(pub)), allowed_representations=['original'])
        return raw, pub, policy

    def consume(self, policy_changes=None, **kwargs):
        raw, pub, policy = self.records()
        policy.update(policy_changes or {})
        params = dict(manifest_raw=raw, publication_raw=encode(pub), policy_raw=encode(policy),
                      policy_sha256=digest(encode(policy)), consumer=policy['consumer'],
                      scope=policy['scope'], purpose=policy['purpose'], source=Source(self.blobs),
                      now=datetime(2026,10,11,tzinfo=timezone.utc))
        params.update(kwargs)
        return consume(**params)


def url(item):
    r = item['reference']
    if item['format'] == 'git-commit-object':
        return f"https://github.com/{r['repository']}/commit/{r['commit']}"
    return f"https://github.com/{r['repository']}/blob/{r['commit']}/{r['path']}"


def handoff():
    return parse((ROOT/'examples/research-to-test/research.handoff.json').read_bytes())


def fixture():
    b = Bundle()
    text = b.add(b'Synthetic cross repository evidence.\n','evidence.txt', repo='synthetic/two',commit='b'*40)
    raw_commit = b'tree '+b'c'*40+b'\nauthor Synthetic <synthetic@example.invalid> 0 +0000\ncommitter Synthetic <synthetic@example.invalid> 0 +0000\n\nSynthetic commit\n'
    commit = b.add(raw_commit,None,'git-commit-object',repo='synthetic/two')
    previous = handoff()
    previous['artifacts'][0].update(locator=url(text),revision='sha256:'+text['reference']['sha256'])
    prior = b.add(encode(previous),'prior.json','handoff-v2',commit='d'*40)
    current = deepcopy(previous)
    current.update(task_id='SYNTHETIC-CROSSREF-CURRENT',attempt=2)
    current['upstream']=[dict(role=previous['role'],task_id=previous['task_id'],attempt=1,
                             relationship='retry_of',handoff_locator=url(prior),
                             revision='sha256:'+prior['reference']['sha256'])]
    current['artifacts'].append(dict(id='SYNTHETIC-COMMIT',kind='commit',
                                    locator=url(commit),revision=commit['reference']['commit'],
                                    summary='Commit existence only.'))
    owner = b.add(encode(current),'handoff.json','handoff-v2')
    b.slot(prior,artifact_slot(previous['artifacts'][0]),url(text),'sha256:'+text['reference']['sha256'],text)
    b.slot(owner,artifact_slot(current['artifacts'][0]),url(text),'sha256:'+text['reference']['sha256'],text)
    b.slot(owner,artifact_slot(current['artifacts'][1]),url(commit),commit['reference']['commit'],commit)
    b.slot(owner,upstream_slot(current['upstream'][0]),url(prior),'sha256:'+prior['reference']['sha256'],prior)
    return b


class CrossrefTests(unittest.TestCase):
    def setUp(self):
        self.b = fixture()

    def test_crossrepo_blob_crosscommit_handoff_commit_output_and_recheck(self):
        receipt, blobs = self.b.consume()
        self.assertEqual(blobs,self.b.blobs)
        self.assertFalse(receipt['authority_granted'])
        self.assertEqual(receipt['slot_bindings'], self.b.manifest['slot_bindings'])
        self.assertEqual(self.b.consume(receipt_raw=encode(receipt))[0],receipt)
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'out'
            write_bundle(output,receipt,blobs)
            for (repo,commit,path),raw in blobs.items():
                dest=output/('artifacts' if path else 'git-commit-objects')/repo/commit/(path or 'commit.raw')
                self.assertEqual(dest.read_bytes(),raw)

    def test_slot_missing_extra_duplicate_conflicting_and_unknown(self):
        for operation in ('missing','extra','duplicate','conflict','unknown'):
            b=deepcopy(self.b);slots=b.manifest['slot_bindings']
            if operation=='missing':slots.pop()
            elif operation=='unknown':slots[-1]['slot']['unknown']='x'
            else:
                extra=deepcopy(slots[-1])
                if operation=='extra':extra['slot']['task_id']='SYNTHETIC-MISSING'
                if operation=='conflict':extra['target']=deepcopy(slots[0]['target'])
                slots.append(extra)
            with self.subTest(operation=operation),self.assertRaises(ValueError):b.consume()

    def test_owner_pin_and_structural_identity(self):
        for field,value in [('size',0),('sha256','0'*64),('commit','f'*40),('path','other.json')]:
            b=deepcopy(self.b);b.manifest['slot_bindings'][0]['owner'][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):b.consume()
        b=deepcopy(self.b);b.manifest['slot_bindings'][0]['slot']['id']='SYNTHETIC-MISSING'
        with self.assertRaises(ValueError):b.consume()

    def test_target_size_hash_repository_oid_path_and_format(self):
        for field,value in [('size',1),('sha256','0'*64),('repository','synthetic/other'),
                            ('commit','e'*40),('path','other.txt'),('object_type','git-commit-object')]:
            b=deepcopy(self.b);b.manifest['slot_bindings'][0]['target']['reference'][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):b.consume()
        b=deepcopy(self.b);b.manifest['slot_bindings'][0]['target']['format']='json'
        with self.assertRaises(ValueError):b.consume()

    def mutate_handoff(self,b,index,change):
        item=b.manifest['artifacts'][index]
        old=deepcopy(item['reference']);key=reference_key(old)
        data=parse(b.blobs[key]);change(data)
        raw=encode(data);b.blobs[key]=raw
        item['reference'].update(size=len(raw),sha256=digest(raw))
        # Pin changed owner only; caller must explicitly adjust in-document links.
        for binding in b.manifest['slot_bindings']:
            if binding['owner']==old:binding['owner']=deepcopy(item['reference'])
        return data

    def test_matching_outer_and_inner_malicious_urls_still_rejected(self):
        original=url(self.b.manifest['artifacts'][0])
        for locator in [original+'?x=1',original+'#x',original.replace('https:','http:'),
                        original.replace('github.com','github.com.evil'),
                        original.replace('/blob/'+'b'*40,'/blob/main'),
                        original.replace('/evidence.txt','/../evidence.txt'),
                        original.replace('/evidence.txt','/%65vidence.txt'),
                        original.replace('github.com/','user@github.com/'),
                        original.replace('synthetic/two','synthetic/one'),
                        original.replace('/blob/','/raw/')]:
            b=deepcopy(self.b)
            self.mutate_handoff(b,3,lambda d:d['artifacts'][0].update(locator=locator))
            b.manifest['slot_bindings'][1]['locator']=locator
            with self.subTest(locator=locator),self.assertRaises(ValueError):b.consume()

    def test_original_locator_revision_cannot_be_overridden(self):
        for field in ('locator','revision'):
            b=deepcopy(self.b);b.manifest['slot_bindings'][0][field]='SYNTHETIC-REPLACEMENT'
            with self.subTest(field=field),self.assertRaises(ValueError):b.consume()

    def test_blob_revision_mismatch_even_if_outer_matches(self):
        b=deepcopy(self.b)
        revision='sha256:'+'0'*64
        self.mutate_handoff(b,3,lambda d:d['artifacts'][0].update(revision=revision))
        b.manifest['slot_bindings'][1]['revision']=revision
        with self.assertRaises(ValueError):b.consume()

    def test_missing_dependency_and_duplicate_identity(self):
        b=deepcopy(self.b);b.manifest['artifacts'].pop(0)
        with self.assertRaises(ValueError):b.consume()
        b=deepcopy(self.b);duplicate=deepcopy(b.manifest['artifacts'][-1])
        duplicate['reference']['path']='copied.json'
        b.manifest['artifacts'].append(duplicate)
        b.blobs[reference_key(duplicate['reference'])]=b.blobs[reference_key(self.b.manifest['artifacts'][-1]['reference'])]
        with self.assertRaises(ValueError):b.consume()

    def test_all_declared_bytes_fetched_before_success(self):
        source=Source(self.b.blobs)
        self.b.consume(source=source)
        self.assertEqual(set(source.calls),set(self.b.blobs))
        b=deepcopy(self.b)
        b.add(b'Unavailable dependency\n','extra.txt')
        with self.assertRaises(KeyError):b.consume(source=Source(self.b.blobs))

    def test_commit_raw_size_sha_oid_and_no_blob_disguise(self):
        for field,value in [('size',1),('sha256','0'*64),('commit','0'*40),('object_type','git-blob')]:
            b=deepcopy(self.b)
            item=b.manifest['artifacts'][1];oldkey=reference_key(item['reference'])
            item['reference'][field]=value
            b.blobs[reference_key(item['reference'])]=b.blobs[oldkey]
            b.manifest['slot_bindings'][2]['target']['reference']=deepcopy(item['reference'])
            with self.subTest(field=field),self.assertRaises(ValueError):b.consume()
        for fmt in ('text','json','handoff-v2'):
            b=deepcopy(self.b);b.manifest['artifacts'][1]['format']=fmt
            with self.subTest(fmt=fmt),self.assertRaises(ValueError):b.consume()

    def test_commit_url_and_revision_and_kind(self):
        for field,value in [('locator',url(self.b.manifest['artifacts'][1])+'/'),
                            ('revision','sha256:'+self.b.manifest['artifacts'][1]['reference']['sha256'])]:
            b=deepcopy(self.b)
            self.mutate_handoff(b,3,lambda d:d['artifacts'][1].update({field:value}))
            b.manifest['slot_bindings'][2][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):b.consume()
        b=deepcopy(self.b)
        self.mutate_handoff(b,3,lambda d:d['artifacts'][1].update(kind='document'))
        with self.assertRaises(ValueError):b.consume()

    def test_private_and_json_downgrade(self):
        b=deepcopy(self.b);self.mutate_handoff(b,3,lambda d:d.update(publication='private_only'))
        with self.assertRaises(ValueError):b.consume()
        for fmt in ('json','text','knowledge-input-v1'):
            b=deepcopy(self.b);b.manifest['artifacts'][-1]['format']=fmt
            with self.subTest(fmt=fmt),self.assertRaises(ValueError):b.consume()
        for raw,fmt,path in [(b'{"publication":"private_only"}','json','private'),
                              (b'{"x":1,"x":2}','json','duplicate'),
                              (b'{"x":NaN}','json','nan'),(b'\xef\xbb\xbf{}','json','bom'),
                              (b'{"task_id":"SYNTHETIC"}','json','reserved'),
                              (b'{"raw_findings":[]}','json','knowledge'),
                              (b'{"document_type":"knowledge_candidates","candidates":[]}',
                               'json','unknown-knowledge-candidates'),
                              (b'{"x":','text','truncated')]:
            b=deepcopy(self.b);b.add(raw,path,fmt)
            with self.subTest(path=path),self.assertRaises(ValueError):b.consume()

    def test_retry_role_task_attempt_and_issue(self):
        for field,value in [('role','test'),('task_id','SYNTHETIC-WRONG'),('attempt',2)]:
            b=deepcopy(self.b)
            d=self.mutate_handoff(b,3,lambda d:d['upstream'][0].update({field:value}))
            b.manifest['slot_bindings'][-1]['slot']=upstream_slot(d['upstream'][0])
            with self.subTest(field=field),self.assertRaises(ValueError):b.consume()
        b=deepcopy(self.b)
        self.mutate_handoff(b,3,lambda d:d['issue'].update(title='Synthetic other Issue'))
        with self.assertRaises(ValueError):b.consume()

    def test_approval_expiry_scope_pin_and_representation(self):
        for change in [dict(consumer_use_approval='pending'),dict(valid_until='2020-01-01T00:00:00Z'),
                       dict(allowed_representations=['edited_derivative']),dict(publication_approval='pending')]:
            with self.subTest(change=change),self.assertRaises(ValueError):self.b.consume(change)
        for kw in [dict(consumer='OTHER'),dict(scope='OTHER'),dict(purpose='OTHER'),
                   dict(policy_sha256='0'*64)]:
            with self.subTest(kw=kw),self.assertRaises(ValueError):self.b.consume(**kw)

    def test_version_mixing_downgrade_and_old_contracts(self):
        raw,pub,policy=self.b.records()
        for version in ('1.0','1.1'):
            for name,doc in [('artifact-delivery',self.b.manifest),('publication-receipt',pub),
                             ('consumption-receipt',self.b.consume()[0])]:
                candidate=deepcopy(doc);candidate['schema_version']=version
                with self.subTest(name=name,version=version),self.assertRaises(ValueError):schema(name,candidate)
            with self.assertRaises(ValueError):self.b.consume(dict(schema_version=version))
            pub['schema_version']=version
            with self.assertRaises(ValueError):
                self.b.consume(dict(publication_receipt_sha256=digest(encode(pub))),publication_raw=encode(pub))
            with self.assertRaises(ValueError):
                verify_handoffs(self.b.manifest['artifacts'],self.b.blobs,version,[])

    def test_receipt_recheck_requires_current_approval_fresh_bytes_and_exact_slots(self):
        receipt,_=self.b.consume()
        b=deepcopy(self.b);key=next(iter(b.blobs));b.blobs[key]=b'changed\n'
        with self.assertRaises(ValueError):b.consume(receipt_raw=encode(receipt))
        with self.assertRaises(ValueError):self.b.consume(dict(consumer_use_approval='pending'),receipt_raw=encode(receipt))
        receipt['slot_bindings'].pop()
        with self.assertRaises(ValueError):self.b.consume(receipt_raw=encode(receipt))

    def test_relative_snapshot_not_redirected_to_identical_copy(self):
        b=Bundle();text=b.add(b'Synthetic relative bytes\n','evidence.txt')
        h=handoff();h['artifacts'][0].update(locator='evidence.txt',revision='sha256:'+text['reference']['sha256'])
        owner=b.add(encode(h),'handoff.json','handoff-v2')
        binding=b.slot(owner,artifact_slot(h['artifacts'][0]),'evidence.txt',h['artifacts'][0]['revision'],text)
        b.consume()
        copy=b.add(b.blobs[reference_key(text['reference'])],'evidence.txt',repo='synthetic/other')
        binding['target']={k:deepcopy(copy[k]) for k in ('reference','format')}
        with self.assertRaises(ValueError):b.consume()


def knowledge_fixture():
    legacy=fixture_manifest('synthetic/knowledge','a'*40)
    b=Bundle();items={}
    for a in legacy['artifacts']:
        path=a['reference']['path']
        items[path]=b.add((ROOT/path).read_bytes(),path,a['format'],repo='synthetic/knowledge')
    # Cross-repo fixed source; only synthetic owner bytes are edited here.
    source=items['examples/knowledge-delivery/source-1.md']
    oldkey=reference_key(source['reference'])
    source['reference'].update(repository='synthetic/sources',commit='b'*40)
    b.blobs[reference_key(source['reference'])]=b.blobs.pop(oldkey)
    for item in items.values():
        if not item['format'].startswith('knowledge-'):continue
        key=reference_key(item['reference']);data=parse(b.blobs[key])
        for finding in data.get('raw_findings',[]):
            for src in finding['sources']:
                if src['locator']=='source-1.md':src['locator']=url(source)
        for article in data['knowledge_references']:
            for src in article['sources']:
                if src['locator']=='source-1.md':src['locator']=url(source)
        raw=encode(data);b.blobs[key]=raw;item['reference'].update(size=len(raw),sha256=digest(raw))
        slots=[]
        for finding in data.get('raw_findings',[]):
            for i,src in enumerate(finding['sources']):
                slots.append((dict(kind='finding-source',finding_id=finding['id'],source_index=i),src))
        for article in data['knowledge_references']:
            slots.append((dict(kind='knowledge-reference',id=article['id']),article))
            for i,src in enumerate(article['sources']):
                slots.append((dict(kind='knowledge-source',id=article['id'],source_index=i),src))
        for art in data.get('artifacts',[]):slots.append((artifact_slot(art),art))
        for slot,src in slots:
            target=source if src['locator']==url(source) else items['examples/knowledge-delivery/'+src['locator']]
            b.slot(item,slot,src['locator'],src['revision'],target)
    b.manifest['knowledge_bindings']=[dict(input=items['examples/knowledge-delivery/input.json']['reference'],
                                         handoff=items['examples/knowledge-delivery/handoff.json']['reference'])]
    return b


class KnowledgeCrossrefTests(unittest.TestCase):
    def test_crossrepo_finding_article_context_sources(self):
        b=knowledge_fixture();b.consume()
        for index in range(len(b.manifest['slot_bindings'])):
            changed=deepcopy(b);changed.manifest['slot_bindings'].pop(index)
            with self.subTest(slot=index),self.assertRaises(ValueError):changed.consume()

    def test_unknown_source_position_and_pair_pin(self):
        b=knowledge_fixture()
        slot=next(s for s in b.manifest['slot_bindings'] if s['slot']['kind']=='finding-source')
        slot['slot']['source_index']=99
        with self.assertRaises(ValueError):b.consume()
        b=knowledge_fixture();b.manifest['knowledge_bindings'][0]['input']['sha256']='0'*64
        with self.assertRaises(ValueError):b.consume()


class CommitGitTests(unittest.TestCase):
    def test_real_git_commit_bytes_type_oid_and_forbidden_modes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);repo=root/'origin';repo.mkdir()
            def git(*args):
                return subprocess.check_output(['git','-C',str(repo),*args],stderr=subprocess.DEVNULL)
            git('init');git('config','user.name','Synthetic');git('config','user.email','synthetic@example.invalid')
            (repo/'evidence.txt').write_bytes(b'Synthetic data\r\n')
            (repo/'link').symlink_to('evidence.txt')
            git('add','.');git('commit','-m','Synthetic fixture')
            sha=git('rev-parse','HEAD').decode().strip()
            git('update-index','--add','--cacheinfo',f'160000,{sha},module');git('commit','-m','Synthetic gitlink')
            sha=git('rev-parse','HEAD').decode().strip();raw=git('cat-file','commit',sha)
            cache=root/'cache';cache.mkdir();source=GitSource(cache);original=source.git
            def local(directory,*args):
                if args[0]=='fetch':
                    return subprocess.check_output(['git','-C',str(directory),'fetch',str(repo),args[-1]],stderr=subprocess.DEVNULL)
                return original(directory,*args)
            source.git=local
            ref=dict(object_type='git-commit-object',repository='synthetic/repo',commit=sha,size=len(raw),sha256=digest(raw))
            self.assertEqual(source.read(ref),raw)
            for field,value in [('size',1),('sha256','0'*64)]:
                with self.subTest(field=field),self.assertRaises(ValueError):source.read(dict(ref,**{field:value}))
            blob=git('rev-parse','HEAD:evidence.txt').decode().strip()
            with self.assertRaises(ValueError):source.read(dict(ref,commit=blob))
            for path in ('link','link/child','module','module/child'):
                with self.subTest(path=path),self.assertRaises(ValueError):
                    source.read(dict(ref,object_type='git-blob',path=path))

    def test_transport_has_no_redirect_or_ambient_credentials(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=GitSource(tmp)
            with patch('scripts.consume_delivery.subprocess.run') as run:
                run.return_value.returncode=0;run.return_value.stdout=b''
                source.git(tmp,'status')
                args,kw=run.call_args
                self.assertIn('http.followRedirects=false',args[0])
                self.assertEqual(kw['env']['GIT_ALLOW_PROTOCOL'],'https')
                self.assertEqual(kw['env']['GIT_CONFIG_GLOBAL'],'/dev/null')
                self.assertNotIn('GITHUB_TOKEN',kw['env'])
