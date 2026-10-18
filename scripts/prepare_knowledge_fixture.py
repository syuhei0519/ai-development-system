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


def fixture_slots(manifest, read):
    """Author bindings for synthetic fixtures only, never upgrade historical records."""
    from copy import deepcopy
    from pathlib import PurePosixPath
    artifacts = manifest['artifacts']
    slots = []
    for a in artifacts:
        a['reference'].setdefault('object_type', 'git-blob')
    def add(owner, slot, locator, revision):
        if not isinstance(locator, str): return
        ref = owner['reference']
        path = str(PurePosixPath(ref['path']).parent / locator)
        target = next((a for a in artifacts if a['reference']['repository'] == ref['repository'] and
                       a['reference']['commit'] == ref['commit'] and a['reference'].get('path') == path), None)
        if target is not None:
            slots.append(dict(owner=deepcopy(ref), slot=slot, locator=locator, revision=revision,
                              target={k:deepcopy(target[k]) for k in ('reference','format')}))
    for owner in artifacts:
        if owner['format'] not in ('handoff-v2','knowledge-input-v1','knowledge-handoff-v1','knowledge-context-v1'): continue
        try: data = json.loads(read(owner['reference']))
        except (ValueError, KeyError): continue
        if not isinstance(data,dict): continue
        for a in data.get('artifacts') or []:
            if isinstance(a,dict) and all(k in a for k in ('id','locator','revision')):
                add(owner,dict(kind='artifact',id=a['id']),a['locator'],a['revision'])
        for u in data.get('upstream') or []:
            add(owner,dict(kind='upstream',**{k:u[k] for k in ('role','task_id','attempt','relationship')}),u['handoff_locator'],u['revision'])
        for f in data.get('raw_findings') or []:
            for i,src in enumerate(f.get('sources') or []):
                add(owner,dict(kind='finding-source',finding_id=f['id'],source_index=i),src['locator'],src['revision'])
        for article in data.get('knowledge_references') or []:
            add(owner,dict(kind='knowledge-reference',id=article['id']),article['locator'],article['revision'])
            for i,src in enumerate(article['sources']):
                add(owner,dict(kind='knowledge-source',id=article['id'],source_index=i),src['locator'],src['revision'])
        for u in data.get('retry_of') or []:
            add(owner,dict(kind='knowledge-retry',task_id=u['task_id'],attempt=u['attempt']),u['handoff_locator'],u['revision'])
    manifest['slot_bindings'] = slots
    manifest.setdefault('knowledge_bindings', [])


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
    manifest = {'schema_version': '1.3', 'document_type': 'artifact_delivery',
                'artifacts': artifacts, 'knowledge_bindings': [{
                    'input': artifacts[0]['reference'], 'handoff': artifacts[1]['reference']}]}
    fixture_slots(manifest, lambda ref: (ROOT / ref['path']).read_bytes())
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
        verify_handoffs(manifest['artifacts'], blobs, '1.3', manifest['knowledge_bindings'], manifest['slot_bindings'])
        manifest_raw = (json.dumps(manifest, indent=2) + '\n').encode()
        publication = {'schema_version': '1.3', 'document_type': 'publication_receipt',
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
