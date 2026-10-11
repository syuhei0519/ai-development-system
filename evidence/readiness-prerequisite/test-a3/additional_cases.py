"""Attempt3 independent synthetic tests. Usage: python additional_cases.py HEAD BASE OUT.
Uses fixture construction only; assertions and fault injections belong to Test3.
No implementation edits, product operations, or authority claims.
"""
import copy, datetime, hashlib, importlib.metadata, json, os, pathlib, socket, subprocess, sys, tempfile
from unittest.mock import patch
R,B,OUT=map(lambda x:pathlib.Path(x).resolve(),sys.argv[1:])
sys.path[:0]=[str(R),str(R/'tests')]
from preparation_completion_fixture import build_preparation
from completion_fixture import build,save,write,handoff,NOW
from scripts import regular_file as rf
from scripts import validate_issue_completion as agg
from jsonschema import Draft202012Validator
rows=[]
def record(name,expected,actual,detail=''):
 rows.append(dict(case=name,expected=expected,actual=actual,passed=expected==actual,detail=detail))
def rejection(name,fn):
 try: value=fn();record(name,'reject','accept',str(value))
 except (OSError,ValueError,AttributeError) as e:record(name,'reject','reject',type(e).__name__+': '+str(e))
def rewrite(p,a,c):
 ar=write(p,'completion.json',a);ar['id']=a['artifact_id']
 write(p,'handoff.json',handoff(c['issue'],ar,a['issue_completion'] if a['issue_completion']=='achieved' else None,[e for e in a['evidence'] if e['kind']=='ac_measurement']))
def history_edit(p,a,c,fn):
 d=json.loads((p/'app-readiness.json').read_bytes());rc=json.loads((p/'app-context.json').read_bytes())
 fn(d,rc)
 rr=write(p,'app-readiness.json',d);rr['id']=d['artifact_id']
 a['member_results'][0].update(readiness_ref={**rr,'id':'app-readiness'},readiness_context_ref=write(p,'app-context.json',rc),readiness_handoff_ref=write(p,'app-handoff.json',handoff(c['issue'],rr)))
def case(name,mut=lambda p,a,c:None,expected=('ready','achieved'),after=None,old=False,pin_mode=None):
 with tempfile.TemporaryDirectory(prefix='test3-synthetic-') as t:
  p=pathlib.Path(t);a,c=build_preparation(p);mut(p,a,c);pin=save(p,a,c)
  if after:after(p,a,c);rewrite(p,a,c)
  if pin_mode=='missing':pin=None
  if pin_mode=='wrong':pin='0'*64
  if pin_mode=='tamper':(p/'context.json').write_bytes((p/'context.json').read_bytes()+b'\n')
  try:
   if old:
    cmd=[sys.executable,str(B/'scripts/validate_issue_completion.py'),str(p/'completion.json'),'--context',str(p/'context.json'),'--context-sha256',pin,'--handoff',str(p/'handoff.json'),'--at',NOW]
    res=subprocess.run(cmd,capture_output=True,text=True,timeout=15);actual='reject' if res.returncode else 'accept';detail=res.stdout+res.stderr
   else:actual=agg.validate_files(p/'completion.json',p/'context.json',pin,p/'handoff.json',now=agg.instant(NOW));detail=''
  except (ValueError,OSError) as e:actual='reject';detail=type(e).__name__+': '+str(e)
  record(name,expected,actual,detail.replace(t,'<SYNTHETIC_ROOT>'))
def hist(fn):return lambda p,a,c:history_edit(p,a,c,fn)
case('typed_preparation_full_product_merge_deploy_achieved')
case('old_aggregate_consumer_rejects_v11',expected='reject',old=True)
for mode in ('missing','wrong','tamper'):case('aggregate_context_pin_'+mode,expected='reject',pin_mode=mode)
for version in ('1.0','1.2','unknown',True,None):
 case('aggregate_invalid_version_'+str(version),lambda p,a,c,v=version:(a.update(schema_version=v),c.update(schema_version=v)),expected='reject')
for field in ('required_prs','current_members','required_verifications','current_deployments','scope_decisions'):
 case('missing_required_collection_'+field,lambda p,a,c,k=field:c[k].pop(0),expected='reject')
for field in ('member_results','verification_results','deployment_results'):
 case('missing_result_'+field,lambda p,a,c,k=field:a[k].pop(0),expected='reject')
for field in ('verbatim','source','verification_phase'):
 def changed_original(p,a,c,k=field):
  c['issue']['acceptance_criteria'][0][k]='postmerge' if k=='verification_phase' else 'synthetic changed'
  a['acceptance_criteria']=copy.deepcopy(c['issue']['acceptance_criteria'])
 case('historical_original_'+field,changed_original,expected='reject')
for field in ('head_sha','base_sha','target_revision','config_revision','merge_group_sha'):
 case('historical_subject_'+field,lambda p,a,c,k=field:c['current_members'][0].update({k:'9'*40}),expected='reject')
case('historical_scope_mismatch',lambda p,a,c:c['required_prs'][1].update(ac_ids=['SYNTHETIC-AC-2']),expected='reject')
case('historical_kind_mismatch',lambda p,a,c:c['required_prs'][0].update(pr_kind='standard',preparation=None,ac_ids=['SYNTHETIC-AC-1']),expected='reject')
for key in ('ci','independent_test','ai_review','github_checks','github_reviews','github_ruleset','github_queue','authorization','dependencies'):
 case('historical_failed_gate_'+key,hist(lambda d,rc,k=key:d['merge_readiness']['checks'][k].update(verdict='fail')),expected='reject')
case('historical_context_condition_mismatch',hist(lambda d,rc:rc['preparation']['conditions'][0].update(verbatim='changed synthetic condition')),expected='reject')
case('historical_expired_policy',hist(lambda d,rc:rc.update(policy_valid_until='2030-01-01T13:00:00Z')),expected='reject')
case('historical_expired_test',hist(lambda d,rc:next(e for e in d['evidence'] if e['kind']=='independent_test').update(valid_until='2030-01-01T13:00:00Z')),expected='reject')
case('preparation_product_target',lambda p,a,c:c['required_verifications'][-1].update(member_ids=['app']),expected='reject')
for field in ('merge_actor','state','merge_sha'):
 value={'merge_actor':'synthetic-unapproved','state':'open','merge_sha':None}[field]
 case('preparation_merge_'+field,lambda p,a,c,k=field,v=value:c['current_members'][0].update({k:v}),expected='reject')
case('preparation_merge_permission_missing',lambda p,a,c:c['scope_decisions'][1]['member_ids'].remove('app'),expected='reject')
case('preparation_required_scope_permission_missing',lambda p,a,c:c['scope_decisions'][0]['member_ids'].remove('app'),expected='reject')
case('delivery_approval_not_merge_permission',lambda p,a,c:c['scope_decisions'][1].update(decision_kind='delivery',allowed_actions=['publish','consume']),expected='reject')
case('deploy_permission_missing',lambda p,a,c:c['scope_decisions'][1]['allowed_actions'].remove('deploy'),expected='reject')
case('operation_permission_expired',lambda p,a,c:c['scope_decisions'][1].update(valid_until=NOW),expected='reject')
case('merge_binding_wrong',lambda p,a,c:next(e for e in a['evidence'] if e['id']=='app-merge')['merge'].update(merge_sha='9'*40),expected='reject')
def missing_vector(p,a,c):
 e=next(e for e in a['evidence'] if e['id']=='integration');e['binding']['merged_members'].pop(0)
 e['source_ref']=write(p,e['id']+'-observation.json',dict(document_type='issue_completion_observation',schema_version='1.0',observation={k:v for k,v in e.items() if k!='source_ref'}))
case('full_merge_vector_cannot_omit_preparation',expected='reject',after=missing_vector)
for kind in ('scope','authorization','deployment','compatibility','integration'):
 case('integration_coverage_cannot_omit_preparation_'+kind,lambda p,a,c,k=kind:next(e for e in a['evidence'] if e['kind']==k)['member_ids'].remove('app'),expected='reject')
for field,value in [('state','failed'),('state','pending'),('deploy_actor','synthetic-unapproved'),('config_sha256','0'*64),('environment_id','synthetic-other'),('workload_id','synthetic-other')]:
 case('deployment_'+field+'_'+str(value),lambda p,a,c,k=field,v=value:c['current_deployments'][0].update({k:v}),expected='reject')
case('deployment_sources_missing',lambda p,a,c:c['current_deployments'][0].update(sources=copy.deepcopy(c['current_deployments'][0]['sources'][:-1])),expected='reject')
case('deployment_image_wrong',lambda p,a,c:c['current_deployments'][0].update(images=[dict(x,digest='sha256:'+'0'*64) for x in c['current_deployments'][0]['images']]),expected='reject')
for field,value in [('producer','synthetic-other'),('result','fail'),('kind','ci'),('phase','premerge'),('environment_id','synthetic-other'),('method','synthetic-other')]:
 case('product_measurement_'+field,lambda p,a,c,k=field,v=value:next(e for e in a['evidence'] if e['id']=='runtime-response').update({k:v}),expected='reject')
case('product_measurement_missing',lambda p,a,c:a['verification_results'][-1].update(evidence_ids=[]),expected='reject')
case('only_preparation_cannot_achieve',lambda p,a,c:[r.update(pr_kind='preparation',ac_ids=[],preparation=copy.deepcopy(c['required_prs'][0]['preparation'])) for r in c['required_prs']],expected='reject')
for mode in ('missing','wrong_root','size','digest','duplicate','unknown','bytes','symlink'):
 def artifact(p,a,c,mode=mode):
  refs=c['required_prs'][0]['preparation']['artifact_refs'];ref=refs[0]['ref'];f=p/'preparation-artifact.txt'
  if mode=='missing':refs.clear()
  elif mode=='wrong_root':refs[0]['ref']=write(p,'wrong.txt',f.read_bytes())
  elif mode=='size':ref['size']+=1
  elif mode=='digest':ref['sha256']='0'*64
  elif mode=='duplicate':refs.append(copy.deepcopy(refs[0]))
  elif mode=='unknown':refs[0]['artifact_id']='UNKNOWN'
  elif mode=='bytes':f.write_bytes(b'changed synthetic bytes')
  else:f.rename(p/'real.txt');f.symlink_to(p/'real.txt')
 case('aggregate_artifact_'+mode,artifact,expected='reject')
with tempfile.TemporaryDirectory(prefix='test3-reader-') as t:
 p=pathlib.Path(t);f=p/'regular';f.write_bytes(b'fixed')
 record('linux_regular_reader','6669786564',rf.read_regular(f).hex())
 fifo=p/'fifo';os.mkfifo(fifo);sock=socket.socket(socket.AF_UNIX);sock.bind(str(p/'socket'))
 (p/'link').symlink_to(f);(p/'ancestor').symlink_to(p,target_is_directory=True)
 for name,path in [('fifo',fifo),('socket',p/'socket'),('directory',p),('symlink',p/'link'),('ancestor_symlink',p/'ancestor'/'regular'),('device',pathlib.Path('/dev/null'))]:
  calls=[];realopen=os.open
  def spy(path,flags,*args,**kwargs):calls.append(str(path));return realopen(path,flags,*args,**kwargs)
  with patch.object(rf.os,'open',side_effect=spy):rejection('reader_'+name,lambda q=path:rf.read_regular(q))
  record('reader_no_data_open_'+name,False,any(x.startswith('/proc/self/fd/') for x in calls))
 sock.close()
 for loc in ('../regular','/tmp/outside','a/../regular','./regular','a//b','a\\b','https://example.invalid/a',''):
  rejection('containment_'+repr(loc),lambda loc=loc:rf.artifact_path(p,loc))
 rejection('bundle_root_escape',lambda:agg.Bundle(p).read(R/'README.md'))
 f.write_bytes(b'x'*rf.MAX_FILE)
 record('16MiB_inclusive',rf.MAX_FILE,len(rf.read_regular(f)))
 with f.open('ab') as fh:fh.write(b'x')
 rejection('16MiB_plus_one',lambda:rf.read_regular(f))
 f.write_bytes(b'fixed')
 rejection('declared_bound',lambda:rf.read_regular(f,limit=4))
 rejection('caller_cannot_raise_hard_limit',lambda:rf.read_regular(f,limit=rf.MAX_FILE+1))
 # Deterministic adversarial reads: file grew immediately after stat/open. Byte
 # requests remain <= declared bound+1 even if an injected source never EOFs.
 counts=[]
 def endless(fd,n):counts.append(n);return b'x'*n
 with patch.object(rf.os,'read',side_effect=endless):rejection('bounded_infinite_source',lambda:rf.read_regular(f,limit=5))
 record('bounded_read_requested_bytes',6,sum(counts))
 realread=os.read
 for mode in ('replace','grow','same_size','ancestor'):
  sub=p/('mutation-'+mode);sub.mkdir();g=sub/'artifact';g.write_bytes(b'fixed');done=[False]
  def mutate(fd,n):
   raw=realread(fd,n)
   if not done[0]:
    done[0]=True
    if mode=='replace':(sub/'new').write_bytes(b'fixed');(sub/'new').replace(g)
    elif mode=='ancestor':sub.rename(p/(mode+'-old'));sub.mkdir();g.write_bytes(b'fixed')
    else:g.write_bytes(b'grown payload' if mode=='grow' else b'other')
   return raw
  with patch.object(rf.os,'read',side_effect=mutate):rejection('during_read_'+mode,lambda:rf.read_regular(g,limit=5))
 realopen=os.open;swapped=[False]
 def swap(path,flags,*args,**kwargs):
  if path=='regular' and not swapped[0]:swapped[0]=True;f.unlink();os.mkfifo(f)
  return realopen(path,flags,*args,**kwargs)
 with patch.object(rf.os,'open',side_effect=swap):rejection('stat_to_open_fifo_swap',lambda:rf.read_regular(f))
 f.unlink();f.write_bytes(b'fixed')
 opath=os.O_PATH
 try:
  del os.O_PATH
  rejection('unsupported_O_PATH_fail_closed_simulated',lambda:rf.read_regular(f))
 finally:os.O_PATH=opath
 def no_proc(path,flags,*args,**kwargs):
  if str(path).startswith('/proc/self/fd/'):raise FileNotFoundError('synthetic missing proc filesystem')
  return realopen(path,flags,*args,**kwargs)
 with patch.object(rf.os,'open',side_effect=no_proc):rejection('unsupported_proc_fail_closed_simulated',lambda:rf.read_regular(f))
 # Mutation after semantic validation, immediately before final all-file reread.
 a,c=build_preparation(p);pin=save(p,a,c);realfinish=agg.Bundle.finish
 def finish_changed(bundle):
  artifact=p/'preparation-artifact.txt';original=artifact.read_bytes();artifact.write_bytes(b'X'+original[1:]);return realfinish(bundle)
 with patch.object(agg.Bundle,'finish',finish_changed):
  rejection('aggregate_final_reread_preparation_artifact',lambda:agg.validate_files(p/'completion.json',p/'context.json',pin,p/'handoff.json',now=agg.instant(NOW)))
for schema in sorted((R/'contracts').glob('*.schema.json')):
 try:Draft202012Validator.check_schema(json.loads(schema.read_bytes()));record('schema_'+schema.name,True,True)
 except Exception as e:record('schema_'+schema.name,True,False,str(e))
protected=['contracts/handoff.schema.json','scripts/validate_handoff.py','scripts/consume_delivery.py','scripts/validate_knowledge.py','contracts/issue-completion.schema.json','contracts/issue-completion-context.schema.json']
protected += [str(p.relative_to(R)) for p in (R/'contracts').glob('*v1.2.schema.json')]+[str(p.relative_to(R)) for p in (R/'contracts').glob('knowledge*.schema.json')]
for name in sorted(set(protected)):record('compatibility_bytes_'+name,(B/name).read_bytes()==(R/name).read_bytes(),True)
result=dict(subject=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(),synthetic=True,completed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),total=len(rows),passed=sum(r['passed'] for r in rows),cases=rows)
OUT.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
print(json.dumps(dict(total=len(rows),passed=result['passed'],deviations=[r for r in rows if not r['passed']]),ensure_ascii=False))
sys.exit(int(result['passed']!=len(rows)))
