"""Independent synthetic probes; run with PB_HEAD=/path/to/fixed/head. No product edits."""
import os,sys,json,copy,tempfile,subprocess,unittest,hashlib
from pathlib import Path
from datetime import datetime,timezone
from unittest.mock import patch
HEAD=Path(os.environ['PB_HEAD'])
sys.path.insert(0,str(HEAD))
from scripts import knowledge_collector as c
F=HEAD/'examples/knowledge-collector'
NOW=datetime(2026,10,11,tzinfo=timezone.utc)
class Memory:
 def __init__(self):
  self.registry=c.parse((F/'registry.template.json').read_bytes());self.data={};self.reads=[]
  for a in self.registry['artifacts']:
   r=a['reference'];self.data[c.refkey(r)]=(HEAD/r['path']).read_bytes()
  for p in (F/'events').glob('*.json'):self.data[('example/repo','a'*40,'examples/knowledge-collector/events/'+p.name)]=p.read_bytes()
 def read(self,r):self.reads.append(c.refkey(r));return self.data[c.refkey(r)]
 def enumerate(self,s):
  return [dict(repository=k[0],commit=k[1],path=k[2],size=len(v),sha256='0'*64) for k,v in sorted(self.data.items()) if k[:2]==(s['repository'],s['commit']) and k[2].startswith(s['inbox_path']+'/')]
class Cases(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
  self.src=Memory();self.reg=self.src.registry;self.s=c.initial('SYNTHETIC-INDEPENDENT','synthetic/independent')
  self.obj={}
 def scan(self):
  self.s,a=c.scan(self.s,c.encode(self.reg),self.src);self.obj.update(a);c.validate_state(self.s)
 def rec(self,action,**kw):
  r={'action':action,**kw}
  if action!='reserve':r['batch_id']=self.batch
  s,a=c.record(self.s,r,self.obj.__getitem__,self.src,now=NOW);c.validate_state(s);self.s=s;self.obj.update(a)
 def reserve(self):
  self.scan();raw=(F/'input.json').read_bytes();self.obj[c.digest(raw)]=raw
  self.batch=c.digest(c.encode(sorted(self.s['events'])))
  self.rec('reserve',event_ids=sorted(self.s['events']),input_sha256=c.digest(raw),lease_until='2026-10-12T00:00:00Z')
 def proof(self):
  raw=b'SYNTHETIC independent observation';self.obj[c.digest(raw)]=raw;return c.digest(raw)
 def test_identity_exact_canonical_and_time_independence(self):
  e=c.parse(next(v for k,v in self.src.data.items() if '/events/' in k[2]));ref=e['source_ref']
  expected=hashlib.sha256((json.dumps(dict(version='1.0',repository=ref['repository'],commit=ref['commit'],path=ref['path'],sha256=ref['sha256'],candidate_id=e['candidate_id'],event_kind=e['event_kind']),sort_keys=True,separators=(',',':'),ensure_ascii=False)+'\n').encode()).hexdigest()
  self.assertEqual(c.event_id(e),expected)
  e['occurred_at']='2030-01-01T00:00:00Z';e['collected_at']=e['occurred_at'];self.assertEqual(c.event_id(e),expected)
 def test_identical_content_distinct_source_preserved(self):
  k=next(k for k in self.src.data if '/events/' in k[2]);e=c.parse(self.src.data[k])
  ref=dict(e['source_ref'],path='synthetic/other.md');raw=self.src.data[c.refkey(e['source_ref'])]
  self.src.data[c.refkey(ref)]=raw;self.reg['artifacts'].append(dict(self.reg['artifacts'][0],reference=ref))
  e['source_ref']=ref;e['finding_refs']=[ref];e['event_id']=c.event_id(e)
  self.src.data[k[:2]+('examples/knowledge-collector/events/'+e['event_id']+'.json',)]=c.encode(e)
  self.scan();self.assertEqual(len(self.s['events']),3);self.assertTrue(all(x['status']=='verified' for x in self.s['events'].values()))
 def test_same_id_payload_collision_retains_both_raw(self):
  self.scan();old=copy.deepcopy(self.s);k=next(k for k in self.src.data if '/events/' in k[2]);self.src.data[k]+=b' '
  self.scan();self.assertEqual(self.s['cursors'],old['cursors']);self.assertEqual(self.s['scans'][-1]['result'],'quarantined')
  self.assertIn(c.digest(self.src.data[k]),self.obj)
  for e in old['events'].values():self.assertIn(e['event_sha256'],self.obj)
 def test_strict_poison_matrix(self):
  key=next(k for k in self.src.data if '/events/' in k[2]);original=self.src.data[key];e=c.parse(original)
  bads=[b'{"a":1,"\\u0061":2}',b'{"a":{"b":1,"b":2}}',b'{"n":NaN}',b'{"n":Infinity}',b'\xef\xbb\xbf'+original,c.encode(dict(e,source_ref=dict(e['source_ref'],size=True))),c.encode(dict(e,runtime_id='SYNTHETIC')),c.encode(dict(e,document_type='handoff'))]
  for raw in bads:
   with self.subTest(raw=raw[:25]):
    self.s=c.initial('SYNTHETIC-INDEPENDENT','synthetic/independent');self.src.data[key]=raw;self.scan()
    self.assertEqual(c.public_observation(self.s)['counts']['quarantined'],1);self.assertEqual(c.public_observation(self.s)['counts']['verified'],1)
 def test_dependency_every_entry_read_even_unused(self):
  raw=b'SYNTHETIC unreferenced dependency\n';ref=dict(repository='example/repo',commit='b'*40,path='unused.md',size=len(raw),sha256=c.digest(raw))
  self.reg['artifacts'].append(dict(self.reg['artifacts'][0],reference=ref));self.src.data[c.refkey(ref)]=raw
  self.scan();self.assertIn(c.refkey(ref),self.src.reads)
 def test_dependency_missing_modified_partial_no_cursor(self):
  self.scan();before=copy.deepcopy(self.s);r=self.reg['artifacts'][0]['reference'];key=c.refkey(r);raw=self.src.data[key]
  for value in (None,raw[:-1],b'X'+raw[1:]):
   with self.subTest(value=value is None):
    if value is None:del self.src.data[key]
    else:self.src.data[key]=value
    with self.assertRaises((ValueError,KeyError)):self.scan()
    self.assertEqual(self.s,before)
 def test_mutable_ref_and_type_downgrade(self):
  for change in ('mutable','type'):
   src=Memory();reg=src.registry
   if change=='mutable':reg['sources'][0]['commit']='main'
   else:reg['artifacts'][0]['format']='json'
   with self.assertRaises(ValueError):c.scan(self.s,c.encode(reg),src)
 def test_catchup_after_interruption_and_full_nonancestor(self):
  self.scan();before=copy.deepcopy(self.s);old=self.src.enumerate
  self.src.enumerate=lambda s:(_ for _ in ()).throw(OSError('synthetic interruption'))
  with self.assertRaises(OSError):self.scan()
  self.assertEqual(self.s,before);self.src.enumerate=old
  for k,v in list(self.src.data.items()):
   if '/events/' in k[2]:self.src.data[(k[0],'f'*40,k[2])]=v
  self.reg['sources'][0]['commit']='f'*40;self.scan()
  self.assertEqual(self.s['cursors']['SYNTHETIC-INBOX'],'f'*40);self.assertEqual(self.s['scans'][-1]['mode'],'full');self.assertEqual(len(self.s['events']),2)
 def test_disappearance_quarantine_and_raw_history(self):
  self.scan();before=copy.deepcopy(self.s);key=next(k for k in self.src.data if '/events/' in k[2]);raw=self.src.data.pop(key)
  self.reg['sources'][0]['commit']='c'*40;self.scan()
  self.assertEqual(self.s['cursors'],before['cursors']);self.assertEqual(self.s['scans'][-1]['result'],'quarantined');self.assertIn(c.digest(raw),self.obj)
 def test_F1_per_source_disappearance_must_not_be_masked(self):
  first=self.reg['sources'][0];second=dict(first,source_id='SYNTHETIC-SECOND',inbox_path='second')
  self.reg['sources'].append(second)
  for k,v in list(self.src.data.items()):
   if '/events/' in k[2]:self.src.data[k[:2]+('second/'+k[2].split('/')[-1],)]=v
  self.scan();before=copy.deepcopy(self.s['cursors'])
  for k in list(self.src.data):
   if k[2].startswith(first['inbox_path']+'/'):del self.src.data[k]
  first['commit']='f'*40;self.scan()
  self.assertEqual(self.s['scans'][-1]['result'],'quarantined','F1: disappearance in first source masked by second; cursor advanced')
  self.assertEqual(self.s['cursors'],before)
 def test_CAS_process_lock_and_fsync_order(self):
  store=c.Store(self.root/'store');events=[]
  fsync=c.os.fsync;replace=c.os.replace
  def fs(fd):events.append('fsync');return fsync(fd)
  def rep(a,b):events.append('replace');return replace(a,b)
  with patch.object(c.os,'fsync',fs),patch.object(c.os,'replace',rep):
   s,pin=store.mutate('absent',self.s['writer'],self.s['scope'],lambda s:c.scan(s,c.encode(self.reg),self.src))
  ix=events.index('replace');self.assertIn('fsync',events[:ix]);self.assertIn('fsync',events[ix+1:])
  with self.assertRaises(ValueError):store.mutate('absent',self.s['writer'],self.s['scope'],lambda s:(s,{}))
  with self.assertRaises(ValueError):store.mutate(pin,'OTHER',self.s['scope'],lambda s:(s,{}))
  with store.lock():
   pid=os.fork()
   if pid==0:
    try:
     with c.Store(store.directory).lock():os._exit(2)
    except ValueError:os._exit(0)
   self.assertEqual(os.waitstatus_to_exitcode(os.waitpid(pid,0)[1]),0)
 def test_all_five_crash_points_real_process_restart(self):
  for point in ['after_objects','after_stage','after_snapshot','after_rename','after_replace']:
   with self.subTest(point=point):
    store=c.Store(self.root/point);s,pin=store.mutate('absent',self.s['writer'],self.s['scope'],lambda s:c.scan(s,c.encode(self.reg),self.src))
    pid=os.fork()
    if pid==0:
     store.mutate(pin,self.s['writer'],self.s['scope'],lambda s:c.scan(s,c.encode(self.reg),self.src),lambda p:os._exit(73) if p==point else None);os._exit(74)
    self.assertEqual(os.waitstatus_to_exitcode(os.waitpid(pid,0)[1]),73)
    fresh=c.Store(store.directory);raw=(store.directory/'state.json').read_bytes();state,_=fresh.load(c.digest(raw))
    self.assertEqual(state['sequence'],s['sequence']+(point in ['after_rename','after_replace']))
    for e in state['events'].values():fresh.read_object(e['event_sha256'])
    fresh.mutate(c.digest(raw),self.s['writer'],self.s['scope'],lambda s:c.scan(s,c.encode(self.reg),self.src))
 def test_F2_crash_during_raw_write_then_retry_recovers(self):
  store=c.Store(self.root/'store');s,pin=store.mutate('absent',self.s['writer'],self.s['scope'],lambda s:c.scan(s,c.encode(self.reg),self.src))
  raw=b'SYNTHETIC newly acquired output bytes\n';rawhash=c.digest(raw);real_durable=c.durable
  pid=os.fork()
  if pid==0:
   def partial(path,data):
    if path.name==rawhash:
     fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);os.write(fd,data[:7]);os.fsync(fd);os._exit(73)
    return real_durable(path,data)
   c.durable=partial
   store.mutate(pin,self.s['writer'],self.s['scope'],lambda s:(s,{rawhash:raw}));os._exit(74)
  self.assertEqual(os.waitstatus_to_exitcode(os.waitpid(pid,0)[1]),73);self.assertEqual(store.load(pin)[0],s)
  # Contract recovery says repeat authorized operation against old pin before replacement.
  store=c.Store(store.directory)
  store.mutate(pin,self.s['writer'],self.s['scope'],lambda s:(s,{rawhash:raw}))
 def test_unknown_no_evidence_expired_lease(self):
  self.reserve();self.rec('dispatch');self.rec('dispatch_unknown')
  self.s['batches'][self.batch]['lease_until']='2000-01-01T00:00:00Z'
  with self.assertRaises(ValueError):self.rec('dispatch')
  with self.assertRaises(KeyError):self.rec('started',runtime_id='SYNTHETIC-RUNTIME',evidence_sha256='0'*64,next_eligible_at=None)
  self.assertEqual({a['action'] for a in c.plan(self.s)['actions']},{'reconcile_start'})
 def test_three_dispatch_terminal_next_scan_no_reset(self):
  self.reserve()
  for i in range(3):
   self.rec('dispatch');self.rec('dispatch_failed',runtime_id=None,evidence_sha256=self.proof(),next_eligible_at=None)
  ledger=copy.deepcopy(self.s['batches'][self.batch]['ledger']);self.scan();c.plan(self.s)
  self.assertEqual(self.s['batches'][self.batch]['ledger'],ledger)
  self.assertEqual({e['status'] for e in self.s['events'].values()},{'terminal'})
  with self.assertRaises(ValueError):self.rec('dispatch')
 def test_delivery_terminal_and_renew_grant_negative_matrix(self):
  self.reserve();self.rec('dispatch');self.rec('started',runtime_id='SYNTHETIC',evidence_sha256=self.proof(),next_eligible_at=None)
  raw=(F/'handoff.json').read_bytes();self.obj[c.digest(raw)]=raw
  self.rec('output_received',runtime_id='SYNTHETIC',evidence_sha256=c.digest(raw),next_eligible_at=None)
  with self.assertRaises(ValueError):self.rec('dispatch')
  for i in range(3):
   self.rec('delivery_start');self.rec('delivery_failed',evidence_sha256=self.proof(),next_eligible_at=None)
  batch=self.s['batches'][self.batch];old=copy.deepcopy(batch['ledger'])
  good=dict(approval='approved',authority='SYNTHETIC',reason='SYNTHETIC recovery',scope=old['scope'],prior_history_sha256=batch['ledger_sha256'],new_epoch=2,limits=dict(dispatch=1,execution=1,delivery=1),relationship='Preserve synthetic prior history')
  for change in [{'scope':'wrong'},{'prior_history_sha256':'0'*64},{'reason':''},{'limits':dict(dispatch=4,execution=1,delivery=1)},{'approval':'denied'}]:
   grant=dict(good,**change);g=c.encode(grant);after=copy.deepcopy(old);after['epochs'].append(dict(id=2,limits=grant['limits'],events=[],terminal='open',grant_sha256=c.digest(g)))
   with self.assertRaises(ValueError):c.record(self.s,dict(action='renew',batch_id=self.batch,ledger=after,resume_state='output_received'),self.obj.__getitem__,self.src,g,c.digest(g),NOW)
  g=c.encode(good);after=copy.deepcopy(old);after['epochs'].append(dict(id=2,limits=good['limits'],events=[],terminal='open',grant_sha256=c.digest(g)))
  req=dict(action='renew',batch_id=self.batch,ledger=after,resume_state='output_received')
  with self.assertRaises(ValueError):c.record(self.s,req,self.obj.__getitem__,self.src,None,None,NOW)
  fresh,_=c.record(self.s,req,self.obj.__getitem__,self.src,g,c.digest(g),NOW)
  self.assertEqual(fresh['batches'][self.batch]['ledger']['epochs'][0],old['epochs'][0]);self.assertEqual(fresh['batches'][self.batch]['output_sha256'],c.digest(raw))
  with self.assertRaises(ValueError):c.record(fresh,dict(action='dispatch',batch_id=self.batch),self.obj.__getitem__,self.src,now=NOW)
 def test_replay_readonly_public_closed(self):
  store=c.Store(self.root/'store');s,pin=store.mutate('absent',self.s['writer'],self.s['scope'],lambda s:c.scan(s,c.encode(self.reg),self.src))
  before={str(p):p.read_bytes() for p in store.directory.rglob('*') if p.is_file()}
  cmd=[sys.executable,str(HEAD/'scripts/knowledge_collector.py'),'replay','--store',str(store.directory),'--previous-sha256',pin]
  r=subprocess.run(cmd,capture_output=True);self.assertEqual(r.returncode,0)
  out=json.loads(r.stdout);self.assertEqual(set(out),{'schema_version','document_type','counts','development_gate_changed','authority_granted'});self.assertFalse(out['authority_granted']);self.assertFalse(out['development_gate_changed'])
  self.assertEqual(before,{str(p):p.read_bytes() for p in store.directory.rglob('*') if p.is_file()})
 def test_F3_real_git_ancestor_symlink_rejected(self):
  repo=self.root/'git';repo.mkdir()
  def git(*args):return subprocess.check_output(['git','-C',str(repo),*args],stderr=subprocess.DEVNULL)
  git('init','-q');git('config','user.name','Synthetic');git('config','user.email','synthetic@example.invalid')
  (repo/'target').mkdir();(repo/'target'/'events').mkdir();(repo/'target'/'events'/'file').write_bytes(b'synthetic');(repo/'alias').symlink_to('target')
  git('add','.');git('commit','-qm','synthetic');sha=git('rev-parse','HEAD').decode().strip()
  src=c.SnapshotSource(self.root/'cache');src.repositories['example/repo',sha]=repo
  with self.assertRaises(ValueError,msg='F3: unsafe ancestor silently interpreted as empty inbox'):
   src.enumerate(dict(source_id='SYNTHETIC',repository='example/repo',commit=sha,inbox_path='alias/events'))

 def test_gitlink_ancestor_rejected(self):
  repo=self.root/'git';repo.mkdir()
  def git(*args):return subprocess.check_output(['git','-C',str(repo),*args],stderr=subprocess.DEVNULL)
  git('init','-q');git('config','user.name','Synthetic');git('config','user.email','synthetic@example.invalid')
  (repo/'f').write_bytes(b'synthetic');git('add','.');git('commit','-qm','synthetic');first=git('rev-parse','HEAD').decode().strip()
  git('update-index','--add','--cacheinfo','160000',first,'module');git('commit','-qm','synthetic gitlink')
  sha=git('rev-parse','HEAD').decode().strip();src=c.SnapshotSource(self.root/'cache');src.repositories['example/repo',sha]=repo
  with self.assertRaises(ValueError,msg='F3: gitlink ancestor interpreted as empty inbox'):
   src.enumerate(dict(source_id='SYNTHETIC',repository='example/repo',commit=sha,inbox_path='module/events'))
 def test_noop_and_unapproved_cli(self):
  self.src.data={k:v for k,v in self.src.data.items() if '/events/' not in k[2]}
  self.scan();self.assertEqual(c.plan(self.s)['actions'],[])
  request=self.root/'request';request.write_bytes(c.encode(self.reg))
  auth=self.root/'auth';auth.write_bytes(b'{"SYNTHETIC_SECRET":"not approval"}')
  result=subprocess.run([sys.executable,str(HEAD/'scripts/knowledge_collector.py'),'scan','--store',str(self.root/'never-created'),'--previous-sha256','absent','--writer',self.s['writer'],'--scope',self.s['scope'],'--request',str(request),'--authorization',str(auth),'--authorization-sha256',c.digest(auth.read_bytes())],capture_output=True)
  self.assertEqual(result.returncode,1);self.assertFalse((self.root/'never-created').exists());self.assertNotIn(b'SYNTHETIC_SECRET',result.stdout+result.stderr)
 def test_closed_registry_state_and_record(self):
  for name,data in [('knowledge-source-registry',self.reg),('knowledge-collection-state',self.s)]:
   with self.assertRaises(ValueError):c.validate(name,dict(data,unexpected='extra'))
   with self.assertRaises(ValueError):c.validate(name,dict(data,schema_version='9.0'))
  self.reserve()
  with self.assertRaises(ValueError):self.rec('dispatch',unexpected='extra')
  with self.assertRaises(ValueError):self.rec('committed',committed_output_pin=[])

if __name__=='__main__':unittest.main(verbosity=2)
