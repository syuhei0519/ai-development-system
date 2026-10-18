#!/usr/bin/env python3
"""Append-only retry transitions against independently pinned Manager history and grants."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
try:
    from .consume_delivery import parse, digest, require, read_local
except ImportError:
    from consume_delivery import parse, digest, require, read_local

KINDS = ('dispatch', 'execution', 'delivery')
LIMITS = dict.fromkeys(KINDS, 3)


def keys(data, expected):
    require(isinstance(data, dict) and set(data) == set(expected.split()), 'invalid retry fields')


def text(value):
    require(isinstance(value, str) and bool(value.strip()), 'missing retry text')


def remaining_budget(epoch):
    counts = Counter(event['kind'] for event in epoch['events'])
    return {kind: epoch['limits'][kind] - counts[kind] for kind in KINDS}


def exhausted_failure(epoch):
    remaining = remaining_budget(epoch)
    for kind in KINDS:
        last = next((e for e in reversed(epoch['events']) if e['kind'] == kind), None)
        if remaining[kind] == 0 and last is not None and last['result'] != 'succeeded':
            return True
    return False


def validate_ledger(ledger):
    keys(ledger, 'version scope epochs')
    require(ledger['version'] == '1.0', 'invalid retry version')
    text(ledger['scope'])
    require(isinstance(ledger['epochs'], list) and bool(ledger['epochs']), 'missing retry epochs')
    for index, epoch in enumerate(ledger['epochs']):
        keys(epoch, 'id limits events terminal grant_sha256')
        require(type(epoch['id']) is int and epoch['id'] == index + 1, 'epoch order')
        keys(epoch['limits'], 'dispatch execution delivery')
        require(all(type(n) is int and (1 if index == 0 else 0) <= n <= 3 for n in epoch['limits'].values()), 'invalid retry budget')
        require(epoch['terminal'] in ('open', 'RETRY_LIMIT_REACHED'), 'invalid terminal state')
        require(isinstance(epoch['events'], list), 'invalid events')
        counts = Counter()
        for event in epoch['events']:
            keys(event, 'kind result evidence')
            require(event['kind'] in KINDS and event['result'] in ('succeeded', 'failed', 'blocked'), 'invalid event')
            text(event['evidence'])
            counts[event['kind']] += 1
        require(all(counts[k] <= epoch['limits'][k] for k in KINDS), 'retry budget exceeded')
        exhausted = any(n == 0 for n in remaining_budget(epoch).values())
        require(epoch['terminal'] != 'RETRY_LIMIT_REACHED' or exhausted, 'stop requires exhausted budget')
        require(not exhausted_failure(epoch) or epoch['terminal'] == 'RETRY_LIMIT_REACHED', 'terminal marker required')
        require(index == len(ledger['epochs']) - 1 or epoch['terminal'] == 'RETRY_LIMIT_REACHED',
                'renewal only after terminal stop')
        if index == 0:
            require(epoch['grant_sha256'] is None and epoch['limits'] == LIMITS, 'initial budget must be three')
        else:
            require(isinstance(epoch['grant_sha256'], str) and len(epoch['grant_sha256']) == 64,
                    'renewal needs external grant digest')


def transition(previous_raw, candidate_raw, previous_sha256, grant_raw=None, grant_sha256=None):
    require(digest(previous_raw) == previous_sha256, 'untrusted history')
    previous, candidate = parse(previous_raw), parse(candidate_raw)
    validate_ledger(previous)
    validate_ledger(candidate)
    require(previous['scope'] == candidate['scope'], 'scope relabeling rejected')
    old, new = previous['epochs'], candidate['epochs']
    if len(new) == len(old):
        require(new[:-1] == old[:-1], 'past epochs changed')
        before, after = old[-1], new[-1]
        require(before['terminal'] != 'RETRY_LIMIT_REACHED', 'RETRY_LIMIT_REACHED: explicit renewal required')
        require(all(before[k] == after[k] for k in ('id','limits','grant_sha256')), 'budget changed')
        if after['events'] == before['events']:
            require(before['terminal'] == 'open' and after['terminal'] == 'RETRY_LIMIT_REACHED' and
                    any(n == 0 for n in remaining_budget(before).values()), 'stop requires exhausted budget')
            return candidate
        require(after['events'][:-1] == before['events'] and len(after['events']) == len(before['events'])+1,
                'history must append exactly one event')
    else:
        require(len(new) == len(old)+1 and new[:-1] == old, 'history reset/reclassification rejected')
        require(old[-1]['terminal'] == 'RETRY_LIMIT_REACHED', 'renewal only after terminal stop')
        require(grant_raw is not None and grant_sha256 is not None and digest(grant_raw) == grant_sha256,
                'independently pinned renewal approval required')
        grant = parse(grant_raw)
        fields = 'approval authority reason scope prior_history_sha256 new_epoch limits relationship'
        bounded = 'increments' in grant
        keys(grant, fields + (' increments explicit_owner_grant expires_at' if bounded else ''))
        require(bounded or exhausted_failure(old[-1]), 'successful exhaustion needs bounded owner grant')
        if bounded:
            require(grant['explicit_owner_grant'] is True, 'explicit owner grant required')
            text(grant['expires_at'])
            expires = datetime.fromisoformat(grant['expires_at'].replace('Z', '+00:00'))
            require(expires.tzinfo is not None and datetime.now(timezone.utc) < expires, 'expired owner grant')
            increments = grant['increments']
            keys(increments, 'dispatch execution delivery')
            require(all(type(n) is int for n in increments.values()) and
                    increments['dispatch'] == increments['execution'] == 0 and
                    1 <= increments['delivery'] <= 3, 'only bounded delivery increment permitted')
            remaining = remaining_budget(old[-1])
            require(grant['limits'] == {k: remaining[k] + increments[k] for k in KINDS},
                    'renewal must preserve other remaining budgets')
        require(grant['approval'] == 'approved', 'renewal not approved')
        for k in ('authority','reason','relationship'): text(grant[k])
        require(grant['scope'] == previous['scope'] and grant['prior_history_sha256'] == digest(previous_raw),
                'renewal history/scope mismatch')
        require(type(grant['new_epoch']) is int and grant['new_epoch'] == new[-1]['id'] and
                grant['limits'] == new[-1]['limits'], 'renewal budget/epoch mismatch')
        require(new[-1]['grant_sha256'] == digest(grant_raw) and new[-1]['events'] == [] and
                new[-1]['terminal'] == 'open', 'renewal must start empty linked epoch')
    return candidate


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('previous','candidate'): parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--previous-sha256', required=True)
    parser.add_argument('--grant', type=Path)
    parser.add_argument('--grant-sha256')
    args=parser.parse_args()
    try:
        transition(read_local(args.previous), read_local(args.candidate), args.previous_sha256,
                   read_local(args.grant) if args.grant else None, args.grant_sha256)
        print('PASS: append-only transition; Manager must persist history before any subsequent dispatch')
        return 0
    except (ValueError, OSError, TypeError, RecursionError):
        print('FAIL: retry transition rejected', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
