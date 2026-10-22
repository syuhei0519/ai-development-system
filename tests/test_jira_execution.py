"""Synthetic offline fixtures; no real authorization or Jira writes."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts.jira_execution import CLOUD, SITE, Invalid, check_execution, digest
from scripts.jira_tracker import ROOT, load_mapping


def fixture(kind='jira-native'):
    key, issue_id = ('PLAT-9001', '99001') if kind == 'jira-native' else ('PLAT-3', '10013')
    source = 'none' if kind == 'jira-native' else 'https://github.com/syuhei0519/backend-app/issues/36'
    ac = '* identity を検証する。\n* 未承認操作を拒否する。'
    description = '## 受入条件\n\n' + ac
    if kind == 'migrated':
        description = '* **元Issue URL**: ' + source + '\n' + description
    identity = dict(site_url=SITE, cloud_id=CLOUD, project_key='PLAT', id=issue_id,
                    key=key, url=SITE + '/browse/' + key)
    base, repo = 'a' * 40, 'syuhei0519/ai-development-system'
    issue = {**identity, 'fields': {'project': {'key': 'PLAT', 'id': '10001'},
        'status': {'name': '進行中', 'id': '10006'}, 'description': description,
        'labels': ['jira-native'] if kind == 'jira-native' else [], 'updated': '2026-10-22T12:00:00Z'}}
    manager = {'reviewed_description_sha256': digest(description), 'reviewed_updated': '2026-10-22T12:00:00Z',
        'unresolved_stop_reasons': [], 'historical_stop_references': [], 'repositories': {repo: base},
        'authorization': {'origin': 'human-conversation', 'verified': True, 'reference': 'fixture-only',
            'identity': identity, 'source': kind, 'repo': repo, 'base_commit': base,
            'ac_sha256': digest(ac), 'state': 'approved',
            'operations': ['repo-change', 'fixture-test', 'draft-pr'], 'resumes': []}}
    handoff = f'''# Handoff
## 目的
- Source: {kind}
- Jira Site: {SITE}
- Jira Cloud ID: {CLOUD}
- Jira Project: PLAT
- Jira ID: {issue_id}
- Jira: {key}
- Jira URL: {identity['url']}
- Source GitHub: {source}
- Target Repo: {repo}
- Base Commit: {base}
- Authorization: fixture-only
### AC
{ac}
## やったこと
fixture only
## 観察結果
- AC Evidence: pending; fixture only, no completion claim
- Unapproved Operations: merge, deploy, credentials, permissions
- Stop Reason: none
## 学び
Independent review pending.
'''
    return {'issue': issue, 'manager': manager}, handoff


class ExecutionTests(unittest.TestCase):
    def setUp(self):
        self.mapping = load_mapping()

    def test_both_sources_and_all_narrow_operations_are_repeatable_read_only(self):
        for kind in ['jira-native', 'migrated']:
            current, handoff = fixture(kind)
            before = deepcopy(current)
            for op in ['repo-change', 'fixture-test', 'draft-pr']:
                a = check_execution(self.mapping, current, handoff, op)
                self.assertEqual(a, check_execution(self.mapping, current, handoff, op))
                self.assertEqual(a['source'], kind)
                self.assertNotIn('authorized', a)
            self.assertEqual(current, before)

    def test_identity_mismatches_are_rejected(self):
        for name in ['site_url', 'cloud_id', 'project_key', 'id', 'key', 'url']:
            current, handoff = fixture()
            current['issue'][name] = 'foreign'
            with self.subTest(name=name), self.assertRaises(Invalid):
                check_execution(self.mapping, current, handoff, 'repo-change')
        for old, new in [('PLAT-9001', 'KAN-9001'), (SITE, SITE + '.evil.example'),
                         ('Jira ID: 99001', 'Jira ID: 0'), ('Jira Project: PLAT', 'Jira Project: KAN')]:
            current, handoff = fixture()
            with self.subTest(old=old), self.assertRaises(Invalid):
                check_execution(self.mapping, current, handoff.replace(old, new), 'repo-change')

    def test_missing_duplicate_unknown_and_changed_handoff_fields(self):
        current, handoff = fixture()
        for bad in [handoff.replace('Source: jira-native', 'Source: guessed'),
                    handoff.replace('Source GitHub: none', 'Source GitHub: https://github.com/syuhei0519/backend-app/issues/9001'),
                    handoff + '- Jira: PLAT-9001\n', handoff.replace('### AC', '### Missing'),
                    handoff.replace('* identity を検証する。', '* different AC'),
                    handoff.replace('Base Commit: ' + 'a' * 40, 'Base Commit: main'),
                    handoff.replace('Stop Reason: none', 'Stop Reason: paused'),
                    handoff.replace('- Unapproved Operations:', '- Other:')]:
            with self.subTest(bad=bad), self.assertRaises(Invalid):
                check_execution(self.mapping, current, bad, 'repo-change')

    def test_current_body_labels_status_and_scope_fail_closed(self):
        mutations = [
            lambda c: c['issue']['fields'].update(labels=['jira-native', 'execution-paused']),
            lambda c: c['issue']['fields'].update(description=''),
            lambda c: c['issue']['fields'].update(description=c['issue']['fields']['description'] + '\nSTOP'),
            lambda c: c['issue']['fields'].update(updated='2026-10-22T13:00:00Z'),
            lambda c: c['issue']['fields'].update(status={'id': '10007', 'name': '完了'}),
            lambda c: c['issue']['fields'].update(status={'id': '99', 'name': 'Review'}),
            lambda c: c['issue']['fields']['project'].update(id='999'),
            lambda c: c['manager'].update(unresolved_stop_reasons=['prose stop']),
            lambda c: c['manager'].update(repositories={}),
            lambda c: c['manager'].update(historical_stop_references=['old-pause']),
        ]
        for i, mutate in enumerate(mutations):
            current, handoff = fixture()
            mutate(current)
            with self.subTest(i=i), self.assertRaises((Invalid, KeyError)):
                check_execution(self.mapping, current, handoff, 'repo-change')

    def test_authority_is_narrow_and_required(self):
        for name, value in [('origin', 'jira-description'), ('verified', False), ('verified', 'true'),
                            ('reference', ''), ('identity', {}), ('source', 'migrated'),
                            ('repo', 'syuhei0519/backend-app'), ('base_commit', 'b' * 40),
                            ('ac_sha256', '0' * 64), ('state', 'pending'), ('operations', []),
                            ('operations', {'repo-change': False}), ('operations', 'repo-change'),
                            ('operations', ['repo-change', 'merge']), ('resumes', ['unapproved-pause'])]:
            current, handoff = fixture()
            current['manager']['authorization'][name] = value
            with self.subTest(name=name, value=value), self.assertRaises(Invalid):
                check_execution(self.mapping, current, handoff, 'repo-change')
        current, handoff = fixture()
        for op in ['merge', 'deploy', 'create-credential', 'grant-permission', 'Done', '']:
            with self.subTest(op=op), self.assertRaises(Invalid):
                check_execution(self.mapping, current, handoff, op)

    def test_contradiction_missing_time_and_partial_ac_rejected(self):
        current, handoff = fixture()
        with self.assertRaises(Invalid):
            check_execution(self.mapping, current, handoff.replace('merge, deploy', 'repo-change, merge, deploy'), 'repo-change')
        partial = handoff.replace('* 未承認操作を拒否する。\n', '')
        current['manager']['authorization']['ac_sha256'] = digest('* identity を検証する。')
        with self.assertRaises(Invalid):
            check_execution(self.mapping, current, partial, 'repo-change')
        current, handoff = fixture()
        current['issue']['fields']['description'] = current['issue']['fields']['description'].replace('## 受入条件', '## 対象外')
        current['manager']['reviewed_description_sha256'] = digest(current['issue']['fields']['description'])
        with self.assertRaises(Invalid):
            check_execution(self.mapping, current, handoff, 'repo-change')
        for value in [None, '', 'bad', '2026-10-22T12:00:00']:
            current, handoff = fixture()
            current['issue']['fields']['updated'] = value
            current['manager']['reviewed_updated'] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                check_execution(self.mapping, current, handoff, 'repo-change')

    def test_migration_source_is_not_weakened_or_inferred(self):
        current, handoff = fixture('migrated')
        for desc in ['', current['issue']['fields']['description'].replace('/36', '/37'),
                     current['issue']['fields']['description'] * 2]:
            bad = deepcopy(current)
            bad['issue']['fields']['description'] = desc
            with self.assertRaises(Invalid):
                check_execution(self.mapping, bad, handoff, 'repo-change')
        for kind in ['jira-native', 'migrated']:
            current, handoff = fixture(kind)
            current['issue']['fields']['labels'] = [] if kind == 'jira-native' else ['jira-native']
            with self.assertRaises(Invalid):
                check_execution(self.mapping, current, handoff, 'repo-change')

    def test_explicit_historical_resume_does_not_override_active_stop(self):
        current, handoff = fixture()
        current['manager']['historical_stop_references'] = ['historical-plan-only']
        current['manager']['authorization']['resumes'] = ['historical-plan-only']
        check_execution(self.mapping, current, handoff, 'repo-change')
        current['issue']['fields']['labels'].append('execution-paused')
        with self.assertRaises(Invalid):
            check_execution(self.mapping, current, handoff, 'repo-change')

    def test_cli_malformed_missing_and_success_with_no_writes(self):
        cli = [sys.executable, str(ROOT / 'scripts/jira_execution.py')]
        current, handoff = fixture()
        with tempfile.TemporaryDirectory() as tmp:
            path, record = Path(tmp) / 'current.json', Path(tmp) / 'handoff.md'
            path.write_text(json.dumps(current), encoding='utf-8')
            record.write_text(handoff, encoding='utf-8')
            args = cli + ['--snapshot', str(path), '--handoff', str(record), '--operation', 'repo-change']
            before = {p.name: p.read_bytes() for p in Path(tmp).iterdir()}
            a = subprocess.run(args, capture_output=True)
            self.assertEqual(a.returncode, 0, a.stderr)
            self.assertEqual(before, {p.name: p.read_bytes() for p in Path(tmp).iterdir()})
            for payload in ['{}', 'null', '[]', 'not json', '{"issue": null}']:
                path.write_text(payload, encoding='utf-8')
                p = subprocess.run(args, capture_output=True)
                self.assertEqual(p.returncode, 1, p.stderr)
                self.assertNotIn(b'Traceback', p.stderr)
