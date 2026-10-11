#!/usr/bin/env python3
"""Write synthetic immutable candidates/Handoff referring to already-fixed sources.

Publish these synthetic files only through an authorized feature branch. Then use
prepare_crossref_bundle.py with their *new* fixed commit. No authorization created.
"""
import argparse
from pathlib import Path
try:
    from .consume_delivery import ROOT, parse, digest, require, schema
    from .prepare_crossref_bundle import encode, fixed_url
except ImportError:
    from consume_delivery import ROOT, parse, digest, require, schema
    from prepare_crossref_bundle import encode, fixed_url


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repository',required=True);p.add_argument('--source-commit',required=True)
    p.add_argument('--output',required=True,type=Path);args=p.parse_args()
    base=f'https://github.com/{args.repository}'
    commit_url=base+'/commit/'+args.source_commit;fixed_url(commit_url,'commit')
    prefix='examples/crossref-delivery/sources'
    candidates=dict(document_type='knowledge_candidates',publication_status='pending_manager_review',candidates=[])
    for cid,kind,path in [('SYNTHETIC-BLOB','blob',prefix+'/blob.txt'),('SYNTHETIC-TREE','tree',prefix)]:
        candidates['candidates'].append(dict(id=cid,domain='synthetic-transport',
            summary='Synthetic transport fixture with deliberately longer candidate summary; no actual knowledge adoption.',
            evidence='Synthetic fixed Git source data only.',source=f'{base}/{kind}/{args.source_commit}/{path}',
            scope='System transport self-verification only.'))
    schema('knowledge-candidates-v1',candidates)
    raw=encode(candidates)
    h=parse((ROOT/'examples/research-to-test/research.handoff.json').read_bytes())
    h.update(task_id='SYNTHETIC-CROSSREF-PRODUCER',role='implementation',summary='Synthetic sample; transport self-verification only.')
    old_id=h['artifacts'][0]['id']
    h['artifacts']=[dict(id=old_id,kind='knowledge',locator='candidates.json',revision='sha256:'+digest(raw),summary='Synthetic candidates.'),
                    dict(id='SYNTHETIC-COMMIT',kind='commit',locator=commit_url,revision=args.source_commit,summary='Commit existence only.')]
    h['knowledge_candidates']=[dict(id=c['id'],domain=c['domain'],summary='Short synthetic summary.',
        evidence_ids=[h['evidence'][0]['id']],raw_locator='candidates.json',publication_safety='safe_synthetic') for c in candidates['candidates']]
    h['evidence'][0].update(locator='candidates.json',observation='Synthetic sample; not an actual product result.')
    require(not args.output.exists(),'output exists');args.output.mkdir(parents=True)
    (args.output/'candidates.json').write_bytes(raw);(args.output/'handoff.json').write_bytes(encode(h))
    print('Synthetic candidate files written; no approval or delivery success claimed.')


if __name__=='__main__':main()
