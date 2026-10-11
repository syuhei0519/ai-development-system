"""Test attempt 3 derivative: fixed head inbox; original helper retained in input/."""
"""Bounded synthetic HTTPS CLI verification; no dispatch or external product action."""
import os,sys,json,subprocess,hashlib,pathlib,datetime
root=pathlib.Path(os.environ['PB_HEAD']);p=pathlib.Path(os.environ['PB_PRIVATE'])/'live-complete';p.mkdir(mode=0o700)
sys.path.insert(0,str(root));from scripts import knowledge_collector as c
from scripts.prepare_collector_fixture import registry
fixed='d3f8f582caef99a0e004c29ad3a430efe7df98bc';writer='SYNTHETIC-INDEPENDENT-TEST';scope='synthetic/pb-test-attempt3';store=p/'store';records=[]
raw=c.encode(registry('syuhei0519/ai-development-system',fixed));(p/'registry.json').write_bytes(raw)
def mutation(op,raw,req):
 (p/req).write_bytes(raw)
 auth=c.encode(dict(schema_version='1.0',document_type='knowledge_collection_authorization',writer=writer,scope=scope,operation=op,request_sha256=c.digest(raw),valid_until='2026-10-12T00:00:00Z',approval='approved',authority='Owner delegated bounded independent synthetic verification; no external dispatch'))
 authpath=p/(op+'-authorization.json');authpath.write_bytes(auth);authpath.chmod(0o600);(p/(op+'-authorization.pin')).write_text(c.digest(auth)+'\n')
 pin=c.digest((store/'state.json').read_bytes()) if store.exists() else 'absent'
 cmd=[sys.executable,str(root/'scripts/knowledge_collector.py'),op,'--store',str(store),'--previous-sha256',pin,'--writer',writer,'--scope',scope,'--request',str(p/req),'--authorization',str(authpath),'--authorization-sha256',c.digest(auth)]
 if op=='record':cmd.extend(['--objects',str(p/'input-objects')])
 r=subprocess.run(cmd,capture_output=True);records.append(dict(operation=op,exit=r.returncode,stdout=json.loads(r.stdout) if r.stdout else None,stderr=r.stderr.decode()));assert r.returncode==0,r.stderr
 return c.parse((store/'state.json').read_bytes())
s1=mutation('scan',raw,'registry.json');s2=mutation('reconcile',raw,'registry.json');assert s1['events']==s2['events'] and len(s2['events'])==2
before={str(f.relative_to(store)):f.read_bytes() for f in store.rglob('*') if f.is_file()}
for op in ['plan','replay']:
 r=subprocess.run([sys.executable,str(root/'scripts/knowledge_collector.py'),op,'--store',str(store),'--previous-sha256',c.digest((store/'state.json').read_bytes()),'--private-plan',str(p/(op+'.json'))],capture_output=True);assert r.returncode==0
 records.append(dict(operation=op,exit=r.returncode,stdout=json.loads(r.stdout),stderr=r.stderr.decode()))
assert before=={str(f.relative_to(store)):f.read_bytes() for f in store.rglob('*') if f.is_file()}
assert (p/'plan.json').read_bytes()==(p/'replay.json').read_bytes()
# Supply the fixed synthetic input explicitly; this registry inventories source evidence only.
input_raw=(root/'examples/knowledge-collector/input.json').read_bytes()
objects=p/'input-objects';objects.mkdir(mode=0o700);(objects/c.digest(input_raw)).write_bytes(input_raw)
request=c.encode(dict(action='reserve',event_ids=sorted(s2['events']),input_sha256=c.digest(input_raw),lease_until='2026-10-12T00:00:00Z'))
s3=mutation('record',request,'reserve.json');assert {e['status'] for e in s3['events'].values()}=={'reserved'}
result=dict(head=fixed,operations=records,event_count=2,scan_reconcile_events_equal=True,plan_replay_equal=True,read_only_store_equal=True,dispatch_performed=False,scope='synthetic-only',observed_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
(p.parent/'live-observation.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS fixed HTTPS scan/reconcile, read-only plan/replay, synthetic reserve; no dispatch')
