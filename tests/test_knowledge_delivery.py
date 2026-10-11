"""Synthetic typed-delivery adversarial tests; no Agent or deployment claims."""
from copy import deepcopy
from datetime import datetime, timezone
import json
import unittest

from jsonschema import Draft202012Validator
from scripts.consume_delivery import ROOT, consume, digest, parse, schema
from scripts.prepare_knowledge_fixture import fixture_manifest
from test_delivery import Source, encode


class KnowledgeDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.manifest = fixture_manifest('example/repo', 'a' * 40)
        self.files = {a['reference']['path']: (ROOT / a['reference']['path']).read_bytes()
                      for a in self.manifest['artifacts']}
        self.policy = parse((ROOT / 'examples/delivery/synthetic.authorization.json').read_bytes())
        self.policy.update(schema_version='1.1', allowed_representations=['original'])
        self.reseal()

    def item(self, name):
        return next(a for a in self.manifest['artifacts'] if a['reference']['path'].endswith('/' + name))

    def data(self, name):
        return parse(self.files[self.item(name)['reference']['path']])

    def replace(self, name, data):
        self.files[self.item(name)['reference']['path']] = encode(data)
        self.reseal()

    def reseal(self):
        # Recompute the outer pins so negative cases test semantics, not stale hashes.
        for a in self.manifest['artifacts']:
            ref = a['reference']; raw = self.files[ref['path']]
            ref.update(size=len(raw), sha256=digest(raw))
        self.mraw = encode(self.manifest)
        self.publication = {'schema_version': self.manifest['schema_version'],
                            'document_type': 'publication_receipt', 'manifest_sha256': digest(self.mraw),
                            'github_state': 'published', 'artifacts': deepcopy(self.manifest['artifacts']),
                            'observation': 'synthetic test-only observation'}
        self.pubraw = encode(self.publication)
        self.policy.update(manifest_sha256=digest(self.mraw), publication_receipt_sha256=digest(self.pubraw))

    def run_consumer(self, **kwargs):
        args = dict(manifest_raw=self.mraw, policy_raw=encode(self.policy), publication_raw=self.pubraw,
                    policy_sha256=digest(encode(self.policy)), consumer=self.policy['consumer'],
                    scope=self.policy['scope'], purpose=self.policy['purpose'], source=Source(self.files),
                    now=datetime(2026, 10, 11, tzinfo=timezone.utc))
        args.update(kwargs)
        return consume(**args)

    def test_complete_bundle_raw_bytes_and_receipt(self):
        receipt, blobs = self.run_consumer()
        self.assertEqual(receipt['schema_version'], '1.1')
        self.assertFalse(receipt['authority_granted'])
        self.assertIn('knowledge-bindings', receipt['verification'])
        self.assertEqual({key[2]: raw for key, raw in blobs.items()}, self.files)
        self.assertEqual(self.run_consumer(receipt_raw=encode(receipt))[0], receipt)

    def test_input_only_and_context_only_are_deliverable(self):
        self.manifest['artifacts'].remove(self.item('handoff.json'))
        del self.manifest['knowledge_bindings'][0]['handoff']
        self.reseal(); self.run_consumer()
        self.manifest['artifacts'].remove(self.item('input.json'))
        self.manifest['knowledge_bindings'] = []
        self.reseal(); self.run_consumer()

    def test_blocked_and_failed_remain_partial_not_completed(self):
        for status in ('blocked', 'failed'):
            with self.subTest(status=status):
                self.setUp(); handoff = self.data('handoff.json')
                handoff.update(status=status, artifacts=[], evidence=[], decisions=[])
                if status == 'blocked':
                    handoff['block_reasons'] = [{'code': 'MISSING_INPUT', 'detail': 'synthetic pending analysis',
                                                  'required_action': 'Obtain supporting observations.'}]
                else:
                    handoff['failure_reasons'] = ['synthetic execution failure']
                self.replace('handoff.json', handoff); self.run_consumer()

    def test_knowledge_cannot_downgrade_even_when_identity_field_missing(self):
        for name in ('input.json', 'handoff.json', 'context.json'):
            self.setUp(); original = self.data(name)
            for missing in (None, *original):
                for kind in ('json', 'text', 'handoff-v2'):
                    with self.subTest(name=name, missing=missing, kind=kind):
                        self.setUp(); changed = deepcopy(original)
                        if missing: del changed[missing]
                        self.item(name)['format'] = kind
                        self.replace(name, changed)
                        with self.assertRaises(ValueError): self.run_consumer()

    def test_wrong_unknown_missing_or_multiple_identity(self):
        for name in ('input.json', 'handoff.json', 'context.json'):
            self.setUp(); original = self.data(name)
            variants = [dict(original, document_type=value) for value in
                        ('knowledge_unknown', 'knowledge_context', [], {}, None, 7)]
            variants += [dict(original, schema_version='2.0'), dict(original, role='implementation'),
                         dict(original, ac_mapping=[]), dict(original, publication='private_only')]
            for field in original:
                variant = deepcopy(original); del variant[field]; variants.append(variant)
            for variant in variants:
                if variant == original: continue
                with self.subTest(name=name, changed=list(variant)):
                    self.setUp(); self.replace(name, variant)
                    with self.assertRaises(ValueError): self.run_consumer()

    def test_strict_json_all_knowledge_formats(self):
        for name in ('input.json', 'handoff.json', 'context.json'):
            self.setUp(); raw = self.files[self.item(name)['reference']['path']]
            malformed = [raw[:-2], raw + b' trailing', b'\xef\xbb\xbf' + raw, b' \n\xef\xbb\xbf' + raw,
                         b'{"nested":{"x":1,"\\u0078":2}}', b'{"x":NaN}', b'{"x":Infinity}',
                         b'{"document_type":"knowledge_input","document_type":"knowledge_handoff"}', b'\xff']
            for payload in malformed:
                with self.subTest(name=name, payload=payload[:20]):
                    self.setUp(); self.files[self.item(name)['reference']['path']] = payload
                    self.reseal()
                    with self.assertRaises(ValueError): self.run_consumer()

    def test_input_output_all_immutable_fields_must_match(self):
        changes = {'assignment': {'scope': 'synthetic changed', 'completion_criteria': ['changed']},
                   'raw_findings': [], 'knowledge_references': [], 'task_id': 'SYNTHETIC-OTHER',
                   'attempt': 2, 'retry_of': [{'task_id': 'SYNTHETIC-PRIOR', 'attempt': 1,
                                             'handoff_locator': 'prior.json', 'revision': 'sha256:' + '0' * 64}]}
        for field, value in changes.items():
            with self.subTest(field=field):
                self.setUp(); data = self.data('handoff.json'); data[field] = value
                self.replace('handoff.json', data)
                with self.assertRaises(ValueError): self.run_consumer()
        # Same IDs/count, changed observations or source must also fail.
        for field in ('observation', 'domain', 'sources'):
            self.setUp(); data = self.data('handoff.json')
            data['raw_findings'][0][field] = 'changed' if field != 'sources' else [
                {'locator': 'source-2.md', 'revision': self.data('context.json')['knowledge_references'][0]['sources'][1]['revision']}]
            self.replace('handoff.json', data)
            with self.subTest(field=field), self.assertRaises(ValueError): self.run_consumer()

    def test_all_findings_decided_once_with_support_and_adopted_article(self):
        variants = []
        base = self.data('handoff.json')
        for field, value in [('decisions', []), ('evidence', []), ('artifacts', [])]:
            data = deepcopy(base); data[field] = value; variants.append(data)
        data = deepcopy(base); data['decisions'][0]['raw_finding_ids'].pop(); variants.append(data)
        data = deepcopy(base); data['decisions'].append(deepcopy(data['decisions'][0])); variants.append(data)
        data = deepcopy(base); data['evidence'][0]['raw_finding_ids'].pop(); variants.append(data)
        data = deepcopy(base); data['artifacts'][0]['kind'] = 'document'; variants.append(data)
        data = deepcopy(base); data['decisions'][0]['article_artifact_ids'] = []; variants.append(data)
        for data in variants:
            self.setUp(); self.replace('handoff.json', data)
            with self.assertRaises(ValueError): self.run_consumer()

    def test_deferred_rejected_are_supported_without_adopted_article(self):
        for outcome in ('deferred', 'rejected'):
            self.setUp(); data = self.data('handoff.json')
            data['decisions'][0].update(outcome=outcome, article_artifact_ids=[])
            data['artifacts'][0]['kind'] = 'document'
            self.replace('handoff.json', data); self.run_consumer()

    def test_missing_source_article_context_or_input_cannot_be_certified(self):
        # A context is optional, but every context that is declared must be fetched.
        for name in ('source-1.md', 'source-2.md', 'article.md', 'input.json'):
            self.setUp(); self.manifest['artifacts'].remove(self.item(name)); self.reseal()
            with self.subTest(name=name), self.assertRaises(ValueError): self.run_consumer()
        self.setUp(); self.files[self.item('context.json')['reference']['path']] = b'{}'
        with self.assertRaises(ValueError): self.run_consumer()

    def test_fixed_locator_digest_and_no_url_fallback(self):
        for locator in ('https://example.invalid/source', '../source-1.md', '/source-1.md', 'a//b', 'a/.git/x', 'missing.md'):
            for name in ('input.json', 'context.json', 'handoff.json'):
                self.setUp(); data = self.data(name)
                data['knowledge_references'][0]['sources'][0]['locator'] = locator
                self.replace(name, data)
                with self.subTest(name=name, locator=locator), self.assertRaises(ValueError): self.run_consumer()
        for revision in ('main', 'a' * 40, 'sha256:' + '0' * 64):
            self.setUp(); data = self.data('context.json')
            data['knowledge_references'][0]['revision'] = revision
            self.replace('context.json', data)
            with self.assertRaises(ValueError): self.run_consumer()
        self.setUp(); self.files[self.item('source-1.md')['reference']['path']] += b'changed\n'
        self.reseal()  # Valid outer digests, invalid in-document source digest.
        with self.assertRaisesRegex(ValueError, 'binding digest mismatch'): self.run_consumer()

    def test_unbound_duplicate_or_wrong_binding_reference(self):
        for change in ('empty', 'duplicate', 'wrong-size', 'wrong-type', 'missing'):
            self.setUp()
            if change == 'empty': self.manifest['knowledge_bindings'] = []
            if change == 'duplicate': self.manifest['knowledge_bindings'] *= 2
            if change == 'wrong-size':
                self.manifest['knowledge_bindings'][0]['input'] = dict(self.item('input.json')['reference'], size=1)
            if change == 'wrong-type': self.manifest['knowledge_bindings'][0]['input'] = self.item('context.json')['reference']
            if change == 'missing': del self.manifest['knowledge_bindings']
            self.reseal()
            with self.subTest(change=change), self.assertRaises(ValueError): self.run_consumer()

    def test_duplicate_document_identity_rejected(self):
        original = self.item('input.json'); clone = deepcopy(original)
        clone['reference']['path'] = 'examples/knowledge-delivery/duplicate.json'
        self.files[clone['reference']['path']] = self.files[original['reference']['path']]
        self.manifest['artifacts'].append(clone)
        self.manifest['knowledge_bindings'].append({'input': clone['reference']})
        self.reseal()
        with self.assertRaisesRegex(ValueError, 'duplicate Knowledge task identity'): self.run_consumer()

    def test_version_matrix_old_schema_rejects_new_types(self):
        for name, data in [('artifact-delivery', self.manifest), ('publication-receipt', self.publication),
                           ('delivery-authorization', self.policy), ('consumption-receipt', self.run_consumer()[0])]:
            old = json.loads((ROOT / f'contracts/{name}.schema.json').read_text())
            self.assertFalse(Draft202012Validator(old).is_valid(data))
            if 'artifacts' in data:
                changed = deepcopy(data); changed['schema_version'] = '1.0'
                with self.assertRaises(ValueError): schema(name, changed)
        for version in ('1.0', '1.2', None, [], True):
            self.setUp(); self.policy['schema_version'] = version
            with self.subTest(version=version), self.assertRaises(ValueError): self.run_consumer()
        self.setUp(); publication = deepcopy(self.publication); publication['schema_version'] = '1.0'
        self.pubraw = encode(publication); self.policy['publication_receipt_sha256'] = digest(self.pubraw)
        with self.assertRaises(ValueError): self.run_consumer()

    def test_legacy_context_generic_json_keeps_legacy_semantics(self):
        self.manifest = {'schema_version': '1.0', 'document_type': 'artifact_delivery',
                         'artifacts': [self.item('context.json')]}
        self.manifest['artifacts'][0]['format'] = 'json'
        self.policy['schema_version'] = '1.0'
        self.reseal(); receipt, _ = self.run_consumer()
        self.assertNotIn('knowledge-bindings', receipt['verification'])

    def test_scope_pin_expiry_and_receipt_do_not_grant_authority(self):
        receipt, _ = self.run_consumer()
        for args in ({'consumer': 'OTHER'}, {'scope': 'OTHER'}, {'purpose': 'implementation'},
                     {'policy_sha256': '0' * 64}):
            with self.assertRaises(ValueError): self.run_consumer(**args)
        for field, value in [('authority_granted', True), ('schema_version', '1.0'), ('verification', 'trusted')]:
            altered = dict(receipt, **{field: value})
            with self.assertRaises(ValueError): self.run_consumer(receipt_raw=encode(altered))
        self.policy['consumer_use_approval'] = 'pending'
        with self.assertRaises(ValueError): self.run_consumer(receipt_raw=encode(receipt))

    def retry_bundle(self):
        # Prior attempt is a separately bound immutable input/handoff pair.
        for name in ('input.json', 'handoff.json'):
            item = deepcopy(self.item(name)); item['reference']['path'] = 'examples/knowledge-delivery/prior-' + name
            self.files[item['reference']['path']] = encode(self.data(name))
            self.manifest['artifacts'].append(item)
        self.manifest['knowledge_bindings'].append({'input': self.item('prior-input.json')['reference'],
                                                    'handoff': self.item('prior-handoff.json')['reference']})
        revision = 'sha256:' + digest(self.files[self.item('prior-handoff.json')['reference']['path']])
        for name in ('input.json', 'handoff.json'):
            data = self.data(name)
            data.update(task_id='SYNTHETIC-RETRY-2', attempt=2, retry_of=[{
                'task_id': data['task_id'], 'attempt': 1, 'handoff_locator': 'prior-handoff.json',
                'revision': revision}])
            self.replace(name, data)
        self.reseal()

    def test_retry_chain_identity_assignment_and_required_bytes(self):
        self.retry_bundle(); self.run_consumer()
        for field, value in [('task_id', 'SYNTHETIC-WRONG'), ('attempt', 2),
                             ('revision', 'sha256:' + '0' * 64), ('handoff_locator', 'article.md')]:
            self.setUp(); self.retry_bundle()
            for name in ('input.json', 'handoff.json'):
                data = self.data(name); data['retry_of'][0][field] = value
                self.replace(name, data)
            with self.subTest(field=field), self.assertRaises(ValueError): self.run_consumer()
        self.setUp(); self.retry_bundle()
        for name in ('input.json', 'handoff.json'):
            data = self.data(name); data['assignment']['scope'] = 'SYNTHETIC-DIFFERENT-SCOPE'
            self.replace(name, data)
        with self.assertRaisesRegex(ValueError, 'retry identity/scope mismatch'): self.run_consumer()
        self.setUp(); self.retry_bundle()
        self.manifest['artifacts'].remove(self.item('prior-input.json')); self.manifest['knowledge_bindings'].pop()
        self.reseal()
        with self.assertRaises(ValueError): self.run_consumer()

    def test_input_and_handoff_from_different_pinned_snapshots(self):
        # Each document resolves its dependencies in its own fixed snapshot.
        for item in list(self.manifest['artifacts']):
            if item['format'] in ('knowledge-input-v1', 'knowledge-context-v1'):
                item['reference']['commit'] = 'b' * 40
            elif item['format'] == 'text':
                clone = deepcopy(item); clone['reference']['commit'] = 'b' * 40
                self.manifest['artifacts'].append(clone)
        self.reseal(); self.run_consumer()

    def test_article_is_nonempty_text_not_another_document(self):
        for raw, kind in [(b'', 'text'), (b'   \n', 'text'), (b'{}', 'json')]:
            self.setUp()
            self.files[self.item('article.md')['reference']['path']] = raw
            self.item('article.md')['format'] = kind
            for name in ('input.json', 'handoff.json', 'context.json'):
                data = self.data(name); data['knowledge_references'][0]['revision'] = 'sha256:' + digest(raw)
                if name == 'handoff.json': data['artifacts'][0]['revision'] = 'sha256:' + digest(raw)
                self.replace(name, data)
            with self.assertRaisesRegex(ValueError, 'article requires nonempty text'): self.run_consumer()

    def test_unknown_format_and_disguised_partial_knowledge(self):
        for kind in ('knowledge-input-v2', 'knowledge', None):
            self.setUp(); self.item('input.json')['format'] = kind; self.reseal()
            with self.assertRaises(ValueError): self.run_consumer()
        for payload in ({'document_type': 'knowledge_unknown'}, {'role': 'knowledge'},
                        {'raw_findings': []}, {'knowledge_references': []}, {'retry_of': []},
                        {'publication': 'private_only'}):
            self.setUp(); self.item('context.json')['format'] = 'json'
            self.replace('context.json', payload)
            with self.assertRaises(ValueError): self.run_consumer()

    def test_schema_reference_definitions_stay_in_sync(self):
        specs = {name: json.loads((ROOT / f'contracts/{name}-v1.1.schema.json').read_text())
                 for name in ('artifact-delivery', 'publication-receipt', 'consumption-receipt', 'delivery-authorization')}
        for spec in specs.values(): Draft202012Validator.check_schema(spec)
        artifacts = specs['artifact-delivery']['properties']['artifacts']
        for name in ('publication-receipt', 'consumption-receipt'):
            self.assertEqual(specs[name]['properties']['artifacts'], artifacts)
        self.assertEqual(specs['artifact-delivery']['properties']['knowledge_bindings']['items']['properties']['input'],
                         artifacts['items']['properties']['reference'])


if __name__ == '__main__':
    unittest.main()
