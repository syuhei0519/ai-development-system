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
