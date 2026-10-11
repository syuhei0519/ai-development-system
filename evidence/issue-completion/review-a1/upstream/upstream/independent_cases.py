#!/usr/bin/env python3
"""Independent Test synthetic CLI probes. Uses public sample bytes, not producer test helpers.
Usage: python independent_cases.py SOURCE_CHECKOUT OUTPUT_DIRECTORY
No network, product operations, source edits, or authorization material.
"""
import copy, hashlib, json, pathlib, shutil, subprocess, sys
S=pathlib.Path(sys.argv[1]).resolve(); O=pathlib.Path(sys.argv[2]).resolve(); O.mkdir(parents=True,exist_ok=True)
NOW='2030-01-03T12:00:00Z'; rows=[]
def raw(x): return (json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode()
def digest(b): return hashlib.sha256(b).hexdigest()
def load(p): return json.loads(p.read_bytes())
def write(p,x): p.write_bytes(x if isinstance(x,bytes) else raw(x))
def ref(p): return dict(id=p.name,locator=p.name,size=p.stat().st_size,sha256=digest(p.read_bytes()))
class Case:
 def __init__(self,name,pending=False):
  self.p=O/name; shutil.copytree(S/'examples/issue-completion'/('synthetic-pending' if pending else 'synthetic-achieved'),self.p,dirs_exist_ok=True)
  self.a=load(self.p/'completion.json'); self.c=load(self.p/'context.json'); self.h=load(self.p/'handoff.json'); self.extra=[]
 def save(self):
  write(self.p/'context.json',self.c); self.pin=digest((self.p/'context.json').read_bytes()); self.a['context_sha256']=self.pin
  for e in self.a['evidence']:
   if e['binding']['type']=='integration':
    e['binding']['context_sha256']=self.pin
    e['binding']['merged_members']=[dict(member_id=m['member_id'],merge_sha=m['merge_sha']) for m in self.c['current_members'] if m['merge_sha']]
    e['binding']['deployments']=[{k:d[k] for k in ('deployment_id','sources','config_sha256','images','environment_id','workload_id')} for d in self.c['current_deployments']] if e['phase']=='postdeploy' else []
   p=self.p/e['source_ref']['locator']; write(p,dict(schema_version='1.0',document_type='issue_completion_observation',observation={k:v for k,v in e.items() if k!='source_ref'})); e['source_ref']=ref(p)
  self.a['integration_readiness']['evidence_ids']=sorted({i for p in self.a['integration_readiness']['checks'].values() for i in p['evidence_ids']})
  write(self.p/'completion.json',self.a)
  # Retain supplied handoff structure, refresh only references to deliberately changed synthetic bytes.
  for a in self.h['artifacts']:
   p=self.p/a['locator']
   if p.exists(): a['revision']='sha256:'+digest(p.read_bytes())
  if self.a['issue_completion']!='achieved': self.h.pop('final_assessment',None)
  write(self.p/'handoff.json',self.h)
 def run(self,expected=1,contains=None):
  cmd=[sys.executable,str(S/'scripts/validate_issue_completion.py'),str(self.p/'completion.json'),'--context',str(self.p/'context.json'),'--context-sha256',self.pin,'--handoff',str(self.p/'handoff.json'),'--at',NOW]+self.extra
  r=subprocess.run(cmd,cwd='/tmp',capture_output=True,text=True)
  passed=r.returncode==expected and (contains is None or contains in r.stdout)
  rows.append(dict(case=self.p.name,expected_exit=expected,actual_exit=r.returncode,expected_output=contains,passed=passed,stdout=r.stdout.strip(),stderr=r.stderr.strip()))
  print(self.p.name, 'PASS' if passed else 'FAIL',r.returncode,flush=True)
def check(name,fn=lambda t:None,expected=1,contains=None,pending=False,after=None):
 t=Case(name,pending); fn(t); t.save()
 if after: after(t)
 t.run(expected,contains); return t
def event(kind='revalidated'):
 return dict(event_id='synthetic-next',kind=kind,observed_at=NOW,affected_ids=['staging'],reason='synthetic independent test',evidence_refs=[])
def previous(t):
 write(t.p/'previous.json',copy.deepcopy(t.a)); r=ref(t.p/'previous.json'); t.c['previous_assessment_sha256']=r['sha256']; t.a['history']['previous_ref']=r; t.a['history']['events'].append(event()); t.extra=['--previous',str(t.p/'previous.json'),'--previous-sha256',r['sha256']]
check('positive_achieved',expected=0,contains='integration=ready; issue_completion=achieved')
check('positive_pending',expected=0,contains='integration=blocked; issue_completion=unverified',pending=True)
for owner,field in [('a','member_results'),('a','deployment_results'),('a','verification_results'),('a','ac_results'),('c','required_prs'),('c','current_members'),('c','required_verifications'),('c','required_deployments'),('c','scope_decisions')]:
 for mode in ('missing','duplicate','extra'):
  def mutate(t,owner=owner,field=field,mode=mode):
   arr=getattr(t,owner)[field]
   if mode=='missing': arr.pop(0)
   else:
    x=copy.deepcopy(arr[0]); arr.append(x)
    if mode=='extra': x[next(k for k in x if k.endswith('_id'))]='synthetic-extra'
  # An additional scope decision is valid; duplicate scope identity is not.
  check(owner+'_'+field+'_'+mode,mutate,expected=0 if field=='scope_decisions' and mode=='extra' else 1)
for field,value in [('head_sha','9'*40),('base_sha','9'*40),('target_revision','9'*40),('merge_group_sha','9'*40),('config_revision','other'),('merge_sha','9'*40),('state','open')]:
 check('old_member_'+field,lambda t,f=field,v=value:t.c['current_members'][0].update({f:v}))
for field,value in [('actor','other'),('member_ids',['app']),('deployment_ids',[]),('status','revoked'),('valid_until',NOW),('allowed_actions',['consume']),('decision_kind','delivery')]:
 check('approval_'+field,lambda t,f=field,v=value:t.c['scope_decisions'][1].update({f:v}))
for field,value in [('sources',[]),('images',[]),('config_sha256','9'*64),('environment_id','other'),('workload_id','other'),('state','pending')]:
 check('deployment_'+field,lambda t,f=field,v=value:t.c['current_deployments'][0].update({f:v}))
for owner,field in [('c','valid_until'),('c','observed_at')]:
 check('context_time_'+field,lambda t,f=field:t.c.update({f:NOW if f=='valid_until' else '2030-01-04T00:00:00Z'}))
for field,value in [('valid_until',NOW),('observed_at','2030-01-01T12:00:00Z'),('phase','premerge'),('kind','integration'),('producer','other'),('method','different'),('workload_id','other')]:
 check('measurement_'+field,lambda t,f=field,v=value:t.a['evidence'][-1].update({f:v}))
check('context_pin_independent',after=lambda t:setattr(t,'pin','0'*64))
check('context_pin_matching_self_claim',after=lambda t:(write(t.p/'context.json',{**t.c,'context_id':'self-copy'}),t.a.update(context_sha256=digest((t.p/'context.json').read_bytes())),write(t.p/'completion.json',t.a)))
def source(t,payload):
 e=t.a['evidence'][-1]; p=t.p/e['source_ref']['locator']; write(p,payload); e['source_ref']=ref(p); write(t.p/'completion.json',t.a)
check('source_receipt_substitution',after=lambda t:source(t,{'document_type':'consumption_receipt','authority_granted':False}))
check('source_knowledge_substitution',after=lambda t:source(t,{'document_type':'knowledge_handoff','summary':'approved'}))
check('source_observation_rewritten',after=lambda t:source(t,{'schema_version':'1.0','document_type':'issue_completion_observation','observation':{}}))
for name in ['completion.json','context.json','handoff.json']:
 for label,b in [('duplicate',b'{"a":1,"a":2}'),('escaped_duplicate',b'{"a":1,"\\u0061":2}'),('nan',b'{"x":NaN}'),('infinity',b'{"x":Infinity}'),('bom',b'\xef\xbb\xbf{}'),('truncated',b'{"a":'),('trailing',b'{}{}')]:
  check(name+'_'+label,after=lambda t,n=name,b=b:write(t.p/n,b))
for label,b in [('duplicate',b'{"a":1,"a":2}'),('nan',b'{"x":NaN}'),('truncated',b'{"a":')]:
 check('source_rehashed_'+label,after=lambda t,b=b:source(t,b))
for mode in ['byte','size','hash','missing','escape','absolute','url','symlink']:
 def alteration(t,mode=mode):
  e=t.a['evidence'][-1]; r=e['source_ref']; p=t.p/r['locator']
  if mode=='byte': p.write_bytes(p.read_bytes()+b'\n')
  elif mode=='size': r['size']+=1
  elif mode=='hash': r['sha256']='0'*64
  elif mode=='missing': p.unlink()
  elif mode=='symlink':
   q=t.p/'link.json'; q.symlink_to(p.name); r['locator']=q.name
  else: r['locator']={'escape':'../outside.json','absolute':'/tmp/outside.json','url':'https://example.invalid/x'}[mode]
  write(t.p/'completion.json',t.a)
 check('blob_'+mode,after=alteration)
for mode in ['role','issue','original','digest','final_missing','same_bytes_other_path','measurement_other_path']:
 def hm(t,mode=mode):
  h=t.h
  if mode=='role': h['role']='test'
  elif mode=='issue': h['issue']['id']='other'
  elif mode=='original': h['issue']['acceptance_criteria'][0]['verbatim']+='!'
  elif mode=='digest': h['artifacts'][0]['revision']='sha256:'+'0'*64
  elif mode=='final_missing': h.pop('final_assessment')
  else:
   a=h['artifacts'][0 if mode=='same_bytes_other_path' else 1]; shutil.copyfile(t.p/a['locator'],t.p/'copy.json'); a['locator']='copy.json'
  write(t.p/'handoff.json',h)
 check('handoff_'+mode,after=hm)
check('previous_valid',previous,expected=0,contains='achieved')
check('previous_pin_wrong',previous,after=lambda t:t.extra.__setitem__(-1,'0'*64))
check('previous_pin_missing',previous,after=lambda t:setattr(t,'extra',[]))
def truncation(t):
 t.a['history']['events']=[event()]; previous(t); t.a['history']['events']=[{**event(),'event_id':'replacement'}]
check('history_prefix_replaced',truncation)
def pending_integration(t):
 t.a['integration_readiness']['checks']['compatibility'].update(verdict='pending',evidence_ids=[]); t.a['integration_readiness']['status']='blocked'; t.a['issue_completion']='unverified'
check('all_ac_met_integration_pending',pending_integration,expected=0,contains='unverified')
for state in ['reverted','rolled_back','failed']:
 def failure(t,state=state):
  if state=='reverted': t.c['current_members'][0].update(state=state,merge_sha='1'*40,merged_at='2030-01-01T13:00:00Z',merge_actor='synthetic-operator'); kind='revert'; affected='app'
  else: t.c['current_deployments'][0].update(state=state,deployed_at='2030-01-02T10:00:00Z',deploy_actor='synthetic-operator'); t.a['deployment_results'][0]['status']=state; kind='rollback' if state=='rolled_back' else 'measurement_failed'; affected='staging'
  t.a['history']['events']=[{**event(kind),'affected_ids':[affected],'evidence_refs':t.c['source_refs']}]; t.a['issue_completion']='not_achieved'
 check('honest_'+state,failure,expected=0,contains='not_achieved',pending=True)
 check('hidden_'+state,lambda t,f=failure:(f(t),t.a.update(issue_completion='unverified')),pending=True)
def remove_check(t):
 previous(t)
 vid='runtime-persistence'; t.c['required_verifications']=[v for v in t.c['required_verifications'] if v['verification_id']!=vid]
 t.a['verification_results']=[v for v in t.a['verification_results'] if v['verification_id']!=vid]
 t.a['evidence']=[e for e in t.a['evidence'] if e['id']!=vid]
 for r in t.a['ac_results']:
  for k in ['verification_ids','evidence_ids']: r[k]=[i for i in r[k] if i!=vid]
 for p in t.a['integration_readiness']['checks'].values(): p['evidence_ids']=[i for i in p['evidence_ids'] if i!=vid]
 for r in t.h['final_assessment']['ac_results']: r['evidence_ids']=[i for i in r['evidence_ids'] if i!=vid]
check('required_subcheck_removed_without_change_event',remove_check)
def pr_alias(t):
 p=t.p/'app-handoff.json'; h=load(p); a=h['artifacts'][0]; q=t.p/'pr-link.json'; q.symlink_to(a['locator']); a['locator']=q.name; write(p,h)
 r=t.a['member_results'][0]['readiness_handoff_ref']; r.update(size=p.stat().st_size,sha256=digest(p.read_bytes()))
check('pr_handoff_symlink_locator',pr_alias)
# Additional independent cross-contract and merge-mode probes.
def edit_pr(t,mid,edit):
 r=next(r for r in t.a['member_results'] if r['member_id']==mid)
 rp=t.p/r['readiness_ref']['locator']; cp=t.p/r['readiness_context_ref']['locator']; hp=t.p/r['readiness_handoff_ref']['locator']
 rd,ct,hd=load(rp),load(cp),load(hp); edit(rd,ct)
 write(rp,rd); write(cp,ct)
 for a in hd['artifacts']:
  if a['id']==rd['artifact_id']:a['revision']='sha256:'+digest(rp.read_bytes())
 write(hp,hd)
 for k,p in [('readiness_ref',rp),('readiness_context_ref',cp),('readiness_handoff_ref',hp)]:r[k].update(size=p.stat().st_size,sha256=digest(p.read_bytes()))
def method(t,value):
 for e in t.a['evidence']:
  if e['merge']:e['merge']['method']=value
 if value=='queue':
  for m in t.c['current_members']:
   mid=m['member_id']; m.update(merge_group_sha='e'*40,target_revision='e'*40)
   def queue(r,c):
    r['subject'].update(merge_group_sha='e'*40,target_revision='e'*40); c['subject']=copy.deepcopy(r['subject']); c['github_requirements']['queue']=True; r['merge_readiness']['checks']['github_queue']['verdict']='pass'
    for e in r['evidence']:e['subject']=copy.deepcopy(r['subject'])
   edit_pr(t,mid,queue)
   for e in t.a['evidence']:
    if e['merge'] and e['merge']['member_id']==mid:e['merge']['target_revision']='e'*40
    if e['phase']=='premerge' and e['binding']['member_id']==mid:e['binding']['subject'].update(merge_group_sha='e'*40,target_revision='e'*40)
for value in ['merge','squash','rebase','queue']:
 check('positive_merge_mode_'+value,lambda t,v=value:method(t,v),expected=0,contains='achieved')
check('queue_method_without_queue_subject',lambda t:method(t,'queue'),after=lambda t:(t.a['evidence'][0]['merge'].update(method='squash'),t.save()))
def expiry(t):
 def edit(r,c):
  for e in r['evidence']:e['valid_until']='2030-01-01T13:00:00Z'
 edit_pr(t,'app',edit)
check('historical_gate_expired_at_merge',expiry)
def github(t):
 def edit(r,c):r['merge_readiness']['checks']['github_reviews']['evidence_ids']=r['merge_readiness']['checks']['ai_review']['evidence_ids']
 edit_pr(t,'app',edit)
check('github_review_replaced_by_ai_review',github)
def fail_integration(t):
 e=next(e for e in t.a['evidence'] if e['id']=='compatibility'); e['result']='fail'
 t.a['integration_readiness']['checks']['compatibility']['verdict']='fail'; t.a['integration_readiness']['status']='blocked'; t.a['issue_completion']='not_achieved'
 t.a['history']['events']=[{**event('measurement_failed'),'evidence_refs':t.c['source_refs']}]
check('integration_failed_all_ac_met',fail_integration,expected=0,contains='not_achieved')
check('integration_failure_event_omitted',lambda t:(fail_integration(t),t.a['history'].update(events=[])))
def failure_latch(t):
 fail_integration(t); t.save(); previous(t)
 e=next(e for e in t.a['evidence'] if e['id']=='compatibility'); e['result']='pass'
 t.a['integration_readiness']['checks']['compatibility']['verdict']='pass'; t.a['integration_readiness']['status']='ready'; t.a['issue_completion']='achieved'
 # Original final handoff retained from the positive template; measurements remain old.
 t.h=load(S/'examples/issue-completion/synthetic-achieved/handoff.json')
check('previous_failure_old_measurements_reused',failure_latch)
check('source_freshness_expired',lambda t:t.a['evidence'][-1].update(valid_until=NOW))
check('source_observed_in_future',lambda t:t.a['evidence'][-1].update(observed_at='2030-01-03T13:00:00Z'))
def one_missing(t):
 vid='runtime-persistence'; t.a['evidence']=[e for e in t.a['evidence'] if e['id']!=vid]
 for r in t.a['verification_results']:
  if r['verification_id']==vid:r.update(outcome='unverified',evidence_ids=[])
 for r in t.a['ac_results']:
  if vid in r['verification_ids']:r.update(outcome='unverified',evidence_ids=[e for e in r['evidence_ids'] if e!=vid])
 t.a['integration_readiness']['checks']['measurement_coverage'].update(verdict='pending',evidence_ids=[]); t.a['integration_readiness']['status']='blocked'; t.a['issue_completion']='unverified'
check('honest_missing_required_subcheck',one_missing,expected=0,contains='unverified')
# Legacy single-PR separation with every AC made premerge and met, still unmerged.
def readiness_single():
 p=O/'single_pr_all_premerge_unmerged'; p.mkdir(exist_ok=True)
 r=load(S/'examples/readiness/pr-ready-issue-unverified.json'); c=load(S/'examples/readiness/context.json')
 r['issue_integration_scope']=c['issue_integration_scope']='single_pr'
 for a in r['acceptance_criteria']:a['verification_phase']='premerge'
 c['acceptance_criteria']=copy.deepcopy(r['acceptance_criteria'])
 measure=next(e for e in r['evidence'] if e['kind']=='ac_measurement')
 measure['ac_ids']=[a['id'] for a in r['acceptance_criteria']]
 for result in r['ac_results']:result.update(outcome='met',evidence_ids=[measure['id']],deferred=None)
 write(p/'readiness.json',r);write(p/'context.json',c)
 for scope,outcome,expected in [('single_pr','unverified',0),('aggregate_required','achieved',1)]:
  r['issue_integration_scope']=c['issue_integration_scope']=scope;r['issue_completion']=outcome
  write(p/'readiness.json',r);write(p/'context.json',c)
  args=[sys.executable,str(S/'scripts/validate_readiness.py'),str(p/'readiness.json'),'--context',str(p/'context.json'),'--at','2030-01-01T12:00:00Z']
  z=subprocess.run(args,capture_output=True,text=True)
  # No private path/log text is copied to the public results.
  rows.append(dict(case='legacy_'+scope+'_'+outcome,expected_exit=expected,actual_exit=z.returncode,expected_output=None,passed=z.returncode==expected,stdout='Legacy record CLI returned '+str(z.returncode),stderr=''))
readiness_single()

write(O/'results.json',{'suite':'independent synthetic CLI cases','cases':rows,'total':len(rows),'passed':sum(r['passed'] for r in rows),'failed':sum(not r['passed'] for r in rows)})
print(json.dumps({'total':len(rows),'failed':[r['case'] for r in rows if not r['passed']]}))
