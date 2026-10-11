"""Synthetic preparation dependency followed by real product measurements."""
from copy import deepcopy
import json
from completion_fixture import build, save, write, handoff, ROOT


def build_preparation(root):
    a, c = build(root)
    a['schema_version'] = c['schema_version'] = '1.1'
    for requirement in c['required_prs']:
        requirement.update(pr_kind='standard', preparation=None)
    d = json.loads((ROOT/'examples/readiness/preparation-ready.json').read_bytes())
    rc = json.loads((ROOT/'examples/readiness/preparation-context.json').read_bytes())
    subject = json.loads((root/'app-readiness.json').read_bytes())['subject']
    d['subject'] = subject
    rc['subject'] = deepcopy(subject)
    for e in d['evidence']:
        e['subject'] = deepcopy(subject)
    for x in (d, rc):
        x['preparation']['artifacts'][0]['revision'] = subject['target_revision']
    ref = write(root, 'preparation-artifact.txt', (ROOT/'examples/readiness/preparation-artifact.txt').read_bytes())
    c['required_prs'][0].update(pr_kind='preparation', ac_ids=[], preparation={
        'related_ac_ids': deepcopy(d['preparation']['related_ac_ids']),
        'artifact_refs': [{'artifact_id': d['preparation']['artifacts'][0]['id'], 'ref': ref}]})
    rr = write(root, 'app-readiness.json', d)
    rr['id'] = d['artifact_id']
    a['member_results'][0].update(readiness_ref={**rr, 'id':'app-readiness'},
        readiness_context_ref=write(root, 'app-context.json', rc),
        readiness_handoff_ref=write(root, 'app-handoff.json', handoff(c['issue'], rr)))
    c['required_verifications'] = [v for v in c['required_verifications'] if v['verification_id'] != 'app-pre']
    a['verification_results'] = [v for v in a['verification_results'] if v['verification_id'] != 'app-pre']
    a['evidence'] = [v for v in a['evidence'] if v['id'] != 'app-pre']
    for v in a['ac_results']:
        for k in ('verification_ids', 'evidence_ids'):
            v[k] = [x for x in v[k] if x != 'app-pre']
    a['integration_readiness']['checks']['measurement_coverage']['evidence_ids'].remove('app-pre')
    # Preparation is a required merged dependency, never a product measurement target.
    for v in c['required_verifications']:
        v['member_ids'] = [x for x in v['member_ids'] if x != 'app']
    for e in a['evidence']:
        if e['kind'] == 'ac_measurement':
            e['member_ids'] = [x for x in e['member_ids'] if x != 'app']
    save(root, a, c)
    return a, c
