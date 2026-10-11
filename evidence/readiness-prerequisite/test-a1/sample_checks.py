"""Run documented synthetic CLI samples; inspect compatibility files at pinned Git refs."""
import hashlib,json,pathlib,subprocess,sys
R=pathlib.Path(sys.argv[1]).resolve();OUT=pathlib.Path(sys.argv[2]);rows=[]
commands=[
 (['scripts/validate_delivery_records.py'],0),
 (['scripts/validate_handoff.py','examples/research-to-test/research.handoff.json','examples/research-to-test/test.blocked.handoff.json','examples/research-to-test/test.handoff.json','examples/failed.handoff.json','examples/partial-assignment.handoff.json'],0),
 (['scripts/validate_knowledge.py','examples/knowledge/input.json','examples/knowledge/handoff.json','examples/knowledge/context.json','examples/knowledge-delivery/input.json','examples/knowledge-delivery/handoff.json','examples/knowledge-delivery/context.json'],0)]
for filename,context,code in [('pr-ready-issue-unverified','context',0),('implementation-only','automatic-context',0),('postdeploy-achieved','context',0),('invalid-premature-achieved','context',1),('invalid-premerge-deferred','context',1),('preparation-ready','preparation-context',0)]:
 cmd=['scripts/validate_readiness.py','examples/readiness/'+filename+'.json','--context','examples/readiness/'+context+'.json','--at','2030-01-01T12:00:00Z']
 if filename=='preparation-ready':cmd+=['--context-sha256',hashlib.sha256((R/'examples/readiness/preparation-context.json').read_bytes()).hexdigest()]
 if filename=='pr-ready-issue-unverified':cmd+=['--handoff','examples/readiness/manager.handoff.json']
 commands.append((cmd,code))
for name in ['achieved','pending']:
 prefix='examples/issue-completion/synthetic-'+name+'/'
 commands.append((['scripts/validate_issue_completion.py',prefix+'completion.json','--context',prefix+'context.json','--context-sha256',hashlib.sha256((R/(prefix+'context.json')).read_bytes()).hexdigest(),'--handoff',prefix+'handoff.json','--at','2030-01-03T12:00:00Z'],0))
for cmd,expected in commands:
 r=subprocess.run([sys.executable,*cmd],cwd=R,capture_output=True,text=True)
 rows.append(dict(command='python '+' '.join(cmd),expected_exit=expected,actual_exit=r.returncode,output=r.stdout+r.stderr))
schema=json.loads((R/'contracts/readiness.schema.json').read_bytes());context=json.loads((R/'contracts/readiness-context.schema.json').read_bytes())
rows.append(dict(check='preparation definitions identical in both schemas',passed=schema['$defs']['preparation']==context['$defs']['preparation']))
changed=subprocess.check_output(['git','diff','--name-only','0083151aa2f6b2aaf0e1db64ada3f196ed766e48','3f41a0470fd0b7a2199be0b947bb22284e993e2f'],cwd=R,text=True).splitlines()
protected=['contracts/handoff.schema.json','scripts/validate_handoff.py','scripts/consume_delivery.py','scripts/validate_knowledge.py','scripts/validate_issue_completion.py','contracts/issue-completion-context.schema.json']
protected+= [str(p.relative_to(R)) for p in (R/'contracts').glob('*v1.2.schema.json')]+[str(p.relative_to(R)) for p in (R/'contracts').glob('knowledge*.schema.json')]
rows.append(dict(check='existing Handoff2 Knowledge1 Delivery1.2 IssueCompletion source bytes unchanged',passed=not set(protected)&set(changed),files=sorted(set(protected))))
for path in ['README.md','contracts/README.md','contracts/readiness.md','examples/README.md','examples/readiness/README.md','workflows/single-issue.md','templates/task-input.md',*[f'agents/{x}.md' for x in ['manager','research-design','implementation','test','review']]]:
 rows.append(dict(check='documentation updated',path=path,passed=path in changed))
r=subprocess.run(['git','diff','--check','0083151aa2f6b2aaf0e1db64ada3f196ed766e48','3f41a0470fd0b7a2199be0b947bb22284e993e2f'],cwd=R,capture_output=True,text=True)
rows.append(dict(check='git diff --check',passed=r.returncode==0,output=r.stdout+r.stderr))
OUT.write_text(json.dumps({'results':rows,'note':'Documentation presence and sample consistency do not certify end-to-end preparation aggregation; see aggregate-results.json.'},indent=2)+'\n')
failed=[r for r in rows if r.get('actual_exit')!=r.get('expected_exit') or r.get('passed') is False]
print(json.dumps({'checks':len(rows),'failures':failed}));sys.exit(bool(failed))
