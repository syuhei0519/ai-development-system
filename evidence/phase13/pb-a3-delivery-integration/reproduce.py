"""Implementation integration self-check runner; requires an explicit checkout path."""
import json, os, re, subprocess, sys
from pathlib import Path
from jsonschema import Draft202012Validator
bundle = Path(__file__).resolve().parent
root = Path(sys.argv[1]).resolve()
report = json.loads((bundle / 'integration-report.json').read_bytes())
actual = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
assert actual == report['head'], 'fixed merged head required'
env = dict(os.environ, PB_HEAD=str(root),
           PB_PRIOR_CASES=str(bundle / 'prior/prior/input/input/upstream/independent_cases.py'))
for row in report['results']['commands']:
    if row['name'] == 'live':
        continue  # Requires separate bounded authority and private output parent.
    command = [s.replace('$BUNDLE', str(bundle)) for s in row['command']]
    subprocess.run(command, cwd=root, env=env, check=True)
for path in report['results']['schemas']:
    Draft202012Validator.check_schema(json.loads((root / path).read_bytes()))
files = [root / 'README.md']
for directory in ('contracts', 'workflows', 'templates'):
    files.extend((root / directory).glob('*.md'))
for path in files:
    for target in re.findall(r'\]\(([^)]+)\)', path.read_text()):
        if '://' not in target and not target.startswith('#'):
            assert (path.parent / target.split('#')[0]).exists(), (path, target)
print('PASS integration self-checks; independent Test/Review remain separate.')
