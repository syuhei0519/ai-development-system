"""Synthetic P-B regression matrix. No Knowledge Agent or scheduler is used."""
from copy import deepcopy
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts import knowledge_collector as c

NOW = datetime(2026, 10, 11, tzinfo=timezone.utc)
FIXTURE = c.ROOT / 'examples/collector'


class Source:
    def __init__(self):
        self.registry = c.parse((FIXTURE / 'registry.template.json').read_bytes())
        self.files = {}
        for a in self.registry['artifacts']:
            r = a['reference']; self.files[c.refkey(r)] = (c.ROOT / r['path']).read_bytes()
        for p in (FIXTURE / 'events').glob('*.json'):
            self.files['example/repo', 'a'*40, 'examples/collector/events/' + p.name] = p.read_bytes()
        self.reads = []

    def read(self, ref):
        self.reads.append(c.refkey(ref))
        return self.files[c.refkey(ref)]

    def enumerate(self, item):
        return [dict(repository=k[0], commit=k[1], path=k[2], size=len(v), sha256='0'*64)
                for k,v in sorted(self.files.items()) if k[:2] == (item['repository'], item['commit'])
                and k[2].startswith(item['inbox_path'] + '/')]

    def bundle(self):
        artifacts = []
        for name in ('input.json','handoff.json','context.json','article.md','source-1.md','source-2.md'):
            raw = (FIXTURE/name).read_bytes(); path = 'examples/collector/' + name
            kind = 'knowledge-' + name[:-5] + '-v1' if name.endswith('.json') else 'text'
            ref = dict(repository='example/repo', commit='b'*40, path=path, size=len(raw), sha256=c.digest(raw))
            self.files[c.refkey(ref)] = raw
            artifacts.append(dict(reference=ref,format=kind,representation='original',public_classification='synthetic_sample',source_alias='SYNTHETIC'))
        manifest = dict(schema_version='1.3',document_type='artifact_delivery',artifacts=artifacts,
                    knowledge_bindings=[dict(input=artifacts[0]['reference'],handoff=artifacts[1]['reference'])])
        from scripts.prepare_knowledge_fixture import fixture_slots
        fixture_slots(manifest, self.read)
        return manifest


class CollectorTests(unittest.TestCase):
    def test_documented_pb_scope_is_consistent(self):
        overview = (c.ROOT / 'contracts/README.md').read_text()
        self.assertIn('過去契約の再現', overview)
        self.assertIn('新規タスクへの必須要件ではない', overview)
        legacy = (c.ROOT / 'contracts/knowledge-collection.md').read_text()
        for boundary in ('P-C', 'P-D', 'unimplemented'):
            self.assertIn(boundary, legacy)
        current_docs = [c.ROOT / 'README.md']
        for directory in ('contracts', 'workflows', 'templates'):
            current_docs.extend((c.ROOT / directory).glob('*.md'))
        for document in current_docs:
            with self.subTest(document=document.relative_to(c.ROOT)):
                self.assertNotIn('後続P-B/C/Dであり未実装', document.read_text())

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.source = Source(); self.registry = self.source.registry
        self.state = c.initial('SYNTHETIC-MANAGER', 'synthetic/knowledge')
        self.objects = {}
        self.input_raw = (FIXTURE/'input.json').read_bytes()
        self.output_raw = (FIXTURE/'handoff.json').read_bytes()
        for raw in (self.input_raw,self.output_raw,b'synthetic observation'):
            self.objects[c.digest(raw)] = raw
        self.evidence = c.digest(b'synthetic observation')

    def scan(self):
        self.state, archive = c.scan(self.state,c.encode(self.registry),self.source)
        self.objects.update(archive); c.validate_state(self.state)
        return self.state

    def record(self, action, **kwargs):
        req=dict(action=action,**kwargs)
        if action != 'reserve': req['batch_id'] = self.batch
        self.state, archive=c.record(self.state,req,self.objects.__getitem__,self.source,now=NOW)
        self.objects.update(archive); c.validate_state(self.state)

    def reserve(self):
        self.scan()
        ids=sorted(self.state['events']); self.batch=c.digest(c.encode(ids))
        self.record('reserve',event_ids=ids,input_sha256=c.digest(self.input_raw),lease_until='2026-10-12T00:00:00Z')

    def start(self):
        self.reserve(); self.record('dispatch')
        self.record('started',runtime_id='SYNTHETIC-RUNTIME',evidence_sha256=self.evidence,next_eligible_at=None)

    def output(self):
        self.start()
        self.record('output_received',runtime_id='SYNTHETIC-RUNTIME',evidence_sha256=c.digest(self.output_raw),next_eligible_at=None)

    def validated(self):
        self.output(); self.record('delivery_start'); self.manifest=self.source.bundle()
        self.record('validated',manifest=self.manifest)

    def status(self):
        statuses={e['status'] for e in self.state['events'].values()}
        self.assertEqual(len(statuses),1); return statuses.pop()

    def test_full_scan_duplicate_noop_retains_raw(self):
        self.scan(); first=deepcopy(self.state['events']); self.scan()
        self.assertEqual(first,self.state['events']); self.assertEqual(len(first),2)
        self.assertEqual(self.state['cursors'],{'SYNTHETIC-INBOX':'a'*40})
        self.assertTrue(all(e['event_sha256'] in self.objects for e in first.values()))

    def test_identity_ignores_time_but_payload_collision_quarantines(self):
        self.scan(); key=next(k for k in self.source.files if '/events/' in k[2])
        event=c.parse(self.source.files[key]); identity=c.event_id(event)
        event['collected_at']='2026-10-12T00:00:00Z'; self.assertEqual(identity,c.event_id(event))
        old=self.source.files[key]; self.source.files[key]=c.encode(event); self.scan()
        self.assertEqual(self.state['events'][identity]['status'],'quarantined')
        self.assertEqual(self.state['events'][identity]['event_sha256'],c.digest(old))
        self.assertIn(c.digest(self.source.files[key]),self.objects)
        self.assertEqual(self.state['scans'][-1]['result'],'quarantined')

    def test_similar_content_different_candidate_keeps_two_sources(self):
        keys=[k for k in self.source.files if '/events/' in k[2]]
        event=c.parse(self.source.files[keys[0]]); event['candidate_id']='SYNTHETIC-OTHER'
        event['event_id']=c.event_id(event)
        self.source.files[keys[0][:2]+('examples/collector/events/'+event['event_id']+'.json',)]=c.encode(event)
        self.scan(); self.assertEqual(len(self.state['events']),3)

    def test_partial_source_read_never_advances_cursor(self):
        self.scan(); before=deepcopy(self.state)
        k=c.refkey(self.registry['artifacts'][0]['reference']); self.source.files[k]=self.source.files[k][:-1]
        with self.assertRaises(ValueError): self.scan()
        self.assertEqual(self.state,before)

    def test_interrupted_enumeration_never_commits(self):
        before=deepcopy(self.state)
        def broken(item): raise OSError('synthetic interruption')
        self.source.enumerate=broken
        with self.assertRaises(OSError): self.scan()
        self.assertEqual(self.state,before)

    def test_partial_event_read(self):
        original=self.source.read
        self.source.read=lambda r: original(r)[:-1] if '/events/' in r['path'] else original(r)
        with self.assertRaises(ValueError): self.scan()
        self.assertEqual(self.state['cursors'],{})

    def test_registry_change_force_push_missing_history_full_reconcile(self):
        self.scan(); prior=deepcopy(self.state['events'])
        self.registry['sources'][0]['commit']='c'*40
        self.scan()
        self.assertEqual(self.state['cursors'],{'SYNTHETIC-INBOX':'a'*40})
        self.assertEqual(self.status(),'quarantined')
        self.assertEqual(self.state['scans'][-1]['mode'],'full')
        for k in prior: self.assertEqual(prior[k]['event_sha256'],self.state['events'][k]['event_sha256'])

    def test_removed_registry_source_not_forgotten(self):
        self.scan(); self.registry['sources'][0].update(source_id='SYNTHETIC-NEW',inbox_path='empty')
        self.scan(); self.assertEqual(self.status(),'quarantined')

    def test_duplicate_inbox_cannot_hide_source_disappearance(self):
        first = self.registry['sources'][0]
        second = dict(first, source_id='SYNTHETIC-SECOND', inbox_path='second')
        self.registry['sources'].append(second)
        for key, raw in list(self.source.files.items()):
            if '/events/' in key[2]:
                self.source.files[key[:2] + ('second/' + key[2].split('/')[-1],)] = raw
        self.exhaust('dispatch')
        before = deepcopy(self.state)
        # An identical copy remains, but the first source's history is missing.
        for key in list(self.source.files):
            if key[2].startswith(first['inbox_path'] + '/'):
                del self.source.files[key]
        first['commit'] = 'f' * 40
        for remove_source in (False, True):
            if remove_source:
                self.registry['sources'].remove(first)
            self.scan()
            self.assertEqual(self.state['cursors'], before['cursors'])
            self.assertEqual(self.state['scans'][-1]['result'], 'quarantined')
            self.assertEqual(self.state['batches'], before['batches'])
            for identity, old in before['events'].items():
                event = self.state['events'][identity]
                self.assertEqual(event['status'], 'quarantined')
                for field in ('source_ids', 'event', 'event_sha256'):
                    self.assertEqual(event[field], old[field])
                self.assertEqual(event['history'][:len(old['history'])], old['history'])
                self.assertIn(old['event_sha256'], self.objects)

    def test_poison_event_does_not_stop_other_events(self):
        self.source.files['example/repo','a'*40,'examples/collector/events/poison.json']=b'{"x":NaN}'
        self.scan(); counts=c.public_observation(self.state)['counts']
        self.assertEqual(counts['quarantined'],1); self.assertEqual(counts['verified'],2)
        self.assertEqual(len([a for a in c.plan(self.state)['actions'] if a['action']=='reserve']),2)

    def test_unknown_fields_versions_private_and_strict_json(self):
        key=next(k for k in self.source.files if '/events/' in k[2]); original=self.source.files[key]
        variants=[dict(c.parse(original),schema_version='2.0'),dict(c.parse(original),runtime_id='SECRET'),dict(c.parse(original),classification='private_only')]
        for raw in [*[c.encode(v) for v in variants],b'\xef\xbb\xbf'+original,b'{"a":1,"a":2}',b'{"x":Infinity}',b'\xff']:
            with self.subTest(raw=raw[:15]):
                self.state=c.initial('SYNTHETIC-MANAGER','synthetic/knowledge'); self.source.files[key]=raw
                self.scan(); self.assertEqual(c.public_observation(self.state)['counts']['quarantined'],1)

    def test_unlisted_dependency_quarantined(self):
        self.registry['artifacts'].pop(); self.scan()
        self.assertEqual(c.public_observation(self.state)['counts']['quarantined'],1)

    def test_typed_dependency_cannot_downgrade(self):
        self.registry['artifacts'][0]['format']='json'
        with self.assertRaises(ValueError): self.scan()

    def test_authority_pin_request_expiry_and_receipt_rejected(self):
        req=c.encode(self.registry)
        auth=dict(schema_version='1.0',document_type='knowledge_collection_authorization',writer='SYNTHETIC-MANAGER',scope='synthetic/knowledge',operation='scan',request_sha256=c.digest(req),valid_until='2026-10-12T00:00:00Z',approval='approved',authority='synthetic test authority')
        raw=c.encode(auth); c.authorize(raw,c.digest(raw),req,'scan','SYNTHETIC-MANAGER','synthetic/knowledge',NOW)
        for pin,request,now in [('0'*64,req,NOW),(c.digest(raw),req+b' ',NOW),(c.digest(raw),req,datetime(2027,1,1,tzinfo=timezone.utc))]:
            with self.assertRaises(ValueError): c.authorize(raw,pin,request,'scan','SYNTHETIC-MANAGER','synthetic/knowledge',now)
        with self.assertRaises(ValueError): c.authorize(b'{}',c.digest(b'{}'),req,'scan','SYNTHETIC-MANAGER','synthetic/knowledge',NOW)

    def test_illegal_transition_and_overlap(self):
        self.reserve()
        for action in ('started','output_received','validated','committed','context_available','delivery_start','renew'):
            with self.subTest(action=action),self.assertRaises(ValueError): self.record(action)
        with self.assertRaises(ValueError): self.record('reserve',event_ids=list(self.state['events']),input_sha256=c.digest(self.input_raw),lease_until='2026-10-12T00:00:00Z')

    def test_dispatch_unknown_lease_expiry_never_restarts(self):
        self.reserve(); self.record('dispatch'); self.record('dispatch_unknown')
        self.state['batches'][self.batch]['lease_until']='2020-01-01T00:00:00Z'
        self.assertTrue(all(a['action']=='reconcile_start' for a in c.plan(self.state)['actions']))
        with self.assertRaises(ValueError): self.record('dispatch')
        self.record('started',runtime_id='SYNTHETIC-RUNTIME',evidence_sha256=self.evidence,next_eligible_at=None)
        self.assertEqual(self.status(),'started')

    def test_observation_runtime_mismatch(self):
        self.start()
        with self.assertRaises(ValueError): self.record('output_received',runtime_id='OTHER',evidence_sha256=c.digest(self.output_raw),next_eligible_at=None)

    def test_output_crash_resumes_delivery_never_execution(self):
        self.output(); frozen=c.encode(self.state); self.state=c.parse(frozen)
        self.assertEqual(self.status(),'output_received')
        self.assertTrue(all(a['action']=='resume_delivery' for a in c.plan(self.state)['actions']))
        with self.assertRaises(ValueError): self.record('dispatch')
        self.record('delivery_start')
        # Crash while fetching: persisted pending delivery cannot reserve another attempt.
        with self.assertRaises(ValueError): self.record('delivery_start')
        self.record('delivery_failed',evidence_sha256=self.evidence,next_eligible_at=None)
        self.record('delivery_start'); self.record('validated',manifest=self.source.bundle())
        self.assertEqual(self.status(),'validated')

    def test_input_output_binding_rejected(self):
        self.output(); self.record('delivery_start'); manifest=self.source.bundle()
        self.state['batches'][self.batch]['input_sha256']='0'*64
        with self.assertRaises(ValueError): self.record('validated',manifest=manifest)

    def test_commit_after_external_git_crash_requires_fixed_bytes(self):
        self.validated(); self.record('commit_pending')
        refs=[dict(a['reference'],commit='d'*40) for a in self.manifest['artifacts']]
        for a,r in zip(self.manifest['artifacts'],refs): self.source.files[c.refkey(r)]=self.source.files[c.refkey(a['reference'])]
        self.state=c.parse(c.encode(self.state))
        self.assertTrue(all(a['action']=='verify_fixed_commit' for a in c.plan(self.state)['actions']))
        self.record('committed',committed_output_pin=refs); self.assertEqual(self.status(),'committed')
        self.record('context_available',context_ref=refs[2]); self.assertEqual(self.status(),'context_available')
        with self.assertRaises(ValueError): self.record('committed',committed_output_pin=refs)

    def test_commit_missing_tampered_or_floating_rejected(self):
        self.validated(); self.record('commit_pending')
        refs=[a['reference'] for a in self.manifest['artifacts']]
        with self.assertRaises(ValueError): self.record('committed',committed_output_pin=refs[:-1])
        bad=deepcopy(refs); bad[0]['commit']='main'
        with self.assertRaises(ValueError): self.record('committed',committed_output_pin=bad)
        self.source.files[c.refkey(refs[0])]+=b'changed'
        with self.assertRaises(ValueError): self.record('committed',committed_output_pin=refs)

    def prepare_retry(self):
        batch=self.state['batches'][self.batch]
        old=c.parse(self.objects[batch['input_sha256']]); attempt=old['attempt']
        if not hasattr(self,'retry_docs'): self.retry_docs={}
        prior=c.parse(self.output_raw)
        for key in ('assignment','raw_findings','knowledge_references','task_id','attempt','retry_of'):
            prior[key]=old[key]
        prior.update(status='failed',system_status='failed',artifacts=[],evidence=[],decisions=[],failure_reasons=['synthetic failure'])
        self.retry_docs[f'input-{attempt}.json']=c.encode(old)
        self.retry_docs[f'handoff-{attempt}.json']=c.encode(prior)
        new=deepcopy(old); new.update(task_id=f'SYNTHETIC-KNOWLEDGE-TASK-{attempt+1}',attempt=attempt+1,
            retry_of=[dict(task_id=old['task_id'],attempt=attempt,handoff_locator=f'handoff-{attempt}.json',revision='sha256:'+c.digest(c.encode(prior)))])
        self.retry_docs[f'input-{attempt+1}.json']=c.encode(new)
        manifest=self.source.bundle()
        manifest['artifacts']=[a for a in manifest['artifacts'] if a['format'] not in ('knowledge-input-v1','knowledge-handoff-v1')]
        manifest['knowledge_bindings']=[]; refs={}
        for name,raw in self.retry_docs.items():
            ref=dict(repository='example/repo',commit='b'*40,path='examples/collector/'+name,size=len(raw),sha256=c.digest(raw))
            self.source.files[c.refkey(ref)]=raw; refs[name]=ref
            kind='knowledge-input-v1' if name.startswith('input') else 'knowledge-handoff-v1'
            manifest['artifacts'].append(dict(reference=ref,format=kind,representation='original',public_classification='synthetic_sample',source_alias='SYNTHETIC'))
        for n in range(1,attempt+2):
            binding=dict(input=refs[f'input-{n}.json'])
            if n<=attempt: binding['handoff']=refs[f'handoff-{n}.json']
            manifest['knowledge_bindings'].append(binding)
        from scripts.prepare_knowledge_fixture import fixture_slots
        fixture_slots(manifest,self.source.read)
        self.record('prepare_retry',input_sha256=c.digest(c.encode(new)),manifest=manifest)

    def exhaust(self,kind):
        if kind=='dispatch': self.reserve()
        elif kind=='execution': self.reserve()
        else: self.output()
        for i in range(3):
            if kind in ('dispatch','execution'):
                if kind=='execution' and i: self.prepare_retry()
                self.record('dispatch')
                if kind=='execution': self.record('started',runtime_id='SYNTHETIC-RUNTIME',evidence_sha256=self.evidence,next_eligible_at=None)
                self.record(kind+'_failed',runtime_id='SYNTHETIC-RUNTIME' if kind=='execution' else None,evidence_sha256=self.evidence,next_eligible_at=None)
            else:
                self.record('delivery_start'); self.record('delivery_failed',evidence_sha256=self.evidence,next_eligible_at=None)
        self.assertEqual(self.status(),'terminal')
        self.assertEqual(self.state['batches'][self.batch]['ledger']['epochs'][-1]['terminal'],'RETRY_LIMIT_REACHED')

    def test_three_dispatch_failure_budget(self): self.exhaust('dispatch')
    def test_three_execution_failure_budget(self): self.exhaust('execution')
    def test_three_delivery_failure_budget(self): self.exhaust('delivery')

    def test_terminal_survives_scan_and_replay(self):
        self.exhaust('dispatch'); before=deepcopy(self.state['batches']); self.scan(); c.plan(self.state)
        self.assertEqual(self.status(),'terminal'); self.assertEqual(before,self.state['batches'])
        with self.assertRaises(ValueError): self.record('dispatch')

    def test_renewal_requires_separate_grant_keeps_history_and_output(self):
        self.exhaust('delivery'); b=self.state['batches'][self.batch]; before=deepcopy(b['ledger'])
        grant=dict(approval='approved',authority='synthetic Manager',reason='synthetic new budget',scope=before['scope'],prior_history_sha256=b['ledger_sha256'],new_epoch=2,limits=dict(dispatch=1,execution=1,delivery=1),relationship='synthetic preserves original three attempts')
        raw=c.encode(grant); after=deepcopy(before)
        after['epochs'].append(dict(id=2,limits=grant['limits'],events=[],terminal='open',grant_sha256=c.digest(raw)))
        request=dict(action='renew',batch_id=self.batch,ledger=after,resume_state='output_received')
        with self.assertRaises(ValueError): c.record(self.state,request,self.objects.__getitem__,self.source,now=NOW)
        self.state,_=c.record(self.state,request,self.objects.__getitem__,self.source,raw,c.digest(raw),NOW)
        self.assertEqual(self.state['batches'][self.batch]['ledger']['epochs'][0],before['epochs'][0])
        self.assertEqual(self.status(),'output_received')
        with self.assertRaises(ValueError): self.record('dispatch')

    def test_retry_history_reset_and_budget_over_three_rejected(self):
        self.exhaust('dispatch'); ledger=deepcopy(self.state['batches'][self.batch]['ledger'])
        ledger['epochs'][0]['events']=[]
        with self.assertRaises(ValueError): self.record('renew',ledger=ledger,resume_state='reserved')

    def test_import_pinned_legacy_terminal_keeps_all_attempts(self):
        self.exhaust('dispatch'); ledger=self.state['batches'][self.batch]['ledger']
        raw=c.encode(ledger); self.objects[c.digest(raw)]=raw
        self.state=c.initial('SYNTHETIC-MANAGER','synthetic/knowledge'); self.scan()
        self.record('reserve',event_ids=sorted(self.state['events']),input_sha256=c.digest(self.input_raw),
                    lease_until='2026-10-12T00:00:00Z',prior_ledger_sha256=c.digest(raw))
        self.assertEqual(self.status(),'terminal')
        self.assertEqual(self.state['batches'][self.batch]['ledger'],ledger)
        with self.assertRaises(ValueError): self.record('dispatch')

    def test_execution_retry_cannot_reuse_attempt_one_input(self):
        self.start(); self.record('execution_failed',runtime_id='SYNTHETIC-RUNTIME',evidence_sha256=self.evidence,next_eligible_at=None)
        with self.assertRaises(ValueError): self.record('dispatch')
        self.prepare_retry(); self.record('dispatch')
        self.assertEqual(self.status(),'dispatching')

    def test_backoff_not_bypassed(self):
        self.reserve(); self.record('dispatch')
        self.record('dispatch_failed',runtime_id=None,evidence_sha256=self.evidence,next_eligible_at='2026-10-13T00:00:00Z')
        with self.assertRaises(ValueError): self.record('dispatch')

    def test_public_output_omits_runtime_authority_bytes_paths(self):
        self.start(); public=c.encode(c.public_observation(self.state))
        for secret in (b'SYNTHETIC-RUNTIME',b'SYNTHETIC-MANAGER',b'synthetic/knowledge',b'input_sha256',b'authorization'):
            self.assertNotIn(secret,public)
        self.assertFalse(c.public_observation(self.state)['development_gate_changed'])

    def test_empty_scan_and_plan_noop(self):
        self.source.files={k:v for k,v in self.source.files.items() if '/events/' not in k[2]}
        self.scan(); self.assertEqual(c.plan(self.state)['actions'],[])
        with self.assertRaises(ValueError): self.record('reserve',event_ids=[],input_sha256=c.digest(self.input_raw),lease_until='2026-10-12T00:00:00Z')

    def store(self): return c.Store(Path(self.temp.name)/'private')

    def test_atomic_cas_stale_and_wrong_writer(self):
        store=self.store(); transform=lambda s:c.scan(s,c.encode(self.registry),self.source)
        state,pin=store.mutate('absent','SYNTHETIC-MANAGER','synthetic/knowledge',transform)
        self.assertEqual(c.digest((store.directory/'state.json').read_bytes()),pin)
        for expected,writer in [('absent','SYNTHETIC-MANAGER'),('0'*64,'SYNTHETIC-MANAGER'),(pin,'OTHER')]:
            with self.assertRaises(ValueError): store.mutate(expected,writer,'synthetic/knowledge',transform)
        self.assertEqual(store.load(pin)[0],state)

    def test_overlap_lock_and_release(self):
        store=self.store()
        with store.lock():
            with self.assertRaises(ValueError):
                with store.lock(): pass
        with store.lock(): pass

    def test_each_persistence_crash_point_recovery(self):
        for point in ('after_objects','after_stage','after_snapshot','after_rename','after_replace'):
            with self.subTest(point=point):
                store=c.Store(Path(self.temp.name)/point)
                def crash(p):
                    if p==point: raise RuntimeError('synthetic crash')
                with self.assertRaises(RuntimeError):
                    store.mutate('absent','SYNTHETIC-MANAGER','synthetic/knowledge',lambda s:c.scan(s,c.encode(self.registry),self.source),crash)
                if point in ('after_rename','after_replace'):
                    raw=(store.directory/'state.json').read_bytes(); state,_=store.load(c.digest(raw)); self.assertEqual(len(state['events']),2)
                    with self.assertRaises(ValueError): store.mutate('absent','SYNTHETIC-MANAGER','synthetic/knowledge',lambda s:(s,{}))
                else:
                    self.assertFalse((store.directory/'state.json').exists())
                    state,pin=store.mutate('absent','SYNTHETIC-MANAGER','synthetic/knowledge',lambda s:c.scan(s,c.encode(self.registry),self.source))
                    self.assertEqual(len(state['events']),2)
                for e in state['events'].values(): self.assertEqual(c.digest(store.read_object(e['event_sha256'])),e['event_sha256'])

    def test_process_exit_leaves_old_cursor_and_releases_writer_lock(self):
        store=self.store(); transform=lambda s:c.scan(s,c.encode(self.registry),self.source)
        state,pin=store.mutate('absent','SYNTHETIC-MANAGER','synthetic/knowledge',transform)
        child=os.fork()
        if child==0:
            def crash(point):
                if point=='after_stage': os._exit(73)
            store.mutate(pin,'SYNTHETIC-MANAGER','synthetic/knowledge',transform,crash)
            os._exit(74)
        _,status=os.waitpid(child,0)
        self.assertEqual(os.waitstatus_to_exitcode(status),73)
        self.assertEqual(store.load(pin)[0],state)
        recovered,newpin=store.mutate(pin,'SYNTHETIC-MANAGER','synthetic/knowledge',transform)
        self.assertEqual(recovered['sequence'],state['sequence']+1)
        self.assertNotEqual(pin,newpin)

    def test_partial_immutable_write_process_restart(self):
        # Exercise writes inside durable(), before the five transaction hooks.
        for destination in ('objects', 'staging', 'snapshots'):
            with self.subTest(destination=destination):
                store = c.Store(Path(self.temp.name) / destination)
                transform = lambda s: c.scan(s, c.encode(self.registry), self.source)
                state, pin = store.mutate('absent', self.state['writer'], self.state['scope'], transform)
                payload = b'SYNTHETIC newly received raw bytes\n'
                key = c.digest(payload)
                previous = {p.name: (p.read_bytes(), p.stat().st_ino)
                            for p in (store.directory / 'objects').iterdir() if p.is_file()}
                child = os.fork()
                if child == 0:
                    original = c.durable
                    def partial(path, raw):
                        if destination in path.relative_to(store.directory).parts:
                            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                            os.write(fd, raw[:7]); os.fsync(fd); os._exit(73)
                        original(path, raw)
                    c.durable = partial
                    store.mutate(pin, state['writer'], state['scope'], lambda s: (s, {key: payload}))
                    os._exit(74)
                self.assertEqual(os.waitstatus_to_exitcode(os.waitpid(child, 0)[1]), 73)
                fresh = c.Store(store.directory)
                self.assertEqual(fresh.load(pin)[0], state)
                recovered, newpin = fresh.mutate(pin, state['writer'], state['scope'],
                                                lambda s: (s, {key: payload}))
                self.assertEqual(recovered['cursors'], state['cursors'])
                self.assertEqual(recovered['sequence'], state['sequence'] + 1)
                self.assertEqual(fresh.read_object(key), payload)
                self.assertEqual(fresh.load(newpin)[0], recovered)
                for name, (raw, inode) in previous.items():
                    path = store.directory / 'objects' / name
                    self.assertEqual((path.read_bytes(), path.stat().st_ino), (raw, inode))

    def test_object_publication_process_crash_before_and_after_link(self):
        for after_link in (False, True):
            with self.subTest(after_link=after_link):
                store = c.Store(Path(self.temp.name) / str(after_link))
                state, pin = store.mutate('absent', self.state['writer'], self.state['scope'],
                                          lambda s: (s, {}))
                payload = b'SYNTHETIC atomic publication\n'; key = c.digest(payload)
                child = os.fork()
                if child == 0:
                    original = c.os.link
                    def link(source, target):
                        if target.name == key:
                            if after_link:
                                original(source, target)
                            os._exit(73)
                        return original(source, target)
                    c.os.link = link
                    store.mutate(pin, state['writer'], state['scope'], lambda s: (s, {key: payload}))
                    os._exit(74)
                self.assertEqual(os.waitstatus_to_exitcode(os.waitpid(child, 0)[1]), 73)
                self.assertEqual(store.load(pin)[0], state)
                path = store.directory / 'objects' / key
                self.assertEqual(path.exists(), after_link)
                if after_link:
                    self.assertEqual(path.read_bytes(), payload)
                    inode = path.stat().st_ino
                fresh = c.Store(store.directory)
                fresh.mutate(pin, state['writer'], state['scope'], lambda s: (s, {key: payload}))
                self.assertEqual(fresh.read_object(key), payload)
                if after_link:
                    self.assertEqual(path.stat().st_ino, inode)

    def test_existing_objects_never_replaced_or_repaired_implicitly(self):
        store = self.store(); raw = b'SYNTHETIC valid object\n'; key = store.put(raw)
        path = store.directory / 'objects' / key
        inode = path.stat().st_ino
        store.put(raw)
        self.assertEqual(path.stat().st_ino, inode)
        # Even a damaged final file from an older writer requires explicit repair.
        path.write_bytes(raw[:7])
        with self.assertRaises(ValueError): store.put(raw)
        self.assertEqual(path.read_bytes(), raw[:7])
        self.assertEqual(path.stat().st_ino, inode)
        path.unlink(); target = Path(self.temp.name) / 'external'; target.write_bytes(raw)
        path.symlink_to(target)
        with self.assertRaises(ValueError): store.put(raw)
        self.assertTrue(path.is_symlink()); self.assertEqual(target.read_bytes(), raw)

    def test_publication_does_not_overwrite_file_appearing_at_link(self):
        store = self.store(); raw = b'SYNTHETIC expected bytes\n'; key = c.digest(raw)
        path = store.directory / 'objects' / key
        original = c.os.link
        for existing in (raw, b'SYNTHETIC conflicting bytes\n'):
            def race(source, target):
                target.write_bytes(existing)
                return original(source, target)
            with patch.object(c.os, 'link', race):
                if existing == raw:
                    store.put(raw)
                else:
                    with self.assertRaises(ValueError): store.put(raw)
            self.assertEqual(path.read_bytes(), existing)
            path.unlink()

    def test_cli_unapproved_request_does_not_create_store_or_leak_bytes(self):
        req=Path(self.temp.name)/'request'; req.write_bytes(c.encode(self.registry))
        auth=Path(self.temp.name)/'auth'; auth.write_bytes(b'{"secret":"SYNTHETIC-SECRET"}')
        target=Path(self.temp.name)/'not-created'
        result=subprocess.run([sys.executable,str(c.ROOT/'scripts/knowledge_collector.py'),'scan',
            '--store',str(target),'--previous-sha256','absent','--writer','SYNTHETIC-MANAGER',
            '--scope','synthetic/knowledge','--request',str(req),'--authorization',str(auth),
            '--authorization-sha256',c.digest(auth.read_bytes())],capture_output=True)
        self.assertEqual(result.returncode,1); self.assertFalse(target.exists())
        self.assertNotIn(b'SYNTHETIC-SECRET',result.stdout+result.stderr)

    def test_append_only_private_snapshots_and_raw_history(self):
        store=self.store(); transform=lambda s:c.scan(s,c.encode(self.registry),self.source)
        state,pin=store.mutate('absent','SYNTHETIC-MANAGER','synthetic/knowledge',transform)
        raw=(store.directory/'state.json').read_bytes()
        second,newpin=store.mutate(pin,'SYNTHETIC-MANAGER','synthetic/knowledge',transform)
        self.assertEqual(second['previous_state_sha256'],pin); self.assertEqual(store.read_object(pin),raw)
        self.assertTrue((store.directory/'snapshots'/pin).exists())
        self.assertNotEqual(pin,newpin)

    def test_cli_replay_has_no_store_mutation_and_no_authority(self):
        store=self.store(); state,pin=store.mutate('absent','SYNTHETIC-MANAGER','synthetic/knowledge',lambda s:c.scan(s,c.encode(self.registry),self.source))
        before={str(p):p.read_bytes() for p in store.directory.rglob('*') if p.is_file()}
        result=subprocess.run([sys.executable,str(c.ROOT/'scripts/knowledge_collector.py'),'replay','--store',str(store.directory),'--previous-sha256',pin],capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr); self.assertFalse(json.loads(result.stdout)['authority_granted'])
        self.assertEqual(before,{str(p):p.read_bytes() for p in store.directory.rglob('*') if p.is_file()})

    def test_store_symlink_and_nonprivate_rejected(self):
        public=Path(self.temp.name)/'public'; public.mkdir(mode=0o755); public.chmod(0o755)
        with self.assertRaises(ValueError): c.Store(public)
        alias=Path(self.temp.name)/'alias'; alias.symlink_to(public)
        with self.assertRaises(ValueError): c.Store(alias)

    def test_schema_closed_and_legacy_files_still_validate(self):
        self.scan(); bad=deepcopy(self.state); bad['scheduler']='enabled'
        with self.assertRaises(ValueError): c.validate_state(bad)
        # Legacy suites run alongside these; new collector does not mutate legacy schemas.
        for p in c.ROOT.joinpath('contracts').glob('knowledge-*.schema.json'):
            c.Draft202012Validator.check_schema(json.loads(p.read_text()))


class GitTreeTests(unittest.TestCase):
    """Actual Git object/tree reads; only fetch transport is replaced with a local fixture."""
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.repo=Path(self.temp.name)/'repo'; self.repo.mkdir()
        self.git('init','-q'); self.git('config','user.name','Synthetic'); self.git('config','user.email','synthetic@example.invalid')
        inbox=self.repo/'inbox'; inbox.mkdir(); (inbox/'event.json').write_bytes(b'synthetic bytes\n')
        self.git('add','.'); self.git('commit','-qm','synthetic fixture')
        self.commit=self.git('rev-parse','HEAD').decode().strip()
        self.source=c.SnapshotSource(Path(self.temp.name)/'cache')
        self.source.repositories['example/repo',self.commit]=self.repo
        self.item=dict(source_id='SYNTHETIC',repository='example/repo',commit=self.commit,inbox_path='inbox')

    def git(self,*args):
        return subprocess.run(['git','-C',str(self.repo),*args],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout

    def newcommit(self):
        self.git('add','.'); self.git('commit','-qm','synthetic unsafe fixture')
        self.commit=self.git('rev-parse','HEAD').decode().strip()
        self.source.repositories['example/repo',self.commit]=self.repo; self.item['commit']=self.commit

    def test_real_tree_full_bytes_and_size(self):
        refs=self.source.enumerate(self.item); self.assertEqual(len(refs),1)
        self.assertEqual(self.source.read(refs[0]),b'synthetic bytes\n')
        refs[0]['size']+=1
        with self.assertRaises(ValueError): self.source.read(refs[0])

    def test_symlink_leaf_and_prefix_fail_closed(self):
        (self.repo/'inbox'/'link').symlink_to('event.json'); self.newcommit()
        with self.assertRaises(ValueError): self.source.enumerate(self.item)
        (self.repo/'alias').symlink_to('inbox'); self.newcommit(); self.item['inbox_path']='alias'
        with self.assertRaises(ValueError): self.source.enumerate(self.item)

    def test_gitlink_rejected(self):
        self.git('update-index','--add','--cacheinfo','160000',self.commit,'inbox/submodule')
        self.git('commit','-qm','synthetic gitlink')
        commit=self.git('rev-parse','HEAD').decode().strip(); self.source.repositories['example/repo',commit]=self.repo
        self.item['commit']=commit
        with self.assertRaises(ValueError): self.source.enumerate(self.item)

    def test_all_inbox_ancestor_types_checked(self):
        original_commit = self.commit
        (self.repo / 'nested').mkdir()
        (self.repo / 'nested' / 'alias').symlink_to('../inbox')
        (self.repo / 'alias').symlink_to('inbox')
        (self.repo / 'nested' / 'file').write_bytes(b'SYNTHETIC ordinary blob')
        self.newcommit()
        self.git('update-index', '--add', '--cacheinfo', '160000', self.commit, 'nested/module')
        self.git('commit', '-qm', 'synthetic gitlink ancestor')
        commit = self.git('rev-parse', 'HEAD').decode().strip()
        self.source.repositories['example/repo', commit] = self.repo
        for path in ('alias/events', 'nested/alias/events', 'nested/module/events',
                     'nested/file/events', 'nested/file'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                self.source.enumerate(dict(self.item, commit=commit, inbox_path=path))
        for path in ('missing/events', 'nested/missing/events'):
            self.assertEqual(self.source.enumerate(dict(self.item, commit=commit, inbox_path=path)), [])
        # Resolution stays pinned even though the working tree now has unsafe aliases.
        self.assertEqual(self.source.enumerate(dict(self.item, commit=original_commit,
                                                   inbox_path='nested/alias/events')), [])

    def test_path_traversal_floating_and_missing(self):
        for path in ('../inbox','inbox/../inbox','/inbox','inbox//bad'):
            with self.subTest(path=path),self.assertRaises(ValueError): self.source.enumerate(dict(self.item,inbox_path=path))
        with self.assertRaises(ValueError): self.source.snapshot('example/repo','main')
        self.assertEqual(self.source.enumerate(dict(self.item,inbox_path='missing')),[])
