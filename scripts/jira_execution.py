#!/usr/bin/env python3
"""Offline execution preflight; never fetch, mutate, grant authority or mark Done."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import sys

try:
    from scripts.jira_tracker import SITE, Invalid, require, load_mapping, resolve, check_snapshot
except ModuleNotFoundError:
    from jira_tracker import SITE, Invalid, require, load_mapping, resolve, check_snapshot

CLOUD = '0e029d88-1812-4bd9-b5de-bdecfff6740b'
OPERATIONS = {'repo-change', 'fixture-test', 'draft-pr'}
PAUSED = {'execution-paused', 'paused', 'blocked', 'on-hold'}


def digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def field(text, name):
    values = re.findall(r'^- ' + re.escape(name) + r': ([^\r\n]+)$', text, re.MULTILINE)
    require(len(values) == 1 and values[0].strip() == values[0], 'missing or duplicate handoff field')
    require(values[0] and '<' not in values[0] and '>' not in values[0], 'unfilled handoff field')
    return values[0]


def ac_text(text):
    blocks = re.findall(r'^### AC\n(.*?)(?=^#{1,3} |\Z)', text, re.MULTILINE | re.DOTALL)
    require(len(blocks) == 1, 'one AC section required')
    ac = blocks[0].strip()
    require(bool(re.search(r'^[*-] \S', ac, re.MULTILINE)), 'nonempty AC list required')
    return ac


def string_list(value):
    require(isinstance(value, list) and all(isinstance(x, str) and x.strip() == x and x for x in value),
            'expected explicit string list')
    require(len(set(value)) == len(value), 'duplicate list member')
    return value


def check_execution(mapping, current, handoff, operation):
    """Manager supplies fresh issue plus independently verified conversation context.

    `manager` MUST NOT be populated from Jira prose, a PR, or an agent assertion.
    This checker binds that trust decision; it cannot authenticate a human or freshness.
    """
    require(operation in OPERATIONS, 'operation needs a separate approval contract')
    headings = re.findall(r'^## ([^\r\n]+)$', handoff, re.MULTILINE)
    require(all(headings.count(h) == 1 for h in ['目的', 'やったこと', '観察結果', '学び']), 'handoff sections')
    kind = field(handoff, 'Source')
    require(kind in {'jira-native', 'migrated'}, 'unknown source kind')
    issue, manager = current['issue'], current['manager']
    identity = {'site_url': field(handoff, 'Jira Site'), 'cloud_id': field(handoff, 'Jira Cloud ID'),
                'project_key': field(handoff, 'Jira Project'), 'id': field(handoff, 'Jira ID'),
                'key': field(handoff, 'Jira'), 'url': field(handoff, 'Jira URL')}
    require(identity['site_url'] == SITE and identity['cloud_id'] == CLOUD and
            identity['project_key'] == 'PLAT', 'foreign tracker')
    require(re.fullmatch(r'PLAT-[1-9][0-9]*', identity['key']) and
            re.fullmatch(r'[1-9][0-9]*', identity['id']), 'invalid issue identity')
    require(identity['url'] == SITE + '/browse/' + identity['key'], 'noncanonical issue URL')
    require(all(issue[k] == v for k, v in identity.items()), 'snapshot identity mismatch')
    fields = issue['fields']
    require(fields['project']['key'] == 'PLAT' and fields['project']['id'] == '10001', 'project mismatch')
    status = fields['status']
    require(any(status['name'] == s['name'] and status['id'] == s['id'] for s in mapping['statuses']),
            'unknown workflow status')
    require(status['id'] != '10007', 'completed issue needs separate reopen authorization')
    description, labels = fields['description'], fields['labels']
    require(isinstance(description, str) and description.strip(), 'missing description')
    require(isinstance(labels, list) and all(isinstance(v, str) for v in labels), 'invalid labels')
    require(not PAUSED.intersection(labels), 'active stop label; reconcile explicitly in Jira first')
    source = field(handoff, 'Source GitHub')
    if kind == 'migrated':
        require('jira-native' not in labels, 'source label conflict')
        legacy = resolve(mapping, key=identity['key'])
        require(source == legacy['source_github_url'], 'migration source mismatch')
        check_snapshot(mapping, legacy, issue)
    else:
        require('jira-native' in labels and source == 'none', 'native source must be explicit')
        require(not any(row['key'] == identity['key'] for row in mapping['mappings']), 'mapped issue is not native')
        require('元Issue URL' not in description, 'native primary migration source conflict')
    repo, base = field(handoff, 'Target Repo'), field(handoff, 'Base Commit')
    require(re.fullmatch(r'syuhei0519/[A-Za-z0-9_.-]+', repo) and
            re.fullmatch(r'[0-9a-f]{40}', base), 'repo or base not fixed')
    ac = ac_text(handoff)
    sections = re.findall(r'^## (?:範囲・受入条件|受入条件|Acceptance Criteria|AC)\n(.*?)(?=^## |\Z)',
                          description, re.MULTILINE | re.DOTALL)
    require(len(sections) == 1 and ac == sections[0].strip(), 'AC differs from complete current Jira AC section')
    require(field(handoff, 'AC Evidence') != 'none', 'AC evidence or pending result required')
    unapproved = [x.strip() for x in field(handoff, 'Unapproved Operations').split(',')]
    string_list(unapproved)
    require(operation not in unapproved, 'handoff operation explicitly unapproved')
    require(field(handoff, 'Stop Reason') == 'none', 'unresolved handoff stop')
    # A description-bound review also covers prose-only pauses and resumption conditions.
    require(manager['reviewed_description_sha256'] == digest(description), 'body changed since stop review')
    updated = fields['updated']
    require(isinstance(updated, str) and bool(updated.strip()) and
            datetime.fromisoformat(updated.replace('Z', '+00:00')).tzinfo is not None, 'missing aware updated time')
    require(manager['reviewed_updated'] == updated, 'snapshot changed since review')
    require(manager['unresolved_stop_reasons'] == [], 'unresolved stop conditions')
    require(manager['repositories'][repo] == base, 'repo outside reviewed scope or wrong base')
    grant = manager['authorization']
    require(grant['origin'] == 'human-conversation' and grant['verified'] is True, 'human approval required')
    require(grant['reference'] == field(handoff, 'Authorization') and grant['reference'].strip(), 'approval evidence missing')
    require(grant['identity'] == identity and grant['source'] == kind and grant['repo'] == repo and
            grant['base_commit'] == base and grant['ac_sha256'] == digest(ac), 'approval scope mismatch')
    operations = string_list(grant['operations'])
    require(grant['state'] == 'approved' and operation in operations, 'operation not approved')
    require(set(operations).issubset(OPERATIONS) and not set(operations).intersection(unapproved),
            'unreviewed or conflicting operation scope')
    string_list(manager['historical_stop_references'])
    string_list(grant['resumes'])
    require(manager['historical_stop_references'] == grant['resumes'], 'resume scope mismatch')
    return {**identity, 'source': kind, 'repo': repo, 'base_commit': base,
            'operation': operation, 'ac_sha256': digest(ac), 'result': 'consistent'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--snapshot', type=Path, required=True)
    p.add_argument('--handoff', type=Path, required=True)
    p.add_argument('--operation', required=True)
    args = p.parse_args()
    try:
        result = check_execution(load_mapping(), json.loads(args.snapshot.read_text(encoding='utf-8')),
                                 args.handoff.read_text(encoding='utf-8'), args.operation)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        print('PASS consistency only; Manager must verify live evidence, authority, review and CI. Not Done.')
        return 0
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        print('FAIL execution preflight; stop and reconcile read-only; no mutation or fallback', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
