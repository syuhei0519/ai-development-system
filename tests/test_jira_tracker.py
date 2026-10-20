"""Offline migration regressions. No Jira/GitHub writes or network client."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts.jira_tracker import (ROOT, Invalid, load_mapping, resolve,
                                 check_snapshot, check_handoff)


def snapshot(identity, status='未着手'):
    return {'key': identity['key'], 'fields': {
        'project': {'key': 'PLAT'}, 'status': {'name': status},
        'description': '* **元Issue URL**: ' + identity['source_github_url'],
        'labels': ['migration-20261020']}}


def handoff(identity):
    return ('# Handoff\n\n## 目的\n'
            f"- Jira: {identity['key']}\n- Jira URL: {identity['url']}\n"
            f"- Source GitHub: {identity['source_github_url']}\n"
            '## やったこと\n未実施\n## 観察結果\n未確認\n## 学び\nReview 未実施\n')


class JiraTrackerTests(unittest.TestCase):
    def setUp(self):
        self.mapping = load_mapping()
        self.identity = resolve(self.mapping, key='PLAT-3')

    def test_complete_mapping_is_bijective_and_repeatable(self):
        self.assertEqual(len(self.mapping['mappings']), 153)
        before = deepcopy(self.mapping)
        for row in self.mapping['mappings']:
            first = resolve(self.mapping, key=row['key'])
            self.assertEqual(first, resolve(self.mapping, source_github_url=row['source_github_url']))
            self.assertEqual(first, resolve(self.mapping, key=row['key']))
        self.assertEqual(self.mapping, before)
        self.assertEqual(self.identity['source_github_url'],
                         'https://github.com/syuhei0519/backend-app/issues/36')

    def test_unknown_unmapped_epic_and_legacy_identity_fail_closed(self):
        for key in ['PLAT-99999', 'PLAT-7', 'backend-app#36', 'KAN-3', None]:
            with self.subTest(key=key), self.assertRaises(Invalid):
                resolve(self.mapping, key=key)
        with self.assertRaises(Invalid):
            resolve(self.mapping, source_github_url='https://github.com/syuhei0519/backend-app/issues/99999')
        with self.assertRaises(Invalid):
            resolve(self.mapping, key='PLAT-3', source_github_url=self.identity['source_github_url'])

    def test_duplicate_source_or_jira_key_is_rejected(self):
        for field in ['key', 'source_github_url']:
            data = deepcopy(self.mapping)
            data['mappings'][1][field] = data['mappings'][0][field]
            with tempfile.TemporaryDirectory() as temp:
                path = Path(temp) / 'mapping.json'
                path.write_text(json.dumps(data), encoding='utf-8')
                with self.subTest(field=field), self.assertRaises(Invalid):
                    load_mapping(path)

    def test_snapshot_observes_actual_status_without_mutation(self):
        for status in ['未着手', '進行中', '完了']:
            current = snapshot(self.identity, status)
            current['fields']['description'] += '\n* **状態案**: Done\n保留・停止を維持'
            before = deepcopy(current)
            result = check_snapshot(self.mapping, self.identity, current)
            self.assertEqual(result['observed_status'], status)
            self.assertEqual(current, before)
            self.assertNotIn('completed', result)
            self.assertNotIn('authorized', result)

    def test_missing_changed_or_multiple_primary_source_rejected(self):
        for desc in ['', 'https://github.com/syuhei0519/backend-app/issues/36',
                     '* **元Issue URL**: https://github.com/syuhei0519/backend-app/issues/37',
                     (snapshot(self.identity)['fields']['description'] + '\n') * 2]:
            current = snapshot(self.identity)
            current['fields']['description'] = desc
            with self.subTest(desc=desc), self.assertRaises(Invalid):
                check_snapshot(self.mapping, self.identity, current)

    def test_foreign_project_key_unknown_status_and_status_id_rejected(self):
        for section, field, value in [('project', 'key', 'KAN'), ('status', 'name', 'Review'),
                                      ('status', 'id', 'wrong')]:
            current = snapshot(self.identity)
            current['fields'][section][field] = value
            with self.subTest(field=field), self.assertRaises(Invalid):
                check_snapshot(self.mapping, self.identity, current)
        current = snapshot(self.identity)
        current['key'] = 'PLAT-4'
        with self.assertRaises(Invalid):
            check_snapshot(self.mapping, self.identity, current)

    def test_handoff_binding_and_duplicate_identity(self):
        text = handoff(self.identity)
        check_handoff(self.identity, text)
        for invalid in [text.replace('PLAT-3', 'PLAT-4'), text + '- Jira: PLAT-3\n',
                        text.replace('- Source GitHub:', '- Legacy source:'),
                        text.replace('## 学び', '## Other')]:
            with self.assertRaises(Invalid):
                check_handoff(self.identity, invalid)

    def test_cli_is_read_only_idempotent_and_missing_evidence_fails(self):
        cli = [sys.executable, str(ROOT / 'scripts/jira_tracker.py')]
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'snapshot.json'
            path.write_text(json.dumps(snapshot(self.identity)), encoding='utf-8')
            record = Path(temp) / 'handoff.md'
            record.write_text(handoff(self.identity), encoding='utf-8')
            before = {p.name: p.read_bytes() for p in Path(temp).iterdir()}
            args = cli + ['--key', 'PLAT-3', '--snapshot', str(path), '--handoff', str(record)]
            a = subprocess.run(args, capture_output=True)
            b = subprocess.run(args, capture_output=True)
            self.assertEqual(a.returncode, 0, a.stderr)
            self.assertEqual(a.stdout, b.stdout)
            self.assertEqual(before, {p.name: p.read_bytes() for p in Path(temp).iterdir()})
            path.write_text('{}', encoding='utf-8')
            self.assertEqual(subprocess.run(args, capture_output=True).returncode, 1)
        self.assertEqual(subprocess.run(cli + ['--key', 'PLAT-3'], capture_output=True).returncode, 1)
        self.assertEqual(subprocess.run(cli + ['--check-mapping'], capture_output=True).returncode, 0)


if __name__ == '__main__':
    unittest.main()
