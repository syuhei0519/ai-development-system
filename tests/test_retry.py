"""Synthetic immutable retry history and renewal regressions."""
from copy import deepcopy
import json
import unittest
from scripts.consume_delivery import digest
from scripts.validate_retry import LIMITS, transition


def raw(d):return json.dumps(d,sort_keys=True).encode()
def ledger():return {'version':'1.0','scope':'SYNTHETIC-B1','epochs':[{'id':1,'limits':dict(LIMITS),'events':[],'terminal':'open','grant_sha256':None}]}
def event(kind='execution',result='failed'):return {'kind':kind,'result':result,'evidence':'SYNTHETIC-OBSERVATION'}
def step(a,b,**kw):return transition(raw(a),raw(b),digest(raw(a)),**kw)


class RetryTests(unittest.TestCase):
    def test_each_budget_is_three_including_initial_attempt(self):
        for kind in LIMITS:
            a=ledger()
            for i in range(3):
                b=deepcopy(a);b['epochs'][0]['events'].append(event(kind))
                if i==2:b['epochs'][0]['terminal']='RETRY_LIMIT_REACHED'
                step(a,b);a=b
            b=deepcopy(a);b['epochs'][0]['events'].append(event(kind))
            with self.assertRaises(ValueError):step(a,b)

    def test_dispatch_execution_delivery_are_separate(self):
        a=ledger()
        for kind in ('dispatch','dispatch','execution','delivery','delivery','execution'):
            b=deepcopy(a);b['epochs'][0]['events'].append(event(kind));step(a,b);a=b
        self.assertEqual(len(a['epochs'][0]['events']),6)

    def exhausted(self):
        a=ledger();a['epochs'][0]['events']=[event() for _ in range(3)];a['epochs'][0]['terminal']='RETRY_LIMIT_REACHED';return a

    def test_no_reclassification_reset_relabel_or_delivery_bypass(self):
        a=self.exhausted()
        for mutate in (lambda b:b['epochs'][0].update(events=[]),lambda b:b.update(scope='new wording'),lambda b:b['epochs'][0]['events'][0].update(kind='dispatch'),lambda b:b['epochs'][0]['events'].append(event('delivery')),lambda b:b['epochs'][0].update(terminal='open')):
            b=deepcopy(a);mutate(b)
            with self.assertRaises(ValueError):step(a,b)

    def renewal(self):
        a=self.exhausted();g={'approval':'approved','authority':'SYNTHETIC-MANAGER','reason':'corrected transport','scope':a['scope'],'prior_history_sha256':digest(raw(a)),'new_epoch':2,'limits':dict(LIMITS),'relationship':'Additional authorized budget; original three attempts remain exhausted.'}
        b=deepcopy(a);b['epochs'].append({'id':2,'limits':dict(LIMITS),'events':[],'terminal':'open','grant_sha256':digest(raw(g))});return a,b,g

    def test_explicit_renewal_preserves_old_terminal_history(self):
        a,b,g=self.renewal();step(a,b,grant_raw=raw(g),grant_sha256=digest(raw(g)))
        self.assertEqual(b['epochs'][0],a['epochs'][0])
        c=deepcopy(b);c['epochs'][-1]['events'].append(event());step(b,c)

    def test_renewal_needs_every_field_and_independent_pin(self):
        a,b,g=self.renewal()
        with self.assertRaises(ValueError):step(a,b)
        with self.assertRaises(ValueError):step(a,b,grant_raw=raw(g),grant_sha256='0'*64)
        for key in g:
            changed=deepcopy(g);del changed[key]
            with self.subTest(key=key),self.assertRaises(ValueError):step(a,b,grant_raw=raw(changed),grant_sha256=digest(raw(changed)))
        for key,value in [('limits',dict(LIMITS,execution=4)),('scope','other'),('prior_history_sha256','0'*64),('approval','pending'),('reason','')]:
            changed=deepcopy(g);changed[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):step(a,b,grant_raw=raw(changed),grant_sha256=digest(raw(changed)))

    def test_trusted_previous_and_no_future_history_mutation(self):
        a=ledger();b=deepcopy(a);b['epochs'][0]['events'].append(event())
        with self.assertRaises(ValueError):transition(raw(a),raw(b),'0'*64)
        a,b,g=self.renewal();step(a,b,grant_raw=raw(g),grant_sha256=digest(raw(g)))
        c=deepcopy(b);c['epochs'][0]['events'][0]['kind']='dispatch';c['epochs'][1]['events'].append(event())
        with self.assertRaises(ValueError):step(b,c)

    def test_successful_third_attempt_does_not_permit_fourth(self):
        a=ledger()
        for _ in range(3):
            b=deepcopy(a);b['epochs'][0]['events'].append(event('dispatch','succeeded'));step(a,b);a=b
        b=deepcopy(a);b['epochs'][0]['events'].append(event('execution','succeeded'));step(a,b)
        c=deepcopy(b);c['epochs'][0]['events'].append(event('dispatch','succeeded'))
        with self.assertRaises(ValueError):step(b,c)


def successful_delivery_exhaustion():
    history = ledger()
    history['epochs'][0]['events'] = [event('dispatch', 'succeeded')] * 2 + [
        event('execution', 'succeeded'), event('delivery'), event('delivery'),
        event('delivery', 'succeeded')]
    return history


def bounded_renewal():
    original = successful_delivery_exhaustion()
    stopped = deepcopy(original)
    stopped['epochs'][-1]['terminal'] = 'RETRY_LIMIT_REACHED'
    grant = {'approval': 'approved', 'authority': 'SYNTHETIC-OWNER',
             'reason': 'Synthetic transport repair', 'scope': stopped['scope'],
             'prior_history_sha256': digest(raw(stopped)), 'new_epoch': 2,
             'limits': {'dispatch': 1, 'execution': 2, 'delivery': 2},
             'increments': {'dispatch': 0, 'execution': 0, 'delivery': 2},
             'explicit_owner_grant': True, 'expires_at': '9999-01-01T00:00:00Z',
             'relationship': 'Same synthetic repair; only two additional delivery slots.'}
    renewed = deepcopy(stopped)
    renewed['epochs'].append({'id': 2, 'limits': deepcopy(grant['limits']), 'events': [],
                              'terminal': 'open', 'grant_sha256': digest(raw(grant))})
    return original, stopped, renewed, grant


class BoundedRenewalTests(unittest.TestCase):
    def approve(self, stopped, renewed, grant):
        step(stopped, renewed, grant_raw=raw(grant), grant_sha256=digest(raw(grant)))

    def test_successful_exhaustion_stop_and_exact_renewal(self):
        original, stopped, renewed, grant = bounded_renewal()
        self.assertEqual(step(original, stopped), stopped)
        self.approve(stopped, renewed, grant)
        self.assertEqual(original['epochs'][0]['events'], stopped['epochs'][0]['events'])
        self.assertEqual(renewed['epochs'][:-1], stopped['epochs'])
        self.assertEqual(renewed['epochs'][-1]['limits'], {'dispatch': 1, 'execution': 2, 'delivery': 2})

    def test_stop_cannot_change_history_or_stop_nonexhausted_or_replay(self):
        original, stopped, renewed, grant = bounded_renewal()
        with self.assertRaises(ValueError): step(stopped, stopped)
        for mutate in (lambda h: h['epochs'][0]['events'].pop(),
                       lambda h: h['epochs'][0]['events'][0].update(result='failed'),
                       lambda h: h.update(scope='SYNTHETIC-OTHER')):
            changed = deepcopy(stopped); mutate(changed)
            with self.assertRaises(ValueError): step(original, changed)
        nonexhausted = ledger(); stop = deepcopy(nonexhausted)
        stop['epochs'][0]['terminal'] = 'RETRY_LIMIT_REACHED'
        with self.assertRaises(ValueError): step(nonexhausted, stop)
        with self.assertRaises(ValueError): self.approve(original, renewed, grant)
        self.approve(stopped, renewed, grant)
        with self.assertRaises(ValueError): self.approve(renewed, renewed, grant)
        replay = deepcopy(renewed); replay['epochs'].append(deepcopy(renewed['epochs'][-1]))
        replay['epochs'][-1]['id'] = 3
        with self.assertRaises(ValueError): self.approve(renewed, replay, grant)

    def test_grant_missing_stale_mismatched_expired_and_broader_budgets(self):
        _, stopped, renewed, grant = bounded_renewal()
        with self.assertRaises(ValueError): step(stopped, renewed)
        with self.assertRaises(ValueError):
            step(stopped, renewed, grant_raw=raw(grant), grant_sha256='0' * 64)
        changes = [('explicit_owner_grant', False), ('expires_at', '2000-01-01T00:00:00Z'),
                   ('expires_at', '9999-01-01'), ('prior_history_sha256', '0' * 64),
                   ('scope', 'SYNTHETIC-OTHER'), ('approval', 'pending'), ('new_epoch', 3),
                   ('limits', dict(grant['limits'], execution=3)),
                   ('limits', dict(grant['limits'], delivery=3)),
                   ('increments', dict(grant['increments'], execution=1)),
                   ('increments', dict(grant['increments'], dispatch=1)),
                   ('increments', dict(grant['increments'], delivery=True))]
        for key in grant:
            changed = deepcopy(grant); del changed[key]
            candidate = deepcopy(renewed); candidate['epochs'][-1]['grant_sha256'] = digest(raw(changed))
            with self.subTest(missing=key), self.assertRaises(ValueError): self.approve(stopped, candidate, changed)
        for key, value in changes:
            changed = deepcopy(grant); changed[key] = value
            candidate = deepcopy(renewed)
            candidate['epochs'][-1]['grant_sha256'] = digest(raw(changed))
            if key == 'limits': candidate['epochs'][-1]['limits'] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                self.approve(stopped, candidate, changed)
        changed = {k: v for k, v in grant.items() if k not in ('increments', 'expires_at', 'explicit_owner_grant')}
        candidate = deepcopy(renewed); candidate['epochs'][-1]['grant_sha256'] = digest(raw(changed))
        with self.assertRaises(ValueError): self.approve(stopped, candidate, changed)

    def test_zero_unrenewed_budget_stays_zero_and_unknown_admission_rejected(self):
        original, stopped, renewed, grant = bounded_renewal()
        for history in (original, stopped, renewed):
            history['epochs'][0]['events'].append(event('dispatch', 'succeeded'))
        grant['prior_history_sha256'] = digest(raw(stopped))
        grant['limits']['dispatch'] = renewed['epochs'][-1]['limits']['dispatch'] = 0
        renewed['epochs'][-1]['grant_sha256'] = digest(raw(grant))
        step(original, stopped); self.approve(stopped, renewed, grant)
        candidate = deepcopy(renewed); candidate['epochs'][-1]['events'].append(event('dispatch'))
        with self.assertRaises(ValueError): step(renewed, candidate)
        candidate = deepcopy(renewed); candidate['epochs'][-1]['events'].append(event('execution', 'unknown'))
        with self.assertRaises(ValueError): step(renewed, candidate)
