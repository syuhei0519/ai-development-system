#!/usr/bin/env python3
"""Append-only retry transitions against independently pinned Manager history and grants."""
import argparse
from collections import Counter
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


def validate_ledger(ledger):
    keys(ledger, 'version scope epochs')
    require(ledger['version'] == '1.0', 'invalid retry version')
    text(ledger['scope'])
    require(isinstance(ledger['epochs'], list) and bool(ledger['epochs']), 'missing retry epochs')
    for index, epoch in enumerate(ledger['epochs']):
        keys(epoch, 'id limits events terminal grant_sha256')
        require(type(epoch['id']) is int and epoch['id'] == index + 1, 'epoch order')
        keys(epoch['limits'], 'dispatch execution delivery')
        require(all(type(n) is int and 1 <= n <= 3 for n in epoch['limits'].values()), 'invalid retry budget')
        require(epoch['terminal'] in ('open', 'RETRY_LIMIT_REACHED'), 'invalid terminal state')
        require(isinstance(epoch['events'], list), 'invalid events')
        counts = Counter()
        for event in epoch['events']:
            keys(event, 'kind result evidence')
            require(event['kind'] in KINDS and event['result'] in ('succeeded', 'failed', 'blocked'), 'invalid event')
            text(event['evidence'])
            counts[event['kind']] += 1
        require(all(counts[k] <= epoch['limits'][k] for k in KINDS), 'retry budget exceeded')
        exhausted_failure = any(counts[k] == epoch['limits'][k] and
            next(e for e in reversed(epoch['events']) if e['kind'] == k)['result'] != 'succeeded'
            for k in KINDS if counts[k])
        require(not exhausted_failure or epoch['terminal'] == 'RETRY_LIMIT_REACHED', 'terminal marker required')
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
        require(after['events'][:-1] == before['events'] and len(after['events']) == len(before['events'])+1,
                'history must append exactly one event')
    else:
        require(len(new) == len(old)+1 and new[:-1] == old, 'history reset/reclassification rejected')
        require(old[-1]['terminal'] == 'RETRY_LIMIT_REACHED', 'renewal only after terminal stop')
        require(grant_raw is not None and grant_sha256 is not None and digest(grant_raw) == grant_sha256,
                'independently pinned renewal approval required')
        grant = parse(grant_raw)
        keys(grant, 'approval authority reason scope prior_history_sha256 new_epoch limits relationship')
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
