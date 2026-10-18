#!/usr/bin/env python3
"""Prepare a synthetic registry for an explicit fixed Git inbox commit. Grants no authority."""
import argparse
from pathlib import Path
try:
    from .knowledge_collector import ROOT, encode, parse, check_reference, validate
except ImportError:
    from knowledge_collector import ROOT, encode, parse, check_reference, validate


def registry(repository, commit):
    check_reference(dict(repository=repository, commit=commit, path='probe'))
    data = parse((ROOT / 'examples/collector/registry.template.json').read_bytes())
    data['sources'][0].update(repository=repository, commit=commit)
    validate('knowledge-source-registry', data)
    return data


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repository', required=True); p.add_argument('--commit', required=True)
    p.add_argument('--output', required=True, type=Path)
    args = p.parse_args()
    with args.output.open('xb') as stream:
        stream.write(encode(registry(args.repository, args.commit)))
