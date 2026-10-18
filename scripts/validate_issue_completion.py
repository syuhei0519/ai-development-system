#!/usr/bin/env python3
"""Check pinned aggregate records offline; never grant merge/deploy/close authority."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.consume_delivery import parse, require
from scripts.validate_handoff import validate as validate_handoff
from scripts.validate_readiness import (instant, validator, validate as validate_readiness,
                                        validate_handoff_pair as readiness_pair)

from scripts.regular_file import read_regular, artifact_path

ASSESSMENT = validator('issue-completion')
CONTEXT = validator('issue-completion-context')
PHASES = {'premerge': 0, 'postmerge': 1, 'postdeploy': 2}
VECTOR_FIELDS = ('deployment_id', 'sources', 'config_sha256', 'images', 'environment_id', 'workload_id')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def same(a, b):
    """Type-sensitive JSON equality; never used to calculate a bytes digest."""
    return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def check_schema(check, document, label):
    require(check.is_valid(document), label + ': invalid schema')


def index(items, key):
    result = {i[key]: i for i in items}
    require(len(result) == len(items), key + ': duplicate identity')
    return result


def keyed_equal(a, b, key):
    return same(index(a, key), index(b, key))


def normalize_vector(items):
    result = index(items, 'deployment_id')
    return {key: {**value, 'sources': index(value['sources'], 'repository'),
                  'images': index(value['images'], 'component')} for key, value in result.items()}


def verification_requirements_changed(previous, verifications):
    """Compare the requirement identity/semantics retained by an assessment.

    Result status, evidence IDs, observation times and binding digests are not
    requirements: a fresh measurement alone must not imply a changed subcheck.
    Unmeasured definitions and failure_action are not stored in v1 assessments;
    their changes must also be recorded by the Manager through scope_revision.
    """
    if set(index(previous['verification_results'], 'verification_id')) != set(verifications):
        return True
    old_ac = {r['ac_id']: set(r['verification_ids']) for r in previous['ac_results']}
    current_ac = {}
    for key, v in verifications.items():
        current_ac.setdefault(v['ac_id'], set()).add(key)
    if old_ac != current_ac:
        return True
    for e in previous['evidence']:
        if e['kind'] != 'ac_measurement':
            continue
        for key in e['verification_ids']:
            v = verifications[key]
            if (e['ac_ids'] != [v['ac_id']] or e['producer'] != v['owner'] or
                    any(e[k] != v[k] for k in ('phase', 'environment_id', 'workload_id', 'method', 'expected_result')) or
                    any(set(e[k]) != set(v[k]) for k in ('member_ids', 'deployment_ids'))):
                return True
    return False


class Bundle:
    """Local regular files only. All refs are relative to the assessment directory.

    Retains initial bytes and rereads the entire accessed set before success. This
    is not a sandbox against a hostile local writer after validation completes.
    """
    def __init__(self, root):
        self.root = Path(root).absolute()
        self.cache = {}
        self.identities = {}

    def path(self, path):
        path = Path(path).absolute()
        require(path.is_relative_to(self.root), 'file escapes bundle root')
        for part in (path, *path.parents):
            require(not part.is_symlink(), 'symlink rejected')
        require(path.is_file() and path.resolve() == path, 'regular canonical file required')
        return path

    def read(self, path):
        path = self.path(path)
        stat = path.stat()
        require(stat.st_size <= 16 * 1024 * 1024, 'file too large')
        raw = read_regular(path)
        require(raw and len(raw) <= 16 * 1024 * 1024, 'empty or oversized file')
        if path in self.cache:
            require(raw == self.cache[path], 'bytes changed during validation')
        self.cache[path] = raw
        return raw

    def locator(self, locator, *, parent=None):
        require(not Path(locator).is_absolute() and '://' not in locator and
                '\\' not in locator and all(p not in ('', '.', '..') for p in locator.split('/')),
                'unsafe local locator')
        return self.path((self.root if parent is None else Path(parent)) / locator)

    def artifact(self, artifact, handoff_path):
        path = self.locator(artifact['locator'], parent=Path(handoff_path).parent)
        raw = self.read(path)
        require(artifact['revision'] == 'sha256:' + sha(raw), 'Handoff artifact sha256 mismatch')
        return path

    def ref(self, ref):
        path = self.locator(ref['locator'])
        raw = self.read(path)
        require(len(raw) == ref['size'] and sha(raw) == ref['sha256'], 'reference size/digest mismatch')
        identity = (path, ref['sha256'], ref['size'])
        require(ref['id'] not in self.identities or self.identities[ref['id']] == identity,
                'reference ID reused for different bytes/path')
        self.identities[ref['id']] = identity
        return raw, path

    def refs(self, document):
        if isinstance(document, dict):
            if set(document) == {'id', 'locator', 'sha256', 'size'}:
                self.ref(document)
            else:
                for value in document.values():
                    self.refs(value)
        elif isinstance(document, list):
            for value in document:
                self.refs(value)

    def finish(self):
        for path, raw in list(self.cache.items()):
            require(self.read(path) == raw, 'bundle changed during validation')


def time_window(item, evaluated, now):
    require(instant(item['observed_at']) <= evaluated <= now < instant(item['valid_until']),
            'active observation future-dated or expired')


def validate_record(data, context, bundle, now, previous=None):
    require(data.get('schema_version') == context.get('schema_version'), 'aggregate version mismatch')
    v11 = data.get('schema_version') == '1.1'
    check_schema(ASSESSMENT, data, 'assessment')
    check_schema(CONTEXT, context, 'context')
    bundle.refs(context)
    bundle.refs(data)
    evaluated = instant(data['evaluated_at'])
    require(now.tzinfo is not None and evaluated <= now, 'invalid evaluation time')
    time_window(context, evaluated, now)
    require(data['issue_id'] == context['issue']['id'] and
            same(data['acceptance_criteria'], context['issue']['acceptance_criteria']) and
            data['scope_revision'] == context['scope_revision'], 'Issue/AC/scope context mismatch')
    acs = index(data['acceptance_criteria'], 'id')
    required = index(context['required_prs'], 'member_id')
    members = index(context['current_members'], 'member_id')
    results = index(data['member_results'], 'member_id')
    deployments = index(context['required_deployments'], 'deployment_id')
    current_deployments = index(context['current_deployments'], 'deployment_id')
    deployment_results = index(data['deployment_results'], 'deployment_id')
    verifications = index(context['required_verifications'], 'verification_id')
    verification_results = index(data['verification_results'], 'verification_id')
    ac_results = index(data['ac_results'], 'ac_id')
    evidence = index(data['evidence'], 'id')
    decisions = index(context['scope_decisions'], 'scope_id')
    require(set(required) == set(members) == set(results), 'required PR set mismatch')
    require(set(deployments) == set(current_deployments) == set(deployment_results), 'deployment set mismatch')
    require(set(verifications) == set(verification_results), 'verification set mismatch')
    require(set(acs) == set(ac_results) == {v['ac_id'] for v in verifications.values()}, 'AC coverage mismatch')
    pr_keys = [(r['repository'], r['pr_number']) for r in required.values() if r['pr_number'] is not None]
    require(len(pr_keys) == len(set(pr_keys)), 'duplicate repository/PR')
    for r in required.values():
        require(set(r['ac_ids']) <= set(acs), 'unknown member AC')
        if r.get('pr_kind') == 'preparation':
            require(set(r['preparation']['related_ac_ids']) <= set(acs), 'unknown related member AC')
            index(r['preparation']['artifact_refs'], 'artifact_id')
        require(set(r['depends_on']) <= set(required) and r['member_id'] not in r['depends_on'], 'invalid dependency')
    visited, active = set(), set()
    def visit(key):
        require(key not in active, 'dependency cycle')
        if key in visited:
            return
        active.add(key)
        for dependency in required[key]['depends_on']:
            visit(dependency)
        active.remove(key)
        visited.add(key)
    for key in required:
        visit(key)
    for v in verifications.values():
        require(set(v['member_ids']) <= set(required) and set(v['deployment_ids']) <= set(deployments), 'unknown verification target')
        require(PHASES[v['phase']] >= PHASES[acs[v['ac_id']]['verification_phase']], 'verification precedes AC phase')
        require(all(v['ac_id'] in required[m]['ac_ids'] for m in v['member_ids']), 'verification outside member AC scope')
        require(v['phase'] != 'premerge' or (len(v['member_ids']) == 1 and not v['deployment_ids']), 'premerge verification must target one PR')
        require(v['phase'] != 'postdeploy' or v['deployment_ids'], 'postdeploy needs deployment targets')
        for did in v['deployment_ids']:
            d = deployments[did]
            require(v['environment_id'] == d['environment_id'] and v['workload_id'] == d['workload_id'], 'verification environment/workload mismatch')
    for item in [*members.values(), *current_deployments.values(), *decisions.values()]:
        time_window(item, evaluated, now)
    for decision in decisions.values():
        require(decision['issue_id'] == data['issue_id'] and decision['revision'] == data['scope_revision'], 'approval Issue/scope revision mismatch')
        require(set(decision['member_ids']) <= set(required) and set(decision['deployment_ids']) <= set(deployments), 'unknown approval target')
        actions = set(decision['allowed_actions'])
        allowed = {'required_scope': {'assess'}, 'delivery': {'publish', 'consume'},
                   'product_operation': {'implement', 'merge', 'deploy', 'rollback', 'close_issue'}}
        require(actions <= allowed[decision['decision_kind']], 'approval kind cannot grant these actions')
    require(any(r['sha256'] == context['scope_revision'] for r in context['source_refs']), 'scope revision must bind a supplied source')
    scope_ok = context['issue_integration_scope'] == 'aggregate_required' and any(
        d['decision_kind'] == 'required_scope' and d['status'] == 'approved' and
        'assess' in d['allowed_actions'] and set(d['member_ids']) == set(required) and
        set(d['deployment_ids']) == set(deployments) for d in decisions.values())

    def authorized(action, actor, mid=None, did=None, at=None):
        return any(d['decision_kind'] == 'product_operation' and d['status'] == 'approved' and
                   d['actor'] == actor and action in d['allowed_actions'] and
                   (mid is None or mid in d['member_ids']) and (did is None or did in d['deployment_ids']) and
                   (at is None or instant(d['observed_at']) <= at < instant(d['valid_until']))
                   for d in decisions.values())

    gates = {}
    for key, result in results.items():
        member, requirement = members[key], required[key]
        merged = member['state'] == 'merged'
        if member['state'] in ('merged', 'reverted'):
            require(all(member[k] is not None for k in ('head_sha', 'base_sha', 'merge_sha', 'merged_at', 'merge_actor')) and member['evidence_refs'], 'merge observation incomplete')
            require(instant(member['merged_at']) <= instant(member['observed_at']), 'merge after observation')
        require(result['approved_head_sha'] in (None, member['head_sha']) and
                result['actual_merge_sha'] in (None, member['merge_sha']) and
                result['merged_at'] in (None, member['merged_at']), 'stale merge/head result')
        refs = [result[k] for k in ('readiness_ref','readiness_context_ref','readiness_handoff_ref')]
        require(all(r is None for r in refs) or all(r is not None for r in refs), 'partial PR pair')
        if all(r is not None for r in refs):
            raw, rp = bundle.ref(refs[0]); ready = parse(raw)
            rc = parse(bundle.ref(refs[1])[0]); hr, hp = bundle.ref(refs[2]); handoff = parse(hr)
            require(member['merged_at'] is not None and result['gate_checked_at'] is not None, 'historical gate needs merge time')
            merge_time = instant(member['merged_at'])
            require(ready.get('pr_kind', 'standard') == requirement.get('pr_kind', 'standard'),
                    'historical PR kind mismatch')
            if requirement.get('pr_kind') == 'preparation':
                require(ready.get('schema_version') == '1.1' and ready.get('preparation') is not None,
                        'preparation requires historical Readiness 1.1')
                preparation = requirement['preparation']
                require(set(preparation['related_ac_ids']) == set(ready['preparation']['related_ac_ids']),
                        'historical related AC mapping mismatch')
                fixed = index(ready['preparation']['artifacts'], 'id')
                delivered = index(preparation['artifact_refs'], 'artifact_id')
                require(set(fixed) == set(delivered), 'preparation artifact set mismatch')
                for aid, artifact in fixed.items():
                    payload, path = bundle.ref(delivered[aid]['ref'])
                    require(path == artifact_path(rp.parent, artifact['locator']),
                            'preparation artifact root/path mismatch')
                    require(len(payload) == artifact['size_bytes'] and sha(payload) == artifact['sha256'],
                            'preparation artifact bytes/digest mismatch')
            require(not validate_readiness(ready, rc, merge_time, artifact_root=rp.parent),
                    'invalid historical Readiness at actual merge')
            require(not validate_handoff(handoff), 'invalid PR Handoff v2')
            artifacts = index(handoff['artifacts'], 'id')
            require(ready['artifact_id'] in artifacts and
                    bundle.artifact(artifacts[ready['artifact_id']], hp) == rp,
                    'PR Handoff must bind evaluated Readiness file')
            require(not readiness_pair(ready, handoff, readiness_bytes=raw, readiness_path=rp, handoff_path=hp), 'invalid PR Readiness/Handoff pair')
            require(ready['merge_readiness']['status'] == 'ready' and ready['issue_integration_scope'] == 'aggregate_required', 'historical aggregate PR not Merge Ready')
            subject = ready['subject']
            require(subject['repository'] == requirement['repository'] and
                    subject['pr_number'] == requirement['pr_number'] and
                    all(subject[k] == member[k] for k in ('head_sha','base_sha','target_revision','config_revision','merge_group_sha')), 'historical PR identity/head/base mismatch')
            require(ready['issue_id'] == data['issue_id'], 'historical Issue mismatch')
            require(set(ready['pr_ac_ids']) == set(requirement['ac_ids']), 'historical PR scope mapping mismatch')
            originals = index(ready['acceptance_criteria'], 'id')
            historical_ids = (requirement['preparation']['related_ac_ids']
                              if requirement.get('pr_kind') == 'preparation' else ready['pr_ac_ids'])
            require(all(k in originals and k in acs and same(originals[k], acs[k]) for k in historical_ids), 'historical AC originals mismatch')
            require(instant(ready['evaluated_at']) <= instant(result['gate_checked_at']) <= merge_time, 'gate time outside merge window')
            gates[key] = ready
        if merged:
            for dep in requirement['depends_on']:
                require(members[dep]['merged_at'] is not None and instant(members[dep]['merged_at']) <= instant(member['merged_at']), 'dependency merged later')
    merge_vector = [{'member_id': k, 'merge_sha': m['merge_sha']} for k, m in members.items() if m['merge_sha'] is not None]
    deploy_vector = [{k: d[k] for k in VECTOR_FIELDS} for d in current_deployments.values()]
    for e in evidence.values():
        time_window(e, evaluated, now)
        require(set(e['member_ids']) <= set(required) and set(e['deployment_ids']) <= set(deployments) and
                set(e['verification_ids']) <= set(verifications) and set(e['ac_ids']) <= set(acs), 'unknown evidence target')
        # Structured raw observations prevent a receipt/article/arbitrary text file
        # from being accepted merely because its digest is known. Truth remains external.
        source = parse(bundle.ref(e['source_ref'])[0])
        expected = {'document_type': 'issue_completion_observation', 'schema_version': '1.0',
                    'observation': {k: v for k, v in e.items() if k != 'source_ref'}}
        require(same(source, expected), 'source observation does not substantiate evidence metadata')
        binding = e['binding']
        require(binding['scope_revision'] == data['scope_revision'], 'evidence scope mismatch')
        if e['phase'] == 'premerge':
            require(binding['type'] == 'pr' and binding['member_id'] in gates, 'premerge needs validated historical subject')
            require(e['member_ids'] == [binding['member_id']] and not e['deployment_ids'] and
                    same(binding['subject'], gates[binding['member_id']]['subject']), 'premerge subject mismatch')
            require(instant(e['observed_at']) <= instant(members[binding['member_id']]['merged_at']), 'premerge observation after merge')
        else:
            require(binding['type'] == 'integration' and binding['context_sha256'] == data['context_sha256'], 'integration context binding mismatch')
            require(len(merge_vector) == len(required) and keyed_equal(binding['merged_members'], merge_vector, 'member_id'), 'full merge vector required')
            require(all(m['merged_at'] is not None and instant(m['merged_at']) <= instant(e['observed_at']) for m in members.values()), 'observation predates required merge')
            expected_deployments = deploy_vector if e['phase'] == 'postdeploy' else []
            require(same(normalize_vector(binding['deployments']), normalize_vector(expected_deployments)), 'deployment vector mismatch')
            if e['phase'] == 'postdeploy':
                require(e['deployment_ids'], 'postdeploy evidence lacks targets')
                require(all(current_deployments[k]['deployed_at'] is not None and
                            instant(current_deployments[k]['deployed_at']) <= instant(e['observed_at']) for k in e['deployment_ids']), 'observation predates deployment')
        require((e['kind'] == 'merge_binding') == (e['merge'] is not None), 'merge details kind mismatch')
        if e['merge'] is not None:
            m = e['merge']; key = m['member_id']
            require(key in gates and e['member_ids'] == [key] and e['phase'] == 'postmerge', 'merge binding target mismatch')
            s, actual = gates[key]['subject'], members[key]
            require(all(m[k] == s[k] for k in ('head_sha','base_sha','target_revision')) and
                    m['merge_sha'] == actual['merge_sha'] and m['merged_at'] == actual['merged_at'], 'merge result correspondence mismatch')
            require((m['method'] == 'queue') == (s['merge_group_sha'] is not None), 'queue method mismatch')

    def proofs(proof, kind, mids=None, dids=None):
        found = []
        for eid in proof['evidence_ids']:
            require(eid in evidence, 'missing proof evidence')
            e = evidence[eid]; found.append(e)
            require(e['kind'] == kind and e['result'] == proof['verdict'], 'proof kind/result mismatch')
            require(mids is None or set(e['member_ids']) == set(mids), 'proof member coverage mismatch')
            require(dids is None or set(e['deployment_ids']) == set(dids), 'proof deployment coverage mismatch')
        require(proof['verdict'] == 'pending' or found, 'proof missing')
        return found

    merges_ok, auth_ok = True, scope_ok
    for key, result in results.items():
        m = members[key]
        proofs(result['merge_binding'], 'merge_binding', [key], [])
        proofs(result['historical_merge_gate'], 'merge_binding', [key], [])
        valid = (m['state'] == 'merged' and key in gates and required[key]['pr_number'] is not None and
                 result['approved_head_sha'] == m['head_sha'] and result['actual_merge_sha'] == m['merge_sha'] and
                 result['merged_at'] == m['merged_at'])
        for name in ('merge_binding','historical_merge_gate'):
            require(result[name]['verdict'] != 'pass' or valid, 'unverified merge cannot pass')
        merges_ok &= valid and all(result[k]['verdict'] == 'pass' for k in ('merge_binding','historical_merge_gate'))
        auth_ok &= m['merged_at'] is not None and authorized('merge', m['merge_actor'], mid=key, at=instant(m['merged_at']))
    deployment_ok = True
    for key, d in deployments.items():
        actual, result = current_deployments[key], deployment_results[key]
        require(set(d['member_ids']) <= set(required), 'unknown deployment member')
        index(d['expected_sources'], 'repository'); index(d['expected_images'], 'component')
        index(actual['sources'], 'repository'); index(actual['images'], 'component')
        require(actual['environment_id'] == d['environment_id'] and actual['workload_id'] == d['workload_id'], 'wrong deployment environment/workload')
        defined = (d['definition_state'] == 'defined' and bool(d['expected_sources']) and d['expected_config_sha256'] is not None and
                   ((d['image_requirement'] == 'required' and bool(d['expected_images'])) or
                    (d['image_requirement'] == 'none' and not d['expected_images'] and d['no_image_basis'] is not None)))
        if actual['state'] == 'failed':
            require(actual['evidence_refs'], 'failed deployment requires observation bytes')
        if actual['state'] in ('deployed', 'rolled_back'):
            require(actual['deployed_at'] is not None and actual['deploy_actor'] is not None and actual['evidence_refs'], 'deployment observation incomplete')
            require(instant(actual['deployed_at']) <= instant(actual['observed_at']), 'deployment after observation')
        match = (defined and actual['state'] == 'deployed' and
                 keyed_equal(d['expected_sources'], actual['sources'], 'repository') and
                 d['expected_config_sha256'] == actual['config_sha256'] and keyed_equal(d['expected_images'], actual['images'], 'component'))
        if match:
            require(all(members[m]['state'] == 'merged' and members[m]['merged_at'] is not None and
                        instant(members[m]['merged_at']) <= instant(actual['deployed_at']) for m in d['member_ids']), 'deployment predates member merge')
        observations = [evidence[e] for e in result['evidence_ids'] if e in evidence]
        require(len(observations) == len(result['evidence_ids']), 'unknown deployment evidence')
        for e in observations:
            require(e['kind'] == 'deployment' and e['deployment_ids'] == [key] and set(e['member_ids']) == set(d['member_ids']), 'deployment proof coverage/kind')
        expected = ('failed' if actual['state'] == 'failed' else 'rolled_back' if actual['state'] == 'rolled_back' else
                    'ready' if match and observations and all(e['phase'] == 'postdeploy' and e['result'] == 'pass' for e in observations) else 'blocked')
        require(result['status'] == expected, 'deployment status contradicts observation')
        deployment_ok &= expected == 'ready'
        auth_ok &= actual['deployed_at'] is not None and authorized('deploy', actual['deploy_actor'], did=key, at=instant(actual['deployed_at']))
    for key, result in verification_results.items():
        v = verifications[key]
        found = []
        for eid in result['evidence_ids']:
            require(eid in evidence, 'missing measurement')
            e = evidence[eid]; found.append(e)
            require(e['kind'] == 'ac_measurement' and e['verification_ids'] == [key] and e['ac_ids'] == [v['ac_id']] and
                    e['phase'] == v['phase'] and set(e['member_ids']) == set(v['member_ids']) and
                    set(e['deployment_ids']) == set(v['deployment_ids']) and e['producer'] == v['owner'] and
                    all(e[k] == v[k] for k in ('environment_id','workload_id','method','expected_result')), 'measurement identity/phase/target/method/producer mismatch')
        outcomes = {e['result'] for e in found}
        expected = 'not_met' if 'fail' in outcomes else 'met' if found and outcomes == {'pass'} else 'unverified'
        require(result['outcome'] == expected, 'measurement outcome mismatch')
        # No unreferenced failing measurement may silently disappear from results.
        require(all(e['id'] in result['evidence_ids'] for e in evidence.values() if e['kind'] == 'ac_measurement' and key in e['verification_ids']), 'measurement omitted from result')
    for key, result in ac_results.items():
        required_ids = {v['verification_id'] for v in verifications.values() if v['ac_id'] == key}
        require(set(result['verification_ids']) == required_ids, 'AC required subcheck set mismatch')
        outcomes = {verification_results[v]['outcome'] for v in required_ids}
        expected = 'not_met' if 'not_met' in outcomes else 'unverified' if 'unverified' in outcomes else 'met'
        require(result['outcome'] == expected, 'AC outcome contradicts subchecks')
        require(set(result['evidence_ids']) == {e for v in required_ids for e in verification_results[v]['evidence_ids']}, 'AC evidence set mismatch')
    integration = data['integration_readiness']
    kinds = {'scope':'scope','required_merges':'merge_binding','deployment':'deployment','compatibility':'compatibility',
             'measurement_coverage':'ac_measurement','current_evidence':'integration','authorizations':'authorization'}
    for key, proof in integration['checks'].items():
        # Empty deployment set still needs explicit scope evidence, not vacuous success.
        kind = 'scope' if key == 'deployment' and not deployments else kinds[key]
        found = proofs(proof, kind)
        if proof['verdict'] == 'pass':
            expected_members = ({mid for mid, r in required.items() if r.get('pr_kind') != 'preparation'}
                                if key == 'measurement_coverage' else set(required))
            require(bool(expected_members) and {m for e in found for m in e['member_ids']} == expected_members,
                    'integration check misses required members')
            if key in ('scope','deployment','compatibility','current_evidence','authorizations'):
                require({d for e in found for d in e['deployment_ids']} == set(deployments), 'integration check misses deployments')
            if key in ('compatibility','current_evidence'):
                require(all(e['phase'] == ('postdeploy' if deployments else 'postmerge') for e in found), 'integration proof precedes integration')
            if key == 'measurement_coverage':
                require({v for e in found for v in e['verification_ids']} == set(verifications), 'measurement coverage incomplete')
    require(set(integration['evidence_ids']) == {e for p in integration['checks'].values() for e in p['evidence_ids']}, 'integration evidence set mismatch')
    calculated = {'scope':scope_ok,'required_merges':merges_ok,'deployment':deployment_ok,
                  'measurement_coverage':all(r['outcome'] == 'met' for r in ac_results.values()),'authorizations':auth_ok}
    for key, ok in calculated.items():
        require(integration['checks'][key]['verdict'] != 'pass' or ok, key + ': unsupported pass')
    ready = all(calculated.values()) and all(p['verdict'] == 'pass' for p in integration['checks'].values())
    failed = (any(r['outcome'] == 'not_met' for r in ac_results.values()) or any(m['state'] == 'reverted' for m in members.values()) or
              any(d['state'] in ('failed','rolled_back') for d in current_deployments.values()) or
              any(e['result'] == 'fail' for e in evidence.values()) or any(p['verdict'] == 'fail' for p in integration['checks'].values()))
    events = data['history']['events']; index(events, 'event_id')
    for event in events:
        require(instant(event['observed_at']) <= evaluated, 'future history event')
        require(event['kind'] not in ('measurement_failed','rollback','revert') or event['evidence_refs'], 'failure history needs evidence')
    require(all(instant(a['observed_at']) <= instant(b['observed_at']) for a,b in zip(events,events[1:])), 'history not chronological')
    if previous is not None:
        check_schema(ASSESSMENT, previous, 'previous')
        old_events = previous['history']['events']
        require(previous['issue_id'] == data['issue_id'] and instant(previous['evaluated_at']) <= evaluated, 'previous Issue/time mismatch')
        require(same(events[:len(old_events)], old_events) and len(events) > len(old_events), 'history must be append-only')
        additions = events[len(old_events):]
        require(all(instant(e['observed_at']) >= instant(previous['evaluated_at']) for e in additions), 'new event predates previous assessment')
        changed_kinds = {e['kind'] for e in additions}
        old_members = index(previous['member_results'], 'member_id')
        if (set(old_members) != set(results) or
                not same(previous['acceptance_criteria'], data['acceptance_criteria']) or
                previous['scope_revision'] != data['scope_revision'] or
                verification_requirements_changed(previous, verifications)):
            require('required_set_changed' in changed_kinds, 'scope/required set change needs history event')
        if any(old_members[k]['approved_head_sha'] != results[k]['approved_head_sha'] for k in set(old_members) & set(results)):
            require('head_changed' in changed_kinds, 'head change needs history event')
        old_vectors = [e['binding']['deployments'] for e in previous['evidence'] if e['phase'] == 'postdeploy']
        if old_vectors and not same(normalize_vector(old_vectors[0]), normalize_vector(deploy_vector)):
            require(bool({'deployment_changed','config_changed','rollback'} & changed_kinds), 'deployment change needs history event')
        if previous['issue_completion'] == 'not_achieved':
            # Conservative unresolved-failure latch. A current pending assessment
            # retains not_achieved; only new measurements + explicit repair can clear it.
            repaired = ready and any(e['kind'] == 'revalidated' and e['evidence_refs'] for e in additions) and all(
                instant(e['observed_at']) > instant(previous['evaluated_at']) for e in evidence.values() if e['kind'] in ('ac_measurement','integration'))
            failed |= not repaired
    for key, member in members.items():
        if member['state'] == 'reverted':
            require(any(e['kind'] == 'revert' and key in e['affected_ids'] for e in events), 'revert history missing')
    for key, deployment in current_deployments.items():
        if deployment['state'] in ('failed','rolled_back'):
            kind = 'rollback' if deployment['state'] == 'rolled_back' else 'measurement_failed'
            require(any(e['kind'] == kind and key in e['affected_ids'] for e in events), 'deployment failure history missing')
    if failed:
        require(any(e['kind'] in ('measurement_failed','rollback','revert') for e in events), 'known failure must remain in history')
    ready &= not failed
    completion = 'not_achieved' if failed else 'achieved' if ready else 'unverified'
    require(integration['status'] == ('ready' if ready else 'blocked') and data['issue_completion'] == completion, 'derived completion/readiness mismatch')
    return completion


def validate_handoff_pair(data, handoff, bundle, assessment_path, handoff_path, raw):
    require(not validate_handoff(handoff), 'invalid Handoff v2')
    require(handoff['role'] == 'manager' and handoff['issue']['id'] == data['issue_id'], 'Issue Handoff must be Manager for same Issue')
    originals = [{k: ac[k] for k in ('id','verbatim','source')} for ac in data['acceptance_criteria']]
    require(same(handoff['issue']['acceptance_criteria'], originals), 'Issue Handoff AC originals mismatch')
    artifacts = index(handoff['artifacts'], 'id')
    require(data['artifact_id'] in artifacts, 'Issue Handoff artifact_id missing')
    artifact = artifacts[data['artifact_id']]
    def artifact_path(a):
        return bundle.artifact(a, handoff_path)
    require(artifact['kind'] == 'other' and artifact_path(artifact) == bundle.path(assessment_path) and
            bundle.read(assessment_path) == raw and same(parse(raw), data), 'Issue Handoff must bind evaluated file and initial bytes')
    final = handoff.get('final_assessment')
    require(data['issue_completion'] != 'achieved' or (final is not None and handoff['status'] == 'completed'), 'achieved needs completed Manager final')
    if final:
        require(final['outcome'] == data['issue_completion'], 'Issue Handoff outcome mismatch')
        results = index(data['ac_results'], 'ac_id'); he = index(handoff['evidence'], 'id'); ce = index(data['evidence'], 'id')
        require({r['ac_id']: r['outcome'] for r in final['ac_results']} == {k: r['outcome'] for k,r in results.items()}, 'Issue Handoff AC outcomes mismatch')
        for result in final['ac_results']:
            expected = {bundle.ref(ce[e]['source_ref'])[1] for e in results[result['ac_id']]['evidence_ids']}
            actual = set()
            for eid in result['evidence_ids']:
                require(eid in he, 'Handoff final evidence missing')
                for aid in he[eid]['artifact_ids']:
                    require(aid in artifacts, 'Handoff evidence artifact missing')
                    actual.add(artifact_path(artifacts[aid]))
            require(actual == expected, 'Handoff final evidence must map to same measurement bytes')


def validate_files(file, context_file, context_sha256, handoff_file, *, now=None, previous_file=None, previous_sha256=None):
    file = Path(file).absolute(); bundle = Bundle(file.parent)
    raw = bundle.read(file); data = parse(raw)
    context_raw = bundle.read(Path(context_file).absolute()); context = parse(context_raw)
    require(re.fullmatch('[0-9a-f]{64}', context_sha256 or '') is not None and sha(context_raw) == context_sha256, 'untrusted current context pin')
    require(data.get('schema_version') == context.get('schema_version'), 'aggregate version mismatch')
    check_schema(ASSESSMENT, data, 'assessment')
    check_schema(CONTEXT, context, 'context')
    require(data['context_sha256'] == context_sha256, 'assessment context digest mismatch')
    previous = None; ref = data['history']['previous_ref']; pin = context['previous_assessment_sha256']
    if pin is None:
        require(ref is None and previous_file is None and previous_sha256 is None, 'unexpected previous state')
    else:
        require(previous_file is not None and previous_sha256 == pin and ref is not None, 'independent latest previous pin required')
        prev_raw = bundle.read(Path(previous_file).absolute())
        ref_raw, ref_path = bundle.ref(ref)
        require(ref_path == bundle.path(Path(previous_file).absolute()) and prev_raw == ref_raw and sha(prev_raw) == pin, 'previous pin/file mismatch')
        previous = parse(prev_raw)
    completion = validate_record(data, context, bundle, now or datetime.now(timezone.utc), previous)
    handoff_file = Path(handoff_file).absolute()
    validate_handoff_pair(data, parse(bundle.read(handoff_file)), bundle, file, handoff_file, raw)
    bundle.finish()
    return data['integration_readiness']['status'], completion


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('file', type=Path)
    p.add_argument('--context', required=True, type=Path)
    p.add_argument('--context-sha256', required=True)
    p.add_argument('--handoff', required=True, type=Path)
    p.add_argument('--previous', type=Path)
    p.add_argument('--previous-sha256')
    p.add_argument('--at', help='synthetic/historical replay only; never current authority')
    a = p.parse_args()
    try:
        now = instant(a.at) if a.at else datetime.now(timezone.utc)
        require(now.tzinfo is not None, 'timezone required')
        status, outcome = validate_files(a.file, a.context, a.context_sha256, a.handoff, now=now,
                                        previous_file=a.previous, previous_sha256=a.previous_sha256)
        print(f'PASS {"REPLAY" if a.at else "CURRENT"}: integration={status}; issue_completion={outcome}; record consistency only; no authority granted')
        return 0
    except (OSError, ValueError, KeyError, TypeError, OverflowError, RecursionError, RuntimeError) as exc:
        # Avoid echoing private or attacker-controlled JSON values/paths.
        print('FAIL: aggregate record rejected; no completion or authority granted', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
