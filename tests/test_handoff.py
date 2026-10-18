"""Contract regression tests, using exclusively synthetic fixtures."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import unittest

from scripts.validate_handoff import ROOT, VALIDATOR, validate, validate_markdown


def fixture(name='research-to-test/research.handoff.json'):
    return json.loads((ROOT / 'examples' / name).read_text(encoding='utf-8'))


class HandoffTests(unittest.TestCase):
    def test_markdown_and_json_cli_compatibility(self):
        text = (ROOT / 'templates/handoff.md').read_text()
        self.assertEqual(validate_markdown(text), [])
        self.assertTrue(validate_markdown(text.replace('## 学び', '## Other')))
        self.assertTrue(validate_markdown(text + '\n## 学び\n'))
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/validate_handoff.py'),
                                 str(ROOT / 'templates/handoff.md'),
                                 str(ROOT / 'examples/research-to-test/research.handoff.json')], capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_valid_statuses_and_retry(self):
        for name in ('research-to-test/research.handoff.json',
                     'research-to-test/test.blocked.handoff.json',
                     'research-to-test/test.handoff.json', 'failed.handoff.json'):
            with self.subTest(name=name):
                self.assertEqual(validate(fixture(name)), [])

    def test_issue_roles_use_issue_contract(self):
        for role in ('manager', 'research-design', 'implementation', 'test', 'review'):
            data = fixture()
            data['role'] = role
            with self.subTest(role=role):
                self.assertEqual(validate(data), [])

    def test_completed_requires_evidence_artifacts_and_ac_mapping(self):
        for field in ('artifacts', 'evidence', 'ac_mapping'):
            data = fixture()
            data[field] = []
            with self.subTest(field=field):
                self.assertFalse(VALIDATOR.is_valid(data))
        self.assertTrue(validate(fixture('invalid-completed.handoff.json')))

    def test_blocked_and_failed_require_explanations(self):
        for status, field, name in (
            ('blocked', 'block_reasons', 'research-to-test/test.blocked.handoff.json'),
            ('failed', 'failure_reasons', 'failed.handoff.json'),
        ):
            data = fixture(name)
            data[field] = []
            with self.subTest(status=status):
                self.assertFalse(VALIDATOR.is_valid(data))

    def test_missing_ac_requires_specific_block(self):
        for status in ('completed', 'failed'):
            data = fixture()
            data['issue']['acceptance_criteria'] = []
            data['status'] = status
            data['failure_reasons'] = ['synthetic failure']
            with self.subTest(status=status):
                self.assertFalse(VALIDATOR.is_valid(data))
        data = fixture('research-to-test/test.blocked.handoff.json')
        data['block_reasons'][0]['code'] = 'OTHER'
        self.assertFalse(VALIDATOR.is_valid(data))

    def test_partial_missing_ac_can_be_reported_without_fabrication(self):
        data = fixture('research-to-test/test.blocked.handoff.json')
        data['issue']['acceptance_criteria'] = fixture()['issue']['acceptance_criteria']
        self.assertEqual(validate(data), [])

    def test_blank_strings_and_wrong_types_rejected(self):
        mutations = (
            ('task_id', ''), ('task_id', ' \t\n'), ('attempt', '1'),
            ('attempt', True), ('attempt', 0), ('attempt', 4),
            ('status', 'success'), ('role', 'unknown'), ('artifacts', {}),
            ('summary', None), ('system_status', 'running'), ('unexpected', 'value'),
        )
        for key, value in mutations:
            data = fixture()
            data[key] = value
            with self.subTest(key=key, value=value):
                self.assertFalse(VALIDATOR.is_valid(data))
        for collection, field in (('artifacts', 'locator'), ('evidence', 'claim'),
                                  ('ac_mapping', 'scope')):
            data = fixture()
            data[collection][0][field] = '   '
            with self.subTest(collection=collection):
                self.assertFalse(VALIDATOR.is_valid(data))
        data = fixture()
        data['issue']['acceptance_criteria'][0]['verbatim'] = '\n'
        self.assertFalse(VALIDATOR.is_valid(data))

    def test_completed_cannot_claim_system_failure_or_unverified_ac(self):
        for field, value in (('system_status', 'failed'), ('block_reasons', [
            {'code': 'OTHER', 'detail': 'synthetic', 'required_action': 'synthetic'}]),
            ('failure_reasons', ['synthetic'])):
            data = fixture()
            data[field] = value
            with self.subTest(field=field):
                self.assertFalse(VALIDATOR.is_valid(data))
        data = fixture()
        data['ac_mapping'][0]['disposition'] = 'unverified'
        self.assertTrue(validate(data))

    def test_integrity_rejects_dangling_references_and_duplicate_ids(self):
        for collection, field in (('evidence', 'artifact_ids'), ('ac_mapping', 'evidence_ids'),
                                  ('knowledge_candidates', 'evidence_ids')):
            data = fixture()
            data[collection][0][field] = ['SYNTHETIC-MISSING']
            with self.subTest(collection=collection):
                self.assertTrue(VALIDATOR.is_valid(data))
                self.assertTrue(validate(data))
        for collection in ('artifacts', 'evidence', 'knowledge_candidates', 'ac_mapping'):
            data = fixture()
            data[collection].append(deepcopy(data[collection][0]))
            with self.subTest(collection=collection):
                self.assertTrue(validate(data))

    def test_completed_requires_every_assigned_ac(self):
        data = fixture()
        extra = deepcopy(data['issue']['acceptance_criteria'][0])
        extra['id'] = 'SYNTHETIC-AC-2'
        data['issue']['acceptance_criteria'].append(extra)
        data['assignment']['ac_ids'].append('SYNTHETIC-AC-2')
        self.assertTrue(VALIDATOR.is_valid(data))
        self.assertTrue(validate(data))


    def test_partial_assignment_leaves_other_ac_unverified(self):
        for role in ('research-design', 'implementation', 'test', 'review'):
            for disposition in ('not_assigned', 'unverified'):
                data = fixture('partial-assignment.handoff.json')
                data['role'] = role
                data['ac_mapping'][1]['disposition'] = disposition
                with self.subTest(role=role, disposition=disposition):
                    self.assertEqual(validate(data), [])
            data['ac_mapping'].pop()  # Outside-scope AC need not be mapped.
            self.assertEqual(validate(data), [])

    def test_cannot_cover_unassigned_or_mislabel_assigned_ac(self):
        data = fixture('partial-assignment.handoff.json')
        data['assignment']['ac_ids'] = ['SYNTHETIC-AC-2']
        self.assertTrue(validate(data))
        data = fixture()
        data['ac_mapping'][0]['disposition'] = 'not_assigned'
        self.assertTrue(validate(data))

    def test_assignment_rejects_empty_unknown_and_duplicate_ids(self):
        for ids in ([], ['SYNTHETIC-UNKNOWN'], ['SYNTHETIC-AC-1'] * 2):
            data = fixture()
            data['assignment']['ac_ids'] = ids
            with self.subTest(ids=ids):
                self.assertTrue(validate(data))

    def test_only_manager_can_make_final_issue_assessment(self):
        data = fixture()
        data['final_assessment'] = {
            'outcome': 'achieved', 'rationale': 'synthetic sample: fictional final review',
            'ac_results': [{'ac_id': 'SYNTHETIC-AC-1', 'outcome': 'met',
                            'evidence_ids': ['SYNTHETIC-EVIDENCE-1']}],
        }
        for role in ('research-design', 'implementation', 'test', 'review'):
            data['role'] = role
            with self.subTest(role=role):
                self.assertFalse(VALIDATOR.is_valid(data))
        data['role'] = 'manager'
        self.assertEqual(validate(data), [])
        data['final_assessment']['ac_results'][0]['evidence_ids'] = []
        self.assertTrue(validate(data))

    def test_manager_final_assessment_requires_all_issue_acs_and_consistency(self):
        data = fixture('partial-assignment.handoff.json')
        data['role'] = 'manager'
        data['final_assessment'] = {
            'outcome': 'unverified', 'rationale': 'synthetic sample: AC-2 unverified',
            'ac_results': [
                {'ac_id': 'SYNTHETIC-AC-1', 'outcome': 'met', 'evidence_ids': ['SYNTHETIC-EVIDENCE-1']},
                {'ac_id': 'SYNTHETIC-AC-2', 'outcome': 'unverified', 'evidence_ids': []},
            ],
        }
        self.assertEqual(validate(data), [])  # Manager task done; Issue not yet accepted.
        data['final_assessment']['outcome'] = 'achieved'
        self.assertTrue(validate(data))
        data['final_assessment']['ac_results'].pop()
        self.assertTrue(validate(data))
        data['final_assessment']['ac_results'].append(deepcopy(data['final_assessment']['ac_results'][0]))
        self.assertTrue(validate(data))

    def test_v1_and_knowledge_role_require_explicit_migration(self):
        for key, value in (('schema_version', '1.0'), ('role', 'knowledge')):
            data = fixture()
            data[key] = value
            self.assertTrue(validate(data))

    def test_retry_chain_validation(self):
        data = fixture('research-to-test/test.handoff.json')
        for key, value in (('attempt', 2), ('role', 'review'), ('task_id', data['task_id'])):
            changed = deepcopy(data)
            changed['upstream'][-1][key] = value
            with self.subTest(key=key):
                self.assertTrue(validate(changed))
        data['upstream'] = []
        self.assertFalse(VALIDATOR.is_valid(data))
        data = fixture('research-to-test/test.handoff.json')
        data['attempt'] = 1
        self.assertTrue(validate(data))

    def test_format_cannot_certify_truth(self):
        data = fixture()
        data['evidence'][0]['observation'] = 'synthetic sample: an unsupported fictional claim'
        self.assertEqual(validate(data), [])  # Manager must inspect actual evidence.

    def test_cli_exit_codes_and_working_directory_independence(self):
        script = ROOT / 'scripts/validate_handoff.py'
        for name, code in (('research-to-test/research.handoff.json', 0),
                           ('invalid-completed.handoff.json', 1), ('missing.json', 1)):
            result = subprocess.run([sys.executable, str(script), str(ROOT / 'examples' / name)],
                                    cwd=ROOT.parent, capture_output=True, text=True, check=False)
            with self.subTest(name=name):
                self.assertEqual(result.returncode, code)


if __name__ == '__main__':
    unittest.main()
