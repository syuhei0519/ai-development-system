"""Bounded Review checks: fixed public evidence and synthetic pre-record inputs.

No build, container, external API or registry effects. Original input files are
read-only; every mutation is confined to a fresh TemporaryDirectory.
"""
import argparse
import copy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import tempfile
from unittest.mock import patch


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    out = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(out)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--checkout', type=Path, required=True)
    ap.add_argument('--test-evidence', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    m = module('review_release', args.checkout/'ci/github/release.py')
    fixture = module('review_fixture', args.checkout/'ci/github/order-release_test.py')
    checks = []
    def refused(label, fn):
        try:
            fn()
        except (ValueError, KeyError, FileNotFoundError):
            checks.append(dict(case=label, result='refused'))
        else:
            raise AssertionError(label)
    def write(p, d):
        p.write_text(json.dumps(d))
    # Check the exact Test-published bytes, without reconstructing originals.
    for service, foreign in [('backend', 'order'), ('order', 'backend')]:
        with tempfile.TemporaryDirectory() as tmp:
            public = Path(tmp)
            names = ['image-scan.json', 'image-proof.json', 'sbom-proof.json', 'sbom.cdx.json']
            good = {}
            for name in names:
                raw = (args.test_evidence/(service+'-'+name)).read_bytes()
                (public/name).write_bytes(raw)
                good[name] = raw
            identity = m.load(public/'image-scan.json')['imageIdentity']
            m.check_image(identity, public)
            checks.append(dict(case=service+'/actual-public-positive', result='pass'))
            for variant in [('image-scan.json',), ('image-proof.json',), ('image-scan.json', 'image-proof.json')]:
                for name in variant:
                    (public/name).write_bytes((args.test_evidence/(foreign+'-'+name)).read_bytes())
                refused(service+'/actual-foreign-'+','.join(variant), lambda: m.check_image(identity, public))
                for name in variant:
                    (public/name).write_bytes(good[name])
            for field in ['runId', 'runAttempt']:
                for kind, value in [('float', float(identity[field])), ('str', str(identity[field])), ('bool', True), ('null', None)]:
                    scan = m.decode(good['image-scan.json'])
                    proof = m.decode(good['image-proof.json'])
                    scan['imageIdentity'][field] = value
                    proof['identity'] = scan['imageIdentity']
                    write(public/'image-scan.json', scan)
                    proof['imageScanSha256'] = m.sha((public/'image-scan.json').read_bytes())
                    write(public/'image-proof.json', proof)
                    refused(service+'/actual-summary-proof-'+field+'-'+kind, lambda: m.check_image(identity, public))
                    for name in ['image-scan.json', 'image-proof.json']:
                        (public/name).write_bytes(good[name])
            # Rehashed foreign summary AND foreign identity still cannot match selected OCI identity.
            scan = m.decode((args.test_evidence/(foreign+'-image-scan.json')).read_bytes())
            proof = m.decode(good['image-proof.json'])
            write(public/'image-scan.json', scan)
            proof.update(identity=scan['imageIdentity'], rawScanSha256=scan['rawScanSha256'], imageScanSha256=m.sha((public/'image-scan.json').read_bytes()))
            write(public/'image-proof.json', proof)
            refused(service+'/actual-foreign-summary-rehashed-proof', lambda: m.check_image(identity, public))
    # Execute real record() in the existing bounded synthetic OCI fixture.
    fx = fixture.Interop()
    fx.setUp()
    try:
        source = Path('.validation/source-identity.json')
        original = source.read_bytes()
        for field in ['runId', 'runAttempt']:
            for kind, value in [('float', float(json.loads(original)[field])), ('str', str(json.loads(original)[field])), ('bool', True), ('null', None)]:
                doc = json.loads(original)
                doc[field] = value
                write(source, doc)
                Path('.security/public/release-record.json').unlink(missing_ok=True)
                refused('synthetic/pre-record-source-'+field+'-'+kind, fixture.p.record)
                assert not Path('.security/public/release-record.json').exists()
                source.write_bytes(original)
        fixture.p.record()
        checks.append(dict(case='synthetic/restored-record-positive', result='pass'))
    finally:
        fx.doCleanups()
    args.output.write_text(json.dumps(dict(document_type='bounded_review_probe', checks=checks, total=len(checks), external_operations=False, rebuild=False), indent=2)+'\n')
    print('PASS:', len(checks), 'bounded checks; actual public evidence and synthetic pre-record boundaries')


if __name__ == '__main__':
    main()
