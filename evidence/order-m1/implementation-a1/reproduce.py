"""Read-only comparison against fixed M0. Run after checking out the M1 head."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument('--repo', type=Path, required=True)
parser.add_argument('--helm', default='helm')
a = parser.parse_args()
base = 'bc6adaedcd645a4663c23284b977a3dd36c0796d'
head = 'e0f79a61643d31a29de73ffc54bb6a31c320f0df'
repo = a.repo.resolve()
def git(*args):
    return subprocess.check_output(['git', '-C', str(repo), *args])
assert git('rev-parse', 'HEAD').decode().strip() == head
files = git('ls-tree', '-r', '--name-only', base, 'charts', 'environments/local').decode().splitlines()
with tempfile.TemporaryDirectory() as tmp:
    old = Path(tmp)
    for name in files:
        data = git('show', base + ':' + name)
        assert (repo / name).read_bytes() == data, name
        p = old / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    for chart in ('frontend', 'backend', 'postgresql'):
        args = [a.helm, 'template', chart, 'charts/' + chart, '--namespace', 'account', '-f', 'environments/local/' + chart + '.yaml']
        before = subprocess.check_output(args, cwd=old)
        after = subprocess.check_output(args, cwd=repo)
        assert before == after, chart
        print(chart, len(after), hashlib.sha256(after).hexdigest())
for chart in ('order', 'order-postgresql'):
    rendered = subprocess.check_output([a.helm, 'template', chart, 'charts/' + chart, '-f', 'environments/local/' + chart + '.yaml'], cwd=repo)
    assert not rendered.strip(), chart
print(json.dumps({'unchanged_files': len(files), 'unchanged_renders': 3, 'disabled_empty_renders': 2}))
