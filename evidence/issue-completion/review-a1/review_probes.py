#!/usr/bin/env python3
"""Independent Review synthetic probes. No source edits, network, or product execution.
Usage: python review_probes.py HEAD_CHECKOUT NEW_OUTPUT
Preserved upstream helper definitions are loaded without executing their cases.
"""
import ast
import copy
import json
from pathlib import Path
import sys

head, output = map(Path, sys.argv[1:3])
helper=Path(__file__).parent/'upstream/upstream/independent_cases.py'
tree=ast.parse(helper.read_bytes(),filename=str(helper))
tree.body=[n for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom,ast.FunctionDef,ast.ClassDef,ast.Assign))]
old=sys.argv;sys.argv=[str(helper),str(head),str(output)]
ns={'__name__':'review_helpers','__file__':str(helper)}
exec(compile(tree,str(helper),'exec'),ns);sys.argv=old
check,previous,event,write,load,ref=[ns[k] for k in ('check','previous','event','write','load','ref')]

def unseen_definition(t, mode):
    # Previous pending v1 has IDs but no ac_measurement definitions. Keep its raw bytes.
    old=load(head/'examples/issue-completion/synthetic-pending/completion.json')
    write(t.p/'previous.json',old);r=ref(t.p/'previous.json')
    t.c['previous_assessment_sha256']=r['sha256']
    t.a['history']={'previous_ref':r,'events':[event(),{**event('head_changed'),'event_id':'first-merge-heads','affected_ids':['app','config','client']}]}
    t.extra=['--previous',str(t.p/'previous.json'),'--previous-sha256',r['sha256']]
    t.c['required_verifications'][-1]['method']+=' new approved method'
    t.a['evidence'][-1]['method']+=' new approved method'
    if mode:
        oldscope=t.c['scope_revision']
        write(t.p/'scope.txt',('synthetic scope with full definitions: '+json.dumps(t.c['required_verifications'],sort_keys=True)+'\n').encode())
        scope=ref(t.p/'scope.txt')
        def replace(x):
            if isinstance(x,dict):
                if set(x)=={'id','locator','sha256','size'} and x['locator']=='scope.txt':return copy.deepcopy(scope)
                return {k:replace(v) for k,v in x.items()}
            if isinstance(x,list):return [replace(v) for v in x]
            return scope['sha256'] if x==oldscope else x
        t.c=replace(t.c);t.a=replace(t.a)
    if mode==2:t.a['history']['events'].append({**event('required_set_changed'),'event_id':'new-scope','affected_ids':['runtime-persistence'],'evidence_refs':t.c['source_refs']})

check('known_limit_unmeasured_definition_then_full_measurements',lambda t:unseen_definition(t,0),expected=0,contains='achieved')
check('unmeasured_definition_scope_bump_needs_event',lambda t:unseen_definition(t,1))
check('unmeasured_definition_scope_and_event_with_full_measurements',lambda t:unseen_definition(t,2),expected=0,contains='achieved')
def missing_measurement(t):
    unseen_definition(t,2)
    t.a['verification_results'][-1]['evidence_ids']=[]
    t.a['evidence'].pop()
check('updated_scope_cannot_replace_missing_measurement',missing_measurement)

def source_type(t):
    e=t.a['evidence'][-1]; p=t.p/e['source_ref']['locator'];s=load(p)
    s['observation']['independent']=1
    write(p,s);e['source_ref']=ref(p);write(t.p/'completion.json',t.a)
check('observation_boolean_integer_mismatch',after=source_type)

def extra_failure(t):
    e=copy.deepcopy(t.a['evidence'][-1]);e.update(id='unreferenced-failure',kind='failure',result='fail',verification_ids=[],ac_ids=[])
    e['source_ref']['locator']='unreferenced-failure.json';t.a['evidence'].append(e)
    t.a['history']['events']=[{**event('measurement_failed'),'evidence_refs':t.c['source_refs']}]
check('extra_active_failure_cannot_achieve',extra_failure)

def previous_symlink(t):
    p=t.p/'previous.json';p.rename(t.p/'real-previous.json');p.symlink_to('real-previous.json')
check('previous_leaf_symlink',previous,after=previous_symlink)
def previous_bytes(t):
    p=t.p/'previous.json';p.write_bytes(p.read_bytes()+b'\n')
check('previous_one_byte_mutation',previous,after=previous_bytes)
def ancestor(t):
    parent=t.p.parent; original=t.p
    real=parent/(t.p.name+'-real');original.rename(real);original.symlink_to(real.name,target_is_directory=True)
check('assessment_root_symlink',after=ancestor)

def scope_receipt(t):
    t.c['scope_decisions'][1]['decision_kind']='delivery';t.c['scope_decisions'][1]['allowed_actions']=['consume','publish']
check('delivery_approval_cannot_authorize_merge_deploy',scope_receipt)

def equality_expiry(t):
    t.a['evidence'][-1]['valid_until']=ns['NOW']
check('expiry_exact_boundary',equality_expiry)

def future_previous(t):
    previous(t);p=t.p/'previous.json';a=load(p);a['evaluated_at']='2030-01-03T13:00:00Z';write(p,a);r=ref(p)
    t.c['previous_assessment_sha256']=r['sha256'];t.a['history']['previous_ref']=r;t.extra[-1]=r['sha256']
check('previous_future_evaluation',future_previous)
rows=ns['rows']
result={'suite':'independent review synthetic probes','total':len(rows),'passed':sum(r['passed'] for r in rows),'known_limit_cases':['known_limit_unmeasured_definition_then_full_measurements'],'cases':rows}
write(output/'results.json',result)
print(json.dumps({'total':result['total'],'passed':result['passed']}))
sys.exit(0 if all(r['passed'] for r in rows) else 1)
