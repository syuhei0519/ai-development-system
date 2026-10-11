"""Synthetic regressions for required-subcheck history and PR locator policy."""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest

from completion_fixture import build, save, write, NOW, SAMPLE
from scripts.validate_issue_completion import validate_files, instant


class RepairTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.a, self.c = build(self.root)
        self.previous_args = {}

    def validate(self):
        save(self.root, self.a, self.c)
        return validate_files(self.root / 'completion.json', self.root / 'context.json',
                              self.a['context_sha256'], self.root / 'handoff.json',
                              now=instant(NOW), **self.previous_args)

    def pin_previous(self):
        ref = write(self.root, 'previous.json', self.a)
        self.c['previous_assessment_sha256'] = ref['sha256']
        self.a['history'] = dict(previous_ref=ref, events=[self.event('revalidated')])
        self.previous_args = dict(previous_file=self.root / 'previous.json', previous_sha256=ref['sha256'])

    def event(self, kind):
        return dict(event_id=kind, kind=kind, observed_at=NOW,
                    affected_ids=['runtime-persistence'], reason=SAMPLE, evidence_refs=[])

    def rebuild_results(self):
        # Refresh all current-set bindings, so the only rejection is history.
        measurements = {e['verification_ids'][0]: e for e in self.a['evidence'] if e['kind'] == 'ac_measurement'}
        self.a['verification_results'] = [dict(verification_id=v['verification_id'], outcome='met',
            evidence_ids=[measurements[v['verification_id']]['id']], reason=SAMPLE) for v in self.c['required_verifications']]
        for r in self.a['ac_results']:
            r['verification_ids'] = [v['verification_id'] for v in self.c['required_verifications'] if v['ac_id'] == r['ac_id']]
            r['evidence_ids'] = [measurements[k]['id'] for k in r['verification_ids']]
        self.a['integration_readiness']['checks']['measurement_coverage']['evidence_ids'] = [e['id'] for e in measurements.values()]

    def require_change_event(self):
        with self.assertRaisesRegex(ValueError, 'scope/required set change needs history event'):
            self.validate()
        self.a['history']['events'].append(self.event('required_set_changed'))
        self.assertEqual(self.validate(), ('ready', 'achieved'))

    def test_subcheck_add_remove_rename_and_ac_reassignment(self):
        for mode in ('add', 'remove', 'rename', 'ac'):
            with self.subTest(mode=mode):
                self.a, self.c = build(self.root)
                self.pin_previous()
                v = self.c['required_verifications'][-1]
                e = self.a['evidence'][-1]
                if mode == 'remove':
                    self.c['required_verifications'].pop()
                    self.a['evidence'].pop()
                elif mode in ('add', 'rename'):
                    if mode == 'add':
                        v, e = copy.deepcopy(v), copy.deepcopy(e)
                        self.c['required_verifications'].append(v)
                        self.a['evidence'].append(e)
                    v['verification_id'] = 'runtime-additional'
                    e.update(id='runtime-additional', verification_ids=['runtime-additional'])
                else:
                    v['ac_id'] = self.c['issue']['acceptance_criteria'][0]['id']
                    e['ac_ids'] = [v['ac_id']]
                self.rebuild_results()
                self.require_change_event()

    def test_subcheck_semantic_changes_with_matching_current_measurements(self):
        cases = [('method', 'synthetic different method'), ('expected_result', 'synthetic different result'),
                 ('owner', 'synthetic-other-tester'), ('member_ids', ['app']),
                 ('phase', 'postmerge'), ('environment_id', 'synthetic-other-ci'),
                 ('workload_id', 'synthetic-other-tests')]
        for field, value in cases:
            with self.subTest(field=field):
                self.a, self.c = build(self.root)
                self.pin_previous()
                # Environment/workload changes on a premerge check need no deployment mutation.
                vid = 'app-pre' if field in ('environment_id', 'workload_id', 'phase') else 'runtime-persistence'
                v = next(v for v in self.c['required_verifications'] if v['verification_id'] == vid)
                e = next(e for e in self.a['evidence'] if e['id'] == vid)
                v[field] = value
                e['producer' if field == 'owner' else field] = value
                if field == 'phase':
                    v['deployment_ids'] = []
                    e['deployment_ids'] = []
                    e['observed_at'] = '2030-01-03T10:00:00Z'
                self.require_change_event()

    def test_same_requirements_reordered_and_new_observations_need_no_set_event(self):
        self.pin_previous()
        self.c['required_verifications'].reverse()
        self.a['verification_results'].reverse()
        for v in self.c['required_verifications']:
            v['member_ids'].reverse()
        for e in self.a['evidence']:
            if e['kind'] == 'ac_measurement':
                e['member_ids'].reverse()
                e['observation'] += ' new observation'
                if e['phase'] == 'postdeploy':
                    e['observed_at'] = '2030-01-03T11:00:00Z'
        for r in self.a['ac_results']:
            r['verification_ids'].reverse()
        self.assertEqual(self.validate(), ('ready', 'achieved'))

    def test_set_event_in_old_history_does_not_cover_new_change(self):
        self.a['history']['events'] = [self.event('required_set_changed')]
        self.validate()
        old = copy.deepcopy(self.a['history']['events'])
        self.pin_previous()
        self.a['history']['events'] = old + [self.event('revalidated')]
        self.c['required_verifications'][-1]['method'] += ' changed'
        self.a['evidence'][-1]['method'] += ' changed'
        with self.assertRaisesRegex(ValueError, 'scope/required set change needs history event'):
            self.validate()

    def pr_locator(self, locator, nested=False):
        path = self.root / 'app-handoff.json'
        h = json.loads(path.read_bytes())
        h['artifacts'][0]['locator'] = locator
        if nested:
            path = self.root / 'nested' / path.name
        self.a['member_results'][0]['readiness_handoff_ref'] = write(self.root, str(path.relative_to(self.root)), h)

    def test_pr_handoff_locator_rejects_leaf_and_ancestor_symlinks(self):
        (self.root / 'pr-link.json').symlink_to('app-readiness.json')
        (self.root / 'linked-dir').symlink_to('.', target_is_directory=True)
        for locator in ('pr-link.json', 'linked-dir/app-readiness.json'):
            with self.subTest(locator=locator):
                self.pr_locator(locator)
                with self.assertRaisesRegex(ValueError, 'symlink rejected'):
                    self.validate()

    def test_pr_handoff_locator_rejects_lexical_aliases_and_other_files(self):
        (self.root / 'subdir').mkdir()
        (self.root / 'copy.json').write_bytes((self.root / 'app-readiness.json').read_bytes())
        for locator in ('./app-readiness.json', 'subdir/../app-readiness.json',
                        'subdir//app-readiness.json', 'subdir\\app-readiness.json',
                        str(self.root / 'app-readiness.json'), 'https://example.invalid/readiness',
                        '../app-readiness.json', 'copy.json'):
            with self.subTest(locator=locator):
                self.pr_locator(locator)
                with self.assertRaises(ValueError):
                    self.validate()

    def test_pr_handoff_locator_rejects_non_regular_files(self):
        (self.root / 'directory').mkdir()
        os.mkfifo(self.root / 'pipe')
        for locator in ('directory', 'pipe', 'missing'):
            with self.subTest(locator=locator):
                self.pr_locator(locator)
                with self.assertRaisesRegex(ValueError, 'regular canonical file required'):
                    self.validate()

    def test_pr_handoff_nested_relative_regular_file_is_valid(self):
        nested = self.root / 'nested'
        nested.mkdir()
        raw = (self.root / 'app-readiness.json').read_bytes()
        self.a['member_results'][0]['readiness_ref'] = write(self.root, 'nested/app-readiness.json', raw)
        self.pr_locator('app-readiness.json', nested=True)
        self.assertEqual(self.validate(), ('ready', 'achieved'))


if __name__ == '__main__':
    unittest.main()
