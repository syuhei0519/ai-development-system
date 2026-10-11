"""Independent Review synthetic boundaries. No network, product mutation or dispatch.

Run PB_HEAD=/fixed/checkout PB_PRIOR_CASES=/verified/independent_cases.py python this_file.py.
"""
import copy
import importlib.util
import os
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('prior', os.environ['PB_PRIOR_CASES'])
prior = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)
c = prior.c

class ReviewBoundaries(unittest.TestCase):
    setUp = prior.Cases.setUp
    scan = prior.Cases.scan
    rec = prior.Cases.rec
    reserve = prior.Cases.reserve
    proof = prior.Cases.proof

    def duplicate_source(self):
        first = self.reg['sources'][0]
        self.reg['sources'].append(dict(first, source_id='SYNTHETIC-REVIEW-TWO', inbox_path='second'))
        for key, raw in list(self.src.data.items()):
            if '/events/' in key[2]:
                self.src.data[key[:2] + ('second/' + key[2].split('/')[-1],)] = raw

    def test_first_scan_cross_source_collision_retains_both_payloads(self):
        self.duplicate_source()
        key = next(k for k in self.src.data if k[2].startswith('second/'))
        original = self.src.data[key]
        self.src.data[key] = original + b' '
        self.scan()
        identity = c.parse(original)['event_id']
        self.assertEqual(self.s['events'][identity]['status'], 'quarantined')
        self.assertEqual(self.s['cursors'], {})
        self.assertEqual(self.s['scans'][-1]['result'], 'quarantined')
        self.assertIn(c.digest(original), self.obj)
        self.assertIn(c.digest(original + b' '), self.obj)

    def test_missing_source_interrupts_reserved_batch_without_reset(self):
        self.duplicate_source()
        self.reserve()
        ledger = copy.deepcopy(self.s['batches'][self.batch])
        old = copy.deepcopy(self.s['cursors'])
        for key in list(self.src.data):
            if key[2].startswith('second/'):
                del self.src.data[key]
        self.scan()
        self.assertEqual(self.s['cursors'], old)
        self.assertEqual(self.s['batches'][self.batch], ledger)
        with self.assertRaises(ValueError):
            self.rec('dispatch')
        self.assertTrue(all(e['status'] == 'quarantined' for e in self.s['events'].values()))

    def test_collided_event_never_becomes_verified_on_clean_reappearance(self):
        self.scan()
        key = next(k for k in self.src.data if '/events/' in k[2])
        original = self.src.data[key]
        identity = c.parse(original)['event_id']
        self.src.data[key] += b' '
        self.scan()
        history = copy.deepcopy(self.s['events'][identity]['history'])
        self.src.data[key] = original
        self.scan()
        self.assertEqual(self.s['events'][identity]['status'], 'quarantined')
        self.assertEqual(self.s['events'][identity]['history'], history)

    def test_failed_final_directory_sync_requires_reload_not_blind_retry(self):
        store = c.Store(self.root / 'store')
        state, pin = store.mutate('absent', self.s['writer'], self.s['scope'], lambda s: c.scan(s, c.encode(self.reg), self.src))
        sync = c.fsync_dir
        def fail_final(path):
            if path == store.directory:
                raise OSError('SYNTHETIC final directory sync failure')
            return sync(path)
        with patch.object(c, 'fsync_dir', fail_final), self.assertRaises(OSError):
            store.mutate(pin, self.s['writer'], self.s['scope'], lambda s: c.scan(s, c.encode(self.reg), self.src))
        raw = (store.directory / 'state.json').read_bytes()
        fresh, _ = store.load(c.digest(raw))
        self.assertEqual(fresh['sequence'], state['sequence'] + 1)
        with self.assertRaises(ValueError):
            store.mutate(pin, self.s['writer'], self.s['scope'], lambda s: (s, {}))
        for item in fresh['events'].values():
            store.read_object(item['event_sha256'])

    def test_registry_order_does_not_lose_membership_or_raw(self):
        self.duplicate_source()
        self.scan()
        old = copy.deepcopy(self.s['events'])
        self.reg['sources'].reverse()
        self.reg['artifacts'].reverse()
        self.scan()
        self.assertEqual(self.s['events'], old)
        for item in old.values():
            self.assertIn(item['event_sha256'], self.obj)

if __name__ == '__main__':
    unittest.main(verbosity=2)
