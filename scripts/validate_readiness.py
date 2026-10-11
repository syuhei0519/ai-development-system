#!/usr/bin/env python3
"""Validate recorded gates against a supplied current snapshot; no live GitHub approval."""
import argparse
import hashlib
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
FORMATS = FormatChecker()


@FORMATS.checks('date-time', raises=(ValueError, OverflowError))
def timestamp(value):
    """Check timestamps without jsonschema's optional format dependencies."""
    if not isinstance(value, str):
        return True  # The schema's type check handles this.
    if not re.fullmatch(r'\d{4}-\d\d-\d\d[Tt]\d\d:\d\d:\d\d(?:\.\d+)?(?:[Zz]|[+-]\d\d:\d\d)', value):
        return False
    instant(value)
    return True


def validator(name):
    schema = json.loads((ROOT / 'contracts' / f'{name}.schema.json').read_text())
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FORMATS)


VALIDATOR = validator('readiness')
CONTEXT_VALIDATOR = validator('readiness-context')


def instant(value):
    return datetime.fromisoformat(value.upper().replace('Z', '+00:00'))


def validate(data, context, now=None, *, artifact_root=None):
    errors = []
    for label, document, check in [('assessment', data, VALIDATOR),
                                    ('context', context, CONTEXT_VALIDATOR)]:
        errors.extend(f'{label} schema {list(e.absolute_path)}: {e.message}'
                      for e in check.iter_errors(document))
    if errors:
        return errors
    now = now or datetime.now(timezone.utc)
    evaluated = instant(data['evaluated_at'])
    if evaluated > now:
        errors.append('evaluated_at is in the future')
    for field in ('subject', 'issue_id', 'acceptance_criteria', 'pr_ac_ids', 'deployment_effect',
                  'issue_integration_scope'):
        if data[field] != context[field]:
            errors.append(f'{field}: does not match current context; revalidate')
    for field in ('schema_version', 'pr_kind', 'preparation'):
        if data.get(field) != context.get(field):
            errors.append(f'{field}: does not match current context; revalidate')
    subject = data['subject']
    if subject['merge_group_sha'] is not None and subject['target_revision'] != subject['merge_group_sha']:
        errors.append('merge-group evidence must target the current merge-group revision')
    policy_start = instant(context['policy_observed_at'])
    policy_end = instant(context['policy_valid_until'])
    if not policy_start <= evaluated <= now < policy_end:
        errors.append('current policy snapshot is future-dated or expired')

    def index(items, key, label):
        result = {item[key]: item for item in items}
        if len(result) != len(items):
            errors.append(f'{label}: duplicate IDs')
        return result

    criteria = index(data['acceptance_criteria'], 'id', 'acceptance_criteria')
    results = index(data['ac_results'], 'ac_id', 'ac_results')
    evidence = index(data['evidence'], 'id', 'evidence')
    if set(results) != set(criteria):
        errors.append('ac_results must cover exactly all Issue ACs')
    scope = set(data['pr_ac_ids'])
    if not scope <= set(criteria):
        errors.append('pr_ac_ids contains unknown ACs')
    for item in evidence.values():
        if item['subject'] != context['subject']:
            errors.append(f'evidence {item["id"]}: stale subject (head/base/target/config/merge-group)')
        if not instant(item['observed_at']) <= evaluated <= now < instant(item['valid_until']):
            errors.append(f'evidence {item["id"]}: future-dated or expired')
        if not set(item['ac_ids']) <= set(criteria):
            errors.append(f'evidence {item["id"]}: unknown ACs')

    def proofs(refs, kind, ac_id=None):
        if not refs:
            errors.append(f'{kind}: evidence required')
        found = []
        for eid in refs:
            item = evidence.get(eid)
            if item is None:
                errors.append(f'{kind}: unknown evidence {eid}')
                continue
            found.append(item)
            if item['kind'] != kind:
                errors.append(f'{kind}: wrong evidence kind {eid}')
            if ac_id is not None and ac_id not in item['ac_ids']:
                errors.append(f'{kind}: evidence does not cover AC {ac_id}')
            if kind in ('independent_test', 'ai_review') and (
                    not item['independent'] or item['producer'] == data['implementation_actor']):
                errors.append(f'{kind}: independent producer required')
        return found

    proofs(data['deployment_effect_evidence_ids'], 'deployment_impact')
    group_ok = {}
    for group in ('implementation', 'deployment', 'merge'):
        checks = data[group + '_readiness']['checks']
        ok = True
        for kind, check in checks.items():
            verdict = check['verdict']
            if verdict != 'pending' or check['evidence_ids']:
                proofs(check['evidence_ids'], kind)
            if verdict == 'not_applicable':
                key = kind.removeprefix('github_')
                if kind not in ('github_checks', 'github_reviews', 'github_queue') or context['github_requirements'][key]:
                    errors.append(f'{group}/{kind}: required gate cannot be not_applicable')
            elif verdict != 'pass':
                ok = False
        group_ok[group] = ok

    merged = data['lifecycle']['merged_at']
    deployed = data['lifecycle']['deployed_at']
    if merged and instant(merged) > evaluated:
        errors.append('merged_at is after assessment')
    if deployed and (not merged or not instant(merged) <= instant(deployed) <= evaluated):
        errors.append('deployed_at requires preceding merge and cannot be after assessment')
    scoped_acs_ok = True
    for ac_id, result in results.items():
        if ac_id not in criteria:
            continue
        phase = criteria[ac_id]['verification_phase']
        deferred = result['deferred']
        outcome = result['outcome']
        if outcome != 'unverified':
            measured = proofs(result['evidence_ids'], 'ac_measurement', ac_id)
            event = merged if phase == 'postmerge' else deployed if phase == 'postdeploy' else None
            if phase != 'premerge' and not event:
                errors.append(f'{ac_id}: {phase} outcome requires actual lifecycle event')
            if event and any(instant(e['observed_at']) < instant(event) for e in measured):
                errors.append(f'{ac_id}: measurement predates required event')
        elif result['evidence_ids']:
            proofs(result['evidence_ids'], 'ac_measurement', ac_id)
        if deferred is not None:
            if phase == 'premerge' or outcome != 'unverified':
                errors.append(f'{ac_id}: only unverified postmerge/postdeploy AC may be deferred')
            proofs(deferred['evidence_ids'], 'deferral_basis', ac_id)
        if ac_id in scope and not (outcome == 'met' or (
                outcome == 'unverified' and phase != 'premerge' and deferred is not None)):
            scoped_acs_ok = False
    if data.get('pr_kind') == 'preparation':
        preparation = data['preparation']
        related = set(preparation['related_ac_ids'])
        if not related <= set(criteria):
            errors.append('preparation: unknown related product AC')
        conditions = index(preparation['conditions'], 'id', 'preparation conditions')
        measurements = index(data['preparation_results'], 'condition_id', 'preparation results')
        artifacts = index(preparation['artifacts'], 'id', 'preparation artifacts')
        followup = index(preparation['followup'], 'ac_id', 'preparation followup')
        baseline = index(preparation['product_outcomes'], 'ac_id', 'product outcomes')
        if set(conditions) & set(criteria):
            errors.append('preparation conditions must not be product ACs')
        if set(measurements) != set(conditions):
            errors.append('preparation results must cover exactly all conditions')
        if set(followup) != related:
            errors.append('preparation followup must cover exactly related product ACs')
        if set(baseline) != set(criteria) or any(
                r['outcome'] != baseline.get(aid, {}).get('outcome') for aid, r in results.items()):
            errors.append('preparation must preserve all Manager product outcomes')
        # Conservative boundary: any known product failure blocks preparation merge,
        # including failures outside the related subset. No reclassification/deferral.
        scoped_acs_ok = not any(r['outcome'] == 'not_met' for r in results.values())
        for aid, artifact in artifacts.items():
            if artifact['revision'] != subject['target_revision']:
                errors.append(f'preparation artifact {aid}: revision differs from target')
            try:
                if artifact_root is None:
                    raise ValueError('materialized artifact root required')
                root = Path(artifact_root).resolve(strict=True)
                target = (root / artifact['locator']).resolve(strict=True)
                if not target.is_relative_to(root):
                    raise ValueError('artifact path escapes root')
                payload = target.read_bytes()
                if len(payload) != artifact['size_bytes'] or hashlib.sha256(payload).hexdigest() != artifact['sha256']:
                    raise ValueError('artifact bytes/size/digest mismatch')
            except (OSError, ValueError, RuntimeError) as exc:
                errors.append(f'preparation artifact {aid}: {exc}')
        for cid, measurement in measurements.items():
            if measurement['outcome'] != 'met':
                scoped_acs_ok = False
            for item in proofs(measurement['evidence_ids'], 'preparation_measurement'):
                if cid not in item.get('condition_ids', []) or set(item.get('artifact_ids', [])) != set(artifacts):
                    errors.append('preparation measurement must bind condition and all fixed artifacts')
        for kind in ('independent_test', 'ai_review'):
            check = data['merge_readiness']['checks'][kind]
            for item in proofs(check['evidence_ids'], kind):
                if set(item.get('condition_ids', [])) != set(conditions) or set(item.get('artifact_ids', [])) != set(artifacts):
                    errors.append(f'{kind}: must cover all preparation conditions and fixed artifacts')
        for item in evidence.values():
            if not set(item.get('condition_ids', [])) <= set(conditions) or not set(item.get('artifact_ids', [])) <= set(artifacts):
                errors.append('preparation evidence has unknown condition/artifact')
    outcomes = {r['outcome'] for r in results.values()}
    integration = data['issue_integration']
    integrated = False
    if integration['verdict'] != 'pending' or integration['evidence_ids']:
        observations = proofs(integration['evidence_ids'], 'issue_integration')
    else:
        observations = []
    if integration['verdict'] == 'not_applicable':
        errors.append('Issue integration cannot be not_applicable')
    if integration['verdict'] == 'pass':
        integrated = (data['issue_integration_scope'] == 'single_pr' and merged is not None
                      and subject['pr_number'] is not None and bool(observations))
        if not integrated:
            errors.append('Issue integration requires merged single-PR scope; aggregation is unsupported')
        for observation in observations:
            if set(observation['ac_ids']) != set(criteria):
                errors.append('Issue integration evidence must cover all Issue ACs')
            if merged and instant(observation['observed_at']) < instant(merged):
                errors.append('Issue integration observation predates merge')
    completion = ('not_achieved' if 'not_met' in outcomes else
                  'not_achieved' if integration['verdict'] == 'fail' else
                  'unverified' if 'unverified' in outcomes or not integrated else 'achieved')
    if data['issue_completion'] != completion:
        errors.append('issue_completion contradicts all-AC measured outcomes')

    # Implementation can proceed while deployment is blocked. Neither is Issue Completion.
    expected = {
        'implementation': group_ok['implementation'],
        'deployment': group_ok['deployment'],
        'merge': group_ok['merge'] and group_ok['implementation'] and scoped_acs_ok
                 and data['subject']['pr_number'] is not None
                 and (data['deployment_effect'] == 'none' or group_ok['deployment']),
    }
    if context['github_requirements']['queue'] and data['subject']['merge_group_sha'] is None:
        expected['merge'] = False
    for group, ready in expected.items():
        if data[group + '_readiness']['status'] != ('ready' if ready else 'blocked'):
            errors.append(f'{group}_readiness: status contradicts required gates')
    return errors


def validate_handoff_pair(data, handoff, *, readiness_bytes=None,
                          readiness_path=None, handoff_path=None):
    # Handoff v2.0 remains unchanged; link the independent contract via an artifact.
    from scripts.validate_handoff import validate as validate_handoff
    errors = validate_handoff(handoff)
    if errors:
        return errors
    # Bind the actual file inspected by the CLI, not just two matching declarations.
    if readiness_path is None or handoff_path is None or not isinstance(readiness_bytes, bytes):
        return ['handoff pairing requires initial raw bytes and actual file paths']
    artifacts = [a for a in handoff['artifacts'] if a['id'] == data.get('artifact_id')]
    if len(artifacts) != 1:
        return ['handoff must reference exactly the readiness artifact_id']
    artifact = artifacts[0]
    if artifact['kind'] != 'other' or not re.fullmatch(r'sha256:[0-9a-f]{64}', artifact['revision']):
        return ['readiness artifact requires kind=other and fixed sha256 digest revision']
    try:
        locator = artifact['locator']
        if '://' in locator:
            return ['materialize readiness artifact locally; remote locators are not fetched']
        target = (Path(handoff_path).resolve().parent / locator).resolve(strict=True)
        if target != Path(readiness_path).resolve(strict=True):
            return ['handoff locator refers to a different readiness file']
        payload = target.read_bytes()
        if payload != readiness_bytes:
            return ['readiness bytes changed after initial read']
        # Type-sensitive comparison also protects callers of this pairing helper.
        # Python object equality alone treats JSON true and 1 as equal.
        if json.dumps(json.loads(readiness_bytes), sort_keys=True) != json.dumps(data, sort_keys=True):
            return ['initial readiness bytes differ from the evaluated document']
        if artifact['revision'] != 'sha256:' + hashlib.sha256(readiness_bytes).hexdigest():
            return ['readiness artifact digest mismatch']
    except (OSError, ValueError, RuntimeError) as exc:
        return [f'readiness artifact unreadable: {exc}']
    if handoff['issue']['id'] != data['issue_id']:
        errors.append('handoff issue differs from readiness issue')
    originals = [{k: ac[k] for k in ('id', 'verbatim', 'source')} for ac in data['acceptance_criteria']]
    if handoff['issue']['acceptance_criteria'] != originals:
        errors.append('handoff AC originals differ from readiness assessment')
    final = handoff.get('final_assessment')
    if final:
        if final['outcome'] != data['issue_completion']:
            errors.append('handoff final_assessment contradicts issue_completion')
        expected = {r['ac_id']: r['outcome'] for r in data['ac_results']}
        if {r['ac_id']: r['outcome'] for r in final['ac_results']} != expected:
            errors.append('handoff final AC outcomes differ from measured readiness outcomes')
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('file', type=Path)
    parser.add_argument('--context', type=Path, required=True,
                        help='Manager-supplied current revision, AC scope and policy snapshot')
    parser.add_argument('--context-sha256', help='independently supplied Manager context pin; required for v1.1')
    parser.add_argument('--handoff', type=Path, help='also cross-check an Issue handoff v2.0')
    parser.add_argument('--at', help='explicit replay time (not current merge authorization)')
    args = parser.parse_args()
    try:
        now = instant(args.at) if args.at else datetime.now(timezone.utc)
        if now.tzinfo is None:
            raise ValueError('--at must include a timezone')
        readiness_bytes = args.file.read_bytes()
        data = json.loads(readiness_bytes)
        context_bytes = args.context.read_bytes()
        context = json.loads(context_bytes)
        if data.get('schema_version') == '1.1' and not args.context_sha256:
            raise ValueError('v1.1 requires independent Manager --context-sha256')
        if args.context_sha256 and hashlib.sha256(context_bytes).hexdigest() != args.context_sha256:
            raise ValueError('Manager context digest mismatch')
        errors = validate(data, context, now, artifact_root=args.file.resolve().parent)
        if args.handoff and not errors:
            errors += validate_handoff_pair(
                data, json.loads(args.handoff.read_text(encoding='utf-8')),
                readiness_bytes=readiness_bytes, readiness_path=args.file, handoff_path=args.handoff)
    except (OSError, ValueError, OverflowError) as exc:
        errors = [str(exc)]
    if errors:
        print('FAIL ' + str(args.file), file=sys.stderr)
        for error in errors:
            print('  ' + error, file=sys.stderr)
        return 1
    print(f'PASS {args.file} (record consistency only; not evidence truth or live GitHub permission)')
    if args.at:
        print('REPLAY: explicit historical time; not current readiness')
    return 0


if __name__ == '__main__':
    sys.path.insert(0, str(ROOT))
    sys.exit(main())
