"""Deterministic synthetic sample builder; never represents a product observation."""
import copy
import json
from pathlib import Path
from scripts.validate_issue_completion import sha

ROOT = Path(__file__).resolve().parents[1]
NOW = '2030-01-03T12:00:00Z'
END = '2030-01-04T00:00:00Z'
OBS = '2030-01-03T10:00:00Z'
MERGED = '2030-01-01T13:00:00Z'
DEPLOYED = '2030-01-02T10:00:00Z'
SAMPLE = 'synthetic sample: fictional record, no product result or authority'


def encode(data):
    return (json.dumps(data, indent=2, ensure_ascii=False) + '\n').encode()


def write(root, name, data):
    raw = data if isinstance(data, bytes) else encode(data)
    (root / name).write_bytes(raw)
    return dict(id=name, locator=name, sha256=sha(raw), size=len(raw))


def proof(ids=(), verdict='pass'):
    return dict(verdict=verdict,evidence_ids=list(ids),reason=SAMPLE)


def handoff(issue, artifact, outcome=None, measurements=()):
    h = json.loads((ROOT/'examples/readiness/manager.handoff.json').read_text())
    h['issue'] = copy.deepcopy(issue)
    h['issue']['acceptance_criteria'] = [{k:a[k] for k in ('id','verbatim','source')} for a in issue['acceptance_criteria']]
    h['task_id'] = 'SYNTHETIC-AGGREGATE-MANAGER'
    h['summary'] = SAMPLE
    h['assignment'] = dict(scope=SAMPLE,ac_ids=[a['id'] for a in issue['acceptance_criteria']],completion_criteria=[SAMPLE])
    h['artifacts'] = [dict(id=artifact['id'],kind='other',locator=artifact['locator'],revision='sha256:'+artifact['sha256'],summary=SAMPLE)]
    h['evidence'] = [dict(id='record',claim=SAMPLE,artifact_ids=[artifact['id']],locator=artifact['locator'],observation=SAMPLE)]
    h['ac_mapping'] = [dict(ac_id=a['id'],disposition='covered',scope='Synthetic record validation only',artifact_ids=[artifact['id']],evidence_ids=['record']) for a in issue['acceptance_criteria']]
    h.pop('final_assessment',None)
    if outcome:
        results=[]
        for a in issue['acceptance_criteria']:
            eids=[]
            for e in measurements:
                if a['id'] not in e['ac_ids']: continue
                ref=e['source_ref']; eid=e['id']; eids.append(eid)
                h['artifacts'].append(dict(id=ref['id'],kind='test-report',locator=ref['locator'],revision='sha256:'+ref['sha256'],summary=SAMPLE))
                h['evidence'].append(dict(id=eid,claim=SAMPLE,artifact_ids=[ref['id']],locator=ref['locator'],observation=SAMPLE))
            results.append(dict(ac_id=a['id'],outcome='met',evidence_ids=eids))
        h['final_assessment']=dict(outcome=outcome,ac_results=results,rationale=SAMPLE)
    return h


def build(root, pending=False, same_repo=False, queue=False):
    root=Path(root); root.mkdir(parents=True,exist_ok=True)
    base=json.loads((ROOT/'examples/readiness/pr-ready-issue-unverified.json').read_text())
    acs=base['acceptance_criteria']; mids=['app','config','client']; did='staging'
    scope=write(root,'scope.txt',(SAMPLE+'\n').encode())
    issue=dict(id=base['issue_id'],source='synthetic sample request',title='synthetic sample: three PR aggregate',acceptance_criteria=acs)
    c=dict(schema_version='1.1',document_type='issue_completion_context',context_id='SYNTHETIC-CURRENT',issue=issue,
           issue_integration_scope='aggregate_required',scope_revision=scope['sha256'],scope_decisions=[],required_prs=[],required_deployments=[],required_verifications=[],current_members=[],current_deployments=[],observed_at=OBS,valid_until=END,source_refs=[scope],previous_assessment_sha256=None)
    a=dict(schema_version='1.1',document_type='issue_completion_assessment',artifact_id='SYNTHETIC-COMPLETION',assessor_role='manager',evaluated_at=NOW,context_sha256='0'*64,issue_id=issue['id'],acceptance_criteria=acs,scope_revision=scope['sha256'],member_results=[],deployment_results=[],evidence=[],verification_results=[],ac_results=[],integration_readiness=dict(status='ready',checks={},evidence_ids=[],reason=SAMPLE),issue_completion='achieved',reasons=[SAMPLE],history=dict(previous_ref=None,events=[]))
    readiness={}
    for i,mid in enumerate(mids):
        repo='example/synthetic-app' if same_repo else 'example/synthetic-'+mid
        head=hex(i+10)[2:]*40; merge=hex(i+1)[2:]*40
        c['required_prs'].append(dict(pr_kind='standard',preparation=None,member_id=mid,repository=repo,pr_number=i+1,scope=SAMPLE,ac_ids=[x['id'] for x in acs],depends_on=[] if i==0 else [mids[i-1]],requirement_source=scope))
        c['current_members'].append(dict(member_id=mid,state='merged',head_sha=head,base_sha='f'*40,target_revision='e'*40 if queue else head,config_revision='synthetic-policy-and-environment-v1',merge_group_sha='e'*40 if queue else None,merge_sha=merge,merged_at=MERGED,merge_actor='synthetic-operator',observed_at=OBS,valid_until=END,evidence_refs=[scope]))
        r=copy.deepcopy(base)
        r['subject'].update(repository=repo,pr_number=i+1,head_sha=head,base_sha='f'*40,target_revision='e'*40 if queue else head,merge_group_sha='e'*40 if queue else None)
        r['issue_integration_scope']='aggregate_required'
        if queue: r['merge_readiness']['checks']['github_queue']['verdict']='pass'
        for e in r['evidence']: e['subject']=copy.deepcopy(r['subject'])
        rc=json.loads((ROOT/'examples/readiness/context.json').read_text())
        for k in ('subject','issue_id','acceptance_criteria','pr_ac_ids','deployment_effect','issue_integration_scope'): rc[k]=copy.deepcopy(r[k])
        rc['github_requirements']['queue']=queue
        rr=write(root,mid+'-readiness.json',r); rr['id']=r['artifact_id']
        rh=handoff(issue,rr)
        readiness[mid]=r
        a['member_results'].append(dict(member_id=mid,readiness_ref={**rr,'id':mid+'-readiness'},readiness_context_ref=write(root,mid+'-context.json',rc),readiness_handoff_ref=write(root,mid+'-handoff.json',rh),gate_checked_at='2030-01-01T12:30:00Z',approved_head_sha=head,actual_merge_sha=merge,merged_at=MERGED,merge_binding=proof([mid+'-merge']),historical_merge_gate=proof([mid+'-merge'])))
        c['required_verifications'].append(dict(verification_id=mid+'-pre',ac_id=acs[0]['id'],phase='premerge',member_ids=[mid],deployment_ids=[],environment_id='synthetic-ci',workload_id='synthetic-tests',method='synthetic unit checks',expected_result='synthetic pass',owner='synthetic-tester',failure_action='repair and retest'))
    sources=[dict(repository=r['repository'],revision=m['merge_sha']) for r,m in zip(c['required_prs'],c['current_members'])]
    if same_repo: sources=[sources[-1]]
    images=[dict(component='synthetic-app',digest='sha256:'+'d'*64)]
    c['required_deployments']=[dict(deployment_id=did,definition_state='defined',environment_id='synthetic-staging',workload_id='synthetic-service',member_ids=mids,expected_sources=sources,expected_config_sha256='c'*64,image_requirement='required',expected_images=images,no_image_basis=None)]
    c['current_deployments']=[dict(deployment_id=did,state='deployed',sources=sources,config_sha256='c'*64,images=images,environment_id='synthetic-staging',workload_id='synthetic-service',deployed_at=DEPLOYED,deploy_actor='synthetic-operator',observed_at=OBS,valid_until=END,evidence_refs=[scope])]
    for suffix in ('response','persistence'):
        c['required_verifications'].append(dict(verification_id='runtime-'+suffix,ac_id=acs[1]['id'],phase='postdeploy',member_ids=mids,deployment_ids=[did],environment_id='synthetic-staging',workload_id='synthetic-service',method='synthetic '+suffix,expected_result='synthetic pass',owner='synthetic-tester',failure_action='repair and retest'))
    for kind,actions in [('required_scope',['assess']),('product_operation',['merge','deploy'])]:
        c['scope_decisions'].append(dict(scope_id=kind,revision=scope['sha256'],status='approved',authority='synthetic-owner',actor='synthetic-operator',decision_kind=kind,scope=SAMPLE,issue_id=issue['id'],member_ids=mids,deployment_ids=[did],allowed_actions=actions,evidence_refs=[scope],observed_at='2030-01-01T09:00:00Z',valid_until=END))
    def evidence(eid,kind,phase='postdeploy',members=None,deploys=None):
        return dict(id=eid,kind=kind,phase=phase,member_ids=mids if members is None else members,deployment_ids=[did] if deploys is None else deploys,verification_ids=[],ac_ids=[],binding={},environment_id='synthetic-staging',workload_id='synthetic-service',method='synthetic observation',expected_result='synthetic pass',merge=None,observed_at=OBS,valid_until=END,producer='synthetic-tester',independent=True,result='pass',source_ref={},observation=SAMPLE)
    for mid in mids:
        e=evidence(mid+'-merge','merge_binding','postmerge',[mid],[])
        s=readiness[mid]['subject']; m=next(x for x in c['current_members'] if x['member_id']==mid)
        e['merge']=dict(member_id=mid,head_sha=s['head_sha'],base_sha=s['base_sha'],target_revision=s['target_revision'],merge_sha=m['merge_sha'],merged_at=MERGED,method='queue' if queue else 'squash')
        a['evidence'].append(e)
    for name,kind in [('scope','scope'),('authorization','authorization'),('deployment','deployment'),('compatibility','compatibility'),('integration','integration')]: a['evidence'].append(evidence(name,kind))
    for v in c['required_verifications']:
        e=evidence(v['verification_id'],'ac_measurement',v['phase'],v['member_ids'],v['deployment_ids'])
        for k in ('environment_id','workload_id','method','expected_result'): e[k]=v[k]
        e.update(verification_ids=[v['verification_id']],ac_ids=[v['ac_id']])
        if v['phase']=='premerge':
            mid=v['member_ids'][0]; e['observed_at']='2030-01-01T10:00:00Z'
            e['binding']=dict(type='pr',member_id=mid,subject=readiness[mid]['subject'],scope_revision=c['scope_revision'])
        a['evidence'].append(e)
        a['verification_results'].append(dict(verification_id=v['verification_id'],outcome='met',evidence_ids=[e['id']],reason=SAMPLE))
    for ac in acs:
        vids=[v['verification_id'] for v in c['required_verifications'] if v['ac_id']==ac['id']]
        a['ac_results'].append(dict(ac_id=ac['id'],outcome='met',verification_ids=vids,evidence_ids=vids))
    a['deployment_results']=[dict(deployment_id=did,status='ready',evidence_ids=['deployment'],reason=SAMPLE)]
    checks=dict(scope=['scope'],required_merges=[m+'-merge' for m in mids],deployment=['deployment'],compatibility=['compatibility'],measurement_coverage=[v['verification_id'] for v in c['required_verifications']],current_evidence=['integration'],authorizations=['authorization'])
    a['integration_readiness']['checks']={k:proof(v) for k,v in checks.items()}
    if pending:
        for m in c['current_members']:
            m.update(state='open',merge_sha=None,merged_at=None,merge_actor=None)
        c['current_deployments'][0].update(state='pending',deployed_at=None,deploy_actor=None)
        for r in a['member_results']:
            for k in ('readiness_ref','readiness_context_ref','readiness_handoff_ref','gate_checked_at','approved_head_sha','actual_merge_sha','merged_at'): r[k]=None
            r['merge_binding']=proof(verdict='pending'); r['historical_merge_gate']=proof(verdict='pending')
        a['evidence']=[]
        for r in a['verification_results']+a['ac_results']: r.update(outcome='unverified',evidence_ids=[])
        a['deployment_results'][0].update(status='blocked',evidence_ids=[])
        a['integration_readiness'].update(status='blocked',checks={k:proof(verdict='pending') for k in checks})
        a['issue_completion']='unverified'
    save(root,a,c)
    return a,c


def save(root,a,c,final=None):
    root=Path(root)
    cr=write(root,'context.json',c); a['context_sha256']=cr['sha256']
    for e in a['evidence']:
        if e['phase']!='premerge':
            e['binding']=dict(type='integration',context_sha256=cr['sha256'],scope_revision=c['scope_revision'],merged_members=[dict(member_id=m['member_id'],merge_sha=m['merge_sha']) for m in c['current_members'] if m['merge_sha']],deployments=[{k:d[k] for k in ('deployment_id','sources','config_sha256','images','environment_id','workload_id')} for d in c['current_deployments']] if e['phase']=='postdeploy' else [])
        e['source_ref']=write(root,e['id']+'-observation.json',dict(document_type='issue_completion_observation',schema_version='1.0',observation={k:v for k,v in e.items() if k!='source_ref'}))
    a['integration_readiness']['evidence_ids']=sorted({e for p in a['integration_readiness']['checks'].values() for e in p['evidence_ids']})
    ar=write(root,'completion.json',a); ar['id']=a['artifact_id']
    h=handoff(c['issue'],ar,a['issue_completion'] if (a['issue_completion']=='achieved' if final is None else final) else None,[e for e in a['evidence'] if e['kind']=='ac_measurement'])
    write(root,'handoff.json',h)
    return cr['sha256']
