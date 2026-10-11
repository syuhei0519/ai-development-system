# Edited derivative of Test1 aggregate_reproducer.py: explicit 1.1 mapping, fixed artifact delivery, no product claim by preparation.
"""Synthetic end-to-end: a merged preparation member cannot enter Issue Completion.
Usage: python aggregate_reproducer.py HEAD_CHECKOUT OUTPUT_JSON
No product observations, source edits or authority. All fixtures generated in temporary storage.
"""
import copy,hashlib,json,pathlib,subprocess,sys,tempfile
R=pathlib.Path(sys.argv[1]).resolve();out=pathlib.Path(sys.argv[2]);sys.path[:0]=[str(R),str(R/'tests')]
from completion_fixture import build,save,write,handoff
from scripts.validate_readiness import validate,instant
rows=[]
with tempfile.TemporaryDirectory(prefix='aggregate-preparation-') as temp:
 p=pathlib.Path(temp);a,c=build(p)
 def execute(case, expected=0):
  pin=save(p,a,c)
  cmd=[sys.executable,str(R/'scripts/validate_issue_completion.py'),str(p/'completion.json'),'--context',str(p/'context.json'),'--context-sha256',pin,'--handoff',str(p/'handoff.json'),'--at','2030-01-03T12:00:00Z']
  x=subprocess.run(cmd,capture_output=True,text=True,cwd=R)
  rows.append(dict(case=case,expected_exit=expected,actual_exit=x.returncode,output=(x.stdout+x.stderr).replace(temp,'<SYNTHETIC_ROOT>')))
 execute('existing_standard_aggregate_control')
 a['schema_version']=c['schema_version']='1.1'
 for r in c['required_prs']:r.update(pr_kind='standard',preparation=None)
 d=json.loads((R/'examples/readiness/preparation-ready.json').read_bytes());rc=json.loads((R/'examples/readiness/preparation-context.json').read_bytes())
 # First member is now preparation; the remaining product members still provide all measured product ACs.
 subject=json.loads((p/'app-readiness.json').read_bytes())['subject']
 d['subject']=subject;rc['subject']=copy.deepcopy(subject)
 for e in d['evidence']:e['subject']=copy.deepcopy(subject)
 for x in (d,rc):x['preparation']['artifacts'][0]['revision']=subject['target_revision']
 (p/'preparation-artifact.txt').write_bytes((R/'examples/readiness/preparation-artifact.txt').read_bytes())
 rr=write(p,'app-readiness.json',d);rr['id']=d['artifact_id']
 a['member_results'][0]['readiness_ref']={**rr,'id':'app-readiness'}
 a['member_results'][0]['readiness_context_ref']=write(p,'app-context.json',rc)
 a['member_results'][0]['readiness_handoff_ref']=write(p,'app-handoff.json',handoff(c['issue'],rr))
 # Do not claim this preparation member measured product premerge checks.
 c['required_verifications']=[v for v in c['required_verifications'] if v['verification_id']!='app-pre']
 a['verification_results']=[v for v in a['verification_results'] if v['verification_id']!='app-pre']
 a['evidence']=[v for v in a['evidence'] if v['id']!='app-pre']
 for v in a['ac_results']:
  for k in ('verification_ids','evidence_ids'):v[k]=[x for x in v[k] if x!='app-pre']
 a['integration_readiness']['checks']['measurement_coverage']['evidence_ids'].remove('app-pre')
 # Product measurements target standard members; full merge/integration vectors retain preparation.
 for v in c['required_verifications']:v['member_ids']=[x for x in v['member_ids'] if x!='app']
 for e in a['evidence']:
  if e['kind']=='ac_measurement':e['member_ids']=[x for x in e['member_ids'] if x!='app']
 c['required_prs'][0].update(pr_kind='preparation',preparation=dict(related_ac_ids=copy.deepcopy(d['preparation']['related_ac_ids']),artifact_refs=[dict(artifact_id=d['preparation']['artifacts'][0]['id'],ref=write(p,'preparation-artifact.txt',(R/'examples/readiness/preparation-artifact.txt').read_bytes()))]))
 direct=validate(d,rc,instant('2030-01-01T13:00:00Z'),artifact_root=p)
 rows.append(dict(case='preparation_historical_readiness_direct_with_root',expected_errors=[],actual_errors=direct))
 missing=validate(d,rc,instant('2030-01-01T13:00:00Z'))
 rows.append(dict(case='missing_root_still_rejected',expected_errors=['preparation artifact scaffold: materialized artifact root required'],actual_errors=missing))
 c['required_prs'][0]['ac_ids']=[]
 execute('preparation_empty_product_scope_in_aggregate')
 c['required_prs'][0]['ac_ids']=copy.deepcopy(d['preparation']['related_ac_ids'])
 execute('related_product_scope_cannot_substitute_empty_preparation_scope', expected=1)
out.write_text(json.dumps({'subject':'checkout argument; see revision.json','synthetic':True,'results':rows},indent=2)+'\n')
print(out.read_text())
sys.exit(int(any(r.get('actual_exit',0)!=r.get('expected_exit',0) or r.get('actual_errors',[])!=r.get('expected_errors',[]) for r in rows)))
