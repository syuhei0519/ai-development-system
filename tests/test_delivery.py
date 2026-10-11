"""Consumer transport and trust boundary regressions; fixtures are public/synthetic only."""
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts.consume_delivery import (ROOT, GitSource, consume, digest, parse, schema,
                                       safe_path, write_bundle)


def encode(data): return (json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode()


class Source:
    def __init__(self, files): self.files=files
    def read(self, ref): return self.files[ref['path']]


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.raw=(ROOT/'examples/research-to-test/research.handoff.json').read_bytes()
        h=parse(self.raw)
        h['artifacts']=[dict(h['artifacts'][0], locator='design.txt', revision='sha256:'+digest(b'synthetic design\n'))]
        h['artifacts'][0]['id']='SYNTHETIC-DESIGN-1'
        # Preserve fixture IDs in evidence and mappings.
        old_id=parse(self.raw)['artifacts'][0]['id']
        h['artifacts'][0]['id']=old_id
        self.files={'handoff.json':encode(h),'design.txt':b'synthetic design\n','data.json':b'{"unicode":"\xe6\x98\x9f"}\n'}
        self.manifest={'schema_version':'1.0','document_type':'artifact_delivery','artifacts':[
            {'reference':{'repository':'example/repo','commit':'a'*40,'path':path,'size':len(raw),'sha256':digest(raw)},
             'representation':'edited_derivative','format':'handoff-v2' if path=='handoff.json' else 'json' if path.endswith('.json') else 'text',
             'public_classification':'synthetic_sample','source_alias':'SYNTHETIC-ORIGINAL'} for path,raw in self.files.items()]}
        self.policy=parse((ROOT/'examples/delivery/synthetic.authorization.json').read_bytes())
        self.policy['allowed_representations']=['edited_derivative']
        self.reseal()

    def reseal(self):
        self.mraw=encode(self.manifest)
        self.publication={'schema_version':'1.0','document_type':'publication_receipt','manifest_sha256':digest(self.mraw),
                          'github_state':'published','artifacts':deepcopy(self.manifest['artifacts']),'observation':'synthetic observed publication'}
        self.pubraw=encode(self.publication)
        self.policy['manifest_sha256']=digest(self.mraw)
        self.policy['publication_receipt_sha256']=digest(self.pubraw)

    def run_consumer(self, **kw):
        args=dict(manifest_raw=self.mraw, policy_raw=encode(self.policy),publication_raw=self.pubraw,
                  policy_sha256=digest(encode(self.policy)), consumer=self.policy['consumer'],scope=self.policy['scope'],
                  purpose=self.policy['purpose'],source=Source(self.files),now=datetime(2026,10,11,tzinfo=timezone.utc))
        args.update(kw)
        return consume(**args)

    def test_success_preserves_exact_bytes_and_rechecks_receipt(self):
        receipt,blobs=self.run_consumer()
        self.assertFalse(receipt['authority_granted'])
        self.assertEqual(self.run_consumer(receipt_raw=encode(receipt))[0],receipt)
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'verified';write_bundle(output,receipt,blobs)
            self.assertEqual((output/'artifacts/example/repo'/('a'*40)/'data.json').read_bytes(),self.files['data.json'])
            with self.assertRaises(ValueError):write_bundle(output,receipt,blobs)

    def test_raw_tamper_truncation_size_hash_and_commit_mismatch(self):
        original=deepcopy(self.files)
        for raw in (b'',original['design.txt'][:-1],b'X'+original['design.txt'][1:]):
            self.files['design.txt']=raw
            with self.assertRaises(ValueError):self.run_consumer()
        self.files=original
        for field,value in (('size',999),('sha256','0'*64),('commit','b'*40)):
            with self.subTest(field=field):
                # Untrusted manifest edit must fail the independently pinned hash.
                changed=deepcopy(self.manifest);changed['artifacts'][0]['reference'][field]=value
                with self.assertRaises(ValueError):self.run_consumer(manifest_raw=encode(changed))

    def test_approval_scope_representation_and_expiry(self):
        for k,v in [('consumer_use_approval','pending'),('allowed_representations',['original']),('valid_until','2020-01-01T00:00:00Z'),('valid_until','2030-01-01')]:
            old=deepcopy(self.policy);self.policy[k]=v
            with self.subTest(k=k),self.assertRaises(ValueError):self.run_consumer()
            self.policy=old
        for k,v in [('consumer','OTHER'),('scope','implementation'),('purpose','implementation'),('policy_sha256','0'*64)]:
            with self.subTest(k=k),self.assertRaises(ValueError):self.run_consumer(**{k:v})

    def test_receipts_cannot_authorize_and_tampering_rejected(self):
        receipt,_=self.run_consumer()
        for k,v in [('authority_granted',True),('scope','other'),('manifest_sha256','0'*64),('verification','trust me')]:
            changed=deepcopy(receipt);changed[k]=v
            with self.subTest(k=k),self.assertRaises(ValueError):self.run_consumer(receipt_raw=encode(changed))
        self.policy['consumer_use_approval']='pending'
        with self.assertRaises(ValueError):self.run_consumer(receipt_raw=encode(receipt))
        self.policy['consumer_use_approval']='approved'
        altered=deepcopy(self.publication);altered['observation']='tampered'
        with self.assertRaises(ValueError):self.run_consumer(publication_raw=encode(altered))

    def test_strict_json_and_handoff(self):
        for raw in (b'{"x":1,"x":2}',b'{"x":NaN}',b'{"x":1} trailing',b'\xff'):
            with self.subTest(raw=raw),self.assertRaises(ValueError):parse(raw)
        for raw in (b'{"x":1,"x":2}',b'{}'):
            self.files['handoff.json']=raw
            self.manifest['artifacts'][0]['reference'].update(size=len(raw),sha256=digest(raw));self.reseal()
            with self.assertRaises(ValueError):self.run_consumer()

    def test_unavailable_and_missing_bound_artifact(self):
        with patch.object(Source,'read',side_effect=OSError('unavailable')):
            with self.assertRaises(OSError):self.run_consumer()
        self.manifest['artifacts'].pop(1);self.reseal()
        with self.assertRaises(ValueError):self.run_consumer()

    def test_dangerous_paths_urls_refs_and_types(self):
        for path in ('../x','a/../x','/tmp/x','a//b','a/./b','-x','a;touch','a\\b','a\nb','a/.git/x','https://x','a%2fb'):
            with self.subTest(path=path),self.assertRaises(ValueError):safe_path(path)
        for field,value in [('repository','https://evil/x'),('repository','-u/x'),('commit','main'),('commit','a'*39),('commit','a'*40+';x'),('size',True),('size',-1)]:
            original=deepcopy(self.manifest);self.manifest['artifacts'][0]['reference'][field]=value;self.reseal()
            with self.subTest(field=field,value=value),self.assertRaises(ValueError):self.run_consumer()
            self.manifest=original
        self.reseal()

    def test_handoff_mistyped_or_private_or_binding_changed(self):
        self.manifest['artifacts'][0]['format']='json';self.reseal()
        with self.assertRaises(ValueError):self.run_consumer()
        self.manifest['artifacts'][0]['format']='handoff-v2'
        h=parse(self.files['handoff.json']);h['artifacts'][0]['revision']='sha256:'+'f'*64
        self.files['handoff.json']=encode(h)
        self.manifest['artifacts'][0]['reference'].update(size=len(encode(h)),sha256=digest(encode(h)));self.reseal()
        with self.assertRaises(ValueError):self.run_consumer()
        h['publication']='private_only';self.files['handoff.json']=encode(h)
        self.manifest['artifacts'][0]['reference'].update(size=len(encode(h)),sha256=digest(encode(h)));self.reseal()
        with self.assertRaises(ValueError):self.run_consumer()

    def test_duplicate_paths_publication_mismatch_and_schema_version(self):
        original=deepcopy(self.manifest)
        self.manifest['artifacts'].append(deepcopy(self.manifest['artifacts'][0]));self.reseal()
        with self.assertRaises(ValueError):self.run_consumer()
        self.manifest=original;self.reseal()
        self.publication['artifacts'].pop();self.pubraw=encode(self.publication)
        self.policy['publication_receipt_sha256']=digest(self.pubraw)
        with self.assertRaises(ValueError):self.run_consumer()
        self.reseal();self.manifest['schema_version']='2.0';self.reseal()
        with self.assertRaises(ValueError):self.run_consumer()

    def test_upstream_identity_and_retry_binding(self):
        previous=parse(self.files['handoff.json'])
        current=deepcopy(previous)
        current['attempt']=2;current['task_id']='SYNTHETIC-NEXT'
        current['upstream']=[{'role':previous['role'],'task_id':previous['task_id'],'attempt':1,
                             'handoff_locator':'previous.json','revision':'sha256:'+digest(encode(previous)),
                             'relationship':'retry_of'}]
        self.files['previous.json']=encode(previous)
        artifact=deepcopy(self.manifest['artifacts'][0]);artifact['reference'].update(path='previous.json',size=len(encode(previous)),sha256=digest(encode(previous)))
        self.manifest['artifacts'].append(artifact)
        def update():
            self.files['handoff.json']=encode(current)
            self.manifest['artifacts'][0]['reference'].update(size=len(encode(current)),sha256=digest(encode(current)))
            self.reseal()
        update();self.run_consumer()
        current['upstream'][0]['task_id']='SYNTHETIC-WRONG';update()
        with self.assertRaises(ValueError):self.run_consumer()
        current['upstream'][0]['task_id']=previous['task_id']
        current['issue']['title']='SYNTHETIC-OTHER-ISSUE';update()
        with self.assertRaises(ValueError):self.run_consumer()

    def test_cli_fails_without_output_or_leaked_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'manifest').write_bytes(self.mraw);(p/'policy').write_bytes(encode(self.policy));(p/'pub').write_bytes(self.pubraw)
            run=subprocess.run([sys.executable,str(ROOT/'scripts/consume_delivery.py'),'--manifest',str(p/'manifest'),'--authorization',str(p/'policy'),'--publication',str(p/'pub'),'--output',str(p/'out'),'--authorization-sha256','0'*64,'--consumer','SYNTHETIC','--scope','SYNTHETIC','--purpose','contract-review'],capture_output=True)
            self.assertEqual(run.returncode,1);self.assertFalse((p/'out').exists());self.assertNotIn(b'Traceback',run.stderr)


class GitTransportTests(unittest.TestCase):
    def test_real_git_full_blob_no_checkout_and_forbidden_modes(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);repo=p/'origin';repo.mkdir()
            def git(*args):return subprocess.check_output(['git','-C',str(repo),*args],stderr=subprocess.DEVNULL)
            git('init');git('config','user.name','Synthetic');git('config','user.email','synthetic@example.invalid')
            (repo/'nested').mkdir();raw=b'raw\r\n\x00bytes\n';(repo/'nested/data').write_bytes(raw)
            (repo/'link').symlink_to('nested/data');git('add','.');git('commit','-m','synthetic fixture')
            sha=git('rev-parse','HEAD').decode().strip()
            git('update-index','--add','--cacheinfo',f'160000,{sha},module');git('commit','-m','synthetic gitlink')
            sha=git('rev-parse','HEAD').decode().strip()
            temp=p/'consumer';temp.mkdir();source=GitSource(temp);original=source.git
            def local_git(directory,*args):
                if args[0]=='fetch':
                    # Test-only transport injection. Production CLI has no file/URL override.
                    return subprocess.check_output(['git','-C',str(directory),'fetch',str(repo),args[-1]],stderr=subprocess.DEVNULL)
                return original(directory,*args)
            source.git=local_git
            ref={'repository':'example/repo','commit':sha,'path':'nested/data','size':len(raw),'sha256':digest(raw)}
            self.assertEqual(source.read(ref),raw)
            for path in ('link','link/child','module','module/child','missing'):
                with self.subTest(path=path),self.assertRaises(ValueError):source.read(dict(ref,path=path))
            with self.assertRaises(ValueError):source.read(dict(ref,size=1))
            with self.assertRaises(subprocess.CalledProcessError):source.read(dict(ref,commit='f'*40))

    def test_timeout_unavailable_and_commit_identity(self):
        with tempfile.TemporaryDirectory() as temp:
            source=GitSource(temp)
            with patch('scripts.consume_delivery.subprocess.run',side_effect=subprocess.TimeoutExpired('git',120)):
                with self.assertRaises(subprocess.TimeoutExpired):source.read({'repository':'example/repo','commit':'a'*40,'path':'x','size':1,'sha256':'a'*64})
        with tempfile.TemporaryDirectory() as temp:
            source=GitSource(temp)
            with patch.object(source,'git',side_effect=[b'',b'',b'commit\n',b'b'*40+b'\n']):
                with self.assertRaises(ValueError):source.read({'repository':'example/repo','commit':'a'*40,'path':'x','size':1,'sha256':'a'*64})

    def test_samples_and_schemas(self):
        for name in ('synthetic','research-public'):
            schema('artifact-delivery',parse((ROOT/f'examples/delivery/{name}.manifest.json').read_bytes()))
            schema('publication-receipt',parse((ROOT/f'records/artifact-delivery/{name}.publication.json').read_bytes()))
