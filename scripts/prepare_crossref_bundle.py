#!/usr/bin/env python3
"""Prepare private Delivery 1.2 record candidates from public fixed Git bytes.

No authorization is created; these records are not a Consumer success. The
operator must obtain a separate Manager authorization before consume_delivery.
"""
import argparse
from copy import deepcopy
import json
from pathlib import Path, PurePosixPath
import re
import tempfile
try:
    from .consume_delivery import (GitSource, parse, digest, schema, reference_key,
                                   artifact_slot, upstream_slot, require, safe_path)
    from .delivery_candidates import snapshot_tree
except ImportError:
    from consume_delivery import (GitSource, parse, digest, schema, reference_key,
                                  artifact_slot, upstream_slot, require, safe_path)
    from delivery_candidates import snapshot_tree


def encode(data):
    return (json.dumps(data, ensure_ascii=False, indent=2)+'\n').encode()


def fixed_url(locator, kind):
    match = re.fullmatch(r'https://github.com/([A-Za-z0-9-]+/[A-Za-z0-9_.-]+)/'+kind+
                         r'/([0-9a-f]{40})(?:/(.+))?', locator)
    require(match is not None, 'canonical fixed Git URL required')
    repo, commit, path = match.groups()
    require((kind == 'commit') == (path is None), 'URL path mismatch')
    if path:safe_path(path)
    return repo, commit, path


class Preparation:
    def __init__(self, source, classification='public_safe'):
        self.source, self.classification = source, classification
        self.manifest = dict(schema_version='1.2', document_type='artifact_delivery',
                             artifacts=[], knowledge_bindings=[], slot_bindings=[], candidate_bindings=[])
        self.items, self.raw, self.pending = {}, {}, []

    def add(self, repo, commit, path=None, expected=None):
        key = (repo, commit, path)
        if key in self.items:
            if expected:require(expected == 'sha256:'+self.items[key]['reference']['sha256'], 'declared digest mismatch')
            return self.items[key]
        require(len(self.items) < 128, 'artifact count limit')
        ref = dict(object_type='git-blob' if path else 'git-commit-object',repository=repo,commit=commit)
        if path:ref['path'] = path
        directory = self.source.repository(ref)
        obj = commit+':'+path if path else commit
        size = int(self.source.git(directory,'cat-file','-s',obj))
        require(0 <= size <= 16*1024*1024, 'artifact size limit')
        # Source.read checks ancestor modes, exact sizes, object types and OIDs.
        raw = self.source.git(directory,'cat-file','blob' if path else 'commit',obj)
        ref.update(size=size,sha256=digest(raw))
        require(self.source.read(ref) == raw, 'preparation retrieval mismatch')
        if expected:require(expected == 'sha256:'+digest(raw), 'declared digest mismatch')
        fmt='git-commit-object' if path is None else 'text'
        data=None
        if path:
            try:data=parse(raw)
            except json.JSONDecodeError:pass
            if data is not None:
                if isinstance(data,dict) and data.get('document_type')=='knowledge_candidates':fmt='knowledge-candidates-v1'
                elif isinstance(data,dict) and 'task_id' in data:fmt='handoff-v2'
                else:fmt='json'
        item=dict(reference=ref,format=fmt,representation='original',
                  public_classification=self.classification,source_alias='PUBLIC-FIXED-SOURCE')
        self.items[key]=item;self.raw[key]=raw;self.manifest['artifacts'].append(item)
        require(sum(len(v) for v in self.raw.values()) <= 64*1024*1024, 'bundle size limit')
        if fmt=='handoff-v2':self.pending.append((item,data))
        return item

    def dependency(self, owner, locator, revision, commit=False):
        if locator.startswith('https://'):
            repo, sha, path = fixed_url(locator,'commit' if commit else 'blob')
        else:
            require(not commit,'commit needs fixed URL');safe_path(locator)
            ref=owner['reference'];repo,sha=ref['repository'],ref['commit']
            path=str(PurePosixPath(ref['path']).parent/locator)
        if commit:require(revision==sha,'commit revision mismatch')
        return self.add(repo,sha,path,None if commit else revision)

    def finish(self):
        while self.pending:
            owner,data=self.pending.pop(0)
            for a in data['artifacts']:
                target=self.dependency(owner,a['locator'],a['revision'],a['kind']=='commit')
                self.slot(owner,artifact_slot(a),a['locator'],a['revision'],target)
                if target['format']=='knowledge-candidates-v1':self.candidates(owner,a,target)
            for u in data['upstream']:
                target=self.dependency(owner,u['handoff_locator'],u['revision'])
                self.slot(owner,upstream_slot(u),u['handoff_locator'],u['revision'],target)
        schema('artifact-delivery',self.manifest)
        return self.manifest

    def slot(self, owner, slot, locator, revision, target):
        self.manifest['slot_bindings'].append(dict(owner=deepcopy(owner['reference']),slot=slot,
             locator=locator,revision=revision,target={k:deepcopy(target[k]) for k in ('reference','format')}))

    def candidates(self, producer, artifact, owner):
        data=parse(self.raw[reference_key(owner['reference'])]);schema('knowledge-candidates-v1',data)
        binding=dict(profile='knowledge-candidates-v1',owner=deepcopy(owner['reference']),
                     producer=deepcopy(producer['reference']),producer_artifact_id=artifact['id'],
                     candidate_ids=[c['id'] for c in data['candidates']],sources=[])
        for c in data['candidates']:
            parts = c['source'].split('/')
            require(len(parts) > 5 and parts[5] in ('blob', 'tree'),
                    'canonical fixed Git source URL required')
            kind = parts[5]
            repo,commit,path=fixed_url(c['source'],kind)
            if kind=='blob':target=dict(kind=kind,reference=self.add(repo,commit,path)['reference'])
            else:
                snap,_=snapshot_tree(self.source,dict(repository=repo,commit=commit,path=path))
                target=dict(kind=kind,snapshot=snap)
            binding['sources'].append(dict(candidate_id=c['id'],source=c['source'],target=target))
        self.manifest['candidate_bindings'].append(binding)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository',required=True);parser.add_argument('--commit',required=True)
    parser.add_argument('--handoff-path',required=True);parser.add_argument('--handoff-sha256',required=True)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    require(not args.output.exists(),'output already exists')
    with tempfile.TemporaryDirectory(prefix='prepare-crossref-') as temp:
        prep=Preparation(GitSource(temp))
        prep.add(args.repository,args.commit,args.handoff_path,'sha256:'+args.handoff_sha256)
        manifest=prep.finish();raw=encode(manifest)
    publication=dict(schema_version='1.2',document_type='publication_receipt',manifest_sha256=digest(raw),
                     github_state='published',artifacts=manifest['artifacts'],
                     observation='Fixed public Git bytes retrieved during record preparation. Candidate records only; no Consumer approval or success, no source truth or product acceptance.')
    schema('publication-receipt',publication)
    args.output.mkdir(mode=0o700,parents=True)
    (args.output/'manifest.json').write_bytes(raw)
    (args.output/'publication-receipt.json').write_bytes(encode(publication))
    for p in sorted(args.output.iterdir()):print(p.name,len(p.read_bytes()),digest(p.read_bytes()))
    print('Prepared record candidates only; obtain independent Manager authorization before CLI consumption.')


if __name__=='__main__':main()
