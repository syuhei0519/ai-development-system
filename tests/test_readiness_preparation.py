"""Synthetic preparation contract regressions; no independent business verdict."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts.validate_readiness import validate, validate_handoff_pair
from test_readiness import fixture, NOW, ROOT, FIXTURES


class PreparationTests(unittest.TestCase):
    def setUp(self):
        self.data = fixture('preparation-ready.json')
        self.context = fixture('preparation-context.json')

    def errors(self, data=None, context=None, root=FIXTURES):
        return validate(data or self.data, context or self.context, NOW, artifact_root=root)

    def test_ready_retains_unverified_original_phases(self):
        self.assertEqual(self.errors(), [])
        self.assertEqual(self.data['acceptance_criteria'], fixture()['acceptance_criteria'])
        self.assertTrue(all(r['outcome'] == 'unverified' for r in self.data['ac_results']))
        self.assertEqual(self.data['issue_completion'], 'unverified')

    def test_standard_empty_rejected_both_versions(self):
        for version in ('1.0', '1.1'):
            d,c=fixture(),fixture('context.json')
            for x in (d,c):
                x.update(schema_version=version,pr_ac_ids=[])
                if version=='1.1': x.update(pr_kind='standard',preparation=None)
            self.assertTrue(self.errors(d,c))
            d['pr_ac_ids']=c['pr_ac_ids']=fixture()['pr_ac_ids']
            self.assertEqual(self.errors(d,c), [])

    def test_each_preparation_field_required(self):
        for field in self.data['preparation']:
            d=deepcopy(self.data);del d['preparation'][field]
            self.assertTrue(self.errors(d), field)
        for field in self.data['preparation']['followup'][0]:
            d,c=deepcopy(self.data),deepcopy(self.context)
            for x in (d,c): del x['preparation']['followup'][0][field]
            self.assertTrue(self.errors(d,c), field)

    def test_conditions_empty_unmeasured_failed_duplicate_unknown(self):
        for mutate in (
            lambda d: d.update(preparation_results=[]),
            lambda d: d['preparation_results'][0].update(evidence_ids=[]),
            lambda d: d['preparation_results'][0].update(outcome='unverified'),
            lambda d: d['preparation_results'][0].update(outcome='not_met'),
            lambda d: d['preparation_results'][0].update(condition_id='UNKNOWN'),
            lambda d: d['preparation_results'].append(deepcopy(d['preparation_results'][0])),
            lambda d: d['preparation_results'][0].update(evidence_ids=['measurement']),
        ):
            d=deepcopy(self.data);mutate(d);self.assertTrue(self.errors(d))

    def test_context_mismatch_and_unknown_ac(self):
        for mutate in (
            lambda c: c.update(pr_kind='standard'),
            lambda c: c['preparation'].update(scope_reason='changed'),
            lambda c: c['preparation']['conditions'][0].update(verbatim='changed'),
            lambda c: c['acceptance_criteria'][0].update(verification_phase='postdeploy'),
        ):
            c=deepcopy(self.context);mutate(c);self.assertTrue(self.errors(context=c))
        self.data['preparation']['related_ac_ids']=['UNKNOWN']
        self.context['preparation']=deepcopy(self.data['preparation'])
        self.assertTrue(self.errors())

    def test_none_aggregate_only_and_old_consumer_rejects(self):
        for field,values in [('deployment_effect',['automatic','unknown']),('issue_integration_scope',['single_pr','unknown']),('schema_version',['1.0'])]:
            for value in values:
                d,c=deepcopy(self.data),deepcopy(self.context)
                d[field]=c[field]=value
                self.assertTrue(self.errors(d,c), (field,value))

    def test_all_existing_gates_still_block(self):
        for kind in self.data['merge_readiness']['checks']:
            d=deepcopy(self.data);d['merge_readiness']['checks'][kind]['verdict']='fail'
            self.assertTrue(self.errors(d),kind)
        for kind in ('independent_test','ai_review'):
            for change in ({'producer':self.data['implementation_actor']},{'independent':False},{'artifact_ids':['unknown']},{'condition_ids':['unknown']}):
                d=deepcopy(self.data); next(e for e in d['evidence'] if e['kind']==kind).update(change)
                self.assertTrue(self.errors(d))
            d=deepcopy(self.data);d['merge_readiness']['checks'][kind]['evidence_ids']=[]
            self.assertTrue(self.errors(d))

    def test_product_failure_anywhere_blocks_and_cannot_hide(self):
        self.data['ac_results'][0].update(outcome='not_met',evidence_ids=['measurement'])
        self.data['issue_completion']='not_achieved'
        self.assertTrue(self.errors())  # context snapshot refuses changed outcome
        self.data['preparation']['product_outcomes'][0]['outcome']='not_met'
        self.context['preparation']=deepcopy(self.data['preparation'])
        self.assertTrue(self.errors())  # cannot claim ready
        self.data['merge_readiness']['status']='blocked'
        self.assertEqual(self.errors(), [])
        self.data['ac_results'][0].update(outcome='unverified',evidence_ids=[])
        self.assertTrue(self.errors())

    def test_premerge_deferral_and_premature_achieved_rejected(self):
        self.data['ac_results'][0]['deferred']=fixture()['ac_results'][1]['deferred']
        self.assertTrue(self.errors())
        self.data=fixture('preparation-ready.json');self.data['issue_completion']='achieved'
        self.assertTrue(self.errors())

    def test_expired_subject_and_artifact_bytes(self):
        d=deepcopy(self.data);d['evidence'][-1]['valid_until']='2030-01-01T12:00:00Z'
        self.assertTrue(self.errors(d))
        c=deepcopy(self.context);c['policy_valid_until']='2030-01-01T12:00:00Z'
        self.assertTrue(self.errors(context=c))
        for field in ('head_sha','base_sha','target_revision','config_revision'):
            c=deepcopy(self.context);c['subject'][field]='f'*40
            self.assertTrue(self.errors(context=c))
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'preparation-artifact.txt';p.write_bytes((FIXTURES/p.name).read_bytes()+b'changed')
            self.assertTrue(self.errors(root=tmp));p.unlink();self.assertTrue(self.errors(root=tmp))
        for field,value in [('sha256','0'*64),('size_bytes',1),('revision','f'*40),('locator','../README.md')]:
            d,c=deepcopy(self.data),deepcopy(self.context)
            for x in (d,c): x['preparation']['artifacts'][0][field]=value
            self.assertTrue(self.errors(d,c))

    def test_cli_context_pin_required_and_verified(self):
        cmd=[sys.executable,str(ROOT/'scripts/validate_readiness.py'),str(FIXTURES/'preparation-ready.json'),'--context',str(FIXTURES/'preparation-context.json'),'--at',NOW.isoformat()]
        pin=hashlib.sha256((FIXTURES/'preparation-context.json').read_bytes()).hexdigest()
        for extra,code in [([],1),(['--context-sha256','0'*64],1),(['--context-sha256',pin],0)]:
            r=subprocess.run(cmd+extra,capture_output=True,text=True,cwd=ROOT.parent)
            self.assertEqual(r.returncode,code,r.stderr)

    def test_handoff_binding_applies_to_preparation(self):
        h=fixture('manager.handoff.json');h.pop('final_assessment',None)
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'readiness.json';p.write_text(json.dumps(self.data));b=p.read_bytes()
            a=next(a for a in h['artifacts'] if a['id']==self.data['artifact_id'])
            a.update(locator=p.name,revision='sha256:'+hashlib.sha256(b).hexdigest())
            args=dict(readiness_bytes=b,readiness_path=p,handoff_path=Path(tmp)/'handoff.json')
            self.assertEqual(validate_handoff_pair(self.data,h,**args),[])
            p.write_bytes(b+b'\n');self.assertTrue(validate_handoff_pair(self.data,h,**args))
