#!/usr/bin/env python3
"""Validate shape and local references; never certify evidence or AC truth."""
import argparse
import json
import re
from pathlib import Path
import sys

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / 'contracts/handoff.schema.json').read_text(encoding='utf-8'))
Draft202012Validator.check_schema(SCHEMA)
VALIDATOR = Draft202012Validator(SCHEMA)


def integrity_errors(data):
    """Checks JSON Schema cannot express: IDs, coverage and retry continuity."""
    errors = []
    collections = {
        'acceptance_criteria': data['issue']['acceptance_criteria'],
        'artifacts': data['artifacts'],
        'evidence': data['evidence'],
        'knowledge_candidates': data['knowledge_candidates'],
    }
    ids = {}
    for name, items in collections.items():
        ids[name] = {item['id'] for item in items}
        if len(ids[name]) != len(items):
            errors.append(f'{name}: duplicate IDs')

    def check_refs(values, collection, context):
        missing = set(values) - ids[collection]
        if missing:
            errors.append(f'{context}: unknown {collection} IDs: {sorted(missing)}')

    for item in data['evidence']:
        check_refs(item['artifact_ids'], 'artifacts', f'evidence {item["id"]}')
    assigned = set(data['assignment']['ac_ids'])
    missing_originals = data['status'] == 'blocked' and any(
        reason['code'] == 'MISSING_ACCEPTANCE_CRITERIA' for reason in data['block_reasons'])
    if not missing_originals:
        check_refs(assigned, 'acceptance_criteria', 'assignment')
    mapped = []
    covered = set()
    for item in data['ac_mapping']:
        mapped.append(item['ac_id'])
        if item['disposition'] == 'covered':
            covered.add(item['ac_id'])
            if item['ac_id'] not in assigned:
                errors.append('ac_mapping: cannot cover an unassigned AC')
        if item['disposition'] == 'not_assigned' and item['ac_id'] in assigned:
            errors.append('ac_mapping: assigned AC cannot be not_assigned')
        check_refs([item['ac_id']], 'acceptance_criteria', 'ac_mapping')
        check_refs(item['artifact_ids'], 'artifacts', 'ac_mapping')
        check_refs(item['evidence_ids'], 'evidence', 'ac_mapping')
    if len(set(mapped)) != len(mapped):
        errors.append('ac_mapping: duplicate AC mappings')
    if data['status'] == 'completed' and covered != assigned:
        errors.append('ac_mapping: completed requires every assigned AC to be covered')
    final = data.get('final_assessment')
    if final is not None:
        results = final['ac_results']
        final_ids = [item['ac_id'] for item in results]
        if len(set(final_ids)) != len(final_ids) or set(final_ids) != ids['acceptance_criteria']:
            errors.append('final_assessment: requires exactly one result for every Issue AC')
        for item in results:
            check_refs(item['evidence_ids'], 'evidence', 'final_assessment')
        outcomes = {item['outcome'] for item in results}
        expected = ('not_achieved' if 'not_met' in outcomes else
                    'unverified' if 'unverified' in outcomes else 'achieved')
        if final['outcome'] != expected:
            errors.append('final_assessment: overall outcome contradicts AC results')
    for item in data['knowledge_candidates']:
        check_refs(item['evidence_ids'], 'evidence', f'knowledge {item["id"]}')
    retries = [item for item in data['upstream'] if item['relationship'] == 'retry_of']
    if data['attempt'] == 1 and retries:
        errors.append('attempt 1 cannot have retry_of')
    if data['attempt'] > 1:
        if len(retries) != 1:
            errors.append('retry requires exactly one retry_of')
        elif retries[0]['attempt'] != data['attempt'] - 1 or retries[0]['role'] != data['role']:
            errors.append('retry_of must be the previous attempt of the same role')
    if any(item['task_id'] == data['task_id'] for item in data['upstream']):
        errors.append('upstream cannot reference the current task_id')
    return errors


def validate(data):
    errors = [f'schema {"/".join(map(str, error.absolute_path)) or "/"}: {error.message}'
              for error in VALIDATOR.iter_errors(data)]
    if errors:
        return errors
    return [f'integrity: {error}' for error in integrity_errors(data)]


def validate_markdown(text):
    """Check the four learning sections; never infer semantic completion."""
    headings = re.findall(r'^##[ \t]+([^\r\n]+)', text, re.MULTILINE)
    required = ['目的', 'やったこと', '観察結果', '学び']
    return [f'missing or duplicate section: {name}' for name in required if headings.count(name) != 1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('files', nargs='+', type=Path)
    args = parser.parse_args()
    failed = False
    for path in args.files:
        try:
            raw = path.read_text(encoding='utf-8')
            errors = validate_markdown(raw) if path.suffix.lower() == '.md' else validate(json.loads(raw))
        except (OSError, ValueError) as exc:
            errors = [str(exc)]
        if errors:
            failed = True
            print(f'FAIL {path}', file=sys.stderr)
            for error in errors:
                print(f'  {error}', file=sys.stderr)
        else:
            print(f'PASS {path} (shape + local references only; not business approval)')
    return int(failed)


if __name__ == '__main__':
    sys.exit(main())
