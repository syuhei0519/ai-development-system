"""Synthetic content/type regressions with valid outer hashes and authority pins."""
from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import test_delivery as fixtures
from scripts.consume_delivery import main, write_bundle


class DeliveryContentTests(unittest.TestCase):
    setUp = fixtures.DeliveryTests.setUp
    reseal = fixtures.DeliveryTests.reseal
    run_consumer = fixtures.DeliveryTests.run_consumer

    def replace_handoff(self, raw, path='handoff.txt', kind='text'):
        item = self.manifest['artifacts'][0]
        self.files.pop(item['reference']['path'])
        self.files[path] = raw
        item['reference'].update(path=path, size=len(raw), sha256=fixtures.digest(raw))
        item['format'] = kind
        self.reseal()  # Integrity and approval pins match; rejection must be content-based.

    def test_disguised_handoff_matrix_with_valid_outer_pins(self):
        original = fixtures.parse(self.files['handoff.json'])
        variants = {'complete': original}
        for field in original:
            changed = deepcopy(original)
            del changed[field]
            variants['missing-' + field] = changed
        for field, value in [('publication', 'private_only'), ('attempt', True),
                             ('artifacts', None), ('schema_version', '1.0')]:
            variants['invalid-' + field] = dict(original, **{field: value})
        missing = deepcopy(original)
        missing['artifacts'][0]['locator'] = 'unlisted.txt'
        variants['unlisted-binding'] = missing
        wrong = deepcopy(original)
        wrong['artifacts'][0]['revision'] = 'sha256:' + '0' * 64
        variants['wrong-binding'] = wrong
        for name, data in variants.items():
            for path in ('handoff.txt', 'opaque', 'document.md', 'handoff.JSON'):
                for kind in ('text', 'json'):
                    with self.subTest(variant=name, path=path, kind=kind):
                        self.replace_handoff(fixtures.encode(data), path, kind)
                        with self.assertRaises(ValueError):
                            self.run_consumer()

    def test_strict_json_cannot_fall_back_to_text(self):
        raw = self.files['handoff.json']
        malformed = [
            raw[:-2], b'{', b'[', b'{"task_id":', raw + b' trailing',
            raw.replace(b'"schema_version": "2.0"',
                        b'"schema_version":"2.0","schema_version":"2.0"'),
            b'{"nested":{"key":1,"key":2}}',
            b'{"nested":{"key":1,"ke\\u0079":2}}',
            b'{"x":NaN}', b'{"x":Infinity}', b'{"x":-Infinity}',
            b'\xff', b'\xef\xbb\xbf' + raw, b' \n\xef\xbb\xbf' + raw,
            b' \r\n\t' + raw[:-2],
        ]
        for payload in malformed:
            with self.subTest(payload=payload[:32]):
                self.replace_handoff(payload)
                with self.assertRaises(ValueError):
                    self.run_consumer()

    def test_json_values_and_encoded_wrappers_cannot_claim_text(self):
        handoff = fixtures.parse(self.files['handoff.json'])
        for data in (handoff, [handoff], {'payload': handoff},
                     json.dumps(handoff), {}, [], None, True, 42):
            with self.subTest(type=type(data).__name__):
                self.replace_handoff(fixtures.encode(data))
                with self.assertRaisesRegex(ValueError, 'must not be typed text'):
                    self.run_consumer()

    def test_correctly_typed_handoff_at_non_json_path_runs_all_checks(self):
        original = fixtures.parse(self.files['handoff.json'])
        self.replace_handoff(fixtures.encode(original), 'handoff.txt', 'handoff-v2')
        self.run_consumer()
        variants = [dict(original, publication='private_only'),
                    dict(original, assignment=None)]
        for field, value in [('locator', 'unlisted.txt'), ('revision', 'sha256:' + '0' * 64)]:
            data = deepcopy(original)
            data['artifacts'][0][field] = value
            variants.append(data)
        for data in variants:
            with self.subTest(data=data['publication']):
                self.replace_handoff(fixtures.encode(data), 'handoff.txt', 'handoff-v2')
                with self.assertRaises(ValueError):
                    self.run_consumer()

    def test_incomplete_json_handoff_is_not_generic_data(self):
        for data in ({'task_id': 'SYNTHETIC'}, {'ac_mapping': []}, {'system_status': 'completed'},
                     {'schema_version': '2.0', 'assignment': {}},
                     {'schema_version': '2.0', 'issue': {}},
                     {'schema_version': '2.0', 'upstream': []}):
            self.replace_handoff(fixtures.encode(data), 'opaque', 'json')
            with self.subTest(data=data), self.assertRaisesRegex(ValueError, 'must be typed handoff-v2'):
                self.run_consumer()

    def test_normal_markdown_text_and_generic_json_preserve_raw_bytes(self):
        texts = [b'Ordinary text\r\n', b'# Markdown\n\n- list\n\n```json\n{"example": 1}\n```\n',
                 '日本語の設計書\n'.encode(), b'', b'Notes: {not a JSON document}\n',
                 b'[Guide](https://example.invalid)\n', b'[Guide][ref]\n',
                 b'[ref]: https://example.invalid\n', b'- [ ] Markdown task\n']
        for raw in texts:
            self.replace_handoff(raw, 'notes.md', 'text')
            receipt, blobs = self.run_consumer()
            self.assertEqual(blobs[('example/repo', 'a' * 40, 'notes.md')], raw)
            self.assertFalse(receipt['authority_granted'])
        self.replace_handoff(b'{"ordinary":"data"}\n', 'opaque', 'json')
        self.run_consumer()

    def test_json_suffix_cannot_claim_invalid_plain_text(self):
        for path in ('document.json', 'document.JSON', 'document.Json'):
            self.replace_handoff(b'ordinary prose', path, 'text')
            with self.subTest(path=path), self.assertRaises(ValueError):
                self.run_consumer()

    def test_cli_rejects_disguise_without_output_or_receipt(self):
        self.replace_handoff(self.files['handoff.json'])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = ['consume_delivery.py']
            for name, raw in [('manifest', self.mraw), ('authorization', fixtures.encode(self.policy)),
                              ('publication', self.pubraw)]:
                path = root / name
                path.write_bytes(raw)
                args.extend(['--' + name, str(path)])
            args.extend(['--output', str(root / 'out'), '--authorization-sha256',
                         fixtures.digest(fixtures.encode(self.policy)), '--consumer', self.policy['consumer'],
                         '--scope', self.policy['scope'], '--purpose', self.policy['purpose']])
            out, err = io.StringIO(), io.StringIO()
            with patch.object(sys, 'argv', args), patch('scripts.consume_delivery.GitSource',
                    return_value=fixtures.Source(self.files)), redirect_stdout(out), redirect_stderr(err):
                self.assertEqual(main(), 1)
            self.assertFalse((root / 'out').exists())
            self.assertEqual(out.getvalue(), '')
            self.assertEqual(err.getvalue(), 'FAIL: delivery rejected; no verified bundle produced\n')

    def test_verify_receipt_checks_new_fetch_not_old_output(self):
        receipt, blobs = self.run_consumer()
        with tempfile.TemporaryDirectory() as tmp:
            old = Path(tmp) / 'old'
            write_bundle(old, receipt, blobs)
            data = old / 'artifacts/example/repo' / ('a' * 40) / 'design.txt'
            data.write_bytes(b'local tampering')
            # The API has no old-directory input. It validates the newly read source.
            current, fresh = self.run_consumer(receipt_raw=fixtures.encode(receipt))
            new = Path(tmp) / 'new'
            write_bundle(new, current, fresh)
            self.assertEqual((new / data.relative_to(old)).read_bytes(), self.files['design.txt'])
            self.assertEqual(data.read_bytes(), b'local tampering')
            self.files['design.txt'] = b'source tampering'
            with self.assertRaises(ValueError):
                self.run_consumer(receipt_raw=fixtures.encode(receipt))
