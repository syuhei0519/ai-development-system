#!/usr/bin/env python3
"""Validate Knowledge input, handoff or consumer context without Issue AC gates."""
import argparse
import json
from pathlib import Path
import sys

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
VALIDATORS = {}
for kind in ('input', 'handoff', 'context'):
    schema = json.loads((ROOT / f'contracts/knowledge-{kind}.schema.json').read_text(encoding='utf-8'))
    Draft202012Validator.check_schema(schema)
    VALIDATORS[f'knowledge_{kind}'] = Draft202012Validator(schema)


def validate(data):
    if not isinstance(data, dict) or data.get('document_type') not in VALIDATORS:
        return ['schema: unknown Knowledge document_type']
    errors = [f'schema: {error.json_path}: {error.message}'
              for error in VALIDATORS[data['document_type']].iter_errors(data)]
    if errors:
        return errors
    ids = {}
    for name in ('raw_findings', 'knowledge_references', 'artifacts', 'evidence'):
        items = data.get(name, [])
        ids[name] = {item['id'] for item in items}
        if len(ids[name]) != len(items):
            errors.append(f'integrity: duplicate {name} IDs')

    def refs(values, kind):
        if not set(values) <= ids[kind]:
            errors.append(f'integrity: unknown {kind} reference')

    for previous in data.get('retry_of', []):
        if previous['attempt'] != data['attempt'] - 1 or previous['task_id'] == data['task_id']:
            errors.append('integrity: retry must reference previous attempt and a different task')
    for item in data.get('evidence', []):
        refs(item['artifact_ids'], 'artifacts')
        refs(item['raw_finding_ids'], 'raw_findings')
    decided = []
    evidence = {item['id']: item for item in data.get('evidence', [])}
    artifacts = {item['id']: item for item in data.get('artifacts', [])}
    for decision in data.get('decisions', []):
        decided.extend(decision['raw_finding_ids'])
        refs(decision['raw_finding_ids'], 'raw_findings')
        refs(decision['evidence_ids'], 'evidence')
        refs(decision['article_artifact_ids'], 'artifacts')
        supported = {raw_id for evidence_id in decision['evidence_ids']
                     for raw_id in evidence.get(evidence_id, {}).get('raw_finding_ids', [])}
        if not set(decision['raw_finding_ids']) <= supported:
            errors.append('integrity: decision lacks evidence for its raw findings')
        if any(artifacts.get(key, {}).get('kind') != 'knowledge'
               for key in decision['article_artifact_ids']):
            errors.append('integrity: curated article must reference a knowledge artifact')
    if len(decided) != len(set(decided)):
        errors.append('integrity: raw finding has multiple conflicting decisions')
    if data.get('status') == 'completed' and set(decided) != ids['raw_findings']:
        errors.append('integrity: completed requires a decision for every supplied raw finding')
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('files', nargs='+', type=Path)
    args = parser.parse_args()
    failed = False
    for path in args.files:
        try:
            errors = validate(json.loads(path.read_text(encoding='utf-8')))
        except (OSError, ValueError) as exc:
            errors = [str(exc)]
        if errors:
            failed = True
            print(f'FAIL {path}: ' + '; '.join(errors), file=sys.stderr)
        else:
            print(f'PASS {path} (shape + local references only; not knowledge approval)')
    return int(failed)


if __name__ == '__main__':
    sys.exit(main())
