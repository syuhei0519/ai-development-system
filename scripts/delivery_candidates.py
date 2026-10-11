"""Immutable candidate profile and complete Git tree snapshots (Delivery 1.2).

Only transport integrity: never adopt a candidate or execute fetched source code.
"""
import hashlib
from pathlib import PurePosixPath
import re

MAX_ENTRIES = 4096  # directories + leaves, per snapshot
MAX_TREES = 1024
MAX_TREE_BYTES = 1024 * 1024
MAX_TREE_TOTAL = 4 * 1024 * 1024
MAX_FILE = 16 * 1024 * 1024
MAX_BUNDLE = 64 * 1024 * 1024


def require(condition, message):
    if not condition:
        raise ValueError(message)


def oid(kind, raw):
    return hashlib.sha1(kind.encode() + b' ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


def tree_entries(raw):
    """Parse *all* raw tree bytes; truncated enumeration cannot match its Git OID."""
    entries, names, pos = [], set(), 0
    while pos < len(raw):
        end = raw.find(b'\0', pos)
        require(end >= 0 and end + 21 <= len(raw), 'truncated Git tree')
        header = raw[pos:end].split(b' ')
        require(len(header) == 2, 'invalid tree entry')
        mode, name = header
        name = name.decode('utf-8')
        require(name not in names and name not in ('.', '..', '.git') and
                '/' not in name and bool(name), 'unsafe/duplicate tree name')
        require(mode in (b'40000', b'100644', b'100755', b'120000', b'160000'), 'nonregular tree entry')
        names.add(name)
        entries.append((mode.decode(), name, raw[end+1:end+21].hex()))
        require(len(entries) <= MAX_ENTRIES, 'tree entry limit')
        pos = end + 21
    return entries


def snapshot_tree(source, ref):
    """Fresh Git only; derive complete snapshot and bytes without trusting an inventory."""
    # The same fixed-commit acquisition and safe reference checks used for blobs.
    directory = source.repository(ref)
    metadata_bytes = 0
    def read_object(kind, sha, maximum):
        require(source.git(directory, 'cat-file', '-t', sha).strip() == kind.encode(), 'tree object type mismatch')
        size = int(source.git(directory, 'cat-file', '-s', sha))
        require(0 <= size <= maximum, 'tree object size limit')
        raw = source.git(directory, 'cat-file', kind, sha)
        require(len(raw) == size and oid(kind, raw) == sha, 'tree object size/OID mismatch')
        return raw
    def read_tree(sha):
        nonlocal metadata_bytes
        raw = read_object('tree', sha, MAX_TREE_BYTES)
        metadata_bytes += len(raw)
        require(metadata_bytes <= MAX_TREE_TOTAL, 'tree metadata limit')
        return tree_entries(raw)
    raw_commit = read_object('commit', ref['commit'], MAX_FILE)
    first = raw_commit.split(b'\n', 1)[0]
    require(re.fullmatch(b'tree [0-9a-f]{40}', first), 'invalid commit root')
    root = first[5:].decode()
    # Parse complete ancestor trees, rejecting special edges rather than following them.
    for part in ref['path'].split('/'):
        found = [(mode, sha) for mode, name, sha in read_tree(root) if name == part]
        require(len(found) == 1 and found[0][0] == '40000', 'missing/non-tree ancestor')
        root = found[0][1]
    trees, files, blobs = [], [], {}
    total_bytes = 0
    pending = [('', root)]
    while pending:
        parent, sha = pending.pop()
        for mode, name, child in read_tree(sha):
            require(mode in ('40000', '100644', '100755'), 'symlink/gitlink/nonregular tree entry')
            require(re.fullmatch(r'[A-Za-z0-9_.-]+', name), 'unsafe snapshot name')
            path = str(PurePosixPath(parent) / name)
            require(len(ref['path'] + '/' + path) <= 512, 'tree path limit')
            require(len(trees) + len(files) < MAX_ENTRIES, 'snapshot entry limit')
            if mode == '40000':
                trees.append(dict(path=path, oid=child))
                require(len(trees) <= MAX_TREES, 'snapshot tree limit')
                pending.append((path, child))
            else:
                raw = read_object('blob', child, MAX_FILE)
                total_bytes += len(raw)
                require(total_bytes <= MAX_BUNDLE, 'snapshot bytes limit')
                files.append(dict(path=path, mode=mode, oid=child, size=len(raw),
                                  sha256=hashlib.sha256(raw).hexdigest()))
                blobs[(ref['repository'], ref['commit'], ref['path']+'/'+path)] = raw
    snapshot = dict(profile='git-tree-snapshot-v1', repository=ref['repository'],
                    commit=ref['commit'], path=ref['path'], oid=root,
                    trees=sorted(trees, key=lambda x:x['path']), files=sorted(files, key=lambda x:x['path']))
    return snapshot, blobs


def verify_candidates(by_ref, parsed, blobs, bindings, source=None):
    """Check producer/raw-locator/IDs/source slots, then full source bytes and trees."""
    require(isinstance(bindings, list), 'candidate bindings required')
    def key(ref):return (ref['repository'], ref['commit'], ref['path'])
    def reference(ref, fmt):
        k = key(ref)
        require(k in by_ref and by_ref[k]['reference'] == ref and by_ref[k]['format'] == fmt,
                'candidate reference/type mismatch')
        return k
    def linked(producer, locator, owner):
        ref = by_ref[owner]['reference']
        if locator.startswith('https://'):
            return locator == f"https://github.com/{ref['repository']}/blob/{ref['commit']}/{ref['path']}"
        # Safe lexical relative path; no normalization of traversal.
        require(re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_./-]*', locator) and
                all(p not in ('', '.', '..', '.git') for p in locator.split('/')), 'unsafe candidate locator')
        return owner == (producer[0], producer[1], str(PurePosixPath(producer[2]).parent / locator))
    owners, claims, extra_blobs = set(), set(), {}
    snapshots = {}
    for binding in bindings:
        owner = reference(binding['owner'], 'knowledge-candidates-v1')
        producer = reference(binding['producer'], 'handoff-v2')
        require(owner not in owners, 'duplicate candidate owner')
        owners.add(owner)
        data, handoff = parsed[owner], parsed[producer]
        artifacts = [a for a in handoff['artifacts'] if a['id'] == binding['producer_artifact_id']]
        require(len(artifacts) == 1 and artifacts[0]['kind'] == 'knowledge' and
                linked(producer, artifacts[0]['locator'], owner) and
                artifacts[0]['revision'] == 'sha256:'+binding['owner']['sha256'], 'candidate producer artifact mismatch')
        candidates = {c['id']:c for c in data['candidates']}
        require(len(candidates) == len(data['candidates']), 'duplicate candidate ID')
        declared = binding['candidate_ids']
        require(len(declared) == len(set(declared)) and set(declared) == set(candidates), 'candidate ID set mismatch')
        associated = [c for c in handoff['knowledge_candidates'] if linked(producer, c['raw_locator'], owner)]
        require({c['id'] for c in associated} == set(candidates), 'producer candidate set mismatch')
        for candidate in associated:
            require(candidate['domain'] == candidates[candidate['id']]['domain'], 'candidate domain mismatch')
            identity = (producer, candidate['id'])
            require(identity not in claims, 'ambiguous candidate producer')
            claims.add(identity)
        used = set()
        for slot in binding['sources']:
            cid = slot['candidate_id']
            require(cid in candidates and cid not in used and slot['source'] == candidates[cid]['source'],
                    'candidate source slot mismatch')
            used.add(cid)
            target = slot['target']
            if target['kind'] == 'blob':
                ref = target['reference']; k = key(ref)
                require(k in by_ref and by_ref[k]['reference'] == ref and ref['object_type'] == 'git-blob',
                        'candidate blob missing/mismatch')
                require(slot['source'] == f"https://github.com/{ref['repository']}/blob/{ref['commit']}/{ref['path']}",
                        'candidate blob URL mismatch')
                require(len(blobs[k]) == ref['size'] and hashlib.sha256(blobs[k]).hexdigest() == ref['sha256'],
                        'candidate blob size/hash mismatch')
            else:
                snap = target['snapshot']
                require(slot['source'] == f"https://github.com/{snap['repository']}/tree/{snap['commit']}/{snap['path']}",
                        'candidate tree URL mismatch')
                require(source is not None, 'tree source retrieval required')
                sk = key(snap)
                require(sk not in snapshots or snapshots[sk] == snap, 'conflicting tree snapshot')
                if sk not in snapshots:
                    actual, tree_blobs = snapshot_tree(source, snap)
                    # Canonical path ordering also excludes duplicate/ambiguous inventories.
                    require(actual == snap, 'incomplete/altered tree snapshot')
                    snapshots[sk] = snap
                    for k, raw in tree_blobs.items():
                        require(k not in blobs or blobs[k] == raw, 'conflicting source bytes')
                        require(k not in extra_blobs or extra_blobs[k] == raw, 'conflicting tree bytes')
                        extra_blobs[k] = raw
                    require(sum(len(v) for v in {**blobs, **extra_blobs}.values()) <= MAX_BUNDLE,
                            'bundle plus tree bytes limit')
        require(used == set(candidates), 'missing candidate source slot')
    require(owners == {k for k,a in by_ref.items() if a['format'] == 'knowledge-candidates-v1'},
            'unbound candidates document')
    # Any Handoff claiming this typed payload must be its unique bound producer.
    for producer, item in by_ref.items():
        if item['format'] != 'handoff-v2':continue
        for candidate in parsed[producer]['knowledge_candidates']:
            if any(linked(producer, candidate['raw_locator'], owner) for owner in owners):
                require((producer, candidate['id']) in claims, 'unbound producer candidate')
    return extra_blobs
