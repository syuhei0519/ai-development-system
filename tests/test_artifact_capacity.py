"""Offline synthetic Delivery 1.3 capacity and unchanged fail-closed boundaries."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import consume_delivery as delivery
from scripts.prepare_crossref_bundle import Preparation
from test_crossref_delivery import Bundle, Source, fixture, handoff, encode, url
import test_crossref_delivery as crossref
import test_candidate_delivery as candidates


def capacity_bundle(count=128, version='1.3'):
    b = fixture()  # includes prior/current Handoffs, retry closure and commit bytes
    b.manifest['schema_version'] = version
    while len(b.manifest['artifacts']) < count:
        n = len(b.manifest['artifacts'])
        b.add(f'Synthetic evidence {n}\r\n'.encode(), f'evidence-{n}.txt')
    return b


class CapacityTests(unittest.TestCase):
    def test_128_existing_plus_followup_129_and_256_preserve_every_byte(self):
        b = capacity_bundle(version='1.3')
        old_receipt, original = b.consume()
        self.assertEqual(len(original), 128)
        b.manifest['schema_version'] = '1.3'
        self.assertEqual(b.consume()[1], original)
        prior = b.manifest['artifacts'][3]
        previous = json.loads(b.blobs[delivery.reference_key(prior['reference'])])
        h = handoff()
        h.update(task_id='SYNTHETIC-CAPACITY-FOLLOWUP', artifacts=[])
        h['evidence'] = []
        h['knowledge_candidates'] = []
        h['status'] = 'blocked'
        h['block_reasons'] = [dict(code='OTHER', detail='Synthetic boundary fixture.', required_action='Synthetic followup.')]
        for row in h['ac_mapping']:
            row.update(disposition='unverified', artifact_ids=[], evidence_ids=[])
        h['upstream'] = [dict(role=previous['role'], task_id=previous['task_id'], attempt=previous['attempt'],
            relationship='dependency', handoff_locator=url(prior), revision='sha256:'+prior['reference']['sha256'])]
        owner = b.add(encode(h), 'followup.json', 'handoff-v2')
        u = h['upstream'][0]
        b.slot(owner, delivery.upstream_slot(u), u['handoff_locator'], u['revision'], prior)
        for count in (129, 256):
            while len(b.manifest['artifacts']) < count:
                b.add(b'Synthetic later evidence.\n', f'later-{len(b.manifest["artifacts"])}.txt')
            receipt, blobs = b.consume()
            self.assertEqual(len(receipt['artifacts']), count)
            self.assertEqual({k:blobs[k] for k in original}, original)
            self.assertFalse(receipt['authority_granted'])
            self.assertEqual(b.consume(receipt_raw=encode(receipt))[0], receipt)
            with tempfile.TemporaryDirectory() as tmp:
                out = Path(tmp)/'fresh'
                delivery.write_bundle(out, receipt, blobs)
                for (repo, commit, path), raw in blobs.items():
                    p = out/('artifacts' if path else 'git-commit-objects')/repo/commit/(path or 'commit.raw')
                    self.assertEqual(p.read_bytes(), raw)
                with self.assertRaises(ValueError): delivery.write_bundle(out, receipt, blobs)
        with self.assertRaises(ValueError): b.consume(receipt_raw=encode(old_receipt))
        b.add(b'Synthetic overflow.', 'overflow.txt')
        source = Source(b.blobs)
        with self.assertRaises(ValueError): b.consume(source=source)
        self.assertEqual(source.calls, [])

    def test_versions_schema_receipts_and_only_capacity_delta(self):
        self.assertEqual(delivery.ARTIFACT_LIMITS, {'1.3':256})
        for name in delivery.DELIVERY_SCHEMAS:
            spec = json.loads((delivery.ROOT/f'contracts/{name}.schema.json').read_bytes())
            self.assertEqual(spec['properties']['schema_version']['const'], '1.3')
        b = capacity_bundle(129)
        receipt = b.consume()[0]
        raw,pub,policy = b.records()
        for name,record in [('artifact-delivery',b.manifest),('publication-receipt',pub),('consumption-receipt',receipt)]:
            record = deepcopy(record); record['schema_version'] = '1.2'
            with self.assertRaises(ValueError): delivery.schema(name, record)
        for version in ('1.2', '1.4'):
            with self.assertRaises(ValueError): b.consume(dict(schema_version=version))
        pub['schema_version']='1.2'
        with self.assertRaises(ValueError): b.consume(dict(publication_receipt_sha256=delivery.digest(encode(pub))),publication_raw=encode(pub))

    def test_extended_bundle_rejects_missing_duplicate_tamper_type_and_authority(self):
        for mode in ('closure','slot','duplicate','tamper','type','scope','representation','pin'):
            b = capacity_bundle(129)
            kw = {}
            if mode == 'closure': b.manifest['artifacts'].pop(0)
            elif mode == 'slot': b.manifest['slot_bindings'].pop()
            elif mode == 'duplicate': b.manifest['artifacts'].append(deepcopy(b.manifest['artifacts'][0]))
            elif mode == 'tamper': b.blobs[delivery.reference_key(b.manifest['artifacts'][0]['reference'])] += b'changed'
            elif mode == 'type': b.manifest['artifacts'][3]['format'] = 'json'
            elif mode == 'scope': kw['scope'] = 'OTHER'
            elif mode == 'representation': kw['policy_changes'] = dict(allowed_representations=['edited_derivative'])
            else: kw['policy_sha256'] = '0'*64
            with self.subTest(mode=mode), self.assertRaises(ValueError): b.consume(**kw)

    def test_actual_total_bytes_and_single_file_bounds(self):
        b = Bundle(); b.manifest['schema_version'] = '1.3'
        raw = b'x' * delivery.MAX_FILE
        for n in range(4): b.add(raw, f'large-{n}.txt')
        self.assertEqual(sum(map(len,b.consume()[1].values())), delivery.MAX_BUNDLE)
        b.add(b'x','overflow.txt')
        source=Source(b.blobs)
        with self.assertRaisesRegex(ValueError, 'bundle too large'): b.consume(source=source)
        self.assertEqual(source.calls, [])
        b=Bundle();b.manifest['schema_version']='1.3';b.add(raw+b'x','oversize.txt')
        with self.assertRaises(ValueError): b.consume()

    def test_cli_exit_and_receipt_capacity_match_schema(self):
        import sys
        for count, expected in ((256, 0), (257, 1)):
            b=capacity_bundle(count)
            raw,pub,policy=b.records()
            with tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp)
                for name,data in [('manifest',raw),('publication',encode(pub)),('authorization',encode(policy))]:
                    (root/name).write_bytes(data)
                argv=['consume_delivery', '--manifest',str(root/'manifest'),
                      '--publication',str(root/'publication'),'--authorization',str(root/'authorization'),
                      '--authorization-sha256',delivery.digest(encode(policy)),
                      '--consumer',policy['consumer'],'--scope',policy['scope'],'--purpose',policy['purpose'],
                      '--output',str(root/'output')]
                source=Source(b.blobs)
                with patch.object(sys,'argv',argv), patch.object(delivery,'GitSource',return_value=source):
                    self.assertEqual(delivery.main(),expected)
                self.assertEqual((root/'output').exists(),expected==0)
                if expected==0:
                    receipt=json.loads((root/'output/consumption-receipt.json').read_bytes())
                    delivery.schema('consumption-receipt',receipt)
                    self.assertEqual(len(receipt['artifacts']),count)
                else:
                    self.assertEqual(source.calls,[])

    def test_preparation_builds_256_and_consumer_accepts(self):
        raw=b'Synthetic prepared bytes.\n'
        class PreparationSource:
            def repository(self, ref): return 'synthetic'
            def git(self, directory, *args):
                return str(len(raw)).encode() if args[1]=='-s' else raw
            def read(self, ref): return raw
        p=Preparation(PreparationSource(),classification='synthetic_sample',version='1.3')
        for n in range(256): p.add('synthetic/repo','a'*40,f'file-{n}.txt')
        b=Bundle();b.manifest=p.finish();b.blobs=p.raw
        self.assertEqual(len(b.consume()[0]['artifacts']),256)
        with self.assertRaisesRegex(ValueError,'artifact count limit'): p.add('synthetic/repo','a'*40,'overflow.txt')

    def test_preparation_version_and_count_before_fetch(self):
        for version,limit in [('1.3',256)]:
            p=Preparation(None,version=version)
            p.items={('synthetic/repo','a'*40,str(n)):None for n in range(limit)}
            with self.assertRaisesRegex(ValueError,'artifact count limit'): p.add('synthetic/repo','a'*40,'new')
        for version in ('1.0','1.1','1.2','1.4'):
            with self.assertRaises(ValueError): Preparation(None,version=version)


# Exercise existing semantic attacks with the new version as well; fixtures stay synthetic.
class CapacityCrossrefTests(crossref.CrossrefTests):
    def setUp(self):
        super().setUp()
        self.b.manifest['schema_version']='1.3'


class CapacityCandidateTests(candidates.CandidateTests):
    def setUp(self):
        original=candidates.candidate_fixture
        def upgraded():
            b=original();b.manifest['schema_version']='1.3';return b
        p=patch.object(candidates,'candidate_fixture',side_effect=upgraded)
        p.start();self.addCleanup(p.stop)


class CapacityTreeTests(candidates.TreeTests):
    def setUp(self):
        original=Bundle.__init__
        def upgraded(b):
            original(b);b.manifest['schema_version']='1.3'
        p=patch.object(Bundle,'__init__',upgraded)
        p.start();self.addCleanup(p.stop)
        super().setUp()
