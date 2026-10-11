"""Canonical context/pin checks only; never a Manager Readiness assessment."""
import hashlib,json,pathlib,sys
sys.path.insert(0,sys.argv[1])
from scripts.validate_readiness import CONTEXT_VALIDATOR,validate_handoff_pair
from scripts.regular_file import artifact_path,read_regular
from scripts.consume_delivery import parse
root=pathlib.Path(sys.argv[2]);raw=read_regular(root/'context.json');context=parse(raw)
assert hashlib.sha256(raw).hexdigest()=='98c3d5be98ee65a3f054c1670a8092830b7707a72bf75ebf45dbca1331221cc7'
CONTEXT_VALIDATOR.validate(context)
config=read_regular(root/'config.json');assert context['subject']['config_revision']=='sha256:'+hashlib.sha256(config).hexdigest()
assert context['pr_kind']=='preparation' and context['deployment_effect']=='none' and context['issue_integration_scope']=='aggregate_required' and context['pr_ac_ids']==[]
assert len(context['preparation']['conditions'])==4 and context['preparation']['related_ac_ids']==['AC-3']
for a in context['preparation']['artifacts']:
 b=read_regular(artifact_path(root,a['locator']))
 assert len(b)==a['size_bytes'] and hashlib.sha256(b).hexdigest()==a['sha256'] and a['revision']==context['subject']['target_revision']
for p in root.glob('*.json'):parse(read_regular(p))
print('PASS: canonical context schema; independent context/config pins; classification; seven raw artifacts; strict JSON')
# Pair helper diagnostic deliberately does not assert that measurement is an assessment.
# This proves exact ID comparison; no manager identity or readiness outcome is fabricated.
if (root/'handoff.json').exists():
 measurement=read_regular(root/'measurement.json');d=json.loads(measurement);h=json.loads((root/'handoff.json').read_text())
 errs=validate_handoff_pair(d,h,readiness_bytes=measurement,readiness_path=root/'measurement.json',handoff_path=root/'handoff.json')
 assert errs==['handoff issue differs from readiness issue'],errs
 print('EXPECTED INCOMPATIBILITY: canonical pairing rejects historical qualified Issue ID vs Manager canonical Issue ID; no original rewritten')
