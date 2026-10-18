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
    from .validate_knowledge import validate as validate_knowledge
    from .delivery_candidates import verify_candidates, oid as git_oid
except ImportError:
    from validate_handoff import validate as validate_handoff
    from validate_knowledge import validate as validate_knowledge
    from delivery_candidates import verify_candidates, oid as git_oid

ROOT = Path(__file__).resolve().parents[1]
MAX_FILE = 16 * 1024 * 1024
MAX_BUNDLE = 64 * 1024 * 1024
ARTIFACT_LIMITS = {'1.3': 256}
DELIVERY_SCHEMAS = {'artifact-delivery', 'delivery-authorization',
                    'publication-receipt', 'consumption-receipt'}
KNOWLEDGE_FORMATS = {f'knowledge-{kind}-v1': f'knowledge_{kind}'
                     for kind in ('input', 'handoff', 'context')}


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
    if name in DELIVERY_SCHEMAS:
        require(isinstance(data, dict) and data.get('schema_version') == '1.3',
                'unsupported delivery version; historical records require their original Git revision')
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
    if ref.get('object_type') != 'git-commit-object':
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

    def repository(self, ref):
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
        return self.repositories[key]

    def read(self, ref):
        directory = self.repository(ref)
        if ref.get('object_type') == 'git-commit-object':
            size = int(self.git(directory, 'cat-file', '-s', ref['commit']))
            require(size == ref['size'] and size <= MAX_FILE, 'Git commit size mismatch')
            raw = self.git(directory, 'cat-file', 'commit', ref['commit'])
            verify_commit_object(ref, raw)
            return raw
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
        raw = self.git(directory, 'cat-file', 'blob', oid.decode())
        require(len(raw) == size and git_oid('blob', raw) == oid.decode(), 'Git blob OID/size mismatch')
        return raw


def read_local(path):
    require(not path.is_symlink() and path.is_file(), 'input must be regular file')
    with path.open('rb') as stream:
        raw = stream.read(MAX_FILE + 1)
    require(len(raw) <= MAX_FILE, 'input too large')
    return raw


def reference_key(ref):
    # None is a distinct object namespace; no blob path can collide with it.
    return (ref['repository'], ref['commit'], ref.get('path'))


def verify_commit_object(ref, raw):
    require(ref.get('object_type') == 'git-commit-object' and
            len(raw) == ref['size'] and digest(raw) == ref['sha256'],
            'raw commit size/hash mismatch')
    # Git SHA-1 OID includes the object header, unlike the raw-payload SHA-256.
    oid = hashlib.sha1(b'commit ' + str(len(raw)).encode('ascii') + b'\0' + raw).hexdigest()
    require(oid == ref['commit'], 'raw commit OID mismatch')


def artifact_slot(artifact):
    return {'kind':'artifact', 'id':artifact['id']}


def upstream_slot(upstream):
    return {'kind':'upstream', **{k:upstream[k] for k in ('role', 'task_id', 'attempt', 'relationship')}}


class SlotResolver:
    """v1.2: every structural dependency has exactly one explicit outer binding.

    No URL traversal: compare the original locator to a canonical string derived
    solely from an enumerated, pinned target. Never rewrite the owner document.
    """
    def __init__(self, by_ref, blobs, bindings):
        require(isinstance(bindings, list), 'slot bindings required')
        self.by_ref, self.blobs = by_ref, blobs
        self.bindings, self.used = {}, set()
        for binding in bindings:
            owner = reference_key(binding['owner'])
            target = reference_key(binding['target']['reference'])
            require(owner in by_ref and by_ref[owner]['reference'] == binding['owner'] and
                    by_ref[owner]['format'] in {'handoff-v2', *KNOWLEDGE_FORMATS},
                    'slot owner reference/type mismatch')
            require(target in by_ref and by_ref[target]['reference'] == binding['target']['reference'] and
                    by_ref[target]['format'] == binding['target']['format'], 'slot target mismatch')
            identity = (owner, json.dumps(binding['slot'], sort_keys=True))
            require(identity not in self.bindings, 'duplicate structural slot')
            self.bindings[identity] = binding

    def bind(self, owner, slot, locator, revision, commit=False):
        identity = (owner, json.dumps(slot, sort_keys=True))
        require(identity in self.bindings and identity not in self.used, 'missing or ambiguous slot')
        binding = self.bindings[identity]
        require(binding['locator'] == locator and binding['revision'] == revision,
                'original locator/revision mismatch')
        ref = binding['target']['reference']
        target = reference_key(ref)
        require(ref['object_type'] == ('git-commit-object' if commit else 'git-blob'),
                'slot object type mismatch')
        if commit:
            require(binding['target']['format'] == 'git-commit-object' and
                    locator == f"https://github.com/{ref['repository']}/commit/{ref['commit']}" and
                    revision == ref['commit'], 'commit URL/revision mismatch')
        else:
            require(revision == 'sha256:' + digest(self.blobs[target]), 'slot digest mismatch')
            if locator.startswith('https://'):
                require(locator == f"https://github.com/{ref['repository']}/blob/{ref['commit']}/{ref['path']}",
                        'blob URL mismatch')
            else:
                safe_path(locator)
                require(target == (owner[0], owner[1], str(PurePosixPath(owner[2]).parent / locator)),
                        'relative slot snapshot mismatch')
        self.used.add(identity)
        return target

    def finish(self):
        require(self.used == set(self.bindings), 'extra slot binding')


def verify_handoffs(artifacts, blobs, version='1.3', knowledge_bindings=None, slot_bindings=None,
                    candidate_bindings=None, source=None):
    require(version == '1.3', 'unsupported delivery version')
    formats = {'text', 'json', 'handoff-v2'}
    if version != '1.0':
        formats.update(KNOWLEDGE_FORMATS)
    if version in ('1.2', '1.3'):
        formats.update(('git-commit-object', 'knowledge-candidates-v1'))
    require(all(a['format'] in formats for a in artifacts), 'unsupported delivery format')
    by_ref = {reference_key(a['reference']): a
              for a in artifacts}
    require(len(by_ref) == len(artifacts), 'duplicate artifact path')
    parsed = {}
    for key, item in by_ref.items():
        raw = blobs[key]
        if item['format'] == 'git-commit-object':
            require(item['reference'].get('object_type') == 'git-commit-object', 'commit type mismatch')
            verify_commit_object(item['reference'], raw)
            continue
        require(item['reference'].get('object_type', 'git-blob') == 'git-blob', 'blob type mismatch')
        # Inspect content even for text/non-.json names. Only syntax errors in
        # ordinary prose may fall back to text; duplicate keys/non-finite numbers
        # and JSON-looking truncated documents must never reach that fallback.
        text = raw.decode('utf-8')
        start = text.lstrip()
        require(not start.startswith('\ufeff'), 'UTF-8 BOM is not supported')
        # A leading Markdown link/reference is ordinary prose, not a JSON array.
        markdown_link = re.match(r'\[[^\]\r\n]+\](?:\([^\r\n]*\)|\[[^\]\r\n]*\]|:[ \t]+\S)', start)
        json_required = (item['format'] != 'text' or
                         key[2].lower().endswith('.json') or
                         start.startswith('{') or
                         (start.startswith('[') and not markdown_link))
        try:
            parsed[key] = parse(raw)
        except json.JSONDecodeError:
            require(not json_required, 'invalid JSON content')
            continue
        require(item['format'] != 'text', 'JSON content must not be typed text')
        if version != '1.0' and isinstance(parsed[key], dict):
            require(parsed[key].get('publication') != 'private_only', 'private document forbidden')
        if item['format'] == 'knowledge-candidates-v1':
            schema('knowledge-candidates-v1', parsed[key])
            candidates = parsed[key]['candidates']
            require(len({c['id'] for c in candidates}) == len(candidates), 'duplicate candidate ID')
        elif item['format'] in KNOWLEDGE_FORMATS:
            data = parsed[key]
            require(isinstance(data, dict) and
                    data.get('document_type') == KNOWLEDGE_FORMATS[item['format']],
                    'Knowledge format/document_type mismatch')
            require(not validate_knowledge(data), 'invalid Knowledge v1.0')
            require(data.get('publication') != 'private_only', 'private Knowledge forbidden')
        elif item['format'] == 'handoff-v2':
            require(not validate_handoff(parsed[key]), 'invalid Handoff v2.0')
            require(parsed[key]['publication'] != 'private_only', 'private Handoff forbidden')
        elif isinstance(parsed.get(key), dict):
            # Reserved Handoff identity/coverage fields still identify incomplete
            # documents: deleting one required field must not downgrade the type.
            data = parsed[key]
            if version in ('1.2', '1.3'):
                require(not (set(data) & {'candidates', 'publication_status'}),
                        'Candidates must use explicit candidate profile')
            if version != '1.0':
                require(not (set(data) & {'raw_findings', 'knowledge_references', 'retry_of'} or
                             data.get('role') == 'knowledge' or
                             (isinstance(data.get('document_type'), str) and
                              data['document_type'].startswith('knowledge'))),
                        'Knowledge must use explicit Knowledge format')
            require(not (set(data) & {'task_id', 'ac_mapping', 'system_status'} or
                         ('schema_version' in data and
                          set(data) & {'issue', 'assignment', 'upstream'})),
                    'Handoff must be typed handoff-v2')
    resolver = SlotResolver(by_ref, blobs, slot_bindings) if version in ('1.2', '1.3') else None
    identities = set()
    for key, item in by_ref.items():
        if item['format'] != 'handoff-v2':
            continue
        handoff = parsed[key]
        if resolver:
            identity = (handoff['role'], handoff['task_id'])
            require(identity not in identities, 'duplicate Handoff task identity')
            identities.add(identity)
        def bind(locator, revision, slot, commit=False):
            if resolver:
                return resolver.bind(key, slot, locator, revision, commit)

            safe_path(locator)
            path = str(PurePosixPath(key[2]).parent / locator)
            target = (key[0], key[1], path)
            require(target in by_ref, 'Handoff referenced bytes missing from bundle')
            require(revision == 'sha256:' + digest(blobs[target]), 'Handoff binding digest mismatch')
            return target
        for artifact in handoff['artifacts']:
            bind(artifact['locator'], artifact['revision'], artifact_slot(artifact), artifact['kind'] == 'commit')
        for upstream in handoff['upstream']:
            target = bind(upstream['handoff_locator'], upstream['revision'], upstream_slot(upstream))
            require(by_ref[target]['format'] == 'handoff-v2', 'upstream must be Handoff')
            previous = parsed[target]
            require(all(previous[k] == upstream[k] for k in ('role', 'task_id', 'attempt')),
                    'upstream identity mismatch')
            if upstream['relationship'] == 'retry_of':
                require(previous['issue'] == handoff['issue'], 'retry Issue mismatch')
    if version != '1.0':
        verify_knowledge_bindings(by_ref, parsed, blobs, knowledge_bindings, resolver)

    if resolver:
        resolver.finish()
        return verify_candidates(by_ref, parsed, blobs, candidate_bindings or [], source)
    return {}


def verify_knowledge_bindings(by_ref, parsed, blobs, bindings, resolver=None):
    """Bind immutable input/output snapshots and every declared Knowledge dependency.

    Locators are safe relative paths in the containing document's repo/commit;
    revisions are raw sha256 digests. No arbitrary URL or prose proves existence.
    """
    require(isinstance(bindings, list), 'Knowledge bindings required')

    def reference(ref, kind):
        key = reference_key(ref)
        require(key in by_ref and by_ref[key]['reference'] == ref and
                by_ref[key]['format'] == kind, 'Knowledge binding reference mismatch')
        return key

    def bind(owner, locator, revision, slot):
        if resolver:
            return resolver.bind(owner, slot, locator, revision)
        safe_path(locator)
        target = (owner[0], owner[1], str(PurePosixPath(owner[2]).parent / locator))
        require(target in by_ref, 'Knowledge referenced bytes missing from bundle')
        require(revision == 'sha256:' + digest(blobs[target]), 'Knowledge binding digest mismatch')
        return target

    def article_bytes(target):
        require(by_ref[target]['format'] == 'text' and bool(blobs[target].strip()),
                'Knowledge article requires nonempty text bytes')

    inputs, handoffs, identities = set(), set(), set()
    for pair in bindings:
        source = reference(pair['input'], 'knowledge-input-v1')
        require(source not in inputs, 'duplicate Knowledge input binding')
        inputs.add(source)
        if 'handoff' in pair:
            result = reference(pair['handoff'], 'knowledge-handoff-v1')
            require(result not in handoffs, 'duplicate Knowledge handoff binding')
            handoffs.add(result)
            require(all(parsed[source][field] == parsed[result][field] for field in
                        ('assignment', 'raw_findings', 'knowledge_references',
                         'task_id', 'attempt', 'retry_of')), 'Knowledge input/handoff mismatch')
    require(inputs == {k for k, a in by_ref.items() if a['format'] == 'knowledge-input-v1'} and
            handoffs == {k for k, a in by_ref.items() if a['format'] == 'knowledge-handoff-v1'},
            'unbound Knowledge input/handoff')
    for key, item in by_ref.items():
        if item['format'] not in KNOWLEDGE_FORMATS:
            continue
        data = parsed[key]
        if 'task_id' in data:
            identity = (data['document_type'], data['task_id'])
            require(identity not in identities, 'duplicate Knowledge task identity')
            identities.add(identity)
        for finding in data.get('raw_findings', []):
            for index, source in enumerate(finding['sources']):
                bind(key, source['locator'], source['revision'],
                     {'kind':'finding-source', 'finding_id':finding['id'], 'source_index':index})
        for article in data['knowledge_references']:
            article_bytes(bind(key, article['locator'], article['revision'], {'kind':'knowledge-reference', 'id':article['id']}))
            for index, source in enumerate(article['sources']):
                bind(key, source['locator'], source['revision'],
                     {'kind':'knowledge-source', 'id':article['id'], 'source_index':index})
        for artifact in data.get('artifacts', []):
            target = bind(key, artifact['locator'], artifact['revision'], artifact_slot(artifact))
            if artifact['kind'] == 'knowledge':
                article_bytes(target)
        for previous in data.get('retry_of', []):
            target = bind(key, previous['handoff_locator'], previous['revision'],
                          {'kind':'knowledge-retry', 'task_id':previous['task_id'], 'attempt':previous['attempt']})
            require(by_ref[target]['format'] == 'knowledge-handoff-v1',
                    'Knowledge retry must reference Knowledge handoff')
            prior = parsed[target]
            require(all(prior[field] == previous[field] for field in ('task_id', 'attempt')) and
                    prior['assignment'] == data['assignment'], 'Knowledge retry identity/scope mismatch')


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
    version = manifest['schema_version']
    require(policy['schema_version'] == version, 'authorization/manifest version mismatch')
    require(digest(publication_raw) == policy['publication_receipt_sha256'], 'publication receipt digest mismatch')
    publication = parse(publication_raw)
    schema('publication-receipt', publication)
    require(publication['schema_version'] == version, 'publication/manifest version mismatch')
    require(publication['manifest_sha256'] == digest(manifest_raw) and
            publication['artifacts'] == manifest['artifacts'], 'publication receipt mismatch')
    artifacts = manifest['artifacts']
    require(len(artifacts) <= ARTIFACT_LIMITS[version], 'artifact count limit')
    keys = [reference_key(a['reference']) for a in artifacts]
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
    if version in ('1.2', '1.3') and any(s['target']['kind'] == 'tree'
            for b in manifest.get('candidate_bindings', []) for s in b['sources']):
        require('original' in policy['allowed_representations'], 'tree originals not approved')
    tree_blobs = verify_handoffs(artifacts, blobs, version, manifest.get('knowledge_bindings'),
                                 manifest.get('slot_bindings'), manifest.get('candidate_bindings'), source)
    blobs.update(tree_blobs)
    receipt = {'schema_version':version, 'document_type':'consumption_receipt',
               'manifest_sha256':digest(manifest_raw), 'authorization_sha256':digest(policy_raw),
               'publication_receipt_sha256':digest(publication_raw),
               'consumer':consumer, 'scope':scope, 'purpose':purpose, 'artifacts':artifacts,
               'verification':('full-raw-bytes-size-sha256-json-handoff-knowledge-bindings'
                               if version == '1.1' else
                               'full-raw-bytes-size-sha256-json-handoff-bindings'),
               'authority_granted':False}
    if version in ('1.2', '1.3'):
        receipt['slot_bindings'] = manifest['slot_bindings']
        receipt['candidate_bindings'] = manifest.get('candidate_bindings', [])
        receipt['verification'] = 'full-raw-bytes-size-sha256-json-handoff-knowledge-slots-git-objects-candidates-trees'
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
            dest = (staged / 'git-commit-objects' / repository / commit / 'commit.raw'
                    if path is None else staged / 'artifacts' / repository / commit / path)
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
