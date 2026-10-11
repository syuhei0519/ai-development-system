#!/usr/bin/env python3
"""Offline sample/schema consistency only; never report remote publication or approval."""
import sys
from jsonschema import Draft202012Validator
try:
    from .consume_delivery import ROOT, parse, schema, digest, require
except ImportError:
    from consume_delivery import ROOT, parse, schema, digest, require


def main():
    try:
        for name in ('artifact-delivery','delivery-authorization','publication-receipt','consumption-receipt'):
            Draft202012Validator.check_schema(parse((ROOT/f'contracts/{name}.schema.json').read_bytes()))
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
        print('PASS: delivery schemas and sample bindings only; no live approval certified')
        return 0
    except (OSError,ValueError):
        print('FAIL: delivery sample contracts',file=sys.stderr)
        return 1


if __name__=='__main__':
    sys.exit(main())
