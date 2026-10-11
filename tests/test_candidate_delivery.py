"""Synthetic candidate/tree integrity. Source code is data and never executed."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts.consume_delivery import GitSource, digest, reference_key, artifact_slot, schema, verify_handoffs
from scripts.delivery_candidates import snapshot_tree, tree_entries, oid
from test_crossref_delivery import Bundle, Source, encode, handoff, url


def candidate_fixture():
    b=Bundle()
    src=b.add(b'Synthetic source bytes\r\n','source.txt',repo='synthetic/source',commit='b'*40)
    data=dict(document_type='knowledge_candidates',publication_status='pending_manager_review',candidates=[
        dict(id='SYNTHETIC-C1',domain='synthetic',summary='Long synthetic candidate explanation.',
             evidence='Synthetic evidence only.',source=url(src),scope='Synthetic test scope.')])
    owner=b.add(encode(data),'candidates.json','knowledge-candidates-v1')
    h=handoff();a=h['artifacts'][0]
    a.update(kind='knowledge',locator='candidates.json',revision='sha256:'+owner['reference']['sha256'])
    h['knowledge_candidates']=[dict(id='SYNTHETIC-C1',domain='synthetic',summary='Short summary.',
                                    evidence_ids=[h['evidence'][0]['id']],raw_locator='candidates.json',
                                    publication_safety='needs_review')]
    producer=b.add(encode(h),'handoff.json','handoff-v2')
    b.slot(producer,artifact_slot(a),a['locator'],a['revision'],owner)
    b.manifest['candidate_bindings']=[dict(profile='knowledge-candidates-v1',owner=deepcopy(owner['reference']),
        producer=deepcopy(producer['reference']),producer_artifact_id=a['id'],candidate_ids=['SYNTHETIC-C1'],
        sources=[dict(candidate_id='SYNTHETIC-C1',source=url(src),target=dict(kind='blob',reference=deepcopy(src['reference'])))])]
    return b


def mutate_document(b,index,fn):
    item=b.manifest['artifacts'][index];old=deepcopy(item['reference']);key=reference_key(old)
    data=json.loads(b.blobs[key]);fn(data);raw=encode(data)
    item['reference'].update(size=len(raw),sha256=digest(raw));b.blobs[key]=raw
    def replace(x):
        if isinstance(x,dict):
            for k,v in x.items():
                if v==old:x[k]=deepcopy(item['reference'])
                else:replace(v)
        elif isinstance(x,list):
            for v in x:replace(v)
    replace(b.manifest['candidate_bindings']);replace(b.manifest['slot_bindings'])
    if index==1:
        mutate_document(b,2,lambda h:h['artifacts'][0].update(revision='sha256:'+digest(raw)))
        b.manifest['slot_bindings'][0]['revision']='sha256:'+digest(raw)


class CandidateTests(unittest.TestCase):
    def test_immutable_candidates_short_summary_and_pending_status(self):
        b=candidate_fixture();before=deepcopy(b.blobs);receipt,blobs=b.consume()
        self.assertEqual(before,blobs);self.assertFalse(receipt['authority_granted'])
        self.assertEqual(receipt['candidate_bindings'],b.manifest['candidate_bindings'])
        self.assertEqual(receipt,b.consume(receipt_raw=encode(receipt))[0])

    def test_required_fields_and_no_added_original_schema(self):
        for field in ('document_type','publication_status','candidates'):
            b=candidate_fixture();mutate_document(b,1,lambda d:d.pop(field))
            with self.subTest(field=field),self.assertRaises(ValueError):b.consume()
        for field in ('schema_version','task_id','attempt','revision','authority'):
            b=candidate_fixture();mutate_document(b,1,lambda d:d.update({field:'SYNTHETIC'}))
            with self.subTest(field=field),self.assertRaises(ValueError):b.consume()

    def test_candidate_fields_types_bounds_and_duplicates(self):
        for field in ('id','domain','summary','evidence','source','scope'):
            for value in (None,[],{},'', ' '*3, 'x'*17000):
                b=candidate_fixture();mutate_document(b,1,lambda d:d['candidates'][0].update({field:value}))
                with self.subTest(field=field,value=type(value)),self.assertRaises(ValueError):b.consume()
            b=candidate_fixture();mutate_document(b,1,lambda d:d['candidates'][0].pop(field))
            with self.assertRaises(ValueError):b.consume()
        for change in (lambda d:d['candidates'].append(deepcopy(d['candidates'][0])),
                       lambda d:d.update(candidates=[]),lambda d:d['candidates'][0].update(extra='x')):
            b=candidate_fixture();mutate_document(b,1,change)
            with self.assertRaises(ValueError):b.consume()

    def test_pending_never_becomes_approval(self):
        b=candidate_fixture()
        with self.assertRaises(ValueError):b.consume(dict(consumer_use_approval='pending'))
        for state in ('approved','public_safe','private_only'):
            b=candidate_fixture();mutate_document(b,1,lambda d:d.update(publication_status=state))
            with self.assertRaises(ValueError):b.consume()

    def test_downgrade_unknown_missing_and_wrong_profiles(self):
        for fmt in ('json','text','handoff-v2','knowledge-input-v1','knowledge-handoff-v1'):
            b=candidate_fixture();b.manifest['artifacts'][1]['format']=fmt
            with self.subTest(fmt=fmt),self.assertRaises(ValueError):b.consume()
        for dt in ('knowledge_unknown','knowledge_input','handoff',None):
            b=candidate_fixture();mutate_document(b,1,lambda d:d.update(document_type=dt))
            with self.assertRaises(ValueError):b.consume()
        b=candidate_fixture();mutate_document(b,1,lambda d:d.pop('document_type'))
        b.manifest['artifacts'][1]['format']='json'
        with self.assertRaises(ValueError):b.consume()

    def test_all_old_versions_reject_new_format(self):
        for version in ('1.0','1.1'):
            b=candidate_fixture();b.manifest['schema_version']=version
            with self.assertRaises(ValueError):schema('artifact-delivery',b.manifest)
            with self.assertRaises(ValueError):verify_handoffs(b.manifest['artifacts'],b.blobs,version,[])

    def test_owner_producer_and_artifact_pins(self):
        for which in ('owner','producer'):
            for field,value in (('size',0),('sha256','0'*64),('path','missing.json'),('commit','c'*40),('repository','synthetic/missing')):
                b=candidate_fixture();b.manifest['candidate_bindings'][0][which][field]=value
                with self.subTest(which=which,field=field),self.assertRaises(ValueError):b.consume()
        b=candidate_fixture();b.manifest['candidate_bindings'][0]['producer_artifact_id']='SYNTHETIC-MISSING'
        with self.assertRaises(ValueError):b.consume()

    def test_missing_extra_duplicate_and_conflicting_bindings(self):
        for operation in ('missing','duplicate','extra-owner','bad-profile','extra-slot','missing-slot','duplicate-slot','bad-slot'):
            b=candidate_fixture();cb=b.manifest['candidate_bindings'];binding=cb[0]
            if operation=='missing':cb.clear()
            elif operation=='duplicate':cb.append(deepcopy(binding))
            elif operation=='extra-owner':
                extra=deepcopy(binding);extra['owner']['path']='extra.json';cb.append(extra)
            elif operation=='bad-profile':binding['profile']='knowledge-candidates-v2'
            elif operation=='missing-slot':binding['sources'].clear()
            elif operation in ('extra-slot','duplicate-slot'):
                extra=deepcopy(binding['sources'][0])
                if operation=='extra-slot':extra['candidate_id']='SYNTHETIC-EXTRA'
                binding['sources'].append(extra)
            else:binding['sources'][0]['candidate_id']='SYNTHETIC-WRONG'
            with self.subTest(operation=operation),self.assertRaises(ValueError):b.consume()

    def test_candidate_set_producer_domain_and_raw_locator(self):
        for ids in ([],['SYNTHETIC-C1','SYNTHETIC-C1'],['SYNTHETIC-OTHER']):
            b=candidate_fixture();b.manifest['candidate_bindings'][0]['candidate_ids']=ids
            with self.assertRaises(ValueError):b.consume()
        for field,value in (('raw_locator','missing.json'),('id','SYNTHETIC-OTHER'),('domain','other')):
            b=candidate_fixture();mutate_document(b,2,lambda d:d['knowledge_candidates'][0].update({field:value}))
            with self.assertRaises(ValueError):b.consume()
        b=candidate_fixture();mutate_document(b,2,lambda d:d.update(knowledge_candidates=[]))
        with self.assertRaises(ValueError):b.consume()

    def test_blob_source_url_and_original_source_exact(self):
        original=url(candidate_fixture().manifest['artifacts'][0])
        for value in (original+'?q=x',original+'#x',original.replace('https:','http:'),original.replace('/blob/'+ 'b'*40,'/blob/main'),
                      original.replace('github.com','github.com.evil'),original.replace('source.txt','%73ource.txt'),
                      original.replace('synthetic/source','synthetic/wrong')):
            b=candidate_fixture();mutate_document(b,1,lambda d:d['candidates'][0].update(source=value))
            b.manifest['candidate_bindings'][0]['sources'][0]['source']=value
            with self.subTest(url=value),self.assertRaises(ValueError):b.consume()
        b=candidate_fixture();b.manifest['candidate_bindings'][0]['sources'][0]['source']=original+'x'
        with self.assertRaises(ValueError):b.consume()

    def test_blob_source_pins_and_missing_bytes(self):
        for field,value in (('size',0),('sha256','0'*64),('path','missing'),('commit','c'*40),('object_type','git-commit-object')):
            b=candidate_fixture();b.manifest['candidate_bindings'][0]['sources'][0]['target']['reference'][field]=value
            with self.assertRaises(ValueError):b.consume()
        b=candidate_fixture();b.manifest['artifacts'].pop(0)
        with self.assertRaises(ValueError):b.consume()
        b=candidate_fixture();b.blobs[reference_key(b.manifest['artifacts'][0]['reference'])]+=b'altered'
        with self.assertRaises(ValueError):b.consume()

    def test_private_producer_and_receipt_tamper(self):
        b=candidate_fixture();mutate_document(b,2,lambda d:d.update(publication='private_only'))
        with self.assertRaises(ValueError):b.consume()
        b=candidate_fixture();receipt,_=b.consume();receipt['candidate_bindings'][0]['candidate_ids']=[]
        with self.assertRaises(ValueError):b.consume(receipt_raw=encode(receipt))


class TreeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        root=Path(self.temp.name);self.repo=root/'origin';self.repo.mkdir()
        self.git('init');self.git('config','user.name','Synthetic');self.git('config','user.email','synthetic@example.invalid')
        (self.repo/'src/nested').mkdir(parents=True)
        (self.repo/'.gitignore').write_text('# Synthetic\n')
        (self.repo/'src/one.txt').write_bytes(b'Synthetic one\r\n')
        (self.repo/'src/nested/two.bin').write_bytes(b'\0\xffSynthetic binary\n')
        (self.repo/'src/run.sh').write_text('# Synthetic data; never executed\n');(self.repo/'src/run.sh').chmod(0o755)
        self.git('add','.');self.git('commit','-m','Synthetic fixture')
        self.sha=self.git('rev-parse','HEAD').decode().strip()
        cache=root/'cache';cache.mkdir();self.source=GitSource(cache);original=self.source.git
        def local(directory,*args):
            if args[0]=='fetch':return subprocess.check_output(['git','-C',str(directory),'fetch',str(self.repo),args[-1]],stderr=subprocess.DEVNULL)
            return original(directory,*args)
        self.source.git=local
        self.ref=dict(repository='synthetic/tree',commit=self.sha,path='src')
        self.snap,self.treebytes=snapshot_tree(self.source,self.ref)

    def git(self,*args):return subprocess.check_output(['git','-C',str(self.repo),*args],stderr=subprocess.DEVNULL)

    def bundle(self):
        b=candidate_fixture();target=dict(kind='tree',snapshot=deepcopy(self.snap))
        loc=f'https://github.com/synthetic/tree/tree/{self.sha}/src'
        mutate_document(b,1,lambda d:d['candidates'][0].update(source=loc))
        b.manifest['candidate_bindings'][0]['sources'][0].update(source=loc,target=target)
        source=Source(b.blobs);source.repository=self.source.repository;source.git=self.source.git
        return b,source

    def test_complete_nested_binary_executable_and_empty_tree(self):
        b,source=self.bundle();receipt,blobs=b.consume(source=source)
        self.assertEqual(len(self.snap['files']),3);self.assertEqual(len(self.snap['trees']),1)
        for k,v in self.treebytes.items():self.assertEqual(blobs[k],v)
        self.assertEqual(b.consume(source=source,receipt_raw=encode(receipt))[0],receipt)
        from scripts.consume_delivery import write_bundle
        out=Path(self.temp.name)/'out';write_bundle(out,receipt,blobs)
        for (repo,commit,path),raw in self.treebytes.items():self.assertEqual((out/'artifacts'/repo/commit/path).read_bytes(),raw)
        empty=subprocess.check_output(['git','-C',str(self.repo),'mktree'],input=b'').decode().strip()
        root_tree=subprocess.check_output(['git','-C',str(self.repo),'mktree'],
            input=f'040000 tree {empty}\tempty\n'.encode()).decode().strip()
        commit=subprocess.check_output(['git','-C',str(self.repo),'commit-tree',root_tree],
            input=b'Synthetic empty subtree\n').decode().strip()
        snap, raw=snapshot_tree(self.source,dict(self.ref,commit=commit,path='empty'))
        self.assertEqual(snap['oid'],empty);self.assertEqual(snap['trees'],[])
        self.assertEqual(snap['files'],[]);self.assertEqual(raw,{})

    def test_inventory_missing_extra_duplicate_mode_oid_size_hash(self):
        for operation in ('missing','extra','duplicate','mode','oid','size','sha256','path','tree-missing','tree-oid','root-oid'):
            b,source=self.bundle();snap=b.manifest['candidate_bindings'][0]['sources'][0]['target']['snapshot']
            if operation=='missing':snap['files'].pop()
            elif operation=='extra':snap['files'].append(dict(snap['files'][0],path='extra.txt'))
            elif operation=='duplicate':snap['files'].append(deepcopy(snap['files'][0]))
            elif operation=='tree-missing':snap['trees'].clear()
            elif operation=='tree-oid':snap['trees'][0]['oid']='0'*40
            elif operation=='root-oid':snap['oid']='0'*40
            else:snap['files'][0][operation]={'mode':'100755','oid':'0'*40,'size':0,'sha256':'0'*64,'path':'other.txt'}[operation]
            with self.subTest(operation=operation),self.assertRaises(ValueError):b.consume(source=source)

    def test_canonical_url_repo_commit_directory(self):
        for field,value in (('path','missing'),('commit','0'*40),('repository','synthetic/other')):
            b,source=self.bundle();b.manifest['candidate_bindings'][0]['sources'][0]['target']['snapshot'][field]=value
            with self.assertRaises(ValueError):b.consume(source=source)

    def test_symlink_gitlink_and_bad_ancestors(self):
        (self.repo/'src/link').symlink_to('one.txt');self.git('add','.');self.git('commit','-m','Synthetic link')
        sha=self.git('rev-parse','HEAD').decode().strip()
        for path in ('src','src/link','src/link/child'):
            with self.assertRaises(ValueError):snapshot_tree(self.source,dict(self.ref,commit=sha,path=path))
        self.git('rm','src/link');self.git('update-index','--add','--cacheinfo',f'160000,{self.sha},src/module')
        self.git('commit','-m','Synthetic gitlink');sha=self.git('rev-parse','HEAD').decode().strip()
        for path in ('src','src/module','src/module/child','src/one.txt','missing'):
            with self.assertRaises(ValueError):snapshot_tree(self.source,dict(self.ref,commit=sha,path=path))

    def test_truncated_enumeration_and_wrong_object_type(self):
        original=self.source.git
        for operation in ('truncate','wrongtype','missing'):
            def altered(directory,*args):
                raw=original(directory,*args)
                if args[:2]==('cat-file','tree') and operation=='truncate':return raw[:-1]
                if args[:2]==('cat-file','-t') and raw==b'tree\n' and operation=='wrongtype':return b'blob\n'
                if args[:2]==('cat-file','tree') and operation=='missing':raise ValueError('Synthetic missing object')
                return raw
            self.source.git=altered
            with self.subTest(operation=operation),self.assertRaises(ValueError):snapshot_tree(self.source,self.ref)
        self.source.git=original

    def test_resource_bounds_fail_without_truncation(self):
        for name,value in (('MAX_ENTRIES',1),('MAX_TREES',0),('MAX_FILE',1),('MAX_BUNDLE',1),('MAX_TREE_BYTES',1),('MAX_TREE_TOTAL',1)):
            with self.subTest(limit=name),patch('scripts.delivery_candidates.'+name,value),self.assertRaises(ValueError):
                snapshot_tree(self.source,self.ref)

    def test_unapproved_tree_and_missing_transport(self):
        b,source=self.bundle()
        for a in b.manifest['artifacts']:a['representation']='edited_derivative'
        with self.assertRaises(ValueError):b.consume(dict(allowed_representations=['edited_derivative']),source=source)
        with self.assertRaises(ValueError):verify_handoffs(b.manifest['artifacts'],b.blobs,'1.2',[],b.manifest['slot_bindings'],b.manifest['candidate_bindings'])

    def test_changed_raw_blob_even_matching_length_rejected_by_oid(self):
        original=self.source.git
        def altered(directory,*args):
            raw=original(directory,*args)
            if args[:2]==('cat-file','blob'):return b'x'*len(raw)
            return raw
        self.source.git=altered
        with self.assertRaises(ValueError):snapshot_tree(self.source,self.ref)

    def test_total_bundle_and_tree_limit(self):
        b,source=self.bundle()
        with patch('scripts.delivery_candidates.MAX_BUNDLE',sum(map(len,self.treebytes.values()))),self.assertRaises(ValueError):
            b.consume(source=source)

    def test_raw_tree_malformed_duplicate_and_unsafe_names(self):
        for raw in (b'100644 a\0short',b'100644 ../x\0'+b'x'*20,
                    b'100644 a\0'+b'x'*20+b'100644 a\0'+b'y'*20,
                    b'100644 .git\0'+b'x'*20,b'777 a\0'+b'x'*20):
            with self.assertRaises(ValueError):tree_entries(raw)

    def test_changed_tree_receipt_and_fresh_retrieval(self):
        b,source=self.bundle();receipt,_=b.consume(source=source)
        receipt['candidate_bindings'][0]['sources'][0]['target']['snapshot']['files'].pop()
        with self.assertRaises(ValueError):b.consume(source=source,receipt_raw=encode(receipt))
        original=source.git
        def missing(directory,*args):
            if args[:2]==('cat-file','blob'):raise ValueError('Synthetic unavailable during recheck')
            return original(directory,*args)
        source.git=missing
        with self.assertRaises(ValueError):b.consume(source=source)


class RetrySupplementTests(unittest.TestCase):
    def test_assignment_conditions_preserve_exact_issue_and_retry(self):
        from test_crossref_delivery import fixture, CrossrefTests
        b=fixture();prior=json.loads(b.blobs[reference_key(b.manifest['artifacts'][2]['reference'])])
        CrossrefTests().mutate_handoff(b,3,lambda h:h['assignment']['completion_criteria'].append(
            'SYNTHETIC-X-7: additional Manager-assigned completion condition, not a new Issue AC.'))
        current=json.loads(b.blobs[reference_key(b.manifest['artifacts'][3]['reference'])])
        self.assertEqual(current['issue'],prior['issue'])
        self.assertEqual(current['assignment']['scope'],prior['assignment']['scope'])
        self.assertEqual(current['attempt'],prior['attempt']+1)
        b.consume()
        CrossrefTests().mutate_handoff(b,3,lambda h:h['issue']['acceptance_criteria'].append(
            dict(id='SYNTHETIC-NEW-AC',verbatim='Would change Issue identity.',source='synthetic')))
        with self.assertRaises(ValueError):b.consume()
