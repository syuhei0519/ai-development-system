#!/usr/bin/env python3
"""Additional independent synthetic probes; never edits the implementation.
Usage: python boundary_cases.py CHECKOUT VERIFIED_INDEPENDENT_CASES OUTPUT [baseline]
Loads only helper definitions from the byte-preserved prior independent test,
not its top-level test executions. Prior expectations are never rewritten.
"""
import ast
import copy
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch

checkout, helper, output = map(Path, sys.argv[1:4])
baseline = len(sys.argv) > 4 and sys.argv[4] == 'baseline'
tree = ast.parse(helper.read_bytes(), filename=str(helper))
tree.body = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom,
             ast.FunctionDef, ast.ClassDef, ast.Assign))]
saved_argv = sys.argv
sys.argv = [str(helper), str(checkout), str(output)]
ns = {'__name__': 'independent_helpers', '__file__': str(helper)}
exec(compile(tree, str(helper), 'exec'), ns)
sys.argv = saved_argv
output.mkdir(parents=True, exist_ok=False)
check, previous, event, write, load, ref = (ns[k] for k in ('check','previous','event','write','load','ref'))

check('F1_original_required_subcheck_removed_without_change_event', ns['remove_check'])
check('F2_original_pr_handoff_symlink_locator', ns['pr_alias'])
if not baseline:
    def required_event(t):
        t.a['history']['events'].append({**event('required_set_changed'), 'event_id':'required-change'})
    check('removed_subcheck_with_new_event', lambda t:(ns['remove_check'](t), required_event(t)), expected=0, contains='achieved')
    def measured(t, with_event=False):
        previous(t)
        t.c['required_verifications'][-1]['method'] += ' changed'
        t.a['evidence'][-1]['method'] += ' changed'
        if with_event: required_event(t)
    check('measured_method_change_no_event', measured)
    check('measured_method_change_with_event', lambda t:measured(t,True), expected=0, contains='achieved')
    def old_event(t):
        t.a['history']['events']=[{**event('required_set_changed'), 'event_id':'old-change'}]
        measured(t)
    check('old_event_cannot_cover_new_change', old_event)
    def reorder(t):
        previous(t); t.c['required_verifications'].reverse(); t.a['verification_results'].reverse()
        for v in t.c['required_verifications']: v['member_ids'].reverse()
        for r in t.a['ac_results']: r['verification_ids'].reverse()
    check('reordering_is_not_requirement_change', reorder, expected=0, contains='achieved')
    def scope_bump(t):
        p=t.p/'scope.txt'; old=t.c['scope_revision']
        p.write_text('synthetic updated approved scope: '+json.dumps(t.c['required_verifications'],sort_keys=True)+'\n')
        r=ref(p)
        def replace(x):
            if isinstance(x,dict):
                if set(x)=={'id','locator','sha256','size'} and x['locator']=='scope.txt': return copy.deepcopy(r)
                return {k:replace(v) for k,v in x.items()}
            if isinstance(x,list): return [replace(v) for v in x]
            return r['sha256'] if x==old else x
        t.c=replace(t.c); t.a=replace(t.a)
    def limit(t, field, bump=False, record=False):
        previous(t); t.c['required_verifications'][-1][field]+=' changed'
        if bump: scope_bump(t)
        if record: required_event(t)
    for field, pending in [('failure_action',False),('method',True),('owner',True),('expected_result',True)]:
        # Known v1 limitation observations, NOT proof of complete change detection.
        check('documented_limit_'+field,lambda t,f=field:limit(t,f),expected=0,
              contains='unverified' if pending else 'achieved',pending=pending)
        check('scope_bump_requires_history_'+field,lambda t,f=field:limit(t,f,True),pending=pending)
        check('manager_scope_and_history_'+field,lambda t,f=field:limit(t,f,True,True),expected=0,
              contains='unverified' if pending else 'achieved',pending=pending)
    def pr_path(t, mode):
        hp=t.p/'app-handoff.json'; h=load(hp); artifact=h['artifacts'][0]
        original=artifact['locator']
        if mode=='ancestor':
            (t.p/'linked').symlink_to('.',target_is_directory=True); locator='linked/'+original
        elif mode=='fifo': os.mkfifo(t.p/'pipe'); locator='pipe'
        elif mode=='directory': (t.p/'dir').mkdir(); locator='dir'
        elif mode=='copy':
            (t.p/'copy.json').write_bytes((t.p/original).read_bytes()); locator='copy.json'
        elif mode=='nested':
            (t.p/'nested').mkdir(); rp=t.p/'nested'/original
            rp.write_bytes((t.p/original).read_bytes()); hp=t.p/'nested/app-handoff.json'
            r=ref(rp);r['locator']='nested/'+original
            t.a['member_results'][0]['readiness_ref']=r; locator=original
        else: locator={'dot':'./'+original,'empty':'dir//'+original,'parent':'dir/../'+original,
                      'absolute':str(t.p/original),'backslash':'dir\\'+original,'missing':'absent.json'}[mode]
        artifact['locator']=locator; write(hp,h)
        r=ref(hp);r['locator']=str(hp.relative_to(t.p));t.a['member_results'][0]['readiness_handoff_ref']=r
    for mode in ['ancestor','fifo','directory','copy','nested','dot','empty','parent','absolute','backslash','missing']:
        check('pr_locator_'+mode,lambda t,m=mode:pr_path(t,m),expected=0 if mode=='nested' else 1,
              contains='achieved' if mode=='nested' else None)
    for filename in ['completion.json','context.json','handoff.json']:
        def leaf(t,filename=filename):
            p=t.p/filename; p.rename(t.p/('real-'+filename));p.symlink_to('real-'+filename)
        check('input_symlink_'+filename,after=leaf)
    def source_ancestor(t):
        (t.p/'linked').symlink_to('.',target_is_directory=True)
        t.a['evidence'][-1]['source_ref']['locator']='linked/'+t.a['evidence'][-1]['source_ref']['locator']
        write(t.p/'completion.json',t.a)
    check('source_ancestor_symlink',after=source_ancestor)
    check('dependency_cycle',lambda t:t.c['required_prs'][0].update(depends_on=['client']))
    check('current_deployment_image_mismatch',lambda t:t.c['current_deployments'][0]['images'][0].update(digest='sha256:'+'1'*64))
    check('current_source_revision_mismatch',lambda t:t.c['current_deployments'][0]['sources'][0].update(revision='9'*40))
    # Mutate an already-read measurement just before final reread, retaining every original pin.
    sys.path.insert(0,str(checkout.resolve()))
    from scripts import validate_issue_completion as vc
    t=ns['Case']('measurement_mutation_before_finish');t.save()
    finish=vc.Bundle.finish
    def tamper(bundle):
        p=t.p/t.a['evidence'][-1]['source_ref']['locator'];p.write_bytes(p.read_bytes()+b'\n');finish(bundle)
    try:
        with patch.object(vc.Bundle,'finish',tamper):
            vc.validate_files(t.p/'completion.json',t.p/'context.json',t.pin,t.p/'handoff.json',now=vc.instant(ns['NOW']))
        rejected=False
    except ValueError as e:
        rejected=str(e)=='bytes changed during validation'
    ns['rows'].append(dict(case=t.p.name,expected_rejection='bytes changed during validation',passed=rejected))

rows=ns['rows']
result={'suite':'original regression baseline' if baseline else 'additional independent boundaries',
        'baseline':baseline,'total':len(rows),'passed':sum(r['passed'] for r in rows),'cases':rows}
if baseline:result['original_bugs_confirmed']=all(r['actual_exit']==0 and not r['passed'] for r in rows)
write(output/'results.json',result)
print(json.dumps({k:v for k,v in result.items() if k!='cases'}))
sys.exit(0 if (result.get('original_bugs_confirmed') if baseline else all(r['passed'] for r in rows)) else 1)
