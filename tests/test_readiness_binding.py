"""Regressions for Issue integration and real artifact delivery."""
from copy import deepcopy
from contextlib import redirect_stderr
import io
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts.validate_readiness import validate, validate_handoff_pair, main, VALIDATOR
from test_readiness import fixture, NOW, ROOT


class IntegrationTests(unittest.TestCase):
    def test_all_premerge_met_without_merge_remains_unverified(self):
        data = fixture('postdeploy-achieved.json')
        context = fixture('context.json')
        for ac in data['acceptance_criteria']:
            ac['verification_phase'] = 'premerge'
        context['acceptance_criteria'] = deepcopy(data['acceptance_criteria'])
        data['lifecycle'] = {'merged_at': None, 'deployed_at': None}
        data['issue_integration'].update(verdict='pending', evidence_ids=[])
        data['issue_completion'] = 'unverified'
        self.assertEqual(validate(data, context, NOW), [])
        self.assertEqual(data['merge_readiness']['status'], 'ready')
        data['issue_completion'] = 'achieved'
        self.assertTrue(validate(data, context, NOW))

    def test_merged_pr_cannot_complete_aggregate_or_unknown_issue(self):
        for scope in ('aggregate_required', 'unknown'):
            data = fixture('postdeploy-achieved.json')
            context = fixture('context.json')
            data['issue_integration_scope'] = context['issue_integration_scope'] = scope
            self.assertTrue(validate(data, context, NOW))
            data['issue_integration'].update(verdict='pending', evidence_ids=[])
            data['issue_completion'] = 'unverified'
            self.assertEqual(validate(data, context, NOW), [])

    def test_integration_scope_cannot_be_downgraded(self):
        data = fixture('postdeploy-achieved.json')
        context = fixture('context.json')
        context['issue_integration_scope'] = 'aggregate_required'
        self.assertTrue(validate(data, context, NOW))

    def test_integration_evidence_required_current_and_complete(self):
        for mutation in (
            lambda d: d['issue_integration'].update(evidence_ids=[]),
            lambda d: d['issue_integration'].update(evidence_ids=['post-measurement']),
            lambda d: d['evidence'][-1].update(ac_ids=['SYNTHETIC-AC-1']),
            lambda d: d['evidence'][-1].update(observed_at='2030-01-01T08:30:00Z'),
            lambda d: d['issue_integration'].update(verdict='not_applicable'),
            lambda d: d.pop('issue_integration_scope'),
        ):
            data = fixture('postdeploy-achieved.json')
            mutation(data)
            self.assertTrue(validate(data, fixture('context.json'), NOW))

    def test_integration_fail_is_not_achieved(self):
        data = fixture('postdeploy-achieved.json')
        data['issue_integration']['verdict'] = 'fail'
        data['issue_completion'] = 'not_achieved'
        self.assertEqual(validate(data, fixture('context.json'), NOW), [])
        data['issue_completion'] = 'unverified'
        self.assertTrue(validate(data, fixture('context.json'), NOW))

    def test_merged_without_integration_evidence_still_unverified(self):
        data = fixture('postdeploy-achieved.json')
        data['issue_integration'].update(verdict='pending', evidence_ids=[])
        data['issue_completion'] = 'unverified'
        self.assertEqual(validate(data, fixture('context.json'), NOW), [])


class ArtifactBindingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / 'assessment.json'
        self.hpath = self.root / 'handoff.json'
        self.data = fixture()
        self.handoff = fixture('manager.handoff.json')
        self.artifact = next(a for a in self.handoff['artifacts'] if a['id'] == self.data['artifact_id'])
        self.path.write_text(json.dumps(self.data))
        self.initial_bytes = self.path.read_bytes()
        self.artifact.update(locator=self.path.name,
                             revision='sha256:' + hashlib.sha256(self.path.read_bytes()).hexdigest())

    def errors(self):
        return validate_handoff_pair(self.data, self.handoff,
                                     readiness_bytes=self.initial_bytes, readiness_path=self.path, handoff_path=self.hpath)

    def test_real_readable_artifact_matches(self):
        self.assertEqual(self.errors(), [])
        self.assertTrue(validate_handoff_pair(self.data, self.handoff))

    def test_missing_wrong_id_or_wrong_kind_rejected(self):
        for field, value in [('id', 'OTHER'), ('kind', 'document'), ('revision', 'main'),
                             ('revision', 'sha256:' + '0' * 64)]:
            original = self.artifact[field]
            self.artifact[field] = value
            self.assertTrue(self.errors())
            self.artifact[field] = original
        self.handoff['artifacts'].remove(self.artifact)
        self.assertTrue(self.errors())

    def test_other_file_even_identical_bytes_is_not_evaluated_artifact(self):
        other = self.root / 'other.json'
        other.write_bytes(self.path.read_bytes())
        self.artifact['locator'] = other.name
        self.assertTrue(self.errors())

    def test_missing_directory_remote_and_unreadable_locator_rejected(self):
        for locator in ('missing.json', '.', 'https://example.invalid/artifact'):
            self.artifact['locator'] = locator
            self.assertTrue(self.errors())
        self.artifact['locator'] = self.path.name
        with patch.object(Path, 'read_bytes', side_effect=PermissionError('unreadable')):
            self.assertTrue(self.errors())

    def test_changed_bytes_and_document_rejected(self):
        self.path.write_bytes(self.path.read_bytes() + b'\n')
        self.assertTrue(self.errors())  # semantic equality does not bypass byte digest
        self.artifact['revision'] = 'sha256:' + hashlib.sha256(self.path.read_bytes()).hexdigest()
        self.assertTrue(self.errors())  # Updating the digest cannot replace initial bytes.
        self.initial_bytes = self.path.read_bytes()
        self.assertEqual(self.errors(), [])
        self.data['artifact_id'] = 'OTHER'
        self.assertTrue(self.errors())
        self.data['artifact_id'] = 'SYNTHETIC-READINESS'
        self.data['issue_id'] = 'DIFFERENT'
        self.assertTrue(self.errors())  # evaluated data must match the file

    def test_cli_materialized_bundle_from_other_cwd(self):
        context = self.root / 'context.json'
        context.write_text(json.dumps(fixture('context.json')))
        command = [sys.executable, str(ROOT / 'scripts/validate_readiness.py'), str(self.path),
                   '--context', str(context), '--context-sha256', hashlib.sha256(context.read_bytes()).hexdigest(), '--handoff', str(self.hpath), '--at', NOW.isoformat()]
        for tampered, expected in [(False, 0), (True, 1)]:
            if tampered:
                self.artifact['revision'] = 'sha256:' + '0' * 64
            self.hpath.write_text(json.dumps(self.handoff))
            run = subprocess.run(command, cwd='/', text=True, capture_output=True)
            self.assertEqual(run.returncode, expected, run.stderr)


class InitialBytesRaceTests(unittest.TestCase):
    setUp = ArtifactBindingTests.setUp
    def race(self, boolean_replacement):
        self.data['subject']['pr_number'] = 1
        for evidence in self.data['evidence']:
            evidence['subject']['pr_number'] = 1
        initial = json.dumps(self.data).encode()
        replacement = initial.replace(b'"pr_number": 1', b'"pr_number": true') if boolean_replacement else initial + b' \n'
        if boolean_replacement:
            self.assertFalse(VALIDATOR.is_valid(json.loads(replacement)))
            self.assertEqual(json.loads(initial), json.loads(replacement))  # original bypass
        context = fixture('context.json')
        context['subject']['pr_number'] = 1
        cpath = self.root / 'context.json'
        cpath.write_text(json.dumps(context))
        self.path.write_bytes(initial)
        self.artifact['revision'] = 'sha256:' + hashlib.sha256(replacement).hexdigest()
        self.hpath.write_text(json.dumps(self.handoff))
        original_read = Path.read_bytes
        reads = []

        def swap_after_read(path):
            payload = original_read(path)
            if path == self.path:
                reads.append(payload)
                if len(reads) == 1:
                    path.write_bytes(replacement)
            return payload

        args = ['validate_readiness.py', str(self.path), '--context', str(cpath),
                '--handoff', str(self.hpath), '--context-sha256', hashlib.sha256(cpath.read_bytes()).hexdigest(), '--at', NOW.isoformat()]
        errors = io.StringIO()
        with patch.object(Path, 'read_bytes', swap_after_read), patch.object(sys, 'argv', args), redirect_stderr(errors):
            self.assertEqual(main(), 1)
        self.assertIn('readiness bytes changed after initial read', errors.getvalue())
        self.assertEqual(reads, [initial, replacement])

    def test_integer_to_boolean_replacement_after_initial_read(self):
        self.race(True)

    def test_whitespace_replacement_after_initial_read(self):
        self.race(False)
