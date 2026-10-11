"""Independent Test attempt 2 synthetic negatives. PB_HEAD and PB_PRIOR_CASES select immutable inputs."""
import os,sys,copy,json,tempfile,subprocess,unittest,importlib.util,socket,ast
from pathlib import Path
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('prior',os.environ['PB_PRIOR_CASES']);prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
c=prior.c; F=prior.F; NOW=prior.NOW; HEAD=prior.HEAD
class Extra(unittest.TestCase):
 setUp=prior.Cases.setUp
 scan=prior.Cases.scan
 rec=prior.Cases.rec
 reserve=prior.Cases.reserve
 proof=prior.Cases.proof
 def saved(self):
  st=c.Store(self.root/'store');s,p=st.mutate('absent',self.s['writer'],self.s['scope'],lambda x:c.scan(x,c.encode(self.reg),self.src));return st,s,p
 def test_source_removal_readdition_keeps_quarantine_history(self):
  a=self.reg['sources'][0]; b=dict(a,source_id='SYNTHETIC-TWO',inbox_path='two');self.reg['sources'].append(b)
  for k,v in list(self.src.data.items()):
   if '/events/' in k[2]:self.src.data[k[:2]+('two/'+k[2].split('/')[-1],)]=v
  self.scan();before=copy.deepcopy(self.s);self.reg['sources'].remove(a);self.scan()
  self.assertEqual(self.s['cursors'],before['cursors'])
  for k,e in self.s['events'].items():
   self.assertEqual(e['source_ids'],before['events'][k]['source_ids']);self.assertEqual(e['status'],'quarantined');self.assertEqual(e['history'][:-1],before['events'][k]['history'])
  self.reg['sources'].append(a);self.scan();self.assertEqual({e['status'] for e in self.s['events'].values()},{'quarantined'})
 def test_registry_overlap_duplicate_source_and_new_id_cannot_reset(self):
  self.scan();before=copy.deepcopy(self.s)
  for second in [dict(self.reg['sources'][0]),dict(self.reg['sources'][0],source_id='SYNTHETIC-2',inbox_path=self.reg['sources'][0]['inbox_path']+'/nested')]:
   self.reg['sources'].append(second)
   with self.assertRaises(ValueError):self.scan()
   self.assertEqual(self.s,before);self.reg['sources'].pop()
  self.reg['sources'][0]['source_id']='SYNTHETIC-RENAMED';self.scan();self.assertEqual(self.s['cursors'],before['cursors']);self.assertEqual({e['status'] for e in self.s['events'].values()},{'quarantined'})
 def test_legacy_corrupt_final_fail_closed_and_preserved(self):
  st,s,p=self.saved();raw=b'SYNTHETIC legacy acquired output';h=c.digest(raw);bad=st.directory/'objects'/h;bad.write_bytes(raw[:3]);before=(st.directory/'state.json').read_bytes()
  with self.assertRaises(ValueError):st.mutate(p,s['writer'],s['scope'],lambda x:(x,{h:raw}))
  self.assertEqual(bad.read_bytes(),raw[:3]);self.assertEqual((st.directory/'state.json').read_bytes(),before)
  with self.assertRaises(ValueError):st.read_object(h)
 def test_fsync_link_rename_failures_leave_retryable_transaction(self):
  for boundary in ['file_fsync','dir_fsync','link','rename']:
   with self.subTest(boundary=boundary):
    st=c.Store(self.root/boundary);s,p=st.mutate('absent',self.s['writer'],self.s['scope'],lambda x:c.scan(x,c.encode(self.reg),self.src));old=(st.directory/'state.json').read_bytes();raw=b'SYNTHETIC '+boundary.encode();h=c.digest(raw)
    if boundary=='file_fsync': target,attr=c.os,'fsync'
    elif boundary=='dir_fsync':target,attr=c,'fsync_dir'
    elif boundary=='link':target,attr=c.os,'link'
    else:target,attr=c.os,'replace'
    with patch.object(target,attr,side_effect=OSError('synthetic failure')):
     with self.assertRaises(OSError):st.mutate(p,s['writer'],s['scope'],lambda x:(x,{h:raw}))
    self.assertEqual((st.directory/'state.json').read_bytes(),old)
    st=c.Store(st.directory);st.mutate(p,s['writer'],s['scope'],lambda x:(x,{h:raw}));self.assertEqual(st.read_object(h),raw)
 def test_existing_good_object_inode_bytes_permissions_preserved(self):
  st,s,p=self.saved();raw=b'SYNTHETIC immutable';h=st.put(raw);f=st.directory/'objects'/h;ino=f.stat().st_ino
  st.put(raw);self.assertEqual(f.stat().st_ino,ino);self.assertEqual(f.read_bytes(),raw)
  for path in st.directory.rglob('*'):
   self.assertEqual(path.stat().st_mode & 0o077,0)
 def test_partial_stage_snapshot_process_crash_retries(self):
  for kind in ['staging','snapshots']:
   with self.subTest(kind=kind):
    st=c.Store(self.root/kind);s,p=st.mutate('absent',self.s['writer'],self.s['scope'],lambda x:c.scan(x,c.encode(self.reg),self.src));old=(st.directory/'state.json').read_bytes();original=c.durable
    pid=os.fork()
    if pid==0:
     def partial(path,raw):
      if path.parent.parent == st.directory/kind:
       fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);os.write(fd,raw[:5]);os.fsync(fd);os._exit(73)
      return original(path,raw)
     c.durable=partial;st.mutate(p,s['writer'],s['scope'],lambda x:c.scan(x,c.encode(self.reg),self.src));os._exit(74)
    self.assertEqual(os.waitstatus_to_exitcode(os.waitpid(pid,0)[1]),73);self.assertEqual((st.directory/'state.json').read_bytes(),old)
    self.assertTrue(list((st.directory/kind).glob('.pending-*')))
    st=c.Store(st.directory);st.mutate(p,s['writer'],s['scope'],lambda x:c.scan(x,c.encode(self.reg),self.src))
 def test_stale_scope_pin_and_failed_transform_no_advance(self):
  st,s,p=self.saved();raw=(st.directory/'state.json').read_bytes()
  for pin,writer,scope in [('0'*64,s['writer'],s['scope']),(p,'WRONG',s['scope']),(p,s['writer'],'wrong')]:
   with self.assertRaises(ValueError):st.mutate(pin,writer,scope,lambda x:(_ for _ in ()).throw(AssertionError('must not transform')))
   self.assertEqual((st.directory/'state.json').read_bytes(),raw)
  key=next(k for k in self.src.data if '/events/' in k[2]);read=self.src.read;self.src.read=lambda r:read(r)[:-1] if c.refkey(r)==key else read(r)
  with self.assertRaises(ValueError):st.mutate(p,s['writer'],s['scope'],lambda x:c.scan(x,c.encode(self.reg),self.src))
  self.assertEqual((st.directory/'state.json').read_bytes(),raw)
 def test_pending_unknown_and_lease_never_allow_second_dispatch(self):
  self.reserve();self.rec('dispatch');old=copy.deepcopy(self.s)
  for action in ['dispatch','delivery_start','commit_pending']:
   with self.assertRaises(ValueError):self.rec(action)
   self.assertEqual(self.s,old)
  self.rec('dispatch_unknown');self.s['batches'][self.batch]['lease_until']='2000-01-01T00:00:00Z';old=copy.deepcopy(self.s)
  for action in ['dispatch','delivery_start']:
   with self.assertRaises(ValueError):self.rec(action)
  self.assertEqual(self.s,old);self.assertEqual({x['action'] for x in c.plan(self.s)['actions']},{'reconcile_start'})
 def test_output_pending_delivery_survives_store_restart(self):
  self.reserve();self.rec('dispatch');self.rec('started',runtime_id='SYNTHETIC-PRIVATE-RUNTIME',evidence_sha256=self.proof(),next_eligible_at=None)
  raw=(F/'handoff.json').read_bytes();self.obj[c.digest(raw)]=raw;self.rec('output_received',runtime_id='SYNTHETIC-PRIVATE-RUNTIME',evidence_sha256=c.digest(raw),next_eligible_at=None);self.rec('delivery_start')
  st=c.Store(self.root/'store');s,p=st.mutate('absent',self.s['writer'],self.s['scope'],lambda x:(self.s,self.obj));self.s=c.Store(st.directory).load(p)[0]
  self.assertEqual(st.read_object(c.digest(raw)),raw);old=copy.deepcopy(self.s)
  for action in ['dispatch','delivery_start']:
   with self.assertRaises(ValueError):self.rec(action)
  self.assertEqual(self.s,old);self.rec('delivery_failed',evidence_sha256=self.proof(),next_eligible_at=None);self.rec('delivery_start')
  self.assertEqual(self.s['batches'][self.batch]['output_sha256'],c.digest(raw))
 def test_poison_public_observation_no_payload_and_no_external_calls(self):
  self.src.data['example/repo','a'*40,'examples/knowledge-collector/events/poison.json']=b'{"SYNTHETIC_PRIVATE_SECRET":NaN}'
  with patch.object(subprocess,'run',side_effect=AssertionError('external process')),patch.object(socket,'socket',side_effect=AssertionError('network')):
   self.scan();out=c.encode(c.public_observation(self.s));c.plan(self.s)
  self.assertNotIn(b'SYNTHETIC_PRIVATE_SECRET',out);self.assertEqual(c.public_observation(self.s)['counts']['quarantined'],1);self.assertEqual(c.public_observation(self.s)['counts']['verified'],2)
 def test_authorization_bad_pin_operation_scope_expiry_receipt(self):
  raw=c.encode(self.reg);a=dict(schema_version='1.0',document_type='knowledge_collection_authorization',writer=self.s['writer'],scope=self.s['scope'],operation='scan',request_sha256=c.digest(raw),valid_until='2026-10-12T00:00:00Z',approval='approved',authority='SYNTHETIC')
  for change in [dict(operation='record'),dict(scope='wrong'),dict(valid_until='2026-10-10T00:00:00Z'),dict(approval='denied'),dict(authority_granted=True)]:
   auth=c.encode(dict(a,**change))
   with self.assertRaises(ValueError):c.authorize(auth,c.digest(auth),raw,'scan',self.s['writer'],self.s['scope'],NOW)
  auth=c.encode(a)
  with self.assertRaises(ValueError):c.authorize(auth,'0'*64,raw,'scan',self.s['writer'],self.s['scope'],NOW)
 def test_git_all_ancestor_levels_boundary_missing_same_prefix(self):
  repo=self.root/'git';repo.mkdir()
  def git(*args,input=None):return subprocess.check_output(['git','-C',str(repo),*args],input=input,stderr=subprocess.DEVNULL)
  git('init','-q');git('config','user.name','Synthetic');git('config','user.email','synthetic@example.invalid');(repo/'root/tree').mkdir(parents=True);(repo/'root/tree/events2').mkdir();(repo/'root/tree/events2/f').write_text('synthetic');(repo/'blob').write_text('synthetic');git('add','.');git('commit','-qm','synthetic');base=git('rev-parse','HEAD').decode().strip()
  for prefix in ['', 'root/', 'root/tree/']:
   (repo/(prefix+'link')).symlink_to('synthetic-target');(repo/(prefix+'file')).write_text('synthetic');git('add',prefix+'link',prefix+'file');git('update-index','--add','--cacheinfo','160000',base,prefix+'module')
  git('commit','-qm','synthetic boundaries');sha=git('rev-parse','HEAD').decode().strip();src=c.SnapshotSource(self.root/'cache');src.repositories['example/repo',sha]=repo
  for prefix in ['', 'root/', 'root/tree/']:
   self.assertTrue(git('ls-tree',sha,'--',prefix+'module').startswith(b'160000 commit'))
   for typ in ['link','file','module']:
    for suffix in ['', '/events','/missing/deep']:
     with self.subTest(path=prefix+typ+suffix),self.assertRaises(ValueError):src.enumerate(dict(repository='example/repo',commit=sha,inbox_path=prefix+typ+suffix))
  for path in ['missing','root/missing/deep','root/tree/events']:
   self.assertEqual(src.enumerate(dict(repository='example/repo',commit=sha,inbox_path=path)),[])
  self.assertEqual(len(src.enumerate(dict(repository='example/repo',commit=sha,inbox_path='root/tree/events2'))),1)
 def test_delivery_budget_and_receipt_cannot_renew(self):
  self.reserve();self.rec('dispatch');self.rec('started',runtime_id='SYNTHETIC',evidence_sha256=self.proof(),next_eligible_at=None)
  raw=(F/'handoff.json').read_bytes();self.obj[c.digest(raw)]=raw;self.rec('output_received',runtime_id='SYNTHETIC',evidence_sha256=c.digest(raw),next_eligible_at=None)
  for n in range(3):
   self.rec('delivery_start');self.rec('delivery_failed',evidence_sha256=self.proof(),next_eligible_at=None)
  old=copy.deepcopy(self.s);batch=self.s['batches'][self.batch];self.assertEqual(batch['ledger']['epochs'][-1]['terminal'],'RETRY_LIMIT_REACHED')
  for action in ['delivery_start','dispatch']:
   with self.assertRaises(ValueError):self.rec(action)
  receipt=c.encode(dict(schema_version='1.0',authority_granted=False,approval='approved'))
  with self.assertRaises(ValueError):c.record(self.s,dict(action='renew',batch_id=self.batch,ledger=batch['ledger'],resume_state='output_received'),self.obj.__getitem__,self.src,receipt,c.digest(receipt),NOW)
  self.assertEqual(self.s,old);self.scan();self.assertEqual(self.s['batches'],old['batches'])
 def test_fixed_commit_ack_requires_complete_bytes_after_restart(self):
  self.reserve();self.rec('dispatch');self.rec('started',runtime_id='SYNTHETIC',evidence_sha256=self.proof(),next_eligible_at=None)
  raw=(F/'handoff.json').read_bytes();self.obj[c.digest(raw)]=raw;self.rec('output_received',runtime_id='SYNTHETIC',evidence_sha256=c.digest(raw),next_eligible_at=None);self.rec('delivery_start')
  artifacts=[]
  for name in ['input.json','handoff.json','context.json','article.md','source-1.md','source-2.md']:
   raw=(F/name).read_bytes();ref=dict(repository='example/repo',commit='b'*40,path='examples/knowledge-collector/'+name,size=len(raw),sha256=c.digest(raw));self.src.data[c.refkey(ref)]=raw
   artifacts.append(dict(reference=ref,format='knowledge-'+name[:-5]+'-v1' if name.endswith('.json') else 'text',representation='original',public_classification='synthetic_sample',source_alias='SYNTHETIC'))
  manifest=dict(schema_version='1.1',document_type='artifact_delivery',artifacts=artifacts,knowledge_bindings=[dict(input=artifacts[0]['reference'],handoff=artifacts[1]['reference'])]);self.rec('validated',manifest=manifest);self.rec('commit_pending')
  st=c.Store(self.root/'store');state,pin=st.mutate('absent',self.s['writer'],self.s['scope'],lambda x:(self.s,self.obj));self.s=c.Store(st.directory).load(pin)[0]
  refs=[dict(a['reference'],commit='c'*40) for a in artifacts]
  for a,r in zip(artifacts,refs):self.src.data[c.refkey(r)]=self.src.data[c.refkey(a['reference'])]
  before=copy.deepcopy(self.s)
  for bad in [refs[:-1],[dict(r,commit='main') for r in refs]]:
   with self.assertRaises(ValueError):self.rec('committed',committed_output_pin=bad)
  key=c.refkey(refs[-1]);original=self.src.data[key];self.src.data[key]=original[:-1]
  with self.assertRaises(ValueError):self.rec('committed',committed_output_pin=refs)
  self.assertEqual(self.s,before);self.src.data[key]=original;self.rec('committed',committed_output_pin=refs);self.assertEqual({e['status'] for e in self.s['events'].values()},{'committed'})
  with self.assertRaises(ValueError):self.rec('context_available',context_ref=refs[0])
  self.rec('context_available',context_ref=refs[2]);self.assertEqual({e['status'] for e in self.s['events'].values()},{'context_available'})
 def test_documented_pb_scope_is_consistent(self):
  text=(HEAD/'contracts/README.md').read_text()
  self.assertNotIn('非同期収集・context生成・ack・周期実行・実Agent利用実証は後続P-B/C/Dであり未実装。',text,'F4: current contract overview contradicts implemented P-B scope')
if __name__=='__main__':unittest.main(verbosity=2)
