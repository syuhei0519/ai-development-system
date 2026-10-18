#!/usr/bin/env python3
"""Read-only workflow route planning and append-only observation records; never dispatch."""
import argparse
from collections import Counter
import copy
import re
import subprocess

try:
    from .model_routing import (obj, const, nullable, TEXT, HEX, COMMIT, parse, encode,
                                check, pinned, digest, git, PILOT, SCOPE, read_regular)
    from .validate_retry import validate_ledger
except ImportError:
    from model_routing import (obj, const, nullable, TEXT, HEX, COMMIT, parse, encode,
                               check, pinned, digest, git, PILOT, SCOPE, read_regular)
    from validate_retry import validate_ledger

REVISION = 'workflow-best-effort-v1'
ROUTES = {'research-design': ('gpt-6.1-sol', 'high'),
          'review': ('gpt-6.1-sol', 'high'),
          'implementation': ('gpt-6.1-sol', 'medium'),
          'test': ('gpt-6.1-sol', 'medium'), 'knowledge': ('gpt-6.1-sol', 'medium')}
POLICY = {'schema_version': '1.0', 'policy_revision': REVISION,
          'global_rollout_enabled': False, 'authorized_new_dispatch_trial': True,
          'default_mode': 'BestEffort', 'strict_opt_in': True, 'manager_runtime': 'Dots',
          'role_routes': {role: {'model': model, 'thinking': effort} for role, (model, effort) in ROUTES.items()},
          'routine_route': {'role': 'routine-consumer', 'model': 'gpt-6-luna', 'thinking': 'low',
                            'kinds': ['routine_classification', 'routine_extraction', 'routine_formatting'],
                            'read_only': True, 'app_code': False, 'security_sensitive': False,
                            'live_infrastructure': False},
          'service_tier': 'default', 'astra_automatic_escalation': False,
          'manual_astra_only': True, 'business_history_reset': False,
          'historical_evaluations_used': 3, 'historical_evaluation_ceiling': 6,
          'historical_pilot': {'id': PILOT, 'launches_consumed': 1, 'limit': 1,
                               'result': 'PINNED_ARTIFACT_UNAVAILABLE', 'root_cause': 'unknown'}}
ESCALATION = obj({'model': const('gpt-6-astra'),
                  'effort': {'enum': ['low', 'medium', 'high', 'xhigh', 'max', 'ultra']},
                  'reason': {'enum': ['complex_design', 'complex_debug', 'complex_security']},
                  'scope': TEXT, 'budget': {'type': 'integer', 'minimum': 1, 'maximum': 3}})
REQUEST = obj({'schema_version': const('1.0'), 'policy_revision': const(REVISION),
               'role': {'enum': ['manager', *ROUTES, 'routine-consumer']},
               'scope': TEXT, 'task_reference': TEXT, 'attempt': {'type': 'integer', 'minimum': 1, 'maximum': 3},
               'dispatch_kind': {'enum': ['new_task', 'explicit_redispatch']},
               'in_progress': const(False), 'mode': {'enum': ['BestEffort', 'Strict']},
               'task_kind': {'enum': ['specialist', *POLICY['routine_route']['kinds']]},
               'read_only': {'type': 'boolean'}, 'app_code': {'type': 'boolean'},
               'security_sensitive': {'type': 'boolean'}, 'live_infrastructure': {'type': 'boolean'},
               'manual_escalation': nullable(ESCALATION)})
APPROVAL = obj({'schema_version': const('1.0'), 'policy_revision': const(REVISION),
                'approved': const(True), 'explicit_dispatch_decision': const(True),
                'request_sha256': HEX, 'policy_sha256': HEX, 'history_sha256': HEX,
                'head_sha': COMMIT, 'routine_scope_approved': {'type': 'boolean'},
                'manual_escalation': nullable(obj({**ESCALATION['properties'], 'approved': const(True)}))})
EVIDENCE = obj({'source': {'enum': ['platform_metadata', 'human_confirmed_ui', 'ui_selector',
                                   'ui_settings', 'ui_aggregate', 'self_report', 'request', 'unknown']},
                'binding': {'enum': ['execution_task', 'selector_settings', 'aggregate', 'unbound']},
                'task_reference': nullable(TEXT), 'provenance': nullable(TEXT),
                'confirmed_by': nullable(TEXT)})
OBSERVATION = obj({'observed_model': nullable(TEXT), 'observed_effort': nullable(TEXT),
                   'model_evidence': nullable(EVIDENCE), 'effort_evidence': nullable(EVIDENCE),
                   'usage': nullable(obj({'input_tokens': {'type': 'integer', 'minimum': 0},
                                          'output_tokens': {'type': 'integer', 'minimum': 0},
                                          'evidence': EVIDENCE}))})
MAX_INPUT = 65536


def budget(history, request):
    validate_ledger(history)
    if history['scope'] != request['scope'] or request['scope'] in (PILOT, SCOPE) or request['task_reference'] == PILOT:
        raise ValueError('scope mismatch or consumed pilot')
    epoch = history['epochs'][-1]
    counts = Counter(e['kind'] for e in epoch['events'])
    remaining = {kind: limit - counts[kind] for kind, limit in epoch['limits'].items()}
    if epoch['terminal'] != 'open' or any(n <= 0 for n in remaining.values()):
        raise ValueError('business budget exhausted')
    executions = sum(e['kind'] == 'execution' for epoch in history['epochs'] for e in epoch['events'])
    if request['attempt'] != executions + 1:
        raise ValueError('business attempt mismatch')
    prior_work = any(epoch['events'] for epoch in history['epochs'])
    if (request['dispatch_kind'] == 'new_task') == prior_work:
        raise ValueError('new scope versus explicit redispatch mismatch')
    return remaining


def route(request, approval, remaining):
    role = request['role']
    escalation = request['manual_escalation']
    routine = request['task_kind'] != 'specialist'
    if approval['routine_scope_approved'] != routine:
        raise ValueError('routine scope requires separate explicit approval')
    if escalation is not None:
        grant = approval['manual_escalation']
        if (role not in ('research-design', 'implementation', 'test', 'review') or routine or
                escalation['scope'] != request['scope'] or grant != dict(escalation, approved=True) or
                escalation['budget'] > min(remaining['dispatch'], remaining['execution'])):
            raise ValueError('manual escalation requires exact scope/model/effort/remaining-budget approval')
        return escalation['model'], escalation['effort']
    if approval['manual_escalation'] is not None:
        raise ValueError('unexpected escalation grant')
    if routine:
        if (role != 'routine-consumer' or not request['read_only'] or
                any(request[k] for k in ('app_code', 'security_sensitive', 'live_infrastructure'))):
            raise ValueError('Luna is limited to explicitly bounded routine read-only work')
        return 'gpt-6-luna', 'low'
    if role == 'routine-consumer':
        raise ValueError('routine consumer cannot do specialist work')
    if role == 'manager':
        return None, None
    return ROUTES[role]


def qualified(evidence, task_reference):
    return (evidence is not None and
            evidence['source'] in ('platform_metadata', 'human_confirmed_ui') and
            evidence['binding'] == 'execution_task' and evidence['task_reference'] == task_reference and
            evidence['provenance'] is not None and evidence['confirmed_by'] is not None)


def evaluate(base, observations, parent_sha256=None):
    model = effort = usage = model_evidence = effort_evidence = None
    mismatch = False
    for observation in observations:
        check(observation, OBSERVATION)
        for field, evidence_key in [('observed_model', 'model_evidence'), ('observed_effort', 'effort_evidence')]:
            value, evidence = observation[field], observation[evidence_key]
            if value is not None and qualified(evidence, base['task_reference']):
                mismatch |= value != base['requested_model' if field == 'observed_model' else 'requested_effort']
                if field == 'observed_model':
                    model, model_evidence = value, copy.deepcopy(evidence)
                else:
                    effort, effort_evidence = value, copy.deepcopy(evidence)
        claim_usage = observation['usage']
        if claim_usage is not None and qualified(claim_usage['evidence'], base['task_reference']):
            usage = copy.deepcopy(claim_usage)
    known = model is not None and effort is not None
    status = 'mismatch' if mismatch else 'verified' if known else 'unverified'
    if base['role'] == 'manager':
        gate = 'manager_local'
    elif mismatch:
        gate = 'blocked_mismatch'
    elif base['mode'] == 'Strict' and (not known or usage is None):
        gate = 'blocked_strict_unknown'
    else:
        gate = 'allowed_verified' if known else 'allowed_unverified'
    args = None
    if gate.startswith('allowed_'):
        args = {'model': base['requested_model'], 'thinking': base['requested_effort'], 'service_tier': 'default'}
    return dict(copy.deepcopy(base), observed_model=model, observed_effort=effort,
                model_evidence=model_evidence, effort_evidence=effort_evidence,
                usage=usage, usage_status='verified' if usage is not None else 'unverified',
                observation_status=status, observation_history=copy.deepcopy(observations),
                parent_record_sha256=parent_sha256, routing_gate=gate, create_arguments=args)


def plan(request_raw, policy_raw, approval_raw, history_raw, *, approval_pin, policy_pin, history_pin, repo, head):
    request = check(parse(request_raw), REQUEST)
    if encode(parse(pinned(policy_raw, policy_pin))) != encode(POLICY):
        raise ValueError('workflow policy mismatch')
    approval = check(parse(pinned(approval_raw, approval_pin)), APPROVAL)
    history = parse(pinned(history_raw, history_pin))
    if (approval['request_sha256'] != digest(request_raw) or approval['policy_sha256'] != policy_pin or
            approval['history_sha256'] != history_pin or approval['head_sha'] != head):
        raise ValueError('independent approval binding mismatch')
    if not re.fullmatch('[0-9a-f]{40}', head) or git(repo, 'rev-parse', 'HEAD').decode().strip() != head:
        raise ValueError('reviewed checkout head mismatch')
    remaining = budget(history, request)
    model, effort = route(request, approval, remaining)
    base = {'schema_version': '1.0', 'document_type': 'model_routing_record',
            'policy_revision': REVISION, 'mode': request['mode'], 'role': request['role'],
            'scope': request['scope'], 'task_reference': request['task_reference'],
            'dispatch_kind': request['dispatch_kind'], 'attempt': request['attempt'],
            'head_sha': head, 'request_sha256': digest(request_raw), 'policy_sha256': policy_pin,
            'approval_sha256': approval_pin, 'business_history_sha256': history_pin,
            'remaining_business_budget': remaining, 'requested_model': model, 'requested_effort': effort,
            'requested_service_tier': 'default', 'manual_escalation': copy.deepcopy(request['manual_escalation']),
            'manager_runtime': 'Dots' if request['role'] == 'manager' else None,
            'dispatch_reserved': False, 'authority_granted': False, 'runtime_enforced': False,
            'quality_gate': 'not_assessed'}
    return evaluate(base, [])


def observe(initial, previous_raw, previous_pin, observation_raw):
    previous = parse(pinned(previous_raw, previous_pin))
    if not isinstance(previous, dict) or set(previous) != set(initial):
        raise ValueError('invalid routing record fields')
    history, parent = previous['observation_history'], previous['parent_record_sha256']
    if not isinstance(history, list) or len(history) >= 32:
        raise ValueError('observation history limit')
    if (parent is None) != (not history) or (parent is not None and not re.fullmatch('[0-9a-f]{64}', parent)):
        raise ValueError('invalid record parent')
    observation_fields = ('observed_model', 'observed_effort', 'model_evidence', 'effort_evidence',
                          'usage', 'usage_status', 'observation_status', 'observation_history',
                          'parent_record_sha256', 'routing_gate', 'create_arguments')
    base = {k: v for k, v in initial.items() if k not in observation_fields}
    # Recompute every prior derived field and retain every prior claim; no mismatch downgrade.
    if encode(previous) != encode(evaluate(base, history, parent)):
        raise ValueError('prior decision/history changed')
    observation = check(parse(observation_raw), OBSERVATION)
    return evaluate(base, [*history, observation], previous_pin)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['plan', 'observe'])
    for key in ('request', 'policy', 'approval', 'history', 'approval-sha256', 'policy-sha256',
                'history-sha256', 'repo', 'head'):
        parser.add_argument('--' + key, required=True)
    for key in ('record', 'record-sha256', 'observation'):
        parser.add_argument('--' + key)
    args = parser.parse_args()
    if args.action == 'observe' and not all((args.record, args.record_sha256, args.observation)):
        parser.error('--record, --record-sha256, --observation required')
    try:
        read = lambda path: read_regular(path, limit=MAX_INPUT)
        initial = plan(read(args.request), read(args.policy), read(args.approval), read(args.history),
                       approval_pin=args.approval_sha256, policy_pin=args.policy_sha256,
                       history_pin=args.history_sha256, repo=args.repo, head=args.head)
        output = observe(initial, read(args.record), args.record_sha256, read(args.observation)) if args.action == 'observe' else initial
        print(encode(output).decode(), end='')
        return 1 if output['routing_gate'].startswith('blocked_') else 0
    except (ValueError, OSError, TypeError, KeyError, subprocess.SubprocessError, RecursionError):
        print('{"error":"WORKFLOW_ROUTING_BLOCKED","authority_granted":false}')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
