"""Synthetic local tests only: never dispatch a model or consume Manager's pilot slot."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts import model_routing as routing

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / 'examples/model-routing'


class RoutingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.state = Path(self.temp.name) / 'SYNTHETIC-reservation.json'
        self.head = routing.git(ROOT, 'rev-parse', 'HEAD').decode().strip()
        self.request = json.loads((EXAMPLES / 'request.json').read_bytes())
        self.policy_raw = (ROOT / 'config/model-routing.yaml').read_bytes()
        self.approval = {'schema_version': '1.0', 'policy_revision': routing.REVISION,
                         'pilot_id': routing.PILOT, 'scope': routing.SCOPE,
                         'approved': True, 'max_launches': 1, 'head_sha': self.head,
                         'independent_review': 'pass', 'same_head_ci': 'pass',
                         'request_sha256': routing.digest(routing.encode(self.request)),
                         'policy_sha256': routing.digest(self.policy_raw)}

    def plan(self, request=None, approval=None, **kwargs):
        request_raw = routing.encode(request or self.request)
        approval = deepcopy(approval or self.approval)
        approval['request_sha256'] = routing.digest(request_raw)
        approval_raw = routing.encode(approval)
        params = dict(approval_pin=routing.digest(approval_raw),
                      policy_pin=routing.digest(self.policy_raw), repo=ROOT, head=self.head)
        params.update(kwargs)
        return routing.plan(request_raw, self.policy_raw, approval_raw, **params)

    def receipt(self, decision):
        reservation = routing.reserve(decision, self.state)
        return {'schema_version': '1.0', 'policy_revision': routing.REVISION,
                'pilot_id': routing.PILOT, 'request_sha256': decision['request_sha256'],
                'reservation_sha256': reservation['reservation_sha256'],
                'admission': 'confirmed', 'observed_model': None, 'observed_effort': None,
                'model_evidence': None, 'effort_evidence': None, 'usage': None}

    def validate(self, decision, receipt, result=None, state_pin=None):
        return routing.validate(decision, self.state.read_bytes(),
                                state_pin or receipt['reservation_sha256'],
                                routing.encode(receipt), result or (EXAMPLES / 'expected.json').read_bytes(),
                                routing.artifact(ROOT, self.head))

    def known(self, receipt, model='gpt-6-luna', effort='low', source='platform_observation'):
        receipt.update(observed_model=model, observed_effort=effort,
                       model_evidence={'source': source, 'reference': 'SYNTHETIC-MODEL-OBSERVATION'},
                       effort_evidence={'source': source, 'reference': 'SYNTHETIC-EFFORT-OBSERVATION'})

    def test_success_and_separate_quality_runtime_results(self):
        decision = self.plan()
        self.assertIsNone(decision['create_arguments'])
        self.assertFalse(decision['runtime_enforced'])
        receipt = self.receipt(decision)
        self.known(receipt)
        result = self.validate(decision, receipt)
        self.assertEqual(result['pilot_result'], 'accepted')
        self.assertEqual(result['quality_result'], 'pass')
        self.assertEqual(result['runtime_evidence'], 'verified')
        self.assertFalse(result['authority_granted'])
        self.assertIsNone(result['usage'])

    def test_strict_unknown_usage_blocks_even_with_matching_model_effort(self):
        decision = self.plan(dict(self.request, mode='Strict'))
        receipt = self.receipt(decision)
        self.known(receipt)
        result = self.validate(decision, receipt)
        self.assertEqual(result['pilot_result'], 'blocked')
        self.assertEqual(result['usage_evidence'], 'unverified')
        self.assertIsNone(result['usage'])
        receipt['usage'] = {'input_tokens': 12, 'output_tokens': 8,
                            'evidence': {'source': 'platform_observation', 'reference': 'SYNTHETIC-USAGE'}}
        result = self.validate(decision, receipt)
        self.assertEqual(result['pilot_result'], 'accepted')
        self.assertEqual(result['usage_evidence'], 'verified')

    def test_exact_arguments_only_after_reservation_and_unknowns_not_copied(self):
        decision = self.plan()
        reserved = routing.reserve(decision, self.state)
        self.assertEqual(reserved['create_arguments'],
                         {'model': 'gpt-6-luna', 'thinking': 'low', 'service_tier': 'standard'})
        saved = json.loads(self.state.read_bytes())
        for field in ('observed_model', 'observed_effort', 'usage', 'create_arguments'):
            self.assertIsNone(saved[field])
        self.assertEqual(saved['launches_consumed'], 1)
        self.assertEqual(self.state.stat().st_mode & 0o777, 0o600)

    def test_missing_observations_strict_vs_best_effort(self):
        for mode in ('Strict', 'BestEffort'):
            with self.subTest(mode=mode):
                self.state = Path(self.temp.name) / mode
                request = dict(self.request, mode=mode)
                decision = self.plan(request)
                receipt = self.receipt(decision)
                result = self.validate(decision, receipt)
                self.assertEqual(result['pilot_result'], 'blocked' if mode == 'Strict' else 'accepted')
                self.assertEqual(result['runtime_evidence'], 'unverified')
                self.assertEqual(result['quality_result'], 'pass')
                self.assertIsNone(result['observed_model'])
                self.assertIsNone(result['observed_effort'])
                self.assertIsNone(result['usage'])

    def test_known_model_or_effort_mismatch_blocks_even_with_one_unknown(self):
        decision = self.plan()
        receipt = self.receipt(decision)
        for model, effort in [('gpt-6-astra', 'low'), ('gpt-6-luna', 'high'), (None, 'high'), ('other', None)]:
            self.known(receipt, model, effort)
            result = self.validate(decision, receipt)
            self.assertEqual(result['pilot_result'], 'blocked')
            self.assertEqual(result['runtime_evidence'], 'mismatch')
            self.assertEqual(result['quality_result'], 'pass')

    def test_self_report_and_request_are_not_observed_evidence(self):
        request = dict(self.request, mode='Strict')
        decision = self.plan(request)
        receipt = self.receipt(decision)
        for source in ('self_report', 'request'):
            self.known(receipt, source=source)
            receipt['usage'] = {'input_tokens': 0, 'output_tokens': 0,
                                'evidence': {'source': source, 'reference': 'SYNTHETIC-CLAIM'}}
            result = self.validate(decision, receipt)
            self.assertEqual(result['pilot_result'], 'blocked')
            for field in ('observed_model', 'observed_effort', 'model_evidence', 'effort_evidence', 'usage'):
                self.assertIsNone(result[field])
        self.known(receipt)
        receipt['model_evidence'] = None
        self.assertIsNone(self.validate(decision, receipt)['observed_model'])

    def test_unknown_or_rejected_admission_stays_consumed_and_blocks(self):
        decision = self.plan()
        receipt = self.receipt(decision)
        self.known(receipt)
        before = self.state.read_bytes()
        for admission in ('unknown', 'rejected'):
            receipt['admission'] = admission
            result = self.validate(decision, receipt)
            self.assertEqual(result['pilot_result'], 'blocked')
            self.assertEqual(result['reservation_status'], 'consumed_pending_reconciliation')
            self.assertEqual(self.state.read_bytes(), before)
            with self.assertRaises(FileExistsError):
                routing.reserve(decision, self.state)

    def test_duplicate_exhausted_and_concurrent_reservation(self):
        decision = self.plan()
        def attempt():
            try:
                routing.reserve(decision, self.state)
                return True
            except FileExistsError:
                return False
        with ThreadPoolExecutor(max_workers=4) as pool:
            self.assertEqual(sum(pool.map(lambda _: attempt(), range(4))), 1)
        # New approval or mode must not reset the one slot at the same path.
        with self.assertRaises(FileExistsError):
            routing.reserve(self.plan(dict(self.request, mode='Strict')), self.state)

    def test_crash_marker_remains_consumed_without_retry(self):
        decision = self.plan()
        with patch.object(routing.os, 'fsync', side_effect=OSError('SYNTHETIC-CRASH')):
            with self.assertRaises(OSError):
                routing.reserve(decision, self.state)
        with self.assertRaises(FileExistsError):
            routing.reserve(decision, self.state)
        self.state.write_bytes(b'')  # Synthetic crash damage, never reset in production.
        with self.assertRaises(FileExistsError):
            routing.reserve(decision, self.state)

    def test_symlink_state_or_parent_cannot_be_used(self):
        target = Path(self.temp.name) / 'target'
        target.write_text('SYNTHETIC')
        self.state.symlink_to(target)
        with self.assertRaises(FileExistsError):
            routing.reserve(self.plan(), self.state)
        link = Path(self.temp.name) / 'linked-parent'
        link.symlink_to(self.temp.name, target_is_directory=True)
        with self.assertRaises(OSError):
            routing.reserve(self.plan(), link / 'state')
        self.assertEqual(target.read_text(), 'SYNTHETIC')

    def test_invalid_route_and_unsafe_scope_fail_closed(self):
        for key, value in [('requested_model', 'gpt-6-astra'), ('requested_model', 'gpt-6-sol'),
                           ('requested_effort', 'high'), ('service_tier', 'priority'),
                           ('role', 'implementation'), ('role', 'test'), ('role', 'review'),
                           ('scope', 'app-code'), ('scope', 'security-sensitive'),
                           ('scope', 'secrets'), ('scope', 'live-infrastructure'),
                           ('permissions', ['write']), ('mode', 'fallback'),
                           ('policy_revision', 'future'), ('pilot_id', 'NEW-PILOT')]:
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                self.plan(dict(self.request, **{key: value}))
        request = deepcopy(self.request)
        request['artifact']['commit'] = 'main'
        with self.assertRaises(ValueError):
            self.plan(request)
        for field in ('commit', 'sha256', 'size_bytes', 'path', 'repository'):
            request = deepcopy(self.request)
            request['artifact'][field] = 'unsafe'
            with self.assertRaises(ValueError):
                self.plan(request)

    def test_missing_approval_bad_pins_head_or_quality_gates_block(self):
        for key in self.approval:
            approval = dict(self.approval)
            del approval[key]
            # plan helper binds the request; all other missing fields tested here.
            if key != 'request_sha256':
                with self.subTest(key=key), self.assertRaises(ValueError):
                    self.plan(approval=approval)
        for key, value in [('approved', False), ('max_launches', 2),
                           ('independent_review', 'pending'), ('same_head_ci', 'pending'),
                           ('head_sha', '0' * 40), ('policy_sha256', '0' * 64)]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.plan(approval=dict(self.approval, **{key: value}))
        for key in ('approval_pin', 'policy_pin'):
            with self.assertRaises(ValueError):
                self.plan(**{key: '0' * 64})
        with self.assertRaises(ValueError):
            routing.artifact(ROOT, '0' * 40)
        with self.assertRaises(ValueError):
            self.plan(approval={'schema_version': '1.0'})

    def test_artifact_commit_size_hash_and_regular_mode_checks(self):
        head = self.head
        actual = routing.git
        for broken_args, broken_output in [(('cat-file', '-t', routing.PIN['commit']), b'blob\n'),
                                           (('ls-tree', routing.PIN['commit'], '--', routing.PIN['path']), b'120000 blob ' + b'0' * 40 + b'\t' + routing.PIN['path'].encode()),
                                           (('cat-file', '-s', routing.PIN['commit'] + ':' + routing.PIN['path']), b'1'),
                                           (('cat-file', 'blob', routing.PIN['commit'] + ':' + routing.PIN['path']), b'x' * routing.PIN['size_bytes'])]:
            def fake(repo, *args):
                return broken_output if args == broken_args else actual(repo, *args)
            with patch.object(routing, 'git', side_effect=fake), self.assertRaises(ValueError):
                routing.artifact(ROOT, head)

    def test_bad_classification_and_receipt_binding_block_without_fallback(self):
        decision = self.plan()
        receipt = self.receipt(decision)
        expected = json.loads((EXAMPLES / 'expected.json').read_bytes())
        expected['classifications'][0]['classification'] = 'rejected'
        result = self.validate(decision, receipt, routing.encode(expected))
        self.assertEqual(result['quality_result'], 'fail')
        self.assertEqual(result['pilot_result'], 'blocked')
        for field in ('request_sha256', 'reservation_sha256'):
            changed = dict(receipt, **{field: '0' * 64})
            with self.assertRaises(ValueError):
                self.validate(decision, changed)
        with self.assertRaises(ValueError):
            self.validate(decision, receipt, state_pin='0' * 64)
        self.state.write_bytes(self.state.read_bytes() + b' ')
        with self.assertRaises(ValueError):
            self.validate(decision, receipt)

    def test_strict_schema_parser_no_missing_fields_or_zero_fill(self):
        for raw in (b'{"nested":{"x":1,"\\u0078":2}}', b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}', b'\xef\xbb\xbf{}',
                    b'{} trailing', b'x' * (routing.MAX_INPUT + 1)):
            with self.assertRaises(ValueError):
                routing.parse(raw)
        decision = self.plan()
        receipt = self.receipt(decision)
        for field in receipt:
            missing = dict(receipt)
            del missing[field]
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.validate(decision, missing, state_pin=receipt['reservation_sha256'])
        for usage in ({'input_tokens': 0, 'output_tokens': 0},
                      {'input_tokens': -1, 'output_tokens': 0, 'evidence': None}):
            with self.assertRaises(ValueError):
                self.validate(decision, dict(receipt, usage=usage))
        self.assertIsNone(self.validate(decision, receipt)['usage'])

    def test_policy_cannot_enable_rollout_or_astra_and_no_enforcement_claims(self):
        for key in ('global_rollout_enabled', 'astra_automatic_escalation'):
            policy = deepcopy(routing.POLICY)
            policy[key] = True
            raw = routing.encode(policy)
            approval = dict(self.approval, policy_sha256=routing.digest(raw))
            with self.assertRaises(ValueError):
                routing.plan(routing.encode(self.request), raw, routing.encode(approval),
                             routing.digest(routing.encode(approval)), routing.digest(raw), ROOT, self.head)
        workflow = (ROOT / 'workflows/model-escalation.md').read_text()
        for phrase in ('no savings claim', 'no runtime enforcement', 'cross-service', 'PR10', '2 used'):
            self.assertIn(phrase, workflow)

    def test_cli_plan_and_missing_approval_do_not_reserve_or_dispatch(self):
        request = Path(self.temp.name) / 'request.json'
        approval = Path(self.temp.name) / 'approval.json'
        request.write_bytes(routing.encode(self.request))
        approval.write_bytes(routing.encode(self.approval))
        argv = ['python3', str(ROOT / 'scripts/model_routing.py'), 'plan',
                '--request', str(request), '--policy', str(ROOT / 'config/model-routing.yaml'),
                '--approval', str(approval), '--approval-sha256', routing.digest(approval.read_bytes()),
                '--policy-sha256', routing.digest(self.policy_raw), '--repo', str(ROOT), '--head', self.head]
        completed = subprocess.run(argv, capture_output=True, check=False)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIsNone(json.loads(completed.stdout)['create_arguments'])
        self.assertFalse(self.state.exists())
        state = Path(self.temp.name) / 'SYNTHETIC-cli-state'
        argv[2] = 'reserve'
        reserved = subprocess.run(argv + ['--state', str(state)], capture_output=True, check=False)
        self.assertEqual(reserved.returncode, 0, reserved.stderr)
        pin = json.loads(reserved.stdout)['reservation_sha256']
        duplicate = subprocess.run(argv + ['--state', str(state)], capture_output=True, check=False)
        self.assertEqual(duplicate.returncode, 1)
        decision = self.plan()
        receipt = {'schema_version': '1.0', 'policy_revision': routing.REVISION,
                   'pilot_id': routing.PILOT, 'request_sha256': decision['request_sha256'],
                   'reservation_sha256': pin, 'admission': 'confirmed',
                   'observed_model': None, 'observed_effort': None,
                   'model_evidence': None, 'effort_evidence': None, 'usage': None}
        receipt_path = Path(self.temp.name) / 'SYNTHETIC-cli-receipt.json'
        receipt_path.write_bytes(routing.encode(receipt))
        argv[2] = 'validate'
        validation_args = ['--state', str(state), '--state-sha256', pin,
                           '--receipt', str(receipt_path), '--result', str(EXAMPLES / 'expected.json')]
        validated = subprocess.run(argv + validation_args, capture_output=True, check=False)
        self.assertEqual(validated.returncode, 0, validated.stderr)
        self.assertEqual(json.loads(validated.stdout)['runtime_evidence'], 'unverified')
        receipt['observed_model'] = 'gpt-6-astra'
        receipt['model_evidence'] = {'source': 'platform_observation', 'reference': 'SYNTHETIC'}
        receipt_path.write_bytes(routing.encode(receipt))
        validated = subprocess.run(argv + validation_args, capture_output=True, check=False)
        self.assertEqual(validated.returncode, 1)
        self.assertEqual(json.loads(validated.stdout)['runtime_evidence'], 'mismatch')
        argv[2] = 'plan'
        approval.unlink()
        completed = subprocess.run(argv, capture_output=True, check=False)
        self.assertEqual(completed.returncode, 1)
        self.assertNotIn(b'SYNTHETIC-MODEL-OBSERVATION', completed.stdout)


if __name__ == '__main__':
    unittest.main()
