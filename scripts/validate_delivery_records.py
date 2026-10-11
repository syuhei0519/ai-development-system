#!/usr/bin/env python3
"""Offline sample/schema consistency only; never report remote publication or approval."""
import sys
from jsonschema import Draft202012Validator
try:
    from .consume_delivery import ROOT, parse, schema, digest, require, verify_handoffs
    from .prepare_knowledge_fixture import fixture_manifest
except ImportError:
    from consume_delivery import ROOT, parse, schema, digest, require, verify_handoffs
    from prepare_knowledge_fixture import fixture_manifest


def main():
    try:
        for name in ('artifact-delivery','delivery-authorization','publication-receipt','consumption-receipt'):
            for suffix in ('', '-v1.1'):
                Draft202012Validator.check_schema(parse((ROOT/f'contracts/{name}{suffix}.schema.json').read_bytes()))
        for name in ('synthetic','research-public'):
            raw=(ROOT/f'examples/delivery/{name}.manifest.json').read_bytes()
            data=parse(raw);schema('artifact-delivery',data)
            pub=(ROOT/f'records/artifact-delivery/{name}.publication.json').read_bytes()
            publication=parse(pub);schema('publication-receipt',publication)
            require(publication['manifest_sha256']==digest(raw) and publication['artifacts']==data['artifacts'],
                    'publication sample binding mismatch')
            if name=='synthetic':
                for auth_name in ('synthetic','invalid-unapproved'):
                    auth=parse((ROOT/f'examples/delivery/{auth_name}.authorization.json').read_bytes())
                    schema('delivery-authorization',auth)
                    require(auth['manifest_sha256']==digest(raw) and auth['publication_receipt_sha256']==digest(pub),
                            'authorization sample binding mismatch')
        fixture = fixture_manifest('example/repo', 'a' * 40)
        blobs = {(a['reference']['repository'], a['reference']['commit'], a['reference']['path']):
                 (ROOT / a['reference']['path']).read_bytes() for a in fixture['artifacts']}
        verify_handoffs(fixture['artifacts'], blobs, '1.1', fixture['knowledge_bindings'])
        template = parse((ROOT / 'examples/knowledge-delivery/authorization.template.json').read_bytes())
        schema('delivery-authorization', template)
        require(template['consumer_use_approval'] == 'pending', 'template must not grant approval')
        print('PASS: delivery schemas and sample bindings only; no live approval certified')
        return 0
    except (OSError,ValueError):
        print('FAIL: delivery sample contracts',file=sys.stderr)
        return 1


if __name__=='__main__':
    sys.exit(main())
