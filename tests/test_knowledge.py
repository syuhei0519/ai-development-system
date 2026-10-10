"""Synthetic regressions for AC-independent Knowledge contracts."""
from copy import deepcopy
import json
import subprocess
import sys
import unittest

from scripts.validate_knowledge import ROOT, validate


def fixture(name='input.json'):
    return json.loads((ROOT / 'examples/knowledge' / name).read_text())


class KnowledgeTests(unittest.TestCase):
    def test_cross_issue_input_and_output_need_no_issue_ac(self):
        for name in ('input.json', 'handoff.json', 'context.json'):
            data = fixture(name)
            self.assertNotIn('issue', data)
            self.assertEqual(validate(data), [])
        data = fixture()
        for raw in data['raw_findings']:
            raw['issue_refs'] = []  # Technical evidence may have no Issue at all.
        self.assertEqual(validate(data), [])

    def test_raw_evidence_requires_sources_and_fixed_revision(self):
        for key, value in (('sources', []), ('observation', '  ')):
            for name in ('input.json', 'handoff.json'):
                data = fixture(name)
                data['raw_findings'][0][key] = value
                with self.subTest(name=name, key=key):
                    self.assertTrue(validate(data))
        data = fixture()
        data['raw_findings'][0]['sources'][0]['revision'] = ''
        self.assertTrue(validate(data))
        data = fixture()
        data['raw_findings'] = []
        self.assertTrue(validate(data))

    def test_completed_requires_evidence_and_complete_decisions(self):
        for key in ('evidence', 'decisions', 'artifacts', 'raw_findings'):
            data = fixture('handoff.json')
            data[key] = []
            with self.subTest(key=key):
                self.assertTrue(validate(data))
        data = fixture('handoff.json')
        data['decisions'][0]['raw_finding_ids'].pop()
        self.assertTrue(validate(data))

    def test_adoption_requires_article_but_defer_or_reject_can_complete(self):
        data = fixture('handoff.json')
        data['decisions'][0]['article_artifact_ids'] = []
        self.assertTrue(validate(data))
        for outcome in ('deferred', 'rejected'):
            data['decisions'][0]['outcome'] = outcome
            self.assertEqual(validate(data), [])

    def test_decisions_need_matching_raw_evidence(self):
        data = fixture('handoff.json')
        data['evidence'][0]['raw_finding_ids'] = ['SYNTHETIC-RAW-1']
        self.assertTrue(validate(data))
        for collection, key in (('evidence', 'artifact_ids'), ('decisions', 'evidence_ids'),
                                ('decisions', 'raw_finding_ids'), ('decisions', 'article_artifact_ids')):
            data = fixture('handoff.json')
            data[collection][0][key] = ['SYNTHETIC-MISSING']
            with self.subTest(collection=collection, key=key):
                self.assertTrue(validate(data))

    def test_duplicate_ids_and_conflicting_decisions_rejected(self):
        for collection in ('raw_findings', 'evidence', 'artifacts', 'decisions'):
            data = fixture('handoff.json')
            data[collection].append(deepcopy(data[collection][0]))
            with self.subTest(collection=collection):
                self.assertTrue(validate(data))

    def test_consumer_context_requires_revision_applicability_sources(self):
        for key in ('revision', 'applicability', 'sources', 'lifecycle', 'review_trigger'):
            data = fixture('context.json')
            del data['knowledge_references'][0][key]
            with self.subTest(key=key):
                self.assertTrue(validate(data))
        data = fixture('context.json')
        data['knowledge_references'][0]['sources'] = []
        self.assertTrue(validate(data))

    def test_blocked_missing_evidence_does_not_use_missing_ac_code(self):
        data = fixture('handoff.json')
        data.update(status='blocked', raw_findings=[], artifacts=[], evidence=[], decisions=[])
        data['block_reasons'] = [{'code': 'MISSING_INPUT', 'detail': 'synthetic sample: raw evidence missing',
                                  'required_action': 'Provide authorized raw findings with sources.'}]
        self.assertEqual(validate(data), [])
        data['block_reasons'][0]['code'] = 'MISSING_ACCEPTANCE_CRITERIA'
        self.assertTrue(validate(data))

    def test_failed_requires_reason(self):
        data = fixture('handoff.json')
        data['status'] = 'failed'
        self.assertTrue(validate(data))
        data['failure_reasons'] = ['synthetic sample: curation check failed']
        self.assertEqual(validate(data), [])

    def test_retry_chain_and_limit(self):
        data = fixture()
        data['attempt'] = 2
        self.assertTrue(validate(data))
        data['retry_of'] = [{'task_id': 'SYNTHETIC-PREVIOUS', 'attempt': 1,
                             'handoff_locator': 'https://example.invalid/previous', 'revision': 'SYNTHETIC-REV-1'}]
        self.assertEqual(validate(data), [])
        data['retry_of'][0]['task_id'] = data['task_id']
        self.assertTrue(validate(data))
        data['attempt'] = 4
        self.assertTrue(validate(data))

    def test_schema_cannot_verify_source_truth(self):
        data = fixture()
        data['raw_findings'][0]['observation'] = 'synthetic sample: unsupported claim requiring human/agent review'
        self.assertEqual(validate(data), [])

    def test_knowledge_cannot_claim_final_issue_assessment(self):
        data = fixture('handoff.json')
        data['final_assessment'] = {'outcome': 'achieved'}
        self.assertTrue(validate(data))

    def test_cli_reports_input_handoff_context_and_bad_input(self):
        script = ROOT / 'scripts/validate_knowledge.py'
        for name, expected in (('input.json', 0), ('handoff.json', 0), ('context.json', 0), ('missing.json', 1)):
            run = subprocess.run([sys.executable, str(script), str(ROOT / 'examples/knowledge' / name)],
                                 cwd=ROOT.parent, capture_output=True, text=True, check=False)
            self.assertEqual(run.returncode, expected)
        self.assertTrue(validate([]))


if __name__ == '__main__':
    unittest.main()
