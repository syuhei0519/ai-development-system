from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from completion_fixture import save, write, handoff, NOW
from preparation_completion_fixture import build_preparation
from scripts.validate_issue_completion import validate_files, instant


class PreparationCompletionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.a, self.c = build_preparation(self.root)

    def validate(self):
        save(self.root, self.a, self.c)
        return validate_files(self.root/'completion.json', self.root/'context.json',
            self.a['context_sha256'], self.root/'handoff.json', now=instant(NOW))

    def reject(self):
        with self.assertRaises((ValueError, OSError)):
            self.validate()

    def test_preparation_then_product_then_full_integration(self):
        self.assertEqual(self.validate(), ('ready','achieved'))
        self.assertEqual(self.c['required_prs'][0]['ac_ids'], [])
        ready = json.loads((self.root/'app-readiness.json').read_bytes())
        self.assertTrue(all(x['outcome']=='unverified' for x in ready['ac_results']))
        self.assertEqual(ready['issue_completion'], 'unverified')
        self.assertTrue(all('app' not in x['member_ids'] for x in self.c['required_verifications']))
        self.assertIn('app', [x['member_id'] for x in self.a['member_results']])

    def test_explicit_version_and_kind_required(self):
        for mode in ('old','mismatch','missing','standard','unknown','related_as_scope'):
            with self.subTest(mode=mode):
                self.a,self.c=build_preparation(self.root)
                r=self.c['required_prs'][0]
                if mode=='old': self.a['schema_version']=self.c['schema_version']='1.0'
                elif mode=='mismatch': self.a['schema_version']='1.0'
                elif mode=='missing': del r['pr_kind']
                elif mode=='standard': r.update(pr_kind='standard',preparation=None)
                elif mode=='unknown': r['pr_kind']='unknown'
                else: r['ac_ids']=r['preparation']['related_ac_ids']
                self.reject()

    def test_related_unknown_missing_changed_and_originals(self):
        for ids in ([], ['UNKNOWN'], ['SYNTHETIC-AC-1']):
            self.a,self.c=build_preparation(self.root)
            self.c['required_prs'][0]['preparation']['related_ac_ids']=ids
            self.reject()
        self.a,self.c=build_preparation(self.root)
        self.c['issue']['acceptance_criteria'][0]['verbatim']+=' changed'
        self.a['acceptance_criteria']=deepcopy(self.c['issue']['acceptance_criteria'])
        self.reject()

    def test_artifact_delivery_exact_set_root_digest(self):
        for mode in ('missing','extra','duplicate','wrong_id','root','digest','size','bytes'):
            with self.subTest(mode=mode):
                self.a,self.c=build_preparation(self.root)
                refs=self.c['required_prs'][0]['preparation']['artifact_refs']
                if mode=='missing': refs.clear()
                elif mode in ('extra','duplicate'):
                    refs.append(deepcopy(refs[0]))
                    if mode=='extra': refs[-1]['artifact_id']='extra'
                elif mode=='wrong_id': refs[0]['artifact_id']='other'
                elif mode=='root': refs[0]['ref']=write(self.root,'other.txt',(self.root/'preparation-artifact.txt').read_bytes())
                elif mode=='digest': refs[0]['ref']['sha256']='0'*64
                elif mode=='size': refs[0]['ref']['size']+=1
                else: (self.root/'preparation-artifact.txt').write_bytes(b'changed')
                self.reject()

    def test_preparation_cannot_measure_product(self):
        self.c['required_verifications'][0]['member_ids']=['app']
        self.reject()

    def test_required_preparation_must_merge_and_cannot_disappear(self):
        for mode in ('open','missing','vector','dependency'):
            self.a,self.c=build_preparation(self.root)
            if mode=='open': self.c['current_members'][0]['state']='open'
            elif mode=='missing': self.c['required_prs'].pop(0)
            elif mode=='vector': self.c['current_members'][0]['merge_sha']=None
            else: self.c['current_members'][0]['merged_at']='2030-01-02T12:00:00Z'
            self.reject()

    def test_product_measurement_missing_failed_fake_stage_deploy(self):
        for mode in ('unmeasured','failed','phase','deployment'):
            self.a,self.c=build_preparation(self.root)
            if mode in ('unmeasured','failed'):
                self.a['verification_results'][-1]['outcome']='unverified' if mode=='unmeasured' else 'not_met'
            elif mode=='phase': self.c['required_verifications'][-1]['phase']='premerge'
            else: self.c['current_deployments'][0]['state']='failed'
            self.reject()

    def test_historical_protection_expiry_and_none_boundary(self):
        for mode in ('expiry','gate','impact','kind'):
            self.a,self.c=build_preparation(self.root)
            d=json.loads((self.root/'app-readiness.json').read_bytes())
            rc=json.loads((self.root/'app-context.json').read_bytes())
            if mode=='expiry': rc['policy_valid_until']='2030-01-01T13:00:00Z'
            elif mode=='gate': d['merge_readiness']['checks']['github_ruleset']['verdict']='fail'
            elif mode=='impact': d['deployment_effect']=rc['deployment_effect']='automatic'
            else: self.c['required_prs'][0].update(pr_kind='standard',preparation=None,ac_ids=['SYNTHETIC-AC-1'])
            rr=write(self.root,'app-readiness.json',d);rr['id']=d['artifact_id']
            self.a['member_results'][0].update(readiness_ref={**rr,'id':'app-readiness'},
                readiness_context_ref=write(self.root,'app-context.json',rc),
                readiness_handoff_ref=write(self.root,'app-handoff.json',handoff(self.c['issue'],rr)))
            self.reject()

    def test_standard_v11_and_legacy_schema(self):
        from completion_fixture import build
        from scripts.validate_issue_completion import ASSESSMENT, CONTEXT
        self.a,self.c=build(self.root)
        self.assertTrue(ASSESSMENT.is_valid(self.a)); self.assertTrue(CONTEXT.is_valid(self.c))
        self.a['schema_version']=self.c['schema_version']='1.1'
        for r in self.c['required_prs']: r.update(pr_kind='standard',preparation=None)
        self.assertTrue(ASSESSMENT.is_valid(self.a)); self.assertTrue(CONTEXT.is_valid(self.c))
        self.assertEqual(self.validate(),('ready','achieved'))
        self.a['schema_version']=self.c['schema_version']='1.0'
        self.assertFalse(ASSESSMENT.is_valid(self.a)); self.assertFalse(CONTEXT.is_valid(self.c))

    def test_only_preparation_cannot_achieve(self):
        for r in self.c['required_prs']:
            r.update(pr_kind='preparation',ac_ids=[],preparation=deepcopy(self.c['required_prs'][0]['preparation']))
        self.reject()

    def test_nested_delivery_and_nonregular_artifact(self):
        import os
        r=self.a['member_results'][0]
        folder=self.root/'nested';folder.mkdir()
        for field in ('readiness_ref','readiness_context_ref','readiness_handoff_ref'):
            ref=r[field]; name=ref['locator']; (self.root/name).rename(folder/name)
            ref['locator']='nested/'+name
        ref=self.c['required_prs'][0]['preparation']['artifact_refs'][0]['ref']
        name=ref['locator'];(self.root/name).rename(folder/name);ref['locator']='nested/'+name
        self.assertEqual(self.validate(),('ready','achieved'))
        (folder/name).unlink();os.mkfifo(folder/name)
        self.reject()
