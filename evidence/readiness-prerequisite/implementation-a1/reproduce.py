"""Run from the fixed System checkout; uses only published synthetic data."""
import importlib.util, json, subprocess, tempfile
from pathlib import Path
from datetime import datetime, timezone
base="0083151aa2f6b2aaf0e1db64ada3f196ed766e48"
with tempfile.TemporaryDirectory() as tmp:
 root=Path(tmp)
 for name in ['scripts/validate_readiness.py','contracts/readiness.schema.json','contracts/readiness-context.schema.json']:
  p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(subprocess.check_output(['git','show',base+':'+name]))
 spec=importlib.util.spec_from_file_location('baseline',root/'scripts/validate_readiness.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 d=json.loads(Path('examples/readiness/pr-ready-issue-unverified.json').read_text());c=json.loads(Path('examples/readiness/context.json').read_text())
 d['pr_ac_ids']=c['pr_ac_ids']=[]
 print('empty product scope:',m.validate(d,c,datetime(2030,1,1,12,tzinfo=timezone.utc)))
 d['pr_ac_ids']=c['pr_ac_ids']=['SYNTHETIC-AC-1'];d['ac_results'][0].update(outcome='unverified',evidence_ids=[])
 print('unverified premerge product:',m.validate(d,c,datetime(2030,1,1,12,tzinfo=timezone.utc)))
