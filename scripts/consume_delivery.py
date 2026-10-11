#!/usr/bin/env python3
"""Verify a pinned public Git bundle; receipt is evidence, never an authority token."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tempfile

from jsonschema import Draft202012Validator
try:
    from .validate_handoff import validate as validate_handoff
except ImportError:
    from validate_handoff import validate as validate_handoff

ROOT = Path(__file__).resolve().parents[1]
MAX_FILE = 16 * 1024 * 1024
MAX_BUNDLE = 64 * 1024 * 1024


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def parse(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'duplicate JSON key')
            result[key] = value
        return result
    def constant(_):
        raise ValueError('non-finite JSON number')
    return json.loads(raw.decode('utf-8'), object_pairs_hook=pairs, parse_constant=constant)


def schema(name, data):
    spec = json.loads((ROOT / 'contracts' / f'{name}.schema.json').read_text())
    require(Draft202012Validator(spec).is_valid(data), f'invalid {name} contract')


def safe_path(value):
    require(isinstance(value, str) and len(value) <= 512 and
            re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_./-]*', value) is not None and
            all(part not in ('', '.', '..', '.git') for part in value.split('/')),
            'unsafe repository path')
    return value


def check_reference(ref):
    require(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9][A-Za-z0-9_.-]{0,99}', ref['repository']) is not None,
            'only canonical GitHub owner/repository accepted')
    require(re.fullmatch('[0-9a-f]{40}', ref['commit']) is not None, 'fixed commit required')
    safe_path(ref['path'])


class GitSource:
    """Fresh isolated bare repositories; no checkout, hooks, submodule, filters or shell."""
    def __init__(self, directory):
        self.directory = Path(directory)
        self.repositories = {}
        self.env = {'PATH': os.defpath, 'HOME': str(self.directory),
                    'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': os.devnull,
                    'GIT_TERMINAL_PROMPT': '0', 'GIT_ALLOW_PROTOCOL': 'https',
                    'GIT_NO_REPLACE_OBJECTS': '1', 'LC_ALL': 'C'}
        # Existing network routing/CA is part of the trusted execution environment.
        for key in ('https_proxy', 'HTTPS_PROXY', 'http_proxy', 'HTTP_PROXY',
                    'all_proxy', 'ALL_PROXY', 'no_proxy', 'NO_PROXY', 'SSL_CERT_FILE'):
            if key in os.environ:
                self.env[key] = os.environ[key]

    def git(self, directory, *args):
        result = subprocess.run(['git', '-c', 'core.hooksPath=/dev/null',
                                 '-c', 'http.followRedirects=false', '-C', str(directory), *args],
                                env=self.env, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                timeout=120, check=False)
        require(result.returncode == 0, 'Git retrieval failed')
        return result.stdout

    def read(self, ref):
        check_reference(ref)
        key = (ref['repository'], ref['commit'])
        if key not in self.repositories:
            directory = self.directory / str(len(self.repositories))
            directory.mkdir()
            self.git(directory, 'init', '--bare', '--template=')
            self.git(directory, 'fetch', '--no-tags', '--depth=1',
                     'https://github.com/' + ref['repository'] + '.git', ref['commit'])
            require(self.git(directory, 'cat-file', '-t', ref['commit']).strip() == b'commit',
                    'object is not a commit')
            require(self.git(directory, 'rev-parse', 'FETCH_HEAD').decode().strip() == ref['commit'],
                    'fetched commit mismatch')
            self.repositories[key] = directory
        directory = self.repositories[key]
        # Inspect each tree edge. A gitlink or symlink is never followed.
        parts = ref['path'].split('/')
        for index in range(len(parts)):
            path = '/'.join(parts[:index + 1])
            entry = self.git(directory, 'ls-tree', '-z', ref['commit'], '--', path)
            require(entry.count(b'\0') == 1, 'missing or ambiguous tree entry')
            header, actual_path = entry[:-1].split(b'\t', 1)
            mode, kind, oid = header.split()
            require(actual_path.decode() == path, 'tree path mismatch')
            if index < len(parts) - 1:
                require(mode == b'040000' and kind == b'tree', 'non-directory ancestor')
            else:
                require(mode in (b'100644', b'100755') and kind == b'blob',
                        'symlink/submodule/non-blob rejected')
        size = int(self.git(directory, 'cat-file', '-s', oid.decode()))
        require(size == ref['size'] and size <= MAX_FILE, 'Git blob size mismatch')
        return self.git(directory, 'cat-file', 'blob', oid.decode())


def read_local(path):
    require(not path.is_symlink() and path.is_file(), 'input must be regular file')
    with path.open('rb') as stream:
        raw = stream.read(MAX_FILE + 1)
    require(len(raw) <= MAX_FILE, 'input too large')
    return raw


def verify_handoffs(artifacts, blobs):
    by_ref = {(a['reference']['repository'], a['reference']['commit'], a['reference']['path']): a
              for a in artifacts}
    parsed = {}
    for key, item in by_ref.items():
        raw = blobs[key]
        # Inspect content even for text/non-.json names. Only syntax errors in
        # ordinary prose may fall back to text; duplicate keys/non-finite numbers
        # and JSON-looking truncated documents must never reach that fallback.
        text = raw.decode('utf-8')
        start = text.lstrip()
        require(not start.startswith('\ufeff'), 'UTF-8 BOM is not supported')
        # A leading Markdown link/reference is ordinary prose, not a JSON array.
        markdown_link = re.match(r'\[[^\]\r\n]+\](?:\([^\r\n]*\)|\[[^\]\r\n]*\]|:[ \t]+\S)', start)
        json_required = (item['format'] in ('json', 'handoff-v2') or
                         key[2].lower().endswith('.json') or
                         start.startswith('{') or
                         (start.startswith('[') and not markdown_link))
        try:
            parsed[key] = parse(raw)
        except json.JSONDecodeError:
            require(not json_required, 'invalid JSON content')
            continue
        require(item['format'] != 'text', 'JSON content must not be typed text')
        if item['format'] == 'handoff-v2':
            require(not validate_handoff(parsed[key]), 'invalid Handoff v2.0')
            require(parsed[key]['publication'] != 'private_only', 'private Handoff forbidden')
        elif isinstance(parsed.get(key), dict):
            # Reserved Handoff identity/coverage fields still identify incomplete
            # documents: deleting one required field must not downgrade the type.
            data = parsed[key]
            require(not (set(data) & {'task_id', 'ac_mapping', 'system_status'} or
                         ('schema_version' in data and
                          set(data) & {'issue', 'assignment', 'upstream'})),
                    'Handoff must be typed handoff-v2')
    for key, item in by_ref.items():
        if item['format'] != 'handoff-v2':
            continue
        handoff = parsed[key]
        def bind(locator, revision):
            safe_path(locator)
            path = str(PurePosixPath(key[2]).parent / locator)
            target = (key[0], key[1], path)
            require(target in by_ref, 'Handoff referenced bytes missing from bundle')
            require(revision == 'sha256:' + digest(blobs[target]), 'Handoff binding digest mismatch')
            return target
        for artifact in handoff['artifacts']:
            bind(artifact['locator'], artifact['revision'])
        for upstream in handoff['upstream']:
            target = bind(upstream['handoff_locator'], upstream['revision'])
            require(by_ref[target]['format'] == 'handoff-v2', 'upstream must be Handoff')
            previous = parsed[target]
            require(all(previous[k] == upstream[k] for k in ('role', 'task_id', 'attempt')),
                    'upstream identity mismatch')
            if upstream['relationship'] == 'retry_of':
                require(previous['issue'] == handoff['issue'], 'retry Issue mismatch')


def consume(manifest_raw, policy_raw, publication_raw, policy_sha256,
            consumer, scope, purpose, source, now=None, receipt_raw=None):
    # Only the operator-supplied pin anchors authority; no value inside this bundle does.
    require(re.fullmatch('[0-9a-f]{64}', policy_sha256) is not None and
            digest(policy_raw) == policy_sha256, 'untrusted authorization bytes')
    policy = parse(policy_raw)
    schema('delivery-authorization', policy)
    require(policy['consumer_use_approval'] == 'approved', 'Consumer use is not approved')
    require((consumer, scope, purpose) == (policy['consumer'], policy['scope'], policy['purpose']),
            'authorization scope mismatch')
    expires = datetime.fromisoformat(policy['valid_until'].replace('Z', '+00:00'))
    require(expires.tzinfo is not None and (now or datetime.now(timezone.utc)) < expires,
            'authorization expired or timezone missing')
    require(digest(manifest_raw) == policy['manifest_sha256'], 'manifest digest mismatch')
    manifest = parse(manifest_raw)
    schema('artifact-delivery', manifest)
    require(digest(publication_raw) == policy['publication_receipt_sha256'], 'publication receipt digest mismatch')
    publication = parse(publication_raw)
    schema('publication-receipt', publication)
    require(publication['manifest_sha256'] == digest(manifest_raw) and
            publication['artifacts'] == manifest['artifacts'], 'publication receipt mismatch')
    artifacts = manifest['artifacts']
    keys = [(a['reference']['repository'], a['reference']['commit'], a['reference']['path']) for a in artifacts]
    require(len(keys) == len(set(keys)), 'duplicate artifact path')
    require(sum(a['reference']['size'] for a in artifacts) <= MAX_BUNDLE, 'bundle too large')
    for artifact in artifacts:
        check_reference(artifact['reference'])
        require(artifact['representation'] in policy['allowed_representations'], 'representation not approved')
    blobs = {}
    for key, artifact in zip(keys, artifacts):
        ref = artifact['reference']
        raw = source.read(ref)
        require(len(raw) == ref['size'] and digest(raw) == ref['sha256'], 'raw size/hash mismatch')
        blobs[key] = raw
    verify_handoffs(artifacts, blobs)
    receipt = {'schema_version':'1.0', 'document_type':'consumption_receipt',
               'manifest_sha256':digest(manifest_raw), 'authorization_sha256':digest(policy_raw),
               'publication_receipt_sha256':digest(publication_raw),
               'consumer':consumer, 'scope':scope, 'purpose':purpose, 'artifacts':artifacts,
               'verification':'full-raw-bytes-size-sha256-json-handoff-bindings',
               'authority_granted':False}
    schema('consumption-receipt', receipt)
    if receipt_raw is not None:
        candidate = parse(receipt_raw)
        schema('consumption-receipt', candidate)
        require(candidate == receipt, 'Consumption Receipt mismatch')
    return receipt, blobs


def write_bundle(output, receipt, blobs):
    # Caller owns parent directory; competing/malicious local writers are outside trust boundary.
    require(not output.exists() and not output.is_symlink(), 'output already exists')
    with tempfile.TemporaryDirectory(prefix='.delivery-', dir=output.parent) as temp:
        staged = Path(temp) / 'verified'
        staged.mkdir(mode=0o700)
        for (repository, commit, path), raw in blobs.items():
            dest = staged / 'artifacts' / repository / commit / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(raw)
        (staged / 'consumption-receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
        os.rename(staged, output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ('manifest', 'authorization', 'publication', 'output'):
        parser.add_argument('--'+arg, required=True, type=Path)
    for arg in ('authorization-sha256', 'consumer', 'scope', 'purpose'):
        parser.add_argument('--'+arg, required=True)
    parser.add_argument('--verify-receipt', type=Path,
                        help='compare receipt with freshly fetched/verified bytes; '
                             'does not inspect any previous output directory')
    args = parser.parse_args()
    try:
        with tempfile.TemporaryDirectory(prefix='delivery-git-') as temp:
            receipt, blobs = consume(read_local(args.manifest), read_local(args.authorization),
                read_local(args.publication), args.authorization_sha256, args.consumer,
                args.scope, args.purpose, GitSource(temp),
                receipt_raw=read_local(args.verify_receipt) if args.verify_receipt else None)
            write_bundle(args.output, receipt, blobs)
        print('PASS: verified bundle and Consumption Receipt written; no authority granted')
        return 0
    except (OSError, ValueError, UnicodeError, RecursionError, subprocess.SubprocessError):
        # Do not echo attacker-controlled input, Git output, credentials or private bytes.
        print('FAIL: delivery rejected; no verified bundle produced', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
