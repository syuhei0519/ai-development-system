"""Synthetic local Git preparation/Consumer regressions; no source execution."""
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from scripts import consume_delivery as delivery
from scripts.prepare_crossref_bundle import Preparation, encode, fixed_url


class PreparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='synthetic-preparation-')
        cls.root = Path(cls.temp.name)
        cls.repo = cls.root / 'origin'
        cls.repo.mkdir()
        cls.git('init')
        cls.git('config', 'user.name', 'Synthetic')
        cls.git('config', 'user.email', 'synthetic@example.invalid')
        (cls.repo / 'docs/tree').mkdir(parents=True)
        cls.raw = b'Synthetic source bytes\r\n'
        for path in ('docs/note.txt', 'docs/tree/note.txt'):
            (cls.repo / path).write_bytes(cls.raw)
        cls.git('add', '.')
        cls.git('commit', '-m', 'Synthetic source')
        cls.commit = cls.git('rev-parse', 'HEAD').decode().strip()
        cls.valid = []
        # Kind words in owner, repository and path must never select the route.
        for repo in ('synthetic/source', 'synthetic/tree', 'tree/blob', 'blob/tree'):
            for kind, path in (('blob', 'docs/note.txt'),
                               ('blob', 'docs/tree/note.txt'), ('tree', 'docs')):
                cls.valid.append((f'https://github.com/{repo}/{kind}/{cls.commit}/{path}', kind))
        u = f'https://github.com/synthetic/source/blob/{cls.commit}/docs/note.txt'
        cls.invalid = [
            '', 'blob', 'https://github.com', 'docs/tree/note.txt',
            u.replace('https:', 'http:'), u.replace('github.com', 'github.com.evil'),
            u.replace('github.com', 'user@github.com'), u.replace('github.com', 'github.com:443'),
            u.replace('https://', 'HTTPS://'), u.replace('/blob/', '/raw/'),
            u.replace('/blob/', '/commit/'), u.replace('/blob/', '/Blob/'),
            u.replace('/blob/', '//blob/'), u.replace('/synthetic/', '//synthetic/'),
            u.replace('/source/', '/source/extra/'), u.replace('/synthetic/', '/bad_owner/'),
            u.replace('/source/', '/bad%2Frepo/'), u.replace('/synthetic/', '/%74ree/'),
            u.replace('/blob/', '/%62lob/'), u.replace(cls.commit, 'main'),
            u.replace(cls.commit, cls.commit[:-1]), u.replace(cls.commit, cls.commit.upper()),
            u.replace('/docs/note.txt', ''), u.replace('/docs/note.txt', '/'),
            u.replace('docs/note.txt', 'docs//note.txt'),
            u.replace('docs/note.txt', 'docs/../note.txt'),
            u.replace('docs/note.txt', 'docs/./note.txt'),
            u.replace('docs/note.txt', 'docs/.git/note.txt'),
            u.replace('docs/note.txt', 'docs%2Ftree/note.txt'),
            u.replace('docs/note.txt', 'docs/%2e%2e/note.txt'),
            u.replace('docs/note.txt', 'docs\\note.txt'),
            u + '?raw=1', u + '#tree', u + '?', u + '#', u + '/', u + '\n',
            u.replace('/blob/', '/tree/') + '?recursive=1',
            u.replace('/blob/', '/tree/').replace('docs/note.txt', 'docs/%74ree'),
        ]
        for index, url in enumerate([v[0] for v in cls.valid] + cls.invalid):
            directory = cls.repo / str(index)
            directory.mkdir()
            candidates = dict(document_type='knowledge_candidates',
                              publication_status='pending_manager_review', candidates=[dict(
                                  id='SYNTHETIC-C', domain='synthetic', summary='Synthetic',
                                  evidence='Synthetic', scope='Synthetic', source=url)])
            raw = encode(candidates)
            (directory / 'candidate.json').write_bytes(raw)
            h = json.loads((delivery.ROOT / 'examples/research-to-test/research.handoff.json').read_bytes())
            h['task_id'] = 'SYNTHETIC-PREPARATION-' + str(index)
            h['artifacts'][0].update(kind='knowledge', locator='candidate.json',
                                     revision='sha256:' + delivery.digest(raw))
            h['knowledge_candidates'] = [dict(id='SYNTHETIC-C', domain='synthetic', summary='Synthetic',
                evidence_ids=[h['evidence'][0]['id']], raw_locator='candidate.json',
                publication_safety='needs_review')]
            (directory / 'handoff.json').write_bytes(encode(h))
        cls.git('add', '.')
        cls.git('commit', '-m', 'Synthetic producers')
        cls.producer_commit = cls.git('rev-parse', 'HEAD').decode().strip()

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    @classmethod
    def git(cls, *args):
        return subprocess.check_output(['git', '-C', str(cls.repo), *args], stderr=subprocess.DEVNULL)

    def prepare(self, index):
        cache = self.root / ('cache-' + str(index))
        cache.mkdir()
        source = delivery.GitSource(cache)
        original = source.git

        def local(directory, *args):
            if args[0] == 'fetch':
                return subprocess.check_output(['git', '-C', str(directory), 'fetch', '--no-tags',
                                                str(self.repo), args[-1]], stderr=subprocess.DEVNULL)
            return original(directory, *args)

        source.git = local  # Only the synthetic fetch destination is substituted.
        prep = Preparation(source, 'synthetic_sample')
        prep.add('synthetic/producer', self.producer_commit, f'{index}/handoff.json')
        return prep, source

    def test_canonical_route_kind_preparation_and_consumer(self):
        for index, (url, kind) in enumerate(self.valid):
            with self.subTest(url=url):
                prep, source = self.prepare(index)
                manifest = prep.finish()
                slot = manifest['candidate_bindings'][0]['sources'][0]
                self.assertEqual(slot['source'], url)
                self.assertEqual(slot['target']['kind'], kind)
                raw = encode(manifest)
                pub = encode(dict(schema_version='1.3', document_type='publication_receipt',
                    manifest_sha256=delivery.digest(raw), github_state='published',
                    artifacts=manifest['artifacts'], observation='Synthetic only'))
                auth = encode(dict(schema_version='1.3', document_type='delivery_authorization',
                    authority='Synthetic', consumer='SYNTHETIC', scope='synthetic', purpose='contract-review',
                    manifest_sha256=delivery.digest(raw), valid_until='2030-01-01T00:00:00Z',
                    public_safety_review='Synthetic', publication_approval='unverified',
                    publication_approval_evidence='Synthetic', consumer_use_approval='approved',
                    consumer_use_evidence='Synthetic', allowed_representations=['original'],
                    publication_receipt_sha256=delivery.digest(pub)))
                args = (raw, auth, pub, delivery.digest(auth), 'SYNTHETIC', 'synthetic',
                        'contract-review', source)
                receipt, blobs = delivery.consume(*args, now=datetime(2026, 10, 11, tzinfo=timezone.utc))
                self.assertFalse(receipt['authority_granted'])
                self.assertIn(self.raw, blobs.values())
                self.assertEqual(receipt, delivery.consume(*args, receipt_raw=encode(receipt),
                    now=datetime(2026, 10, 11, tzinfo=timezone.utc))[0])
                for key, value in prep.raw.items():
                    self.assertEqual(blobs[key], value)

    def test_malformed_candidate_urls_fail_closed(self):
        for index, url in enumerate(self.invalid, start=len(self.valid)):
            with self.subTest(url=url), self.assertRaises(ValueError):
                prep, _ = self.prepare(index)
                prep.finish()

    def test_commit_route_keeps_existing_path_and_revision_rules(self):
        url = f'https://github.com/tree/blob/commit/{self.commit}'
        self.assertEqual(fixed_url(url, 'commit'), ('tree/blob', self.commit, None))
        for invalid in (url + '/docs', url + '?raw=1', url + '#', url.replace('/commit/', '/tree/')):
            with self.subTest(url=invalid), self.assertRaises(ValueError):
                fixed_url(invalid, 'commit')
