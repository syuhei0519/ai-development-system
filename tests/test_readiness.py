"""Synthetic gate regressions; these do not claim live GitHub or business truth."""
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import unittest

from scripts.validate_readiness import validate, validate_handoff_pair

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / 'examples/readiness'
NOW = datetime(2030, 1, 1, 12, tzinfo=timezone.utc)


def fixture(name='pr-ready-issue-unverified.json'):
    return json.loads((FIXTURES / name).read_text())


class ReadinessTests(unittest.TestCase):
    def setUp(self):
        self.data = fixture()
        self.context = fixture('context.json')

    def errors(self):
        return validate(self.data, self.context, NOW)

    def test_ready_pr_does_not_complete_issue(self):
        self.assertEqual(self.errors(), [])
        self.assertEqual(self.data['merge_readiness']['status'], 'ready')
        self.assertEqual(self.data['issue_completion'], 'unverified')

    def test_implementation_allowed_while_deployment_and_merge_blocked(self):
        data = fixture('implementation-only.json')
        self.assertEqual(validate(data, fixture('automatic-context.json'), NOW), [])
        self.assertEqual(data['implementation_readiness']['status'], 'ready')

    def test_postdeploy_all_measured_can_achieve(self):
        self.assertEqual(validate(fixture('postdeploy-achieved.json'), self.context, NOW), [])

    def test_premature_achieved_and_premerge_deferral_fixtures_rejected(self):
        for name in ('invalid-premature-achieved.json', 'invalid-premerge-deferred.json'):
            with self.subTest(name=name):
                self.assertTrue(validate(fixture(name), self.context, NOW))

    def test_premerge_failed_pending_or_approval_wait_cannot_defer(self):
        for outcome in ('not_met', 'unverified'):
            with self.subTest(outcome=outcome):
                data = deepcopy(self.data)
                data['ac_results'][0]['outcome'] = outcome
                data['ac_results'][0]['deferred'] = deepcopy(data['ac_results'][1]['deferred'])
                data['issue_completion'] = 'not_achieved' if outcome == 'not_met' else 'unverified'
                self.assertTrue(validate(data, self.context, NOW))
        self.data['merge_readiness']['checks']['authorization']['verdict'] = 'pending'
        self.assertTrue(self.errors())

    def test_ci_success_cannot_override_ai_review_failure(self):
        self.data['merge_readiness']['checks']['ai_review']['verdict'] = 'fail'
        self.assertTrue(self.errors())
        self.data['merge_readiness']['status'] = 'blocked'
        self.assertEqual(self.errors(), [])

    def test_each_required_merge_gate_blocks_independently(self):
        for kind in self.data['merge_readiness']['checks']:
            for verdict in ('pending', 'fail'):
                data = deepcopy(self.data)
                data['merge_readiness']['checks'][kind]['verdict'] = verdict
                with self.subTest(kind=kind, verdict=verdict):
                    self.assertTrue(validate(data, self.context, NOW))

    def test_ai_review_cannot_substitute_github_required_review(self):
        check = self.data['merge_readiness']['checks']['github_reviews']
        check['evidence_ids'] = ['merge-ai_review']
        self.assertTrue(self.errors())
        check['evidence_ids'] = ['merge-github_reviews']
        check['verdict'] = 'not_applicable'
        self.assertTrue(self.errors())

    def test_current_context_invalidates_changed_revisions(self):
        for field, value in [('head_sha', 'c' * 40), ('base_sha', 'd' * 40),
                             ('target_revision', 'e' * 40), ('config_revision', 'new-policy'),
                             ('merge_group_sha', 'f' * 40), ('pr_number', 43),
                             ('repository', 'example/another')]:
            context = deepcopy(self.context)
            context['subject'][field] = value
            with self.subTest(field=field):
                self.assertTrue(validate(self.data, context, NOW))

    def test_old_evidence_rejected_even_when_assessment_updated(self):
        for field in ('head_sha', 'base_sha', 'target_revision', 'config_revision', 'merge_group_sha'):
            data, context = deepcopy(self.data), deepcopy(self.context)
            data['subject'][field] = context['subject'][field] = 'c' * 40
            with self.subTest(field=field):
                self.assertTrue(validate(data, context, NOW))

    def test_expiry_future_observation_and_policy_expiry(self):
        for field, value in [('valid_until', '2030-01-01T12:00:00Z'),
                             ('observed_at', '2030-01-01T13:00:00Z')]:
            data = deepcopy(self.data)
            data['evidence'][0][field] = value
            self.assertTrue(validate(data, self.context, NOW))
        later = datetime(2030, 1, 3, tzinfo=timezone.utc)
        self.assertTrue(validate(self.data, self.context, later))
        self.context['policy_valid_until'] = '2030-01-01T12:00:00Z'
        self.assertTrue(self.errors())

    def test_each_readiness_has_own_dependencies(self):
        for group in ('implementation', 'deployment', 'merge'):
            data = deepcopy(self.data)
            data[group + '_readiness']['checks']['dependencies']['verdict'] = 'pending'
            with self.subTest(group=group):
                self.assertTrue(validate(data, self.context, NOW))

    def test_automatic_and_unknown_deployment_fail_closed(self):
        for effect in ('automatic', 'unknown'):
            data = fixture('implementation-only.json')
            context = fixture('automatic-context.json')
            data['deployment_effect'] = context['deployment_effect'] = effect
            data['merge_readiness']['status'] = 'ready'
            with self.subTest(effect=effect):
                self.assertTrue(validate(data, context, NOW))

    def test_forged_no_deploy_effect_or_ac_phase_rejected_against_context(self):
        self.context['deployment_effect'] = 'unknown'
        self.assertTrue(self.errors())
        self.context = fixture('context.json')
        self.data['acceptance_criteria'][0]['verification_phase'] = 'postdeploy'
        self.assertTrue(self.errors())

    def test_deferral_requires_all_followup_fields_and_basis(self):
        for field in self.data['ac_results'][1]['deferred']:
            data = deepcopy(self.data)
            del data['ac_results'][1]['deferred'][field]
            with self.subTest(field=field):
                self.assertTrue(validate(data, self.context, NOW))
        self.data['ac_results'][1]['deferred']['evidence_ids'] = ['measurement']
        self.assertTrue(self.errors())

    def test_missing_deferral_cannot_be_ready(self):
        self.data['ac_results'][1]['deferred'] = None
        self.assertTrue(self.errors())
        self.data['merge_readiness']['status'] = 'blocked'
        self.assertEqual(self.errors(), [])

    def test_postdeploy_fake_measurement_before_deploy_rejected(self):
        self.data = fixture('postdeploy-achieved.json')
        self.data['lifecycle']['deployed_at'] = '2030-01-01T11:00:00Z'
        self.assertTrue(self.errors())
        self.data['lifecycle']['deployed_at'] = None
        self.assertTrue(self.errors())

    def test_postmerge_requires_merge_event(self):
        self.data = fixture('postdeploy-achieved.json')
        self.data['acceptance_criteria'][1]['verification_phase'] = 'postmerge'
        self.context['acceptance_criteria'][1]['verification_phase'] = 'postmerge'
        self.assertEqual(self.errors(), [])
        self.data['lifecycle'] = {'merged_at': None, 'deployed_at': None}
        self.assertTrue(self.errors())

    def test_unknown_duplicate_missing_and_wrong_ac_evidence(self):
        for mutate in (
            lambda d: d['evidence'].append(deepcopy(d['evidence'][0])),
            lambda d: d['ac_results'].pop(),
            lambda d: d['ac_results'].append(deepcopy(d['ac_results'][0])),
            lambda d: d['ac_results'][0].update(evidence_ids=['unknown']),
            lambda d: d['ac_results'][0].update(evidence_ids=['basis']),
            lambda d: d['evidence'][-2].update(ac_ids=['SYNTHETIC-AC-2']),
            lambda d: d['acceptance_criteria'].append(deepcopy(d['acceptance_criteria'][0])),
        ):
            data = deepcopy(self.data)
            mutate(data)
            self.assertTrue(validate(data, self.context, NOW))

    def test_required_queue_needs_merge_group_and_its_checks(self):
        self.context['github_requirements']['queue'] = True
        self.data['merge_readiness']['checks']['github_queue']['verdict'] = 'pass'
        self.assertTrue(self.errors())
        self.data['subject']['merge_group_sha'] = self.context['subject']['merge_group_sha'] = 'c' * 40
        self.data['subject']['target_revision'] = self.context['subject']['target_revision'] = 'c' * 40
        self.assertTrue(self.errors())  # old check targets are still stale
        for e in self.data['evidence']:
            e['subject'] = deepcopy(self.context['subject'])
        self.assertEqual(self.errors(), [])

    def test_test_and_review_must_be_independent(self):
        for kind in ('independent_test', 'ai_review'):
            for change in ({'independent': False}, {'producer': self.data['implementation_actor']}):
                data = deepcopy(self.data)
                next(e for e in data['evidence'] if e['kind'] == kind).update(change)
                self.assertTrue(validate(data, self.context, NOW))

    def test_merge_group_cannot_reuse_head_only_test_target(self):
        self.data['subject']['merge_group_sha'] = self.context['subject']['merge_group_sha'] = 'c' * 40
        for e in self.data['evidence']:
            e['subject'] = deepcopy(self.context['subject'])
        self.assertTrue(self.errors())

    def test_unresolved_design_blocks_implementation_and_merge_only(self):
        self.data['implementation_readiness']['checks']['design'].update(
            verdict='pending', evidence_ids=[])
        self.assertTrue(self.errors())
        self.data['implementation_readiness']['status'] = 'blocked'
        self.data['merge_readiness']['status'] = 'blocked'
        self.assertEqual(self.errors(), [])

    def test_pending_gate_is_valid_blocked_record(self):
        self.data['merge_readiness']['checks']['ci'].update(verdict='pending', evidence_ids=[])
        self.data['merge_readiness']['status'] = 'blocked'
        self.assertEqual(self.errors(), [])

    def test_no_pr_cannot_be_merge_ready(self):
        self.data['subject']['pr_number'] = self.context['subject']['pr_number'] = None
        for e in self.data['evidence']:
            e['subject']['pr_number'] = None
        self.assertTrue(self.errors())
        self.data['merge_readiness']['status'] = 'blocked'
        self.assertEqual(self.errors(), [])

    def test_strict_schema_unknown_fields_empty_text_invalid_time(self):
        for mutate in (lambda d: d.update(unexpected=True),
                       lambda d: d.update(implementation_actor=' '),
                       lambda d: d.update(evaluated_at='bad-date'),
                       lambda d: d['subject'].update(head_sha='main'),
                       lambda d: d.update(assessor_role='implementation'),
                       lambda d: d['merge_readiness']['checks'].pop('ci')):
            data = deepcopy(self.data)
            mutate(data)
            self.assertTrue(validate(data, self.context, NOW))

    def test_handoff_pair_prevents_premature_final_achieved(self):
        handoff = fixture('manager.handoff.json')
        self.assertEqual(validate_handoff_pair(self.data, handoff, readiness_bytes=(FIXTURES / 'pr-ready-issue-unverified.json').read_bytes(), readiness_path=FIXTURES / 'pr-ready-issue-unverified.json', handoff_path=FIXTURES / 'manager.handoff.json'), [])
        handoff['final_assessment']['outcome'] = 'achieved'
        handoff['final_assessment']['ac_results'][1].update(
            outcome='met', evidence_ids=[handoff['evidence'][0]['id']])
        self.assertTrue(validate_handoff_pair(self.data, handoff, readiness_bytes=(FIXTURES / 'pr-ready-issue-unverified.json').read_bytes(), readiness_path=FIXTURES / 'pr-ready-issue-unverified.json', handoff_path=FIXTURES / 'manager.handoff.json'))

    def test_record_validator_does_not_certify_truth(self):
        self.data['evidence'][0]['observation'] = 'synthetic sample: unsupported assertion'
        self.assertEqual(self.errors(), [])

    def test_cli_exit_codes_replay_and_cwd_independence(self):
        script = str(ROOT / 'scripts/validate_readiness.py')
        base = [sys.executable, script, str(FIXTURES / 'pr-ready-issue-unverified.json')]
        options = ['--context', str(FIXTURES / 'context.json'), '--at', NOW.isoformat()]
        for args, code in [(base + options, 0), (base, 2),
                           (base + options + ['--at', 'bad'], 1),
                           (base + options + ['--at', '2030-01-01T12:00:00'], 1),
                           ([sys.executable, script, str(FIXTURES / 'missing.json')] + options, 1),
                           ([sys.executable, script, str(FIXTURES / 'invalid-premature-achieved.json')] + options, 1)]:
            with self.subTest(args=args):
                result = subprocess.run(args, cwd=ROOT.parent, capture_output=True, text=True)
                self.assertEqual(result.returncode, code, result.stderr)


if __name__ == '__main__':
    unittest.main()
