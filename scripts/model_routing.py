#!/usr/bin/env python3
"""Local one-shot planner/validator. No network, inference, or task dispatch."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

from jsonschema import Draft202012Validator
try:
    from regular_file import read_regular
except ImportError:
    from scripts.regular_file import read_regular

REVISION = 'bounded-read-only-v1'
PILOT = 'SYNTHETIC-PUBLIC-CLASSIFICATION-01'
SCOPE = 'public-synthetic-read-only-classification'
PIN = {'repository': 'syuhei0519/ai-development-system',
       'commit': '1e0115a27ace0ed7116230e46560648dd1476558',
       'path': 'examples/model-routing/candidates.json', 'size_bytes': 871,
       'sha256': '9883284325ae2d6877d085b4e4b2fb22bfd9710aaf862c99e7f7dd49cf7d7a71'}
POLICY = {'schema_version': '1.0', 'policy_revision': REVISION,
          'global_rollout_enabled': False, 'ordinary_development_policy': 'Strict',
          'preserve_agent_defaults': True, 'astra_automatic_escalation': False,
          'pilot': {'id': PILOT, 'explicit_opt_in_required': True, 'scope': SCOPE,
                    'max_launches': 1, 'automatic_retry': False,
                    'automatic_escalation': False, 'requested_model': 'gpt-6-luna',
                    'requested_effort': 'low', 'service_tier': 'standard'}}
RULES = {'rejected': 'public_safe=false OR evidence_complete=false',
         'deferred': 'otherwise reusable=false', 'adopted': 'otherwise'}
MAX_INPUT = 65536
HEX = {'type': 'string', 'pattern': '^[0-9a-f]{64}$'}
COMMIT = {'type': 'string', 'pattern': '^[0-9a-f]{40}$'}
TEXT = {'type': 'string', 'minLength': 1, 'maxLength': 256, 'pattern': r'^\S(?:[^\r\n]*\S)?$'}
NULL = {'type': 'null'}


def const(value):
    return {'const': value}


def obj(properties):
    return {'type': 'object', 'properties': properties,
            'required': list(properties), 'additionalProperties': False}


def nullable(schema):
    return {'anyOf': [NULL, schema]}


REQUEST = obj({'schema_version': const('1.0'), 'policy_revision': const(REVISION),
               'pilot_id': const(PILOT), 'mode': {'enum': ['Strict', 'BestEffort']},
               'scope': const(SCOPE), 'role': const('classification-consumer'),
               'permissions': const(['read_pinned_file', 'return_classification']),
               'requested_model': const('gpt-6-luna'), 'requested_effort': const('low'),
               'service_tier': const('standard'), 'artifact': const(PIN)})
APPROVAL = obj({'schema_version': const('1.0'), 'policy_revision': const(REVISION),
                'pilot_id': const(PILOT), 'scope': const(SCOPE),
                'approved': const(True), 'max_launches': const(1),
                'request_sha256': HEX, 'policy_sha256': HEX, 'head_sha': COMMIT,
                'independent_review': const('pass'), 'same_head_ci': const('pass')})
EVIDENCE = obj({'source': {'enum': ['platform_observation', 'self_report', 'request']},
                'reference': TEXT})
RECEIPT = obj({'schema_version': const('1.0'), 'policy_revision': const(REVISION),
               'pilot_id': const(PILOT), 'request_sha256': HEX, 'reservation_sha256': HEX,
               'admission': {'enum': ['confirmed', 'unknown', 'rejected']},
               'observed_model': nullable(TEXT), 'observed_effort': nullable(TEXT),
               'model_evidence': nullable(EVIDENCE), 'effort_evidence': nullable(EVIDENCE),
               'usage': nullable(obj({'input_tokens': {'type': 'integer', 'minimum': 0},
                                      'output_tokens': {'type': 'integer', 'minimum': 0},
                                      'evidence': EVIDENCE}))})
CLASSIFICATION = obj({'id': TEXT, 'classification': {'enum': ['adopted', 'deferred', 'rejected']}})
RESULT = obj({'classifications': {'type': 'array', 'minItems': 5, 'maxItems': 5,
                                  'items': CLASSIFICATION}})
CANDIDATE = obj({'id': TEXT, 'public_safe': {'type': 'boolean'},
                 'evidence_complete': {'type': 'boolean'}, 'reusable': {'type': 'boolean'}})
ARTIFACT = obj({'schema_version': const('1.0'), 'publication': const('synthetic_sample'),
                'rules': const(RULES), 'candidates': {'type': 'array', 'minItems': 5,
                                                    'maxItems': 5, 'items': CANDIDATE}})


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def encode(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()


def parse(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate JSON key')
            result[key] = value
        return result
    def nonfinite(_):
        raise ValueError('nonfinite JSON value')
    if len(raw) > MAX_INPUT:
        raise ValueError('input size limit')
    return json.loads(raw.decode('utf-8'), object_pairs_hook=pairs, parse_constant=nonfinite)


def check(value, schema):
    # Do not echo private inputs or full validation messages.
    if not Draft202012Validator(schema).is_valid(value):
        raise ValueError('invalid schema')
    return value


def pinned(raw, expected):
    if not re.fullmatch('[0-9a-f]{64}', expected) or digest(raw) != expected:
        raise ValueError('digest mismatch')
    return raw


def git(repo, *args):
    return subprocess.run(['git', '--no-replace-objects', '-C', str(repo), *args],
                          check=True, capture_output=True, timeout=10).stdout


def artifact(repo, head):
    if not re.fullmatch('[0-9a-f]{40}', head):
        raise ValueError('full head commit required')
    if git(repo, 'rev-parse', 'HEAD').decode().strip() != head:
        raise ValueError('checkout head mismatch')
    if git(repo, 'cat-file', '-t', PIN['commit']).strip() != b'commit':
        raise ValueError('commit object required')
    git(repo, 'merge-base', '--is-ancestor', PIN['commit'], head)
    entry = git(repo, 'ls-tree', PIN['commit'], '--', PIN['path']).decode().strip()
    if not re.fullmatch(r'100644 blob [0-9a-f]{40}\t' + re.escape(PIN['path']), entry):
        raise ValueError('regular pinned blob required')
    name = PIN['commit'] + ':' + PIN['path']
    if int(git(repo, 'cat-file', '-s', name)) != PIN['size_bytes']:
        raise ValueError('artifact size mismatch')
    raw = git(repo, 'cat-file', 'blob', name)
    if len(raw) != PIN['size_bytes']:
        raise ValueError('artifact truncated')
    return check(parse(pinned(raw, PIN['sha256'])), ARTIFACT)


def plan(request_raw, policy_raw, approval_raw, approval_pin, policy_pin, repo, head):
    request = check(parse(request_raw), REQUEST)
    if encode(parse(pinned(policy_raw, policy_pin))) != encode(POLICY):
        raise ValueError('unsupported policy revision or rollout')
    approval = check(parse(pinned(approval_raw, approval_pin)), APPROVAL)
    if (approval['request_sha256'] != digest(request_raw) or
            approval['policy_sha256'] != digest(policy_raw) or approval['head_sha'] != head):
        raise ValueError('approval binding mismatch')
    artifact(repo, head)
    return {'schema_version': '1.0', 'policy_revision': REVISION, 'pilot_id': PILOT,
            'scope': SCOPE, 'mode': request['mode'], 'head_sha': head,
            'request_sha256': digest(request_raw), 'policy_sha256': digest(policy_raw),
            'approval_sha256': digest(approval_raw),
            'requested_model': request['requested_model'],
            'requested_effort': request['requested_effort'],
            'service_tier': request['service_tier'], 'artifact': dict(PIN),
            'observed_model': None, 'observed_effort': None, 'usage': None,
            'runtime_evidence': 'unverified', 'runtime_enforced': False,
            'authority_granted': False, 'local_reservation_created': False,
            'create_arguments': None}


def reserve(decision, state):
    """Exclusive immutable marker; supported on one trusted local POSIX filesystem."""
    state = Path(state).absolute()
    if '..' in state.parts:
        raise ValueError('unsafe state path')
    # Pin each directory with no-follow open. No implicit mkdir/reset API.
    parent = os.open(state.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    fd = None
    try:
        for part in state.parts[1:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            os.close(parent)
            parent = child
        saved = dict(decision, local_reservation_created=True,
                     status='consumed_pending_reconciliation', launches_consumed=1)
        raw = encode(saved)
        # Existence, even a partial marker from a crash, permanently consumes the slot.
        fd = os.open(state.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600, dir_fd=parent)
        with os.fdopen(fd, 'wb') as stream:
            fd = None
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.fsync(parent)
        return dict(saved, reservation_sha256=digest(raw),
                    create_arguments={'model': saved['requested_model'],
                                      'thinking': saved['requested_effort'],
                                      'service_tier': saved['service_tier']})
    finally:
        if fd is not None:
            os.close(fd)
        os.close(parent)


def validate(decision, state_raw, state_pin, receipt_raw, result_raw, candidates):
    expected_state = dict(decision, local_reservation_created=True,
                          status='consumed_pending_reconciliation', launches_consumed=1)
    if encode(parse(pinned(state_raw, state_pin))) != encode(expected_state):
        raise ValueError('reservation binding mismatch')
    receipt = check(parse(receipt_raw), RECEIPT)
    if (receipt['request_sha256'] != decision['request_sha256'] or
            receipt['reservation_sha256'] != state_pin):
        raise ValueError('receipt binding mismatch')
    result = check(parse(result_raw), RESULT)
    expected = [{'id': c['id'], 'classification':
                 'rejected' if not c['public_safe'] or not c['evidence_complete'] else
                 'deferred' if not c['reusable'] else 'adopted'} for c in candidates['candidates']]
    quality = 'pass' if result['classifications'] == expected else 'fail'
    def observed(field, evidence):
        ev = receipt[evidence]
        return receipt[field] if ev and ev['source'] == 'platform_observation' else None
    model = observed('observed_model', 'model_evidence')
    effort = observed('observed_effort', 'effort_evidence')
    mismatch = ((model is not None and model != decision['requested_model']) or
                (effort is not None and effort != decision['requested_effort']))
    known = model is not None and effort is not None
    runtime = 'mismatch' if mismatch else 'verified' if known else 'unverified'
    usage = receipt['usage']
    if usage is not None and usage['evidence']['source'] != 'platform_observation':
        usage = None
    accepted = (quality == 'pass' and not mismatch and receipt['admission'] == 'confirmed'
                and ((known and usage is not None) or decision['mode'] == 'BestEffort'))
    return {'policy_revision': REVISION, 'pilot_id': PILOT, 'mode': decision['mode'],
            'requested_model': decision['requested_model'], 'requested_effort': decision['requested_effort'],
            'observed_model': model, 'observed_effort': effort,
            'model_evidence': receipt['model_evidence'] if model is not None else None,
            'effort_evidence': receipt['effort_evidence'] if effort is not None else None,
            'usage': usage, 'usage_evidence': 'verified' if usage is not None else 'unverified',
            'runtime_evidence': runtime, 'quality_result': quality,
            'admission': receipt['admission'], 'pilot_result': 'accepted' if accepted else 'blocked',
            'launches_consumed': 1, 'reservation_status': 'consumed_pending_reconciliation',
            'runtime_enforced': False, 'authority_granted': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['plan', 'reserve', 'validate'])
    for key in ('request', 'policy', 'approval', 'approval-sha256', 'policy-sha256', 'repo', 'head'):
        parser.add_argument('--' + key, required=True)
    parser.add_argument('--state')
    parser.add_argument('--state-sha256')
    parser.add_argument('--receipt')
    parser.add_argument('--result')
    args = parser.parse_args()
    if args.action in ('reserve', 'validate') and not args.state:
        parser.error('--state required')
    if args.action == 'validate' and not all((args.state_sha256, args.receipt, args.result)):
        parser.error('--state-sha256, --receipt, --result required')
    try:
        read = lambda path: read_regular(path, limit=MAX_INPUT)
        decision = plan(read(args.request), read(args.policy), read(args.approval),
                        args.approval_sha256, args.policy_sha256, args.repo, args.head)
        if args.action == 'reserve':
            output = reserve(decision, args.state)
        elif args.action == 'validate':
            output = validate(decision, read(args.state), args.state_sha256,
                              read(args.receipt), read(args.result), artifact(args.repo, args.head))
        else:
            output = decision
        print(encode(output).decode(), end='')
        return 1 if output.get('pilot_result') == 'blocked' else 0
    except (ValueError, OSError, subprocess.SubprocessError, RecursionError):
        print('{"error":"ROUTING_BLOCKED","authority_granted":false}')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
