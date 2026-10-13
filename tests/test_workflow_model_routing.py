"""Synthetic workflow decisions only; no reservation, inference, task launch or benchmark."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from scripts import workflow_model_routing as routing
from scripts import model_routing as pilot
from scripts.validate_retry import transition

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / 'examples/workflow-model-routing'


class WorkflowRoutingTests(unittest.TestCase):
    def setUp(self):
        self.head = routing.git(ROOT, 'rev-parse', 'HEAD').decode().strip()
        self.request = json.loads((EXAMPLES / 'request.json').read_bytes())
        self.history = json.loads((EXAMPLES / 'history.synthetic.json').read_bytes())
        self.policy_raw = (ROOT / 'config/workflow-model-routing.yaml').read_bytes()
        self.observation = json.loads((EXAMPLES / 'observation.template.json').read_bytes())

    def approval(self, request, history):
        return {'schema_version': '1.0', 'policy_revision': routing.REVISION,
                'approved': True, 'explicit_dispatch_decision': True,
                'request_sha256': routing.digest(routing.encode(request)),
                'policy_sha256': routing.digest(self.policy_raw),
                'history_sha256': routing.digest(routing.encode(history)), 'head_sha': self.head,
                'routine_scope_approved': request['task_kind'] != 'specialist',
                'manual_escalation': None}

    def plan(self, request=None, history=None, approval=None, **pins):
        request, history = request or self.request, history or self.history
        approval = approval or self.approval(request, history)
        raw = routing.encode(approval)
        kwargs = {'approval_pin': routing.digest(raw), 'policy_pin': routing.digest(self.policy_raw),
                  'history_pin': routing.digest(routing.encode(history)), 'repo': ROOT, 'head': self.head}
        kwargs.update(pins)
        return routing.plan(routing.encode(request), self.policy_raw, raw, routing.encode(history), **kwargs)

    def evidence(self, source='human_confirmed_ui', binding='execution_task', **updates):
        return dict({'source': source, 'binding': binding, 'task_reference': self.request['task_reference'],
                     'provenance': 'SYNTHETIC per-task execution panel, observed 2030-01-01T00:00:00Z',
                     'confirmed_by': 'SYNTHETIC-HUMAN-CONFIRMER'}, **updates)

    def known(self, source='human_confirmed_ui', model='gpt-6.1-sol', effort='medium', **updates):
        evidence = self.evidence(source=source, **updates)
        return {'observed_model': model, 'observed_effort': effort,
                'model_evidence': evidence, 'effort_evidence': deepcopy(evidence), 'usage': None}

    def observe(self, initial, previous, observation):
        raw = routing.encode(previous)
        return routing.observe(initial, raw, routing.digest(raw), routing.encode(observation))

    def test_all_role_routes_manager_stays_dots(self):
        routes = {'research-design': ('gpt-6.1-sol', 'high'), 'review': ('gpt-6.1-sol', 'high'),
                  'implementation': ('gpt-6.1-sol', 'medium'), 'test': ('gpt-6.1-sol', 'medium'),
                  'knowledge': ('gpt-6.1-sol', 'medium'), 'manager': (None, None)}
        for role, expected in routes.items():
            with self.subTest(role=role):
                record = self.plan(dict(self.request, role=role))
                self.assertEqual((record['requested_model'], record['requested_effort']), expected)
                if role == 'manager':
                    self.assertEqual(record['manager_runtime'], 'Dots')
                    self.assertIsNone(record['create_arguments'])
                else:
                    self.assertEqual(record['create_arguments'],
                                     {'model': expected[0], 'thinking': expected[1], 'service_tier': 'default'})
                    self.assertEqual(record['routing_gate'], 'allowed_unverified')
                self.assertFalse(record['dispatch_reserved'])
                self.assertFalse(record['authority_granted'])
                self.assertFalse(record['runtime_enforced'])
                self.assertEqual(record['quality_gate'], 'not_assessed')

    def routine(self, kind='routine_classification'):
        return dict(self.request, role='routine-consumer', task_kind=kind, read_only=True, app_code=False)

    def test_luna_only_explicit_routine_classification_extraction_formatting(self):
        for kind in routing.POLICY['routine_route']['kinds']:
            request = self.routine(kind)
            record = self.plan(request)
            self.assertEqual(record['create_arguments'], {'model': 'gpt-6-luna', 'thinking': 'low', 'service_tier': 'default'})
        request = self.routine()
        for key, value in [('role', 'implementation'), ('role', 'test'), ('role', 'knowledge'),
                           ('role', 'review'), ('role', 'research-design'), ('role', 'manager'),
                           ('read_only', False), ('app_code', True), ('security_sensitive', True),
                           ('live_infrastructure', True), ('task_kind', 'specialist')]:
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                self.plan(dict(request, **{key: value}))
        approval = self.approval(request, self.history)
        approval['routine_scope_approved'] = False
        with self.assertRaises(ValueError):
            self.plan(request, approval=approval)
        with self.assertRaises(ValueError):
            self.plan(dict(self.request, requested_model='gpt-6-luna'))

    def test_manual_astra_requires_model_effort_scope_budget_and_explicit_grant(self):
        escalation = {'model': 'gpt-6-astra', 'effort': 'high', 'scope': self.request['scope'],
                      'reason': 'complex_debug', 'budget': 1}
        request = dict(self.request, manual_escalation=escalation)
        with self.assertRaises(ValueError):
            self.plan(request)
        approval = self.approval(request, self.history)
        approval['manual_escalation'] = dict(escalation, approved=True)
        self.assertEqual(self.plan(request, approval=approval)['create_arguments'],
                         {'model': 'gpt-6-astra', 'thinking': 'high', 'service_tier': 'default'})
        for key in escalation:
            broken = deepcopy(request)
            del broken['manual_escalation'][key]
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.plan(broken, approval=approval)
        for key, value in [('model', 'gpt-6-luna'), ('effort', 'guess'), ('scope', 'changed'),
                           ('budget', 0), ('budget', 4), ('reason', 'authentication'),
                           ('reason', 'missing_input'), ('reason', 'artifact_retrieval'),
                           ('reason', 'network'), ('reason', 'environment'), ('reason', 'approval')]:
            broken = deepcopy(request)
            broken['manual_escalation'][key] = value
            grant = self.approval(broken, self.history)
            grant['manual_escalation'] = dict(broken['manual_escalation'], approved=True)
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                self.plan(broken, approval=grant)
        for role in ('manager', 'knowledge', 'routine-consumer'):
            with self.assertRaises(ValueError):
                self.plan(dict(request, role=role), approval=approval)
        self.assertFalse(routing.POLICY['astra_automatic_escalation'])
        self.assertEqual(self.plan()['requested_model'], 'gpt-6.1-sol')

    def test_unknown_strict_vs_best_effort_no_zero_usage_or_request_copy(self):
        for mode in ('Strict', 'BestEffort'):
            record = self.plan(dict(self.request, mode=mode))
            self.assertEqual(record['routing_gate'], 'blocked_strict_unknown' if mode == 'Strict' else 'allowed_unverified')
            self.assertEqual(record['observation_status'], 'unverified')
            for field in ('observed_model', 'observed_effort', 'usage', 'model_evidence', 'effort_evidence'):
                self.assertIsNone(record[field])
            updated = self.observe(record, record, self.observation)
            self.assertEqual(updated['routing_gate'], record['routing_gate'])
            self.assertEqual(updated['observation_history'], [self.observation])

    def test_source_qualified_ui_and_platform_observations(self):
        initial = self.plan()
        for source in ('human_confirmed_ui', 'platform_metadata'):
            result = self.observe(initial, initial, self.known(source=source))
            self.assertEqual(result['observation_status'], 'verified')
            self.assertEqual(result['observed_model'], 'gpt-6.1-sol')
            self.assertEqual(result['model_evidence']['source'], source)
            self.assertEqual(result['effort_evidence']['confirmed_by'], 'SYNTHETIC-HUMAN-CONFIRMER')
            self.assertIsNone(result['usage'])
        for source in ('ui_selector', 'ui_settings', 'ui_aggregate', 'self_report', 'request', 'unknown'):
            result = self.observe(initial, initial, self.known(source=source, model='gpt-6-astra'))
            self.assertEqual(result['routing_gate'], 'allowed_unverified')
            self.assertIsNone(result['observed_model'])
            self.assertEqual(result['observation_history'][0]['model_evidence']['source'], source)
        for updates in ({'binding': 'selector_settings'}, {'binding': 'aggregate'}, {'binding': 'unbound'},
                        {'task_reference': 'OTHER-SYNTHETIC-TASK'}, {'task_reference': None},
                        {'confirmed_by': None}, {'provenance': None}):
            result = self.observe(initial, initial, self.known(**updates))
            self.assertEqual(result['observation_status'], 'unverified')
            self.assertIsNone(result['observed_effort'])

    def test_known_mismatch_sticky_no_fallback_and_all_prior_claims_retained(self):
        for mode in ('Strict', 'BestEffort'):
            initial = self.plan(dict(self.request, mode=mode))
            for model, effort in [('gpt-6-luna', 'medium'), ('gpt-6.1-sol', 'low'), (None, 'high')]:
                bad = self.observe(initial, initial, self.known(model=model, effort=effort))
                self.assertEqual(bad['routing_gate'], 'blocked_mismatch')
                self.assertIsNone(bad['create_arguments'])
                later = self.observe(initial, bad, self.known())
                self.assertEqual(later['routing_gate'], 'blocked_mismatch')
                self.assertEqual(later['observation_history'][:-1], bad['observation_history'])
                self.assertEqual(later['parent_record_sha256'], routing.digest(routing.encode(bad)))

    def test_strict_requires_qualified_usage_no_aggregate_inference(self):
        initial = self.plan(dict(self.request, mode='Strict'))
        observation = self.known()
        result = self.observe(initial, initial, observation)
        self.assertEqual(result['routing_gate'], 'blocked_strict_unknown')
        observation['usage'] = {'input_tokens': 0, 'output_tokens': 0,
                                'evidence': self.evidence(source='ui_aggregate', binding='aggregate')}
        self.assertIsNone(self.observe(initial, initial, observation)['usage'])
        observation['usage']['evidence'] = self.evidence()
        result = self.observe(initial, initial, observation)
        self.assertEqual(result['routing_gate'], 'allowed_verified')
        self.assertEqual(result['usage']['input_tokens'], 0)  # Evidenced zero, never a fill value.
        with self.assertRaises(ValueError):
            self.observe(initial, initial, dict(observation, usage={'input_tokens': 0, 'output_tokens': 0}))

    def test_approval_pins_scope_current_head_in_progress_and_modes(self):
        approval = self.approval(self.request, self.history)
        for key, value in [('approved', False), ('explicit_dispatch_decision', False), ('head_sha', '0' * 40),
                           ('request_sha256', '0' * 64), ('history_sha256', '0' * 64), ('policy_sha256', '0' * 64)]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.plan(approval=dict(approval, **{key: value}))
        for key in ('approval_pin', 'history_pin', 'policy_pin'):
            with self.assertRaises(ValueError):
                self.plan(**{key: '0' * 64})
        for request in (dict(self.request, in_progress=True), dict(self.request, mode='fallback'),
                        dict(self.request, role='unapproved-role'), dict(self.request, scope='changed-scope')):
            with self.assertRaises(ValueError):
                self.plan(request)

    def used_history(self):
        history = deepcopy(self.history)
        history['epochs'][0]['events'] = [{'kind': 'dispatch', 'result': 'succeeded', 'evidence': 'SYNTHETIC-DISPATCH'},
                                         {'kind': 'execution', 'result': 'failed', 'evidence': 'SYNTHETIC-FAILURE'}]
        return history

    def test_redispatch_needs_new_explicit_decision_preserves_old_budgets(self):
        history = self.used_history()
        original = routing.encode(history)
        with self.assertRaises(ValueError):
            self.plan(history=history)
        request = dict(self.request, attempt=2, dispatch_kind='explicit_redispatch')
        record = self.plan(request, history)
        self.assertEqual(record['remaining_business_budget'], {'dispatch': 2, 'execution': 2, 'delivery': 3})
        self.assertEqual(routing.encode(history), original)
        self.assertEqual(record['business_history_sha256'], routing.digest(original))
        approval = self.approval(request, history)
        approval['explicit_dispatch_decision'] = False
        with self.assertRaises(ValueError):
            self.plan(request, history, approval)
        escalation = {'model': 'gpt-6-astra', 'effort': 'high', 'scope': request['scope'],
                      'reason': 'complex_debug', 'budget': 3}
        request['manual_escalation'] = escalation
        approval = self.approval(request, history)
        approval['manual_escalation'] = dict(escalation, approved=True)
        with self.assertRaises(ValueError):
            self.plan(request, history, approval)
        candidate = deepcopy(history)
        candidate['epochs'][0]['events'].append({'kind': 'dispatch', 'result': 'succeeded', 'evidence': 'SYNTHETIC-NEXT'})
        transition(original, routing.encode(candidate), routing.digest(original))
        reset = deepcopy(history)
        reset['epochs'][0]['events'] = []
        with self.assertRaises(ValueError):
            transition(original, routing.encode(reset), routing.digest(original))

    def test_exhausted_retry_and_consumed_pilot_not_renewed_by_route(self):
        for kind in ('dispatch', 'execution', 'delivery'):
            history = deepcopy(self.history)
            history['epochs'][0]['events'] = [{'kind': kind, 'result': 'failed', 'evidence': 'SYNTHETIC-FAILURE'}] * 3
            history['epochs'][0]['terminal'] = 'RETRY_LIMIT_REACHED'
            with self.assertRaises(ValueError):
                self.plan(dict(self.request, dispatch_kind='explicit_redispatch'), history)
        for scope in (pilot.PILOT, pilot.SCOPE):
            request = self.routine()
            request['scope'] = scope
            history = deepcopy(self.history)
            history['scope'] = scope
            with self.assertRaises(ValueError):
                self.plan(request, history)
        with self.assertRaises(ValueError):
            self.plan(dict(self.routine(), task_reference=pilot.PILOT))
        self.assertEqual(routing.POLICY['historical_evaluations_used'], 3)
        self.assertEqual(routing.POLICY['historical_pilot']['launches_consumed'], 1)
        self.assertEqual(routing.POLICY['historical_pilot']['result'], 'PINNED_ARTIFACT_UNAVAILABLE')
        with self.assertRaises(ValueError):
            pilot.check({'error': 'PINNED_ARTIFACT_UNAVAILABLE'}, pilot.RESULT)
        self.assertEqual(hashlib.sha256((ROOT / 'config/model-routing.yaml').read_bytes()).hexdigest(),
                         '2f791794b3672e7cc310ae8e564c46f26b295f3ab416ff661ce9a92ec29cc082')

    def test_previous_record_tampering_or_wrong_pin_is_rejected(self):
        initial = self.plan()
        raw = routing.encode(initial)
        with self.assertRaises(ValueError):
            routing.observe(initial, raw, '0' * 64, routing.encode(self.observation))
        for key, value in [('role', 'review'), ('requested_model', 'gpt-6-astra'), ('attempt', 1),
                           ('business_history_sha256', '0' * 64), ('authority_granted', True)]:
            bad = dict(initial, **{key: value})
            if bad == initial:
                bad[key] = 2
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.observe(initial, bad, self.observation)
        updated = self.observe(initial, initial, self.known(model='gpt-6-luna'))
        updated['routing_gate'] = 'allowed_verified'
        with self.assertRaises(ValueError):
            self.observe(initial, updated, self.observation)

    def test_retained_pr10_prefix_hashes(self):
        for name, size, pin in [('2026-10-13-model-routing-findings.md', 14349, '99e627df84da2e9e1022d76cc12e6d311e4db76c796aa838cb7fb98d835b4876'),
                                ('README.md', 1456, '0f177595e7defe0c2928a11a646599e48e11a48410f745c7cc89352fbb500670')]:
            raw = (ROOT / 'records/model-evaluations' / name).read_bytes()
            self.assertEqual(hashlib.sha256(raw[:size]).hexdigest(), pin)
            self.assertIn(b'2026-10-13 later authorization', raw[size:])
            self.assertIn(b'3/6', raw[size:])
            self.assertIn(b'PINNED_ARTIFACT_UNAVAILABLE', raw[size:])

    def test_cli_only_plan_observe_no_reserve_or_task_calls(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            values = {'request': self.request, 'policy': routing.POLICY, 'history': self.history,
                      'approval': self.approval(self.request, self.history), 'observation': self.observation}
            for name, value in values.items():
                (directory / name).write_bytes(routing.encode(value))
            # Bind raw policy bytes selected for this isolated synthetic CLI test.
            values['approval']['policy_sha256'] = routing.digest((directory / 'policy').read_bytes())
            (directory / 'approval').write_bytes(routing.encode(values['approval']))
            args = ['python3', str(ROOT / 'scripts/workflow_model_routing.py'), 'plan']
            for name in ('request', 'policy', 'history', 'approval'):
                args += ['--' + name, str(directory / name)]
            for name in ('policy', 'history', 'approval'):
                args += ['--' + name + '-sha256', routing.digest((directory / name).read_bytes())]
            args += ['--repo', str(ROOT), '--head', self.head]
            before = set(directory.iterdir())
            result = subprocess.run(args, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(set(directory.iterdir()), before)
            self.assertEqual(json.loads(result.stdout)['create_arguments']['service_tier'], 'default')
            (directory / 'record').write_bytes(result.stdout)
            args[2] = 'observe'
            result = subprocess.run(args + ['--record', str(directory / 'record'), '--record-sha256', routing.digest((directory / 'record').read_bytes()),
                                            '--observation', str(directory / 'observation')], capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(len(json.loads(result.stdout)['observation_history']), 1)
            args[2] = 'reserve'
            result = subprocess.run(args, capture_output=True)
            self.assertEqual(result.returncode, 2)


if __name__ == '__main__':
    unittest.main()
