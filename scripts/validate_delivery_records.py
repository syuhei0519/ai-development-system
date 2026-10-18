#!/usr/bin/env python3
"""Current schema and authored synthetic fixture checks; no historical success conversion."""
import sys
from jsonschema import Draft202012Validator
try:
    from .consume_delivery import ROOT, parse, schema, verify_handoffs
    from .prepare_knowledge_fixture import fixture_manifest
except ImportError:
    from consume_delivery import ROOT, parse, schema, verify_handoffs
    from prepare_knowledge_fixture import fixture_manifest


def main():
    try:
        for name in ('artifact-delivery','delivery-authorization','publication-receipt','consumption-receipt'):
            Draft202012Validator.check_schema(parse((ROOT/f'contracts/{name}.schema.json').read_bytes()))
        schema('delivery-authorization',parse((ROOT/'examples/delivery/current.authorization.json').read_bytes()))
        fixture=fixture_manifest('example/repo','a'*40)
        blobs={(a['reference']['repository'],a['reference']['commit'],a['reference']['path']):
               (ROOT/a['reference']['path']).read_bytes() for a in fixture['artifacts']}
        verify_handoffs(fixture['artifacts'],blobs,'1.3',fixture['knowledge_bindings'],fixture['slot_bindings'])
        print('PASS: current schemas and synthetic fixture; no live approval certified')
        return 0
    except (OSError,ValueError):
        print('FAIL: current delivery contracts',file=sys.stderr)
        return 1

if __name__=='__main__': sys.exit(main())
