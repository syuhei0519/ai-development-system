import sys,pathlib,json,subprocess,hashlib,platform
from jsonschema import Draft202012Validator
root=pathlib.Path(sys.argv[1]).resolve();base=pathlib.Path(sys.argv[2]).resolve(); out=pathlib.Path(sys.argv[3]); checks=[]
def run(args,expected=0):
 p=subprocess.run([sys.executable,*args],cwd=root,capture_output=True,text=True)
 checks.append(dict(command='python '+' '.join(args),expected=expected,actual=p.returncode,passed=p.returncode==expected))
run(['scripts/validate_delivery_records.py'])
run(['scripts/validate_handoff.py','examples/research-to-test/research.handoff.json','examples/research-to-test/test.blocked.handoff.json','examples/research-to-test/test.handoff.json','examples/failed.handoff.json','examples/partial-assignment.handoff.json'])
run(['scripts/validate_knowledge.py',*[f'examples/{folder}/{name}.json' for folder in ('knowledge','knowledge-delivery') for name in ('input','handoff','context')]])
for n,context,handoff in [('pr-ready-issue-unverified','context',True),('implementation-only','automatic-context',False),('postdeploy-achieved','context',False)]:
 run(['scripts/validate_readiness.py',f'examples/readiness/{n}.json','--context',f'examples/readiness/{context}.json','--at','2030-01-01T12:00:00Z']+(['--handoff','examples/readiness/manager.handoff.json'] if handoff else []))
for script in ('consume_delivery','prepare_knowledge_fixture','validate_handoff','validate_knowledge','validate_readiness','validate_retry'):
 run([f'scripts/{script}.py'],2)
for p in sorted((root/'contracts').glob('*.schema.json')):
 Draft202012Validator.check_schema(json.loads(p.read_bytes()));checks.append(dict(check='schema '+p.name,passed=True))
for folder,glob in [('contracts','*.schema.json'),('tests','*.py')]:
 for p in sorted((base/folder).glob(glob)):
  equal=p.read_bytes()==(root/folder/p.name).read_bytes();checks.append(dict(check='legacy byte preservation '+folder+'/'+p.name,passed=equal))
checks.append(dict(check='exact head',passed=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()=='5345303db8c5208859ed741b98f119882de7a973'))
checks.append(dict(check='product tracked clean',passed=not subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=root,text=True)))
result=dict(python=platform.python_version(),jsonschema=__import__('importlib.metadata').metadata.version('jsonschema'),checks=checks,count=len(checks),passed=sum(c['passed'] for c in checks))
out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='checks'}));print([c for c in checks if not c['passed']])
