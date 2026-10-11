import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from completion_fixture import build, save, write, proof, NOW, SAMPLE, encode
from scripts.validate_issue_completion import validate_files, instant, sha, ASSESSMENT, CONTEXT


class CompletionTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.a,self.c=build(self.root)

    def validate(self, **kwargs):
        return validate_files(self.root/'completion.json',self.root/'context.json',self.a['context_sha256'],self.root/'handoff.json',now=instant(NOW),**kwargs)

    def save(self):
        save(self.root,self.a,self.c)

    def reject(self, pattern=None):
        with self.assertRaisesRegex(ValueError,pattern or '.'):
            self.validate()

    def test_synthetic_achieved_three_repos_and_expired_historical_gates(self):
        self.assertEqual(self.validate(),('ready','achieved'))

    def test_same_repo_multiple_prs_squash(self):
        self.a,self.c=build(self.root,same_repo=True)
        self.assertEqual(self.validate(),('ready','achieved'))

    def test_queue_distinct_head_target_result(self):
        self.a,self.c=build(self.root,queue=True)
        self.assertEqual(self.validate(),('ready','achieved'))

    def test_merge_and_rebase_methods(self):
        for method in ('merge','rebase'):
            with self.subTest(method=method):
                for e in self.a['evidence']:
                    if e['merge']: e['merge']['method']=method
                self.save(); self.assertEqual(self.validate(),('ready','achieved'))

    def test_honest_unmerged_unmeasured(self):
        self.a,self.c=build(self.root,pending=True)
        self.assertEqual(self.validate(),('blocked','unverified'))

    def test_missing_extra_duplicate_collections(self):
        for target,field in [('a','member_results'),('a','deployment_results'),('a','verification_results'),('a','ac_results'),('c','current_members'),('c','current_deployments'),('c','required_prs'),('c','required_verifications')]:
            for mode in ('missing','duplicate','extra'):
                with self.subTest(target=target,field=field,mode=mode):
                    self.a,self.c=build(self.root)
                    values=(self.a if target=='a' else self.c)[field]
                    if mode=='missing': values.pop()
                    else:
                        x=copy.deepcopy(values[0]); values.append(x)
                        if mode=='extra': x[next(k for k in x if k.endswith('_id'))]='unexpected'
                    self.save(); self.reject()

    def test_dependency_unknown_self_cycle(self):
        for deps in (['unknown'],['app'],['client']):
            with self.subTest(deps=deps):
                self.a,self.c=build(self.root)
                self.c['required_prs'][0]['depends_on']=deps
                self.save(); self.reject('dependency')

    def test_head_base_target_config_group_changes(self):
        for field,value in [('head_sha','9'*40),('base_sha','9'*40),('target_revision','9'*40),('config_revision','new-policy'),('merge_group_sha','9'*40)]:
            with self.subTest(field=field):
                self.a,self.c=build(self.root)
                self.c['current_members'][0][field]=value
                self.save(); self.reject()

    def test_merge_result_and_head_are_not_interchangeable(self):
        self.a['member_results'][0]['actual_merge_sha']=self.c['current_members'][0]['head_sha']
        self.save(); self.reject('stale')

    def test_missing_merge_correspondence(self):
        self.a['member_results'][0]['merge_binding']=proof(verdict='pending')
        self.save(); self.reject('required_merges')

    def test_merge_source_metadata_forgery(self):
        ref=self.a['evidence'][0]['source_ref']
        fake=dict(document_type='consumption_receipt',authority_granted=False)
        self.a['evidence'][0]['source_ref']=write(self.root,ref['locator'],fake)
        write(self.root,'completion.json',self.a)
        self.reject('source observation')

    def test_measurement_identity_phase_method_producer_environment(self):
        for field,value in [('kind','compatibility'),('phase','postmerge'),('verification_ids',['runtime-response']),('ac_ids',['SYNTHETIC-AC-1']),('producer','imposter'),('environment_id','elsewhere'),('workload_id','elsewhere'),('method','CI'),('expected_result','anything')]:
            with self.subTest(field=field):
                self.a,self.c=build(self.root)
                e=self.a['evidence'][-1]; e[field]=value
                self.save(); self.reject()

    def test_measurement_before_deployment(self):
        self.a['evidence'][-1]['observed_at']='2030-01-01T14:00:00Z'
        self.save(); self.reject('predates deployment')

    def test_full_vector_missing_duplicate_or_stale(self):
        for field in ('merged_members','deployments'):
            for mode in ('missing','duplicate','stale'):
                with self.subTest(field=field,mode=mode):
                    self.a,self.c=build(self.root)
                    e=self.a['evidence'][-1]; values=e['binding'][field]
                    if mode=='missing': values.pop()
                    elif mode=='duplicate': values.append(copy.deepcopy(values[0]))
                    elif field=='merged_members': values[0]['merge_sha']='9'*40
                    else: values[0]['images'][0]['digest']='sha256:'+'9'*64
                    # Do not regenerate binding; update structured source only.
                    e['source_ref']=write(self.root,e['source_ref']['locator'],dict(document_type='issue_completion_observation',schema_version='1.0',observation={k:v for k,v in e.items() if k!='source_ref'}))
                    write(self.root,'completion.json',self.a); self.reject()

    def test_deployment_wrong_source_digest_config_environment_workload(self):
        for field in ('sources','images','config_sha256','environment_id','workload_id','state'):
            with self.subTest(field=field):
                self.a,self.c=build(self.root)
                actual=self.c['current_deployments'][0]
                if field=='sources': actual[field]=actual[field][1:]
                elif field=='images': actual[field]=[dict(component='synthetic-app',digest='sha256:'+'9'*64)]
                else: actual[field]={'config_sha256':'9'*64,'environment_id':'other','workload_id':'other','state':'pending'}[field]
                self.save(); self.reject()

    def test_unknown_deployment_definition(self):
        self.c['required_deployments'][0]['definition_state']='unknown'
        self.save(); self.reject('deployment status')

    def test_approval_scope_actor_action_and_kind(self):
        for field,value in [('status','revoked'),('member_ids',['app']),('deployment_ids',[]),('actor','other'),('allowed_actions',['implement']),('decision_kind','delivery')]:
            with self.subTest(field=field):
                self.a,self.c=build(self.root)
                self.c['scope_decisions'][1][field]=value
                self.save(); self.reject()

    def test_scope_approval_requires_complete_set(self):
        self.c['scope_decisions'][0]['member_ids']=['app']
        self.save(); self.reject('scope')

    def test_unknown_scope_not_ready(self):
        self.c['issue_integration_scope']='unknown'
        self.save(); self.reject('scope')

    def test_original_ac_text_and_source(self):
        for field in ('verbatim','source'):
            with self.subTest(field=field):
                self.a,self.c=build(self.root)
                self.a['acceptance_criteria']=copy.deepcopy(self.a['acceptance_criteria'])
                self.a['acceptance_criteria'][0][field]+=' changed'
                self.save(); self.reject('AC/scope')

    def test_one_subcheck_unverified_cannot_be_met(self):
        self.a['verification_results'][-1].update(outcome='unverified',evidence_ids=[])
        self.a['evidence'].pop()
        self.save(); self.reject()

    def test_expiry_boundary_future_context_approval_evidence(self):
        for where in ('context','approval','evidence','member','deployment'):
            for field,value in [('valid_until',NOW),('observed_at','2030-01-03T13:00:00Z')]:
                with self.subTest(where=where,field=field):
                    self.a,self.c=build(self.root)
                    item={'context':self.c,'approval':self.c['scope_decisions'][0],'evidence':self.a['evidence'][0],'member':self.c['current_members'][0],'deployment':self.c['current_deployments'][0]}[where]
                    item[field]=value
                    self.save(); self.reject('expired')

    def test_historical_gate_expired_at_merge(self):
        self.c['current_members'][0]['merged_at']='2030-01-02T09:00:00Z'
        self.a['member_results'][0]['merged_at']='2030-01-02T09:00:00Z'
        self.save(); self.reject('historical Readiness')

    def test_integration_pending_all_ac_met_has_no_final(self):
        self.a['integration_readiness']['checks']['compatibility']=proof(verdict='pending')
        self.a['integration_readiness']['status']='blocked'; self.a['issue_completion']='unverified'
        self.save(); self.assertEqual(self.validate(),('blocked','unverified'))
        self.assertNotIn('final_assessment',json.loads((self.root/'handoff.json').read_bytes()))

    def test_integration_failure_all_ac_met(self):
        e=next(e for e in self.a['evidence'] if e['id']=='compatibility'); e['result']='fail'
        self.a['integration_readiness']['checks']['compatibility']['verdict']='fail'
        self.a['integration_readiness']['status']='blocked'; self.a['issue_completion']='not_achieved'
        self.a['history']['events']=[self.failure_event()]
        self.save(); self.assertEqual(self.validate(),('blocked','not_achieved'))

    def failure_event(self,kind='measurement_failed'):
        return dict(event_id='failure-1',kind=kind,observed_at=NOW,affected_ids=['staging'],reason=SAMPLE,evidence_refs=self.c['source_refs'])

    def test_rollback_and_revert_cannot_hide_as_unverified(self):
        for state in ('rolled_back','reverted','failed'):
            with self.subTest(state=state):
                self.a,self.c=build(self.root)
                if state=='reverted': self.c['current_members'][0]['state']=state
                else: self.c['current_deployments'][0]['state']=state
                self.a['issue_completion']='unverified'; self.a['integration_readiness']['status']='blocked'
                self.save(); self.reject()

    def test_previous_pin_append_only_and_failure_latch(self):
        self.test_integration_failure_all_ac_met()
        old=copy.deepcopy(self.a); old_ref=write(self.root,'previous.json',old)
        self.c['previous_assessment_sha256']=old_ref['sha256']
        self.a['history']['previous_ref']=old_ref
        self.a['history']['events'].append(dict(event_id='again',kind='revalidated',observed_at=NOW,affected_ids=['staging'],reason=SAMPLE,evidence_refs=self.c['source_refs']))
        self.save()
        kwargs=dict(previous_file=self.root/'previous.json',previous_sha256=old_ref['sha256'])
        self.assertEqual(self.validate(**kwargs),('blocked','not_achieved'))
        with self.assertRaises(ValueError): self.validate()
        with self.assertRaises(ValueError): self.validate(**{**kwargs,'previous_sha256':'0'*64})
        self.a['history']['events'].pop(0); self.save()
        with self.assertRaisesRegex(ValueError,'append-only'): self.validate(**kwargs)

    def test_failure_history_cannot_be_discarded(self):
        self.test_integration_failure_all_ac_met()
        self.a['history']['events']=[]; self.save(); self.reject('history')

    def test_honest_rollback_revert_and_failed_records(self):
        for state in ('rolled_back','reverted','failed'):
            with self.subTest(state=state):
                self.a,self.c=build(self.root,pending=True)
                if state=='reverted':
                    self.c['current_members'][0].update(state=state,merge_sha='1'*40,merged_at='2030-01-01T13:00:00Z',merge_actor='synthetic-operator')
                    event=self.failure_event('revert'); event['affected_ids']=['app']
                else:
                    self.c['current_deployments'][0].update(state=state,deployed_at='2030-01-02T10:00:00Z',deploy_actor='synthetic-operator')
                    event=self.failure_event('rollback' if state=='rolled_back' else 'measurement_failed')
                    self.a['deployment_results'][0]['status']=state
                self.a['issue_completion']='not_achieved'; self.a['history']['events']=[event]
                self.save(); self.assertEqual(self.validate(),('blocked','not_achieved'))
                self.a['issue_completion']='unverified'; self.save(); self.reject('derived')

    def test_measurement_failure_is_not_unverified(self):
        e=self.a['evidence'][-1]; e['result']='fail'
        self.a['verification_results'][-1]['outcome']='not_met'
        self.a['ac_results'][-1]['outcome']='not_met'
        self.a['integration_readiness']['checks']['measurement_coverage']=proof(verdict='pending')
        self.a['integration_readiness']['status']='blocked'; self.a['issue_completion']='not_achieved'
        self.a['history']['events']=[self.failure_event()]
        self.save(); self.assertEqual(self.validate(),('blocked','not_achieved'))
        self.a['verification_results'][-1]['outcome']='unverified'; self.save(); self.reject('measurement outcome')

    def test_history_failure_latch_requires_new_measurement_to_clear(self):
        self.test_integration_failure_all_ac_met()
        old_ref=write(self.root,'previous.json',self.a)
        event=self.a['history']['events'][0]
        self.a,self.c=build(self.root)
        self.c['previous_assessment_sha256']=old_ref['sha256']
        self.a['history']=dict(previous_ref=old_ref,events=[event,dict(event_id='repair',kind='revalidated',observed_at=NOW,affected_ids=['staging'],reason=SAMPLE,evidence_refs=self.c['source_refs'])])
        self.save()
        args=dict(previous_file=self.root/'previous.json',previous_sha256=old_ref['sha256'])
        with self.assertRaisesRegex(ValueError,'derived'): self.validate(**args)
        # Fresh postdeploy checks, including new checks for earlier premerge ACs;
        # do not relabel the old premerge observations to repair a failure.
        later='2030-01-03T13:00:00Z'
        self.a['evaluated_at']=later
        self.a['history']['events'][-1]['observed_at']=later
        # Changing required verification phases is a requirement change, separate
        # from revalidating the repaired failure. Keep the successful expectation.
        self.a['history']['events'].append(dict(event_id='changed-checks',kind='required_set_changed',observed_at=later,affected_ids=['app-pre','config-pre','client-pre'],reason=SAMPLE,evidence_refs=self.c['source_refs']))
        for v in self.c['required_verifications']:
            if v['phase']=='premerge':
                v.update(phase='postdeploy',deployment_ids=['staging'],environment_id='synthetic-staging',workload_id='synthetic-service')
        for e in self.a['evidence']:
            e['observed_at']=later
            if e['phase']=='premerge':
                e.update(phase='postdeploy',deployment_ids=['staging'],environment_id='synthetic-staging',workload_id='synthetic-service')
        self.save()
        status=validate_files(self.root/'completion.json',self.root/'context.json',self.a['context_sha256'],self.root/'handoff.json',now=instant(later),**args)
        self.assertEqual(status,('ready','achieved'))

    def test_closed_schema_and_boolean_pr(self):
        for target in ('extra','boolean','nan','blank'):
            with self.subTest(target=target):
                self.a,self.c=build(self.root)
                if target=='extra': self.c['extra']=True
                elif target=='boolean': self.c['required_prs'][0]['pr_number']=True
                elif target=='nan': self.c['required_prs'][0]['pr_number']=float('nan')
                else: self.c['required_prs'][0]['scope']='  '
                self.save(); self.reject()

    def test_cli_replay_and_required_arguments(self):
        script=Path(__file__).resolve().parents[1]/'scripts/validate_issue_completion.py'
        args=[sys.executable,str(script),str(self.root/'completion.json'),'--context',str(self.root/'context.json'),'--context-sha256',self.a['context_sha256'],'--handoff',str(self.root/'handoff.json'),'--at',NOW]
        result=subprocess.run(args,cwd='/tmp',capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr); self.assertIn('REPLAY',result.stdout); self.assertIn('no authority granted',result.stdout)
        self.assertEqual(subprocess.run(args[:3],capture_output=True).returncode,2)


if __name__=='__main__': unittest.main()
