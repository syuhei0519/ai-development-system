#!/usr/bin/env python3
"""Fetch the published synthetic fixture at a fixed commit and prepare delivery records.

Does not publish, authorize a consumer, run an Agent, or claim operational success.
Run from the checkout being tested. A changed local fixture will fail the Git comparison.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile

try:
    from .consume_delivery import (ROOT, GitSource, digest, schema, require,
                                   verify_handoffs)
except ImportError:
    from consume_delivery import (ROOT, GitSource, digest, schema, require,
                                  verify_handoffs)

FILES = {'input.json': 'knowledge-input-v1', 'handoff.json': 'knowledge-handoff-v1',
         'context.json': 'knowledge-context-v1', 'article.md': 'text',
         'source-1.md': 'text', 'source-2.md': 'text'}


def fixture_manifest(repository, commit):
    artifacts = []
    for name, kind in FILES.items():
        path = 'examples/knowledge-delivery/' + name
        raw = (ROOT / path).read_bytes()
        artifacts.append({'reference': {'repository': repository, 'commit': commit,
                          'path': path, 'size': len(raw), 'sha256': digest(raw)},
                          'representation': 'original', 'format': kind,
                          'public_classification': 'synthetic_sample',
                          'source_alias': 'SYNTHETIC-KNOWLEDGE-DELIVERY'})
    manifest = {'schema_version': '1.1', 'document_type': 'artifact_delivery',
                'artifacts': artifacts, 'knowledge_bindings': [{
                    'input': artifacts[0]['reference'], 'handoff': artifacts[1]['reference']}]}
    schema('artifact-delivery', manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', required=True)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        manifest = fixture_manifest(args.repository, args.commit)
        blobs = {}
        with tempfile.TemporaryDirectory(prefix='knowledge-fixture-git-') as tmp:
            source = GitSource(tmp)
            for item in manifest['artifacts']:
                ref = item['reference']
                raw = source.read(ref)
                require(len(raw) == ref['size'] and digest(raw) == ref['sha256'],
                        'published fixture differs from checkout')
                blobs[(ref['repository'], ref['commit'], ref['path'])] = raw
        verify_handoffs(manifest['artifacts'], blobs, '1.1', manifest['knowledge_bindings'])
        manifest_raw = (json.dumps(manifest, indent=2) + '\n').encode()
        publication = {'schema_version': '1.1', 'document_type': 'publication_receipt',
                       'manifest_sha256': digest(manifest_raw), 'github_state': 'published',
                       'artifacts': manifest['artifacts'],
                       'observation': 'All six synthetic fixture blobs fetched from fixed Git '
                                      'commit and compared by full size/SHA-256. No authority granted.'}
        schema('publication-receipt', publication)
        # Reuse the existing atomic, non-overwriting staging boundary. These are
        # preparation records, not a consumption receipt or authorization.
        require(not args.output.exists() and not args.output.is_symlink(), 'output already exists')
        with tempfile.TemporaryDirectory(prefix='.fixture-', dir=args.output.parent) as tmp:
            staged = Path(tmp) / 'records'
            staged.mkdir(mode=0o700)
            (staged / 'manifest.json').write_bytes(manifest_raw)
            (staged / 'publication-receipt.json').write_text(json.dumps(publication, indent=2) + '\n')
            staged.rename(args.output)
        print('PASS: fixed Git synthetic fixture records prepared; consumer authorization still required')
        return 0
    except (OSError, ValueError, UnicodeError, RecursionError, subprocess.SubprocessError):
        print('FAIL: fixture preparation rejected', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
