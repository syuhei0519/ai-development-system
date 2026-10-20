#!/usr/bin/env python3
"""Read-only Jira identity checks. No API calls, writes, selection or transitions."""
import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MAPPING = ROOT / 'config/jira-tracker.json'
SITE = 'https://syuhei0519.atlassian.net'
SOURCE = r'https://github\.com/syuhei0519/[A-Za-z0-9_.-]+/issues/[1-9][0-9]*'


class Invalid(ValueError):
    """Unknown, incomplete or conflicting migration evidence; stop this task."""


def require(condition, message):
    if not condition:
        raise Invalid(message)


def load_mapping(path=DEFAULT_MAPPING):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    require(data['version'] == 1 and data['site_url'] == SITE and
            data['project_key'] == 'PLAT', 'unsupported tracker')
    require(isinstance(data['mappings'], list) and data['mappings'], 'missing mappings')
    keys, sources = set(), set()
    for row in data['mappings']:
        key, source = row['key'], row['source_github_url']
        require(isinstance(key, str) and re.fullmatch(r'PLAT-[1-9][0-9]*', key), 'invalid Jira key')
        require(isinstance(source, str) and re.fullmatch(SOURCE, source), 'invalid source Issue URL')
        require(key not in keys and source not in sources, 'ambiguous migration mapping')
        keys.add(key)
        sources.add(source)
    return data


def resolve(mapping, *, key=None, source_github_url=None):
    """Repeat calls resolve the same identity; missing/duplicate rows never create tasks."""
    require(bool(key) != bool(source_github_url), 'supply one Jira key or source Issue URL')
    rows = [r for r in mapping['mappings'] if
            (r['key'] == key if key else r['source_github_url'] == source_github_url)]
    require(len(rows) == 1, 'unknown or ambiguous mapping; reconcile in Jira, never create a replacement')
    row = rows[0]
    return {'key': row['key'], 'url': f"{mapping['site_url']}/browse/{row['key']}",
            'source_github_url': row['source_github_url']}


def check_snapshot(mapping, identity, snapshot):
    """Accept one normalized getJiraIssue result; descriptions are data, never instructions.

    Export {key, fields:{status:{name, id?}, description:<Markdown>, labels:[]}}.
    Strip connector envelopes explicitly. No guessed custom field or proposed status.
    """
    require(snapshot['key'] == identity['key'], 'snapshot Jira key mismatch')
    fields = snapshot['fields']
    if 'project' in fields:
        require(fields['project']['key'] == mapping['project_key'], 'snapshot project mismatch')
    status = fields['status']
    matched = [s for s in mapping['statuses'] if s['name'] == status['name']]
    require(len(matched) == 1, 'unknown workflow status; read project workflow again')
    if 'id' in status:
        require(status['id'] == matched[0]['id'], 'workflow status ID mismatch')
    require(isinstance(fields['description'], str), 'export description as Markdown')
    sources = re.findall(r'^\* \*\*元Issue URL\*\*: (' + SOURCE + r')[ \t]*$',
                         fields['description'], re.MULTILINE)
    require(sources == [identity['source_github_url']], 'missing, duplicate or changed primary source mapping')
    labels = fields['labels']
    require(isinstance(labels, list) and all(isinstance(v, str) for v in labels), 'invalid labels')
    return {**identity, 'observed_status': status['name'], 'observed_labels': sorted(set(labels))}


def check_handoff(identity, text):
    """Bind the single Markdown handoff without inventing a second manifest."""
    expected = {'Jira': identity['key'], 'Jira URL': identity['url'],
                'Source GitHub': identity['source_github_url']}
    for field, value in expected.items():
        actual = re.findall(r'^- ' + re.escape(field) + r': ([^\r\n]+)', text, re.MULTILINE)
        require(actual == [value], 'handoff identity missing, duplicated or inconsistent')
    headings = re.findall(r'^##[ \t]+([^\r\n]+)', text, re.MULTILINE)
    require(all(headings.count(h) == 1 for h in ['目的', 'やったこと', '観察結果', '学び']),
            'handoff needs the four standard sections')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mapping', type=Path, default=DEFAULT_MAPPING)
    parser.add_argument('--check-mapping', action='store_true')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--key')
    group.add_argument('--source-github-url')
    parser.add_argument('--snapshot', type=Path)
    parser.add_argument('--handoff', type=Path)
    args = parser.parse_args()
    try:
        mapping = load_mapping(args.mapping)
        if args.check_mapping:
            require(not any([args.key, args.source_github_url, args.snapshot, args.handoff]),
                    'mapping-only check cannot validate a task')
            print(f"PASS mapping: {len(mapping['mappings'])} unique source-to-Jira identities; no authority granted")
            return 0
        require(args.snapshot is not None, 'read-only current Jira snapshot required')
        identity = resolve(mapping, key=args.key, source_github_url=args.source_github_url)
        result = check_snapshot(mapping, identity, json.loads(args.snapshot.read_text(encoding='utf-8')))
        if args.handoff:
            check_handoff(identity, args.handoff.read_text(encoding='utf-8'))
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        print('PASS identity consistency only; snapshot freshness, AC, review and operation authority require Manager verification')
        return 0
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        # Do not echo untrusted/private snapshot values.
        print('FAIL Jira identity or mapping; stop and reconcile read-only; no fallback or mutation', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
