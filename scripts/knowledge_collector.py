#!/usr/bin/env python3
"""Mechanical Knowledge collector. No Agent, scheduler, API or Git write operations."""
import argparse
from collections import Counter
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

from jsonschema import Draft202012Validator, FormatChecker
try:
    from .consume_delivery import (ROOT, MAX_FILE, MAX_BUNDLE, GitSource, check_reference,
        digest, parse, read_local, require, safe_path, verify_handoffs)
    from .validate_retry import validate_ledger, transition as retry_transition, LIMITS
    from .validate_knowledge import validate as validate_knowledge
except ImportError:
    from consume_delivery import (ROOT, MAX_FILE, MAX_BUNDLE, GitSource, check_reference,
        digest, parse, read_local, require, safe_path, verify_handoffs)
    from validate_retry import validate_ledger, transition as retry_transition, LIMITS
    from validate_knowledge import validate as validate_knowledge

STATES = ('pending', 'verified', 'reserved', 'dispatching', 'started', 'output_received',
          'validated', 'commit_pending', 'committed', 'context_available', 'blocked',
          'quarantined', 'dispatch_unknown', 'terminal')


def encode(data):
    return (json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(',', ':'),
                       allow_nan=False) + '\n').encode('utf-8')


def validate(name, data):
    spec = json.loads((ROOT / 'contracts' / (name + '.schema.json')).read_text())
    require(Draft202012Validator(spec, format_checker=FormatChecker()).is_valid(data),
            'invalid collector contract')


def fields(data, names):
    require(isinstance(data, dict) and set(data) == set(names.split()), 'invalid operation fields')


def stamp(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    require(parsed.tzinfo is not None, 'timezone required')
    return parsed


def event_id(event):
    ref = event['source_ref']
    identity = dict(version='1.0', repository=ref['repository'], commit=ref['commit'],
                    path=ref['path'], sha256=ref['sha256'], candidate_id=event['candidate_id'],
                    event_kind=event['event_kind'])
    return digest(encode(identity))


def refkey(ref):
    check_reference(ref)
    return ref['repository'], ref['commit'], ref['path']


def validate_event(event):
    validate('knowledge-event', event)
    require(event['event_id'] == event_id(event), 'identity mismatch')
    for ref in [event['source_ref'], *event['finding_refs']]:
        check_reference(ref)
    require(len({refkey(r) for r in event['finding_refs']}) == len(event['finding_refs']),
            'duplicate finding reference')
    require(event['event_id'] not in event['supersedes'], 'self correction')
    require(event['event_kind'] != 'correction' or event['supersedes'], 'correction needs predecessor')


def authorize(raw, pin, request_raw, operation, writer, scope, now=None):
    require(digest(raw) == pin, 'authorization pin mismatch')
    auth = parse(raw)
    validate('knowledge-collection-authorization', auth)
    require((auth['writer'], auth['scope'], auth['operation'], auth['request_sha256']) ==
            (writer, scope, operation, digest(request_raw)), 'authorization mismatch')
    require((now or datetime.now(timezone.utc)) < stamp(auth['valid_until']), 'authorization expired')


class SnapshotSource(GitSource):
    """All inbox entries from an immutable tree, including unsafe entries (then reject)."""
    def snapshot(self, repository, commit):
        check_reference(dict(repository=repository, commit=commit, path='probe'))
        key = repository, commit
        if key not in self.repositories:
            directory = self.directory / str(len(self.repositories))
            directory.mkdir()
            self.git(directory, 'init', '--bare', '--template=')
            self.git(directory, 'fetch', '--no-tags', '--depth=1',
                     'https://github.com/' + repository + '.git', commit)
            require(self.git(directory, 'cat-file', '-t', commit).strip() == b'commit', 'not commit')
            require(self.git(directory, 'rev-parse', 'FETCH_HEAD').decode().strip() == commit,
                    'snapshot mismatch')
            self.repositories[key] = directory
        return self.repositories[key]

    def enumerate(self, item):
        safe_path(item['inbox_path'])
        directory = self.snapshot(item['repository'], item['commit'])
        # Missing prefix means empty inbox, not missing scan: retained history detects disappearances.
        entries = self.git(directory, 'ls-tree', '-r', '-z', item['commit'], '--', item['inbox_path'])
        result = []
        for entry in entries.split(b'\0'):
            if not entry:
                continue
            header, name = entry.split(b'\t', 1)
            mode, kind, oid = header.split()
            path = name.decode('utf-8')
            require(path.startswith(item['inbox_path'] + '/') and
                    mode in (b'100644', b'100755') and kind == b'blob', 'unsafe inbox tree')
            safe_path(path)
            size = int(self.git(directory, 'cat-file', '-s', oid.decode()))
            require(size <= MAX_FILE and len(result) < 1024, 'inbox resource limit')
            result.append(dict(repository=item['repository'], commit=item['commit'], path=path,
                               size=size, sha256='0' * 64))
        return result


def initial(writer, scope):
    return dict(schema_version='1.0', document_type='knowledge_collection_state', writer=writer,
                scope=scope, sequence=0, previous_state_sha256=None, registry_sha256=None,
                cursors={}, events={}, batches={}, scans=[], publication='private_only')


def validate_state(state):
    validate('knowledge-collection-state', state)
    for identity, event in state['events'].items():
        if event['event'] is not None:
            validate_event(event['event'])
            require(identity == event['event']['event_id'], 'state identity mismatch')
        require(event['history'] and event['history'][-1]['status'] == event['status'], 'state history mismatch')
        if event['batch_id'] is not None:
            require(event['batch_id'] in state['batches'] and
                    identity in state['batches'][event['batch_id']]['event_ids'], 'orphan batch')
    for identity, batch in state['batches'].items():
        validate_ledger(batch['ledger'])
        require(batch['ledger_sha256'] == digest(encode(batch['ledger'])), 'ledger pin mismatch')
        require(identity == digest(encode(sorted(batch['event_ids']))) and
                len(set(batch['event_ids'])) == len(batch['event_ids']), 'batch identity mismatch')
        require(batch['ledger']['scope'] == state['scope'] + '/' + identity, 'retry scope mismatch')
        require(all(e in state['events'] and state['events'][e]['batch_id'] == identity
                    for e in batch['event_ids']), 'batch binding mismatch')


def move(state, identities, status, reason, evidence=None):
    for identity in identities:
        item = state['events'][identity]
        item['status'] = status
        item['history'].append(dict(sequence=state['sequence'] + 1, status=status,
                                    reason=reason, evidence_sha256=evidence))


def scan(state, registry_raw, source):
    registry = parse(registry_raw)
    validate('knowledge-source-registry', registry)
    require(len({s['source_id'] for s in registry['sources']}) == len(registry['sources']),
            'duplicate source')
    require(len({(s['repository'], s['inbox_path']) for s in registry['sources']}) ==
            len(registry['sources']), 'overlapping source snapshot')
    for a in registry['sources']:
        safe_path(a['inbox_path'])
        for b in registry['sources']:
            require(a is b or a['repository'] != b['repository'] or
                    not a['inbox_path'].startswith(b['inbox_path'] + '/'), 'overlapping inbox')
    blobs, archive = {}, {digest(registry_raw): registry_raw}
    total = 0
    # Fetch ALL dependencies first. Any missing/partial/tampered bytes abort the scan transaction.
    for artifact in registry['artifacts']:
        ref = artifact['reference']; key = refkey(ref)
        require(key not in blobs, 'duplicate dependency')
        raw = source.read(ref)
        require(len(raw) == ref['size'] and digest(raw) == ref['sha256'], 'source bytes changed')
        total += len(raw); require(total <= MAX_BUNDLE, 'scan resource limit')
        blobs[key] = raw; archive[digest(raw)] = raw
    verify_handoffs(registry['artifacts'], blobs, '1.1', registry['knowledge_bindings'])
    inventory = {refkey(a['reference']): a['reference'] for a in registry['artifacts']}
    observations = []
    for item in registry['sources']:
        entries = source.enumerate(item)
        require(len(entries) <= 1024 and len({r['path'] for r in entries}) == len(entries),
                'incomplete or duplicate enumeration')
        for ref in entries:
            require(ref['repository'] == item['repository'] and ref['commit'] == item['commit'] and
                    ref['path'].startswith(item['inbox_path'] + '/'), 'snapshot mismatch')
            raw = source.read(ref)
            require(len(raw) == ref['size'], 'partial inbox read')
            total += len(raw); require(total <= MAX_BUNDLE, 'scan resource limit')
            raw_hash = digest(raw); archive[raw_hash] = raw
            try:
                event = parse(raw); validate_event(event)
                require(ref['path'] == item['inbox_path'] + '/' + event['event_id'] + '.json',
                        'event filename mismatch')
                for dependency in [event['source_ref'], *event['finding_refs']]:
                    require(inventory.get(refkey(dependency)) == dependency, 'unlisted dependency')
                observations.append((event['event_id'], raw_hash, event, item['source_id']))
            except (ValueError, UnicodeError, RecursionError):
                # Poison bytes are retained, never executed, never interpolated in public logs.
                observations.append((digest(encode(dict(source=item['source_id'], path=ref['path'],
                                                        sha256=raw_hash))), raw_hash, None, item['source_id']))
    candidate = deepcopy(state)
    seen, anomaly = set(), False
    for identity, raw_hash, event, source_id in observations:
        seen.add(identity)
        old = candidate['events'].get(identity)
        if old:
            if source_id not in old['source_ids']:
                old['source_ids'].append(source_id)
            if old['event_sha256'] != raw_hash:
                move(candidate, [identity], 'quarantined', 'collision', raw_hash); anomaly = True
            continue
        candidate['events'][identity] = dict(event_sha256=raw_hash, event=event,
            source_ids=[source_id], status='pending', batch_id=None, history=[])
        move(candidate, [identity], 'pending', 'discovered', raw_hash)
        move(candidate, [identity], 'verified' if event else 'quarantined',
             'verified' if event else 'poison', raw_hash)
    for identity in state['events'].keys() - seen:
        move(candidate, [identity], 'quarantined', 'missing')
        anomaly = True
    # Missing/colliding historical events cannot be reported as successful scan progress.
    if not anomaly:
        candidate['cursors'] = {s['source_id']: s['commit'] for s in registry['sources']}
    candidate['registry_sha256'] = digest(registry_raw)
    candidate['scans'].append(dict(registry_sha256=digest(registry_raw), mode='full',
        result='quarantined' if anomaly else 'verified', event_digests=[x[1] for x in observations],
        source_snapshots=registry['sources']))
    return candidate, archive


def append_retry(batch, kind, result, evidence):
    before = encode(batch['ledger'])
    after = deepcopy(batch['ledger'])
    epoch = after['epochs'][-1]
    epoch['events'].append(dict(kind=kind, result=result, evidence=evidence))
    if result != 'succeeded' and sum(e['kind'] == kind for e in epoch['events']) == epoch['limits'][kind]:
        epoch['terminal'] = 'RETRY_LIMIT_REACHED'
    batch['ledger'] = retry_transition(before, encode(after), batch['ledger_sha256'])
    batch['ledger_sha256'] = digest(encode(batch['ledger']))


def budget(batch, kind):
    epoch = batch['ledger']['epochs'][-1]
    require(epoch['terminal'] == 'open' and
            sum(e['kind'] == kind for e in epoch['events']) < epoch['limits'][kind], 'RETRY_LIMIT_REACHED')


def verify_bundle(manifest, source):
    # Exact bundle is authorized by the independently pinned record request.
    from_schema = json.loads((ROOT / 'contracts/artifact-delivery-v1.1.schema.json').read_text())
    require(Draft202012Validator(from_schema).is_valid(manifest), 'invalid typed bundle')
    blobs, archive, total = {}, {}, 0
    for a in manifest['artifacts']:
        ref = a['reference']; key = refkey(ref)
        require(key not in blobs, 'duplicate reference')
        raw = source.read(ref)
        require(len(raw) == ref['size'] and digest(raw) == ref['sha256'], 'bundle bytes mismatch')
        total += len(raw); require(total <= MAX_BUNDLE, 'bundle resource limit')
        blobs[key] = raw; archive[digest(raw)] = raw
    verify_handoffs(manifest['artifacts'], blobs, '1.1', manifest['knowledge_bindings'])
    return blobs, archive


def record(state, request, object_read, source, grant_raw=None, grant_pin=None, now=None):
    """Only Manager observations; external actions always happen AFTER persisted reservations."""
    validate('knowledge-collection-record', request)
    candidate = deepcopy(state); archive = {}
    action = request.get('action')
    now = now or datetime.now(timezone.utc)
    if action == 'reserve':
        fields(request, 'action event_ids input_sha256 lease_until' +
               (' prior_ledger_sha256' if 'prior_ledger_sha256' in request else ''))
        ids = request['event_ids']
        require(isinstance(ids, list) and ids and len(ids) == len(set(ids)), 'empty/duplicate batch')
        require(all(e in candidate['events'] and candidate['events'][e]['status'] == 'verified' and
                    candidate['events'][e]['batch_id'] is None for e in ids), 'event already claimed')
        identity = digest(encode(sorted(ids)))
        require(identity not in candidate['batches'], 'batch cannot reset retry history')
        raw = object_read(request['input_sha256']); data = parse(raw)
        require(digest(raw) == request['input_sha256'] and not validate_knowledge(data) and
                data['document_type'] == 'knowledge_input', 'invalid sealed input')
        require(stamp(request['lease_until']) > now, 'invalid lease')
        # One mechanical raw finding per event; supplied input must retain the exact source digests.
        require({f['id'] for f in data['raw_findings']} == set(ids), 'input event coverage mismatch')
        for finding in data['raw_findings']:
            event = candidate['events'][finding['id']]['event']
            expected = {r['sha256'] for r in [event['source_ref'], *event['finding_refs']]}
            require({s['revision'] for s in finding['sources']} == {'sha256:' + h for h in expected},
                    'input source coverage mismatch')
        ledger = dict(version='1.0', scope=state['scope'] + '/' + identity,
                      epochs=[dict(id=1, limits=LIMITS.copy(), events=[], terminal='open', grant_sha256=None)])
        if 'prior_ledger_sha256' in request:
            prior_raw = object_read(request['prior_ledger_sha256'])
            require(digest(prior_raw) == request['prior_ledger_sha256'], 'legacy history pin mismatch')
            ledger = parse(prior_raw); validate_ledger(ledger)
            require(ledger['scope'] == state['scope'] + '/' + identity, 'legacy scope mismatch')
            archive[digest(prior_raw)] = prior_raw
        candidate['batches'][identity] = dict(event_ids=sorted(ids), input_sha256=digest(raw),
            ledger=ledger, ledger_sha256=digest(encode(ledger)), pending=None, runtime_id=None,
            lease_until=request['lease_until'], output_sha256=None, validated_artifacts=[],
            committed_output_pin=[], next_eligible_at=None, new_input_required=False)
        for e in ids: candidate['events'][e]['batch_id'] = identity
        move(candidate, ids, 'terminal' if ledger['epochs'][-1]['terminal'] == 'RETRY_LIMIT_REACHED'
             else 'reserved', 'reserved', digest(raw)); archive[digest(raw)] = raw
        return candidate, archive
    require(isinstance(request.get('batch_id'), str) and request['batch_id'] in candidate['batches'],
            'unknown batch')
    batch = candidate['batches'][request['batch_id']]; ids = batch['event_ids']
    states = {candidate['events'][e]['status'] for e in ids}
    require(len(states) == 1, 'batch interrupted by quarantine')
    status = next(iter(states))
    proof = digest(encode(request))
    if action == 'dispatch':
        fields(request, 'action batch_id')
        require(status == 'reserved' and batch['pending'] is None and batch['output_sha256'] is None,
                'dispatch not allowed')
        require(not batch['new_input_required'], 'new sealed retry input required')
        require(batch['next_eligible_at'] is None or now >= stamp(batch['next_eligible_at']), 'backoff active')
        budget(batch, 'dispatch'); budget(batch, 'execution')
        input_data = parse(object_read(batch['input_sha256']))
        executions = sum(e['kind'] == 'execution' for e in batch['ledger']['epochs'][-1]['events'])
        require(input_data['attempt'] == executions + 1, 'new sealed retry input required')
        batch['pending'] = 'dispatch'
        move(candidate, ids, 'dispatching', 'dispatch', proof)
    elif action == 'prepare_retry':
        fields(request, 'action batch_id input_sha256 manifest')
        require(status == 'reserved' and batch['pending'] is None and batch['output_sha256'] is None,
                'cannot replace active input/output')
        _, archive = verify_bundle(request['manifest'], source)
        require(any(a['format'] == 'knowledge-input-v1' and
                    a['reference']['sha256'] == request['input_sha256']
                    for a in request['manifest']['artifacts']), 'retry input missing')
        new = parse(archive[request['input_sha256']])
        old = parse(object_read(batch['input_sha256']))
        epoch = batch['ledger']['epochs'][-1]
        executions = sum(e['kind'] == 'execution' for e in epoch['events'])
        require(new['attempt'] == executions + 1 and new['task_id'] != old['task_id'] and
                all(new[k] == old[k] for k in ('assignment', 'raw_findings', 'knowledge_references')),
                'retry input identity/scope mismatch')
        if executions:
            require(new['attempt'] == old['attempt'] + 1 and
                    any(r['task_id'] == old['task_id'] and r['attempt'] == old['attempt']
                        for r in new['retry_of']), 'previous execution missing')
            require(any(pair['input']['sha256'] == batch['input_sha256'] and
                        pair.get('handoff', {}).get('sha256') in
                            {r['revision'].removeprefix('sha256:') for r in new['retry_of']} and
                        parse(archive[pair['handoff']['sha256']])['status'] in ('failed', 'blocked')
                        for pair in request['manifest']['knowledge_bindings']),
                    'retry must preserve failed previous input/output binding')
        else:
            require(epoch['id'] > 1 and new['attempt'] == 1 and not new['retry_of'],
                    'new epoch requires separate grant')
        batch['input_sha256'] = request['input_sha256']
        batch['new_input_required'] = False
        move(candidate, ids, status, 'reserved', proof)
    elif action == 'dispatch_unknown':
        fields(request, 'action batch_id')
        require(status == 'dispatching' and batch['pending'] == 'dispatch', 'not dispatching')
        move(candidate, ids, 'dispatch_unknown', 'unknown', proof)
    elif action in ('started', 'dispatch_failed'):
        fields(request, 'action batch_id runtime_id evidence_sha256 next_eligible_at')
        require(status in ('dispatching', 'dispatch_unknown') and batch['pending'] == 'dispatch',
                'no pending dispatch')
        evidence = object_read(request['evidence_sha256'])
        require(digest(evidence) == request['evidence_sha256'], 'observation mismatch')
        archive[digest(evidence)] = evidence
        require((isinstance(request['runtime_id'], str) and bool(request['runtime_id'].strip()))
                if action == 'started' else request['runtime_id'] is None, 'invalid runtime observation')
        append_retry(batch, 'dispatch', 'succeeded' if action == 'started' else 'failed', proof)
        batch['pending'] = 'execution' if action == 'started' else None
        batch['runtime_id'] = request['runtime_id']; batch['next_eligible_at'] = request['next_eligible_at']
        move(candidate, ids, 'started' if action == 'started' else 'reserved', action, proof)
    elif action in ('execution_failed', 'output_received'):
        fields(request, 'action batch_id runtime_id evidence_sha256 next_eligible_at')
        require(status == 'started' and batch['pending'] == 'execution' and
                request['runtime_id'] == batch['runtime_id'], 'execution identity mismatch')
        raw = object_read(request['evidence_sha256'])
        require(digest(raw) == request['evidence_sha256'], 'output observation mismatch')
        archive[digest(raw)] = raw
        append_retry(batch, 'execution', 'succeeded' if action == 'output_received' else 'failed', proof)
        batch['pending'] = None; batch['next_eligible_at'] = request['next_eligible_at']
        if action == 'output_received': batch['output_sha256'] = digest(raw)
        else: batch['new_input_required'] = True
        move(candidate, ids, 'output_received' if action == 'output_received' else 'reserved', action, proof)
    elif action == 'delivery_start':
        fields(request, 'action batch_id')
        require(status == 'output_received' and batch['pending'] is None, 'delivery not allowed')
        require(batch['next_eligible_at'] is None or now >= stamp(batch['next_eligible_at']), 'backoff active')
        budget(batch, 'delivery'); batch['pending'] = 'delivery'
        move(candidate, ids, 'output_received', action, proof)
    elif action == 'delivery_failed':
        fields(request, 'action batch_id evidence_sha256 next_eligible_at')
        require(status == 'output_received' and batch['pending'] == 'delivery', 'no pending delivery')
        raw = object_read(request['evidence_sha256']); require(digest(raw) == request['evidence_sha256'], 'bad evidence')
        archive[digest(raw)] = raw
        append_retry(batch, 'delivery', 'failed', proof); batch['pending'] = None
        batch['next_eligible_at'] = request['next_eligible_at']
        move(candidate, ids, status, action, proof)
    elif action == 'validated':
        fields(request, 'action batch_id manifest')
        require(status == 'output_received' and batch['pending'] == 'delivery', 'no pending delivery')
        blobs, archive = verify_bundle(request['manifest'], source)
        pairs = request['manifest']['knowledge_bindings']
        require(any(p['input']['sha256'] == batch['input_sha256'] and
                    p.get('handoff', {}).get('sha256') == batch['output_sha256'] for p in pairs),
                'sealed input/output mismatch')
        output = parse(archive[batch['output_sha256']])
        require(output['status'] == 'completed', 'Knowledge output incomplete')
        append_retry(batch, 'delivery', 'succeeded', proof); batch['pending'] = None
        batch['validated_artifacts'] = request['manifest']['artifacts']
        move(candidate, ids, 'validated', action, proof)
    elif action == 'commit_pending':
        fields(request, 'action batch_id')
        require(status == 'validated', 'not validated')
        move(candidate, ids, 'commit_pending', action, proof)
    elif action == 'committed':
        fields(request, 'action batch_id committed_output_pin')
        require(status == 'commit_pending', 'not commit pending')
        refs = request['committed_output_pin']
        require(isinstance(refs, list) and refs and len({refkey(r) for r in refs}) == len(refs), 'invalid commit pins')
        # Retain ALL validated bytes, including source evidence. New snapshot must contain the same
        # path->size/hash set. This is byte acknowledgement, never a merge/readiness claim.
        expected = Counter((a['reference']['path'], a['reference']['size'], a['reference']['sha256'])
                           for a in batch['validated_artifacts'])
        require(Counter((r['path'], r['size'], r['sha256']) for r in refs) == expected,
                'committed output set mismatch')
        require(len({(r['repository'], r['commit']) for r in refs}) == 1, 'one committed snapshot required')
        for ref in refs:
            raw = source.read(ref)
            require(len(raw) == ref['size'] and digest(raw) == ref['sha256'], 'commit bytes mismatch')
            archive[digest(raw)] = raw
        batch['committed_output_pin'] = refs
        move(candidate, ids, 'committed', action, proof)
    elif action == 'context_available':
        fields(request, 'action batch_id context_ref')
        require(status == 'committed', 'not committed')
        ref = request['context_ref']
        require(ref in batch['committed_output_pin'], 'context must be committed')
        require(any(a['format'] == 'knowledge-context-v1' and a['reference']['path'] == ref['path'] and
                    a['reference']['sha256'] == ref['sha256'] for a in batch['validated_artifacts']), 'unvalidated context')
        move(candidate, ids, 'context_available', action, proof)
    elif action == 'blocked':
        fields(request, 'action batch_id evidence_sha256')
        require(status in ('reserved', 'validated') and batch['pending'] is None, 'unsafe block')
        raw = object_read(request['evidence_sha256']); require(digest(raw) == request['evidence_sha256'], 'bad evidence')
        archive[digest(raw)] = raw; move(candidate, ids, 'blocked', action, proof)
    elif action == 'renew':
        fields(request, 'action batch_id ledger resume_state')
        require(status == 'terminal' and batch['pending'] is None, 'not terminal')
        before = encode(batch['ledger'])
        batch['ledger'] = retry_transition(before, encode(request['ledger']), batch['ledger_sha256'], grant_raw, grant_pin)
        batch['ledger_sha256'] = digest(encode(batch['ledger']))
        target = 'output_received' if batch['output_sha256'] else 'reserved'
        require(request['resume_state'] == target, 'cannot discard output')
        archive[digest(grant_raw)] = grant_raw
        if target == 'reserved' and any(e['kind'] == 'execution'
                for epoch in batch['ledger']['epochs'][:-1] for e in epoch['events']):
            batch['new_input_required'] = True
        move(candidate, ids, target, 'renewed', proof)
    else:
        raise ValueError('unknown record action')
    if batch['ledger']['epochs'][-1]['terminal'] == 'RETRY_LIMIT_REACHED':
        move(candidate, ids, 'terminal', action, proof)
    return candidate, archive


def plan(state):
    """Private, deterministic suggestions only. Lease expiry does not change any action."""
    validate_state(state)
    result = []
    for identity, item in sorted(state['events'].items()):
        status = item['status']
        action = {'verified': 'reserve', 'reserved': 'dispatch', 'dispatching': 'reconcile_start',
                  'dispatch_unknown': 'reconcile_start', 'started': 'recover_output',
                  'output_received': 'resume_delivery', 'validated': 'commit_pending',
                  'commit_pending': 'verify_fixed_commit'}.get(status, 'none')
        if item['batch_id'] is not None:
            batch = state['batches'][item['batch_id']]
            if status == 'reserved':
                if batch['new_input_required']: action = 'prepare_retry'
                try:
                    budget(batch, 'dispatch'); budget(batch, 'execution')
                except ValueError:
                    action = 'none'
        result.append(dict(event_id=identity, status=status, action=action))
    return dict(schema_version='1.0', authority_granted=False, actions=result)


def public_observation(state):
    counts = Counter(e['status'] for e in state['events'].values())
    return dict(schema_version='1.0', document_type='knowledge_collection_observation',
                counts={s: counts[s] for s in STATES}, development_gate_changed=False,
                authority_granted=False)


def fsync_dir(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try: os.fsync(fd)
    finally: os.close(fd)


def durable(path, raw):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())


class Store:
    """POSIX local filesystem, single trusted Manager, advisory lock + digest CAS + fsync.

    Caller supplies an independently retained latest state pin. Rollback of the entire
    private store by its owner cannot be detected without that external pin.
    """
    def __init__(self, directory):
        self.directory = Path(directory)
        require(not self.directory.is_symlink(), 'unsafe store')
        if not self.directory.exists():
            self.directory.mkdir(mode=0o700)
            fsync_dir(self.directory.parent)
        require(self.directory.stat().st_mode & 0o077 == 0, 'store must be private')
        for name in ('objects', 'snapshots', 'staging'):
            path = self.directory / name
            require(not path.is_symlink(), 'unsafe store child')
            path.mkdir(mode=0o700, exist_ok=True)
        fsync_dir(self.directory)

    @contextmanager
    def lock(self):
        fd = os.open(self.directory / 'writer.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            try: fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError: raise ValueError('overlapping writer') from None
            yield
        finally:
            os.close(fd)

    def load(self, expected, writer=None, scope=None):
        path = self.directory / 'state.json'
        if expected == 'absent':
            require(not path.exists(), 'stale initialization')
            require(writer and scope, 'initial writer/scope required')
            return initial(writer, scope), None
        raw = read_local(path)
        require(digest(raw) == expected, 'stale state digest')
        data = parse(raw); validate_state(data)
        if writer is not None: require(data['writer'] == writer and data['scope'] == scope, 'wrong writer')
        return data, raw

    def read_object(self, sha256):
        require(isinstance(sha256, str) and re.fullmatch('[0-9a-f]{64}', sha256), 'invalid object digest')
        raw = read_local(self.directory / 'objects' / sha256)
        require(digest(raw) == sha256, 'object corrupted')
        return raw

    def put(self, raw):
        require(len(raw) <= MAX_FILE, 'object too large')
        path = self.directory / 'objects' / digest(raw)
        if path.exists(): require(read_local(path) == raw, 'object collision')
        else: durable(path, raw)
        return digest(raw)

    def _commit(self, previous_raw, candidate, archive, crash=lambda point: None):
        candidate = deepcopy(candidate)
        candidate['sequence'] += 1
        candidate['previous_state_sha256'] = digest(previous_raw) if previous_raw else None
        validate_state(candidate)
        # Retain exact previous state and all raw bytes before publishing a cursor.
        if previous_raw: self.put(previous_raw)
        for key, raw in archive.items():
            require(digest(raw) == key, 'archive digest mismatch'); self.put(raw)
        fsync_dir(self.directory / 'objects'); crash('after_objects')
        raw = encode(candidate); pin = digest(raw)
        staged = self.directory / 'staging' / pin
        if staged.exists(): require(read_local(staged) == raw, 'stage collision')
        else: durable(staged, raw)
        fsync_dir(staged.parent); crash('after_stage')
        snapshot = self.directory / 'snapshots' / pin
        if snapshot.exists(): require(read_local(snapshot) == raw, 'snapshot collision')
        else: durable(snapshot, raw)
        fsync_dir(snapshot.parent); crash('after_snapshot')
        # Candidate is complete; state pointer replacement is the single commit point.
        os.replace(staged, self.directory / 'state.json')
        crash('after_rename')
        fsync_dir(self.directory); crash('after_replace')
        return candidate, pin

    def mutate(self, expected, writer, scope, transform, crash=lambda point: None):
        with self.lock():
            state, raw = self.load(expected, writer, scope)
            candidate, archive = transform(state)
            return self._commit(raw, candidate, archive, crash)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('scan', 'reconcile', 'record', 'plan', 'replay'))
    parser.add_argument('--store', type=Path, required=True)
    parser.add_argument('--previous-sha256', required=True)
    parser.add_argument('--writer'); parser.add_argument('--scope')
    parser.add_argument('--request', type=Path)
    parser.add_argument('--authorization', type=Path); parser.add_argument('--authorization-sha256')
    parser.add_argument('--grant', type=Path); parser.add_argument('--grant-sha256')
    parser.add_argument('--objects', type=Path, help='private directory of input/output/evidence bytes keyed by SHA256')
    parser.add_argument('--private-plan', type=Path)
    args = parser.parse_args()
    try:
        if args.operation in ('plan', 'replay'):
            # No mkdir, lock, staging recovery, receipt acceptance or network on read-only replay.
            raw = read_local(args.store / 'state.json')
            require(digest(raw) == args.previous_sha256, 'stale replay state')
            state = parse(raw); private_plan = plan(state)
            if args.private_plan: durable(args.private_plan, encode(private_plan))
            print(json.dumps(public_observation(state), sort_keys=True)); return 0
        require(args.request and args.authorization and args.authorization_sha256 and args.writer and args.scope,
                'mutation requires independent authority')
        request_raw = read_local(args.request)
        authorize(read_local(args.authorization), args.authorization_sha256, request_raw, args.operation,
                  args.writer, args.scope)
        store = Store(args.store)
        def object_read(pin):
            if args.objects:
                require(re.fullmatch('[0-9a-f]{64}', pin), 'invalid object pin')
                raw = read_local(args.objects / pin); require(digest(raw) == pin, 'object pin mismatch')
                return raw
            return store.read_object(pin)
        with tempfile.TemporaryDirectory(prefix='collector-git-') as temp:
            source = SnapshotSource(temp)
            def transform(state):
                if args.operation in ('scan', 'reconcile'):
                    changed, archive = scan(state, request_raw, source)
                else:
                    changed, archive = record(state, parse(request_raw), object_read, source,
                        read_local(args.grant) if args.grant else None, args.grant_sha256)
                # Private audit only; never put request/auth/runtime IDs into stdout.
                archive[digest(request_raw)] = request_raw
                return changed, archive
            state, _ = store.mutate(args.previous_sha256, args.writer, args.scope, transform)
        print(json.dumps(public_observation(state), sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError, KeyError, UnicodeError, RecursionError, subprocess.SubprocessError):
        print('FAIL: Knowledge collection rejected; development gate unchanged', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
