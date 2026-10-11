"""Review-owned synthetic probes; no publishing, authorization creation, or remote mutation.
Usage: python review_probes.py FIXED_HEAD_CHECKOUT OUTPUT.json
"""
import copy
import datetime
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(root))
from scripts import consume_delivery as c
from scripts.prepare_knowledge_fixture import fixture_manifest

def encode(data):
    return (json.dumps(data, ensure_ascii=False, separators=(',', ':')) + '\n').encode()

class Bundle:
    def __init__(self):
        self.m = fixture_manifest('example/repo', 'a' * 40)
        self.files = {self.key(a['reference']): (root / a['reference']['path']).read_bytes()
                      for a in self.m['artifacts']}
        self.policy = c.parse((root / 'examples/delivery/synthetic.authorization.json').read_bytes())
        self.policy.update(schema_version='1.1', allowed_representations=['original'])
        self.options = {}
        self.receipt_change = None
    def key(self, ref):
        return (ref['repository'], ref['commit'], ref['path'])
    def item(self, name):
        return next(a for a in self.m['artifacts'] if a['reference']['path'].endswith('/' + name))
    def data(self, name):
        return c.parse(self.files[self.key(self.item(name)['reference'])])
    def put(self, name, data):
        self.files[self.key(self.item(name)['reference'])] = encode(data)
    def read(self, ref):
        return self.files[self.key(ref)]
    def run(self):
        for a in self.m['artifacts']:
            ref = a['reference']; raw = self.files[self.key(ref)]
            ref.update(size=len(raw), sha256=c.digest(raw))
        mr = encode(self.m)
        pub = dict(schema_version='1.1', document_type='publication_receipt',
                   manifest_sha256=c.digest(mr), github_state='published',
                   artifacts=self.m['artifacts'], observation='Review synthetic transport probe')
        pr = encode(pub)
        self.policy.update(manifest_sha256=c.digest(mr), publication_receipt_sha256=c.digest(pr))
        policy = encode(self.policy)
        args = dict(manifest_raw=mr, publication_raw=pr, policy_raw=policy,
                    policy_sha256=c.digest(policy), consumer=self.policy['consumer'],
                    scope=self.policy['scope'], purpose=self.policy['purpose'], source=self,
                    now=datetime.datetime(2026, 10, 11, tzinfo=datetime.timezone.utc))
        if self.receipt_change:
            r, _ = c.consume(**args); self.receipt_change(r); args['receipt_raw'] = encode(r)
        args.update(self.options)
        return c.consume(**args)

results = []
def probe(name, mutate, expected='reject'):
    b = Bundle(); mutate(b)
    try:
        b.run(); actual = 'accept'; detail = 'accepted'
    except ValueError as exc:
        actual = 'reject'; detail = str(exc)
    except Exception as exc:
        actual = 'crash'; detail = type(exc).__name__
    results.append(dict(id=name, expected=expected, actual=actual, passed=expected == actual, detail=detail))

probe('control-complete', lambda b: None, 'accept')
for value in ['knowledge_future', 'knowledge', 'knowledge_context_v2', 'knowledge_input\u0000']:
    def unknown(b, value=value):
        b.item('context.json')['format'] = 'json'
        b.put('context.json', {'document_type': value})
    probe('reserved-discriminator-' + repr(value), unknown)
for kind in ['knowledge-input-v1', 'knowledge-handoff-v1', 'knowledge-context-v1']:
    for document in ['input.json', 'handoff.json', 'context.json']:
        if kind == 'knowledge-' + document.split('.')[0] + '-v1':
            continue
        probe('wrong-format-' + document + '-' + kind,
              lambda b, document=document, kind=kind: b.item(document).__setitem__('format', kind))

def partial_missing_source(b, state):
    d = b.data('handoff.json'); d.update(status=state, artifacts=[], evidence=[], decisions=[])
    if state == 'blocked':
        d['block_reasons'] = [dict(code='MISSING_INPUT', detail='Synthetic partial result', required_action='Supply source')]
    else:
        d['failure_reasons'] = ['Synthetic failure']
    b.put('handoff.json', d)
    b.m['artifacts'].remove(b.item('source-1.md'))
for state in ['blocked', 'failed']:
    probe('partial-' + state + '-still-requires-sources', lambda b, state=state: partial_missing_source(b, state))

def move_handoff(b, omit=False, corrupt=False):
    # Real tuple keys: unlike a path-only mock, these distinguish both snapshots.
    a = b.item('handoff.json'); old = b.key(a['reference'])
    a['reference'].update(repository='example/other', commit='b' * 40)
    b.files[b.key(a['reference'])] = b.files.pop(old)
    for original in list(b.m['artifacts']):
        if original['format'] != 'text':
            continue
        if omit and original['reference']['path'].endswith('source-1.md'):
            continue
        clone = copy.deepcopy(original); clone['reference'].update(repository='example/other', commit='b' * 40)
        raw = b.files[b.key(original['reference'])]
        if corrupt and original['reference']['path'].endswith('source-1.md'):
            raw += b'Synthetic conflicting snapshot\n'
        b.files[b.key(clone['reference'])] = raw; b.m['artifacts'].append(clone)
probe('distinct-snapshot-pair-with-complete-closure', lambda b: move_handoff(b), 'accept')
probe('distinct-snapshot-cannot-borrow-source-from-other-snapshot', lambda b: move_handoff(b, omit=True))
probe('distinct-snapshot-source-digest-mismatch', lambda b: move_handoff(b, corrupt=True))

for field, value in [('consumer', 'OTHER'), ('scope', 'OTHER'), ('purpose', 'implementation'),
                     ('authorization_sha256', '0' * 64), ('manifest_sha256', '0' * 64),
                     ('publication_receipt_sha256', '0' * 64), ('schema_version', '1.0'),
                     ('verification', 'full-raw-bytes-size-sha256-json-handoff-bindings')]:
    probe('forged-receipt-' + field,
          lambda b, field=field, value=value: setattr(b, 'receipt_change', lambda r: r.__setitem__(field, value)))
probe('forged-receipt-dropped-entry', lambda b: setattr(b, 'receipt_change', lambda r: r['artifacts'].pop()))
probe('representation-not-approved', lambda b: b.policy.__setitem__('allowed_representations', ['edited_derivative']))
probe('expiry-boundary-equal-now', lambda b: b.policy.__setitem__('valid_until', '2026-10-11T00:00:00Z'))
probe('expiry-missing-timezone', lambda b: b.policy.__setitem__('valid_until', '2026-10-12T00:00:00'))
probe('approval-purpose-mismatch', lambda b: b.options.__setitem__('purpose', 'implementation'))

def source_tamper(b):
    original_read = b.read
    b.read = lambda ref: original_read(ref) + (b'X' if ref['path'].endswith('source-1.md') else b'')
probe('transport-extra-byte-after-seal', source_tamper)
def missing_binding(b):
    b.m['knowledge_bindings'][0]['input'] = dict(b.item('input.json')['reference'], commit='c' * 40)
probe('binding-cannot-reference-undeclared-snapshot', missing_binding)

def candidate_boundary(b):
    d = c.parse((root / 'examples/research-to-test/research.handoff.json').read_bytes())
    d['artifacts'][0].update(locator='article.md', revision='sha256:' + c.digest(b.read(b.item('article.md')['reference'])))
    d['knowledge_candidates'] = [dict(id='SYNTHETIC-CANDIDATE', domain='review',
        summary='Synthetic characterization of an explicitly out-of-scope locator.',
        evidence_ids=[d['evidence'][0]['id']], raw_locator='not-in-bundle.md', publication_safety='safe_synthetic')]
    b.m['artifacts'] = [b.item('handoff.json'), b.item('article.md')]
    b.item('handoff.json')['format'] = 'handoff-v2'
    b.put('handoff.json', d); b.m['knowledge_bindings'] = []
probe('known-limit-knowledge-candidate-raw-locator-is-not-bound', candidate_boundary, 'accept')

out = dict(producer='knowledge-delivery-review-a1', synthetic=True,
           head='5345303db8c5208859ed741b98f119882de7a973',
           count=len(results), passed=sum(r['passed'] for r in results), results=results,
           limitation='In-memory synthetic transport with explicit resealing; real positive HTTPS Git verified separately.')
pathlib.Path(sys.argv[2]).write_bytes(encode(out))
print(json.dumps({k: v for k, v in out.items() if k != 'results'}))
for result in results:
    if not result['passed']:
        print(json.dumps(result))
sys.exit(0 if all(r['passed'] for r in results) else 1)
