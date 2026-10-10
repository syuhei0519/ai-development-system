"""Contract regression tests, using exclusively synthetic fixtures."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import unittest

from scripts.validate_handoff import ROOT, VALIDATOR, validate


def fixture(name='research-to-test/research.handoff.json'):
    return json.loads((ROOT / 'examples' / name).read_text(encoding='utf-8'))


class HandoffTests(unittest.TestCase):
    def test_valid_statuses_and_retry(self):
        for name in ('research-to-test/research.handoff.json',
                     'research-to-test/test.blocked.handoff.json',
                     'research-to-test/test.handoff.json', 'failed.handoff.json'):
            with self.subTest(name=name):
                self.assertEqual(validate(fixture(name)), [])

    def test_all_roles_use_same_contract(self):
        for role in ('manager', 'research-design', 'implementation', 'test', 'review', 'knowledge'):
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
        self.assertFalse(VALIDATOR.is_valid(data))

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

    def test_completed_requires_every_supplied_ac(self):
        data = fixture()
        extra = deepcopy(data['issue']['acceptance_criteria'][0])
        extra['id'] = 'SYNTHETIC-AC-2'
        data['issue']['acceptance_criteria'].append(extra)
        self.assertTrue(VALIDATOR.is_valid(data))
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
