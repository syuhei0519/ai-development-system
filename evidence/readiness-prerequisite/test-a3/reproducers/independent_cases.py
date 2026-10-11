"""Independent synthetic boundary cases. Does not modify implementation or grant authority.
Usage: python independent_cases.py HEAD_CHECKOUT BASELINE_CHECKOUT OUTPUT_JSON
Exit 1 denotes a required case deviated from expectation; all cases still run.
"""
import copy, datetime, hashlib, importlib.util, json, os, pathlib, shutil, subprocess, sys, tempfile
R=pathlib.Path(sys.argv[1]).resolve(); B=pathlib.Path(sys.argv[2]).resolve(); OUT=pathlib.Path(sys.argv[3])
sys.path.insert(0,str(R))
from scripts.validate_readiness import validate, validate_handoff_pair
NOW=datetime.datetime(2030,1,1,12,tzinfo=datetime.timezone.utc)
F=R/'examples/readiness'
load=lambda name: json.loads((F/name).read_bytes())
D=load('preparation-ready.json'); C=load('preparation-context.json')
rows=[]
def record(name,expect,actual,detail):
 rows.append(dict(case=name,expected=expect,actual=actual,passed=expect==actual,detail=detail))
def run(name,mut=lambda d,c:None,expect='reject',standard=False):
 d,c=(load('pr-ready-issue-unverified.json'),load('context.json')) if standard else (copy.deepcopy(D),copy.deepcopy(C))
 mut(d,c)
 try: e=validate(d,c,NOW,artifact_root=F);actual='reject' if e else 'accept'
 except Exception as ex: e=[type(ex).__name__+': '+str(ex)];actual='exception'
 record(name,expect,actual,e)
def setpath(obj,path,value):
 for k in path[:-1]: obj=obj[k]
 obj[path[-1]]=copy.deepcopy(value)
def change(path,value,both=False):
 def f(d,c):
  setpath(d,path,value)
  if both:setpath(c,path,value)
 return f
run('preparation_normal_all_products_unverified',expect='accept')
record('fixture_product_and_issue_preservation',True,all(x['outcome']=='unverified' for x in D['ac_results']) and D['issue_completion']=='unverified' and D['acceptance_criteria']==load('pr-ready-issue-unverified.json')['acceptance_criteria'],[])
for ver in ['1.0','1.1']:
 def standard(d,c,ver=ver):
  for x in (d,c):
   x['schema_version']=ver
   if ver=='1.1':x.update(pr_kind='standard',preparation=None)
 run('standard_'+ver+'_normal',standard,'accept',True)
 def empty(d,c,fn=standard):
  fn(d,c); d['pr_ac_ids']=c['pr_ac_ids']=[]
 run('standard_'+ver+'_empty',empty,standard=True)
for path,values in [(('schema_version',),['1.2','2.0',None,1.1]),(('pr_kind',),['unknown','',True]),(('deployment_effect',),['automatic','unknown']), (('issue_integration_scope',),['single_pr','unknown'])]:
 for v in values:run('enum_'+'.'.join(path)+'_'+str(v),change(path,v,True))
for field in C['preparation']:
 run('preparation_missing_'+field,lambda d,c,f=field:[x['preparation'].pop(f) for x in (d,c)])
for field in ['related_ac_ids','conditions','artifacts','followup','product_outcomes']:
 run('preparation_empty_'+field,change(('preparation',field),[],True))
for val in ['', '  ',None,True]:run('scope_reason_'+repr(val),change(('preparation','scope_reason'),val,True))
for collection in ['conditions','artifacts','followup','product_outcomes']:
 first=C['preparation'][collection][0]
 for field in first:
  run(collection+'_missing_'+field,lambda d,c,col=collection,f=field:[x['preparation'][col][0].pop(f) for x in (d,c)])
 for val in [None,True,'x',{}]:run(collection+'_wrong_type_'+repr(val),change(('preparation',collection),val,True))
 run(collection+'_duplicate',change(('preparation',collection),[first,first],True))
 run(collection+'_extra_field',lambda d,c,col=collection:[x['preparation'][col][0].update(unexpected='synthetic') for x in (d,c)])
for val in [[],['UNKNOWN'],['SYNTHETIC-AC-1','SYNTHETIC-AC-1']]:run('related_AC_'+repr(val),change(('preparation','related_ac_ids'),val,True))
for field in ['subject','pr_kind','preparation','acceptance_criteria']:
 run('context_mismatch_'+field,lambda d,c,f=field:c.update({f:None}))
for path,val in [(('preparation','scope_reason'),'changed'),(('preparation','conditions',0,'verbatim'),'changed'),(('preparation','artifacts',0,'sha256'),'0'*64), (('preparation','followup',0,'owner'),'changed')]:
 run('context_only_'+str(path),lambda d,c,p=path,v=val:setpath(c,p,v))
for field in ['head_sha','base_sha','target_revision','config_revision','merge_group_sha']:
 run('context_subject_'+field,lambda d,c,f=field:c['subject'].update({f:'f'*40}))
for target in ['assessment','context']:
 run('extra_top_'+target,lambda d,c,t=target:(d if t=='assessment' else c).update(extra='synthetic'))
for key in ['conditions','artifacts','product_outcomes','followup']:
 def dup(d,c,key=key):
  for x in (d,c):
   v=copy.deepcopy(x['preparation'][key][0]);v[next(k for k in v if k not in ('id','ac_id'))]='different';x['preparation'][key].append(v)
 run('duplicate_id_distinct_value_'+key,dup)
for out in ['unverified','not_met']:
 run('condition_'+out,change(('preparation_results',0,'outcome'),out))
run('condition_missing',change(('preparation_results',),[]))
run('condition_unknown',change(('preparation_results',0,'condition_id'),'UNKNOWN'))
run('condition_no_proof',change(('preparation_results',0,'evidence_ids'),[]))
run('condition_CI_substitution',change(('preparation_results',0,'evidence_ids'),['merge-ci']))
run('condition_is_product_AC',change(('preparation','conditions',0,'id'),'SYNTHETIC-AC-1',True))
for kind in ['independent_test','ai_review','preparation_measurement']:
 for field,val in [('kind','ci'),('subject',dict(D['subject'],head_sha='f'*40)),('artifact_ids',[]),('artifact_ids',['UNKNOWN']),('condition_ids',[]),('condition_ids',['UNKNOWN']),('ac_ids',['UNKNOWN']),('valid_until','2030-01-01T12:00:00Z')]:
  run('proof_'+kind+'_'+field+'_'+str(val),lambda d,c,k=kind,f=field,v=val:next(e for e in d['evidence'] if e['kind']==k).update({f:v}))
 for field in ['kind','subject','producer','independent','ac_ids','condition_ids','artifact_ids']:
  run('proof_missing_'+kind+'_'+field,lambda d,c,k=kind,f=field:next(e for e in d['evidence'] if e['kind']==k).pop(f))
 if kind!='preparation_measurement':
  for field,val in [('producer',D['implementation_actor']),('independent',False)]:
   run('proof_independence_'+kind+'_'+field,lambda d,c,k=kind,f=field,v=val:next(e for e in d['evidence'] if e['kind']==k).update({f:v}))
  # Product AC claims are optional on process evidence; conditions/artifacts are its binding.
  run('process_proof_empty_product_AC_'+kind,lambda d,c,k=kind:next(e for e in d['evidence'] if e['kind']==k).update(ac_ids=[]),expect='accept')
for group in ['implementation','merge']:
 for key in D[group+'_readiness']['checks']:
  for state in ['fail','pending','not_applicable']:
   if key=='github_queue' and state=='not_applicable':continue
   run('gate_'+group+'_'+key+'_'+state,change((group+'_readiness','checks',key,'verdict'),state))
  run('gate_'+group+'_'+key+'_missing_proof',change((group+'_readiness','checks',key,'evidence_ids'),[]))
run('approval_evidence_kind_mismatch',lambda d,c:next(e for e in d['evidence'] if e['id']=='merge-authorization').update(kind='ci'))
run('queue_required_missing_group',lambda d,c:c['github_requirements'].update(queue=True))
run('no_PR',lambda d,c:[x['subject'].update(pr_number=None) for x in (d,c)])
run('expired_policy',lambda d,c:c.update(policy_valid_until=NOW.isoformat()))
run('future_evaluation',change(('evaluated_at',),'2030-01-01T13:00:00Z'))
run('premature_achieved',change(('issue_completion',),'achieved'))
run('aggregate_integration_pass',change(('issue_integration','verdict'),'pass'))
run('premerge_deferral',change(('ac_results',0,'deferred'),load('pr-ready-issue-unverified.json')['ac_results'][1]['deferred']))
def known_failure(d,c):
 d['ac_results'][0].update(outcome='not_met',evidence_ids=['measurement']);d['issue_completion']='not_achieved'
 for x in (d,c):x['preparation']['product_outcomes'][0]['outcome']='not_met'
run('known_product_failure_blocks',known_failure)
def blocked(d,c):known_failure(d,c);d['merge_readiness']['status']='blocked'
run('known_failure_honest_blocked',blocked,'accept')
def hide(d,c):blocked(d,c);d['ac_results'][0].update(outcome='unverified',evidence_ids=[])
run('known_failure_hidden',hide)
for field,val in [('revision','f'*40),('size_bytes',1),('size_bytes',True),('sha256','0'*64),('locator','../README.md'),('locator','https://example.invalid/file'),('locator','missing-file')]:
 run('artifact_'+field+'_'+str(val),change(('preparation','artifacts',0,field),val,True))
# CLI checks materialize all synthetic data, pin raw context, never derive a real authority.
with tempfile.TemporaryDirectory(prefix='independent-readiness-') as t:
 p=pathlib.Path(t);art=p/'preparation-artifact.txt'; original=(F/art.name).read_bytes()
 def cli(d=None,c=None,pin=True,timeout=10,baseline=False):
  (p/'ready.json').write_text(json.dumps(d or D)); raw=json.dumps(c or C).encode();(p/'context.json').write_bytes(raw)
  cmd=[sys.executable,str((B if baseline else R)/'scripts/validate_readiness.py'),str(p/'ready.json'),'--context',str(p/'context.json'),'--at',NOW.isoformat()]
  if pin is not False:cmd+=['--context-sha256',hashlib.sha256(raw).hexdigest() if pin is True else pin]
  try:
   r=subprocess.run(cmd,capture_output=True,text=True,timeout=timeout,cwd=R)
   return ('accept' if r.returncode==0 else 'reject'),dict(returncode=r.returncode,output=(r.stdout+r.stderr).replace(t,'<SYNTHETIC_ROOT>'))
  except subprocess.TimeoutExpired:return 'timeout',{'limit_seconds':timeout}
 art.write_bytes(original)
 for name,pin,exp in [('cli_correct_pin',True,'accept'),('cli_no_pin',False,'reject'),('cli_wrong_pin','0'*64,'reject')]:
  act,detail=cli(pin=pin);record(name,exp,act,detail)
 act,detail=cli(baseline=True,pin=False);record('old_consumer_rejects_1.1','reject',act,detail)
 changed=copy.deepcopy(C);changed['policy_evidence']='synthetic changed context'
 act,detail=cli(c=changed,pin=hashlib.sha256(json.dumps(C).encode()).hexdigest());record('cli_context_bytes_tampered','reject',act,detail)
 for name,mode in [('bytes_changed','bytes'),('directory','dir'),('unreadable','permission'),('external_symlink','symlink')]:
  art.unlink()
  if mode=='bytes':art.write_bytes(original+b'changed')
  elif mode=='dir':art.mkdir()
  elif mode=='permission':art.write_bytes(original);art.chmod(0)
  else:art.symlink_to(F/art.name)
  act,detail=cli();record('artifact_'+name,'reject',act,detail)
  if art.is_dir():art.rmdir()
  else:
   if mode=='permission':art.chmod(0o600)
   art.unlink()
  art.write_bytes(original)
 # A FIFO is not a fixed regular artifact and must not hang the verifier.
 art.unlink();os.mkfifo(art)
 act,detail=cli(timeout=2);record('artifact_FIFO_fail_closed','reject',act,detail)
 art.unlink();art.write_bytes(original)
 # Readiness/Handoff identical-file and digest bindings (existing contract).
 d=copy.deepcopy(D);h=load('manager.handoff.json');h.pop('final_assessment',None)
 raw=json.dumps(d).encode();rp=p/'readiness.json';rp.write_bytes(raw)
 a=next(a for a in h['artifacts'] if a['id']==d['artifact_id']);a.update(locator=rp.name,revision='sha256:'+hashlib.sha256(raw).hexdigest())
 args=dict(readiness_bytes=raw,readiness_path=rp,handoff_path=p/'handoff.json')
 e=validate_handoff_pair(d,h,**args);record('handoff_valid_pair','accept','reject' if e else 'accept',e)
 for field,val in [('id','unknown'),('kind','document'),('revision','sha256:'+'0'*64),('locator','other.json'),('locator','missing.json')]:
  (p/'other.json').write_bytes(raw);hh=copy.deepcopy(h);aa=next(a for a in hh['artifacts'] if a['id']==d['artifact_id']);aa[field]=val
  e=validate_handoff_pair(d,hh,**args);record('handoff_'+field+'_'+val,'reject','reject' if e else 'accept',e)
 rp.write_bytes(raw+b'\n');e=validate_handoff_pair(d,h,**args);record('handoff_changed_bytes','reject','reject' if e else 'accept',e)
# Independent historical baseline reproduction via baseline CLI, no upstream code execution.
with tempfile.TemporaryDirectory() as t:
 p=pathlib.Path(t);d=load('pr-ready-issue-unverified.json');c=load('context.json')
 for case in ['empty_scope','unverified_premerge']:
  d['pr_ac_ids']=c['pr_ac_ids']=[] if case=='empty_scope' else ['SYNTHETIC-AC-1']
  if case=='unverified_premerge':d['ac_results'][0].update(outcome='unverified',evidence_ids=[])
  (p/'d.json').write_text(json.dumps(d));(p/'c.json').write_text(json.dumps(c))
  r=subprocess.run([sys.executable,str(B/'scripts/validate_readiness.py'),str(p/'d.json'),'--context',str(p/'c.json'),'--at',NOW.isoformat()],capture_output=True,text=True)
  record('baseline_obstruction_'+case,'reject','reject' if r.returncode else 'accept',{'returncode':r.returncode,'output':(r.stdout+r.stderr).replace(t,'<SYNTHETIC_ROOT>')})
OUT.write_text(json.dumps({'head':'3f41a0470fd0b7a2199be0b947bb22284e993e2f','cases':rows,'total':len(rows),'passed':sum(r['passed'] for r in rows),'failed':sum(not r['passed'] for r in rows)},ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'total':len(rows),'passed':sum(r['passed'] for r in rows),'deviations':[r for r in rows if not r['passed']]},ensure_ascii=False))
sys.exit(int(any(not r['passed'] for r in rows)))
